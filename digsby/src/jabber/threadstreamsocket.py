from asynchat import async_chat
from util.threads.threadpool2 import threaded
from common import netcall
from util.callbacks import callsback

from common import pref

import sys
import socket
import logging
import common

from util.primitives.synchronization import lock
from util.primitives.funcs import get

try:
    import M2Crypto
    if M2Crypto.version_info < (0, 16):
        tls_available = 0
    else:
        from M2Crypto import SSL
        from M2Crypto.SSL import SSLError
        import M2Crypto.SSL.cb
        tls_available = 1
        SSL_ERROR_WANT_WRITE = SSL.m2.ssl_error_want_write
        SSL_ERROR_WANT_READ = SSL.m2.ssl_error_want_read
except ImportError:
    tls_available = 0


class ThreadStreamSocket(common.socket):

    ac_in_buffer_size       = 4096 * 16
    ac_out_buffer_size      = 4096 * 16

    def __init__(self, sock, collect, term, on_close, on_error, ssl=False):
        self.term = term
        self.tls = None if not ssl else sock
        self.collect_incoming_data = collect
        self.set_terminator(self.term)
        self.__logger=logging.getLogger("ThreadStreamSocket")
        self.on_close = on_close
        self.on_error = on_error
        self.killed   = False
        self.lastbuffer = ''
        self.__want_write = False
        self.__want_read  = False
        common.socket.__init__(self, sock)

    def found_terminator(self):
        self.set_terminator(self.term)

    def handle_error(self, e=None):
        import traceback;traceback.print_exc()
        t, v = sys.exc_info()[:2]
        if t is not None:
            msg = get(get(v.args, 0, 'say what?'), 'message', '')
            if msg.startswith('bad write retry'):
                assert False
                self.__logger.error('Got that weird-ass "bad write retry" message in jabber socket')
#                return

        sslzero_closes = pref('jabber.ssl_error_zero.should_close', type = bool, default = True)
        if t is SSLError and get(v.args, 0, sentinel) == 0:
            self.__logger('SSL error 0!')
            if not sslzero_closes:
                self.__logger('\tnot closing')
                return

        self.__logger.debug('handle_error in %r', self)
        async_chat.close(self)
        if not self.killed:
            self.killed = True
            self.on_error()


    def handle_close(self):
        self.__logger.debug('handle_close in %r', self)
        async_chat.close(self)
        if not self.killed:
            self.killed = True
            self.on_close()

    @lock
    @callsback
    def make_tls(self, ctx, callback=None):
        self._realfileno = self._fileno

        self.socket.setblocking(True)
        self.del_channel()
        dbg = self.__logger.debug

        def blocking_connect():
            try:
                dbg("Creating TLS connection")
                self.tls = SSL.Connection(ctx, self.socket)
                dbg("Setting up TLS connection")
                self.tls.setup_ssl()
                dbg("Setting TLS connect state")
                self.tls.set_connect_state()
                dbg("Starting TLS handshake")
                # self.tls.setblocking(True)
                self.tls.connect_ssl()
                self.socket.setblocking(False)
                self.tls.setblocking(False)
                self.ssocket = self.socket
                self.socket = self.tls
            except Exception, e:
                try:
                    self.socket.close()
                    self.tls.close()
                    dbg('There was an exception in TLS blocking_connect: %r', e)
                except Exception:
                    pass
                raise e

        def win():
            self._fileno = self._realfileno
            self.add_channel()
            callback.success()

        def lose(e):
            netcall(callback.error)

        threaded(blocking_connect)(success = lambda: netcall(win), error=lose)

    def recv(self, buffer_size=4096):
        self.__want_read = False
        try:
            return common.socket.recv(self, buffer_size)
        except SSLError, e:
            if e.args[0] == SSL_ERROR_WANT_WRITE:
                self.__want_write = True
                self.__want_read  = False
                self.__logger.warning("read_want_write")
                return ""
            elif e.args[0] == SSL_ERROR_WANT_READ:
                self.__want_write = False
                self.__want_read  = True
                self.__logger.warning("read_want_read")
                return ""
            else:
                raise socket.error(e)

    def send(self, buffer):
        self.__want_write = False
#        buffer = str(buffer)

        if self.tls is None:
            return common.socket.send(self, buffer)

##        # M2Crypto returns -1 to mean "retry the last write." It has the
##        # strange requirement that exactly the same bytes are tried again
##        # during the next write--so we need to keep our own buffer.
        r = None
        if not self.lastbuffer:
            try:
                r = self.socket.sendall(buffer)
            except SSLError, e:
                if e.args[0] == SSL_ERROR_WANT_WRITE:
                    self.__want_write = True
                    self.__want_read  = False
                    self.__logger.warning("write_want_write")
                    self.lastbuffer = buffer # -1: store the bytes for later
                    return len(buffer)       # consume from asyncore
                elif e.args[0] == SSL_ERROR_WANT_READ:
                    self.__want_write = False
                    self.__want_read  = True
                    self.__logger.warning("write_want_read")
                    return 0
                else:
                    raise socket.error(e, r)
            else:
                if r < 0:
                    raise socket.error('unknown -1 for ssl send')
                return r
        else:
            try:
                # we've got saved bytes--send them first.
                r = self.socket.sendall(self.lastbuffer)
            except SSLError, e:
                if e.args[0] == SSL_ERROR_WANT_WRITE:
                    self.__want_write = True
                    self.__want_read  = False
                    self.__logger.warning("write_want_write (buffer)")
                elif e.args[0] == SSL_ERROR_WANT_READ:
                    self.__want_write = False
                    self.__want_read  = True
                    self.__logger.warning("write_want_read (buffer)")
                else:
                    raise socket.error(e, r)
            else:
                if r < 0:
                    raise socket.error('unknown -1 for ssl send (buffer)')
                elif r < len(self.lastbuffer):
                    self.lastbuffer = self.lastbuffer[r:]
                else:
                    self.lastbuffer = ''
            return 0

    def initiate_send(self):
        #if there's nothing else in the socket buffer, the super class initiate_send won't call send
        # and self.lastbuffer won't be flushed.
        if self.lastbuffer:
            assert self.tls is not None
            assert self.__want_write
            self.send(None)
            return
        return common.socket.initiate_send(self)

    def readable (self):
        "predicate for inclusion in the readable for select()"
        assert not (self.__want_read and self.__want_write)
        return not self.__want_write and (self.__want_read or
                                          common.socket.readable(self))# and not self.lastbuffer

    def writable (self):
        assert not (self.__want_read and self.__want_write)
        "predicate for inclusion in the writable for select()"
        # return len(self.ac_out_buffer) or len(self.producer_fifo) or (not self.connected)
        # this is about twice as fast, though not as clear.
        return (common.socket.writable(self) #async buffer + connection
               or self.lastbuffer            #out buffer
               or self.__want_write) and not self.__want_read

    def _repr(self):
        return 'wr:%s ww:%s lb:%s' % (self.__want_read, self.__want_write, self.lastbuffer)


class ThreadStreamSSLSocket(common.socket):
    def __init__(self, sock, collect, term):
        self.collect_incoming_data = collect
        self.set_terminator(term)
        self.__logger = logging.getLogger("ThreadStreamSSLSocket")
        common.socket.__init__(self, sock)



