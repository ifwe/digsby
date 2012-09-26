from threading import currentThread
import collections
import socket, errno

import warnings

from socket import _socket as socket # original python socket module

import threading
import AsyncoreThread
import util
from util.primitives.synchronization import lock as util_lock
import traceback,sys

import logging

log = logging.getLogger('AsyncSocket')

from asynchat import async_chat as _async_chat, find_prefix_at_end
from asyncore import compact_traceback

import asyncore
_ok_errors = set((asyncore.EINPROGRESS, asyncore.EALREADY, asyncore.EWOULDBLOCK))

class async_chat(_async_chat):
    def connect(self, address):
        #
        # overridden from asyncore.py in the standard library
        # for the errorcode.get below--so that socket errors
        # do not result in KeyErrors
        #
        self.connected = False
        err = self.socket.connect_ex(address)
        # XXX Should interpret Winsock return values
        if err in _ok_errors:
            return
        if err in (0, asyncore.EISCONN):
            self.addr = address
            self.handle_connect_event()
        else:
            raise socket.error, (err, asyncore.errorcode.get(err, 'unknown'))

    def recv(self, buffer_size):
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                # a closed connection is indicated by signaling
                # a read condition, and having recv() return 0.
                self.handle_close()
                return ''
            else:
                return data
        except socket.error, why:
            if why.args[0] == errno.EWOULDBLOCK:
                pass
            # winsock sometimes throws ENOTCONN
            elif why.args[0] in [errno.ECONNRESET, errno.ENOTCONN, errno.ESHUTDOWN, errno.ECONNABORTED]:
                self.handle_close()
                return ''
            else:
                raise


    def handle_read(self):
        try:
            data = self.recv (self.ac_in_buffer_size)
        except socket.error, why:
            self.handle_error(why)
            return

        if data:
            self.process_data(data)

    def process_data(self, data):
        self.ac_in_buffer = self.ac_in_buffer + data

        # Continue to search for self.terminator in self.ac_in_buffer,
        # while calling self.collect_incoming_data.  The while loop
        # is necessary because we might read several data+terminator
        # combos with a single recv(1024).

        while self.ac_in_buffer:
            lb = len(self.ac_in_buffer)
            terminator = self.get_terminator()
            if not terminator:
                # no terminator, collect it all
                self.collect_incoming_data (self.ac_in_buffer)
                self.ac_in_buffer = ''
            elif isinstance(terminator, int) or isinstance(terminator, long):
                # numeric terminator
                n = terminator
                if lb < n:
                    self.collect_incoming_data (self.ac_in_buffer)
                    self.ac_in_buffer = ''
                    self.terminator = self.terminator - lb
                else:
                    self.collect_incoming_data (self.ac_in_buffer[:n])
                    self.ac_in_buffer = self.ac_in_buffer[n:]
                    self.terminator = 0
                    self.found_terminator()
            else:
                # 3 cases:
                # 1) end of buffer matches terminator exactly:
                #    collect data, transition
                # 2) end of buffer matches some prefix:
                #    collect data to the prefix
                # 3) end of buffer does not match any prefix:
                #    collect data
                terminator_len = len(terminator)
                index = self.ac_in_buffer.find(terminator)
                if index != -1:
                    # we found the terminator
                    if index > 0:
                        # don't bother reporting the empty string (source of subtle bugs)
                        self.collect_incoming_data (self.ac_in_buffer[:index])
                    self.ac_in_buffer = self.ac_in_buffer[index+terminator_len:]
                    # This does the Right Thing if the terminator is changed here.
                    self.found_terminator()
                else:
                    # check for a prefix of the terminator
                    index = find_prefix_at_end (self.ac_in_buffer, terminator)
                    if index:
                        if index != lb:
                            # we found a prefix, collect up to the prefix
                            self.collect_incoming_data (self.ac_in_buffer[:-index])
                            self.ac_in_buffer = self.ac_in_buffer[-index:]
                        break
                    else:
                        # no prefix, collect it all
                        self.collect_incoming_data (self.ac_in_buffer)
                        self.ac_in_buffer = ''

class AsyncSocket(object, async_chat):

    def __init__(self, conn = None, family = socket.AF_INET, type = socket.SOCK_STREAM):
        '''
        conn: an existing socket, None (to create a new socket), or False (no socket provided but don't make one yet)
        family and type default to TCP/IP. Changing them only matters if you don't provide a connection (i.e. it is None).
        '''
        object.__init__(self)
        self._lock = threading.RLock()
        self.__refcount = 0
        self._proxy_setup = False
        self.__proxysocket = None
        self._handlers = []
        self.data = ''

        self.family = family
        self.type = type
        if conn is False:  #do not use/make a socket at this time
            async_chat.__init__(self)
            self.__refcount += 1
            AsyncoreThread.start()
        else:
            if conn is None: #make a socket
                async_chat.__init__(self)
                self.make_socket(family = family, type = type)
            else:              #use an existing socket
                async_chat.__init__(self, conn)
                self.__refcount += 1
                AsyncoreThread.start()

    @util_lock
    def make_socket(self, proxy=True, family = socket.AF_INET, type = socket.SOCK_STREAM):
        if getattr(self, '_fileno',  None) is not None:
            self.del_channel()

        if proxy:
            proxy = util.GetProxyInfo()

        self.create_socket(family, type)
        self.__refcount += 1
        AsyncoreThread.start()

    def bind(self, addr):
        retval = self.socket.bind(addr)
        self.addr = self.socket.getsockname()
        return retval

    socketbind = bind

    def log_info(self, message, type='info'):
        """
        Print fancy error messages, since asyncore ruins them for us.
        """

        if __debug__ or type != 'info':
            etype = sys.exc_info()[0]
            if etype is not None:
                traceback.print_exc()

    @util.callsback
    def connect(self, address, use_proxy = True, callback = None):

        if not (self.family == socket.AF_INET and self.type == socket.SOCK_STREAM):
            use_proxy = False

        if use_proxy:
            proxyinfo = self.GetProxyInfo()
        else:
            proxyinfo = {}

        log.info('asyncsocket.connect%r', address)
        if isinstance(self, ProxySocket):
            log.info('\t\twas already a proxy socket')
            old_error, callback.error = callback.error, lambda : (self.handle_close(), old_error())
            async_chat.connect(self, address)
        else:
            if not self._proxy_setup and proxyinfo:
                log.info('\t\tneed to setup proxies')
                sck = self.socket
                self.del_channel()
                psck = ProxySocket(proxyinfo, sck, self.set_socket)
                self.__proxysocket = psck

                import common
                if common.pref('socket.retry_noproxy', type = bool, default = sys.DEV):
                    def retry_noproxy(*a):
                        log.info("Retry no proxy: %r", self)
                        self.__proxysocket = None
                        self.make_socket(proxy = False, family = self.family, type = self.type)
                        AsyncSocket.connect(self, address, use_proxy = False, callback = callback)

                    psck.connect(address, success = callback.success, error = retry_noproxy)
                else:
                    psck.connect(address, callback = callback)
            elif self._proxy_setup:
                log.info('\t\tproxy was already setup, calling handle_connect')
                self.handle_connect_event()
            elif not proxyinfo:
                log.info('\t\tno proxy neecessary')
                self._proxy_setup = True
                AsyncoreThread.call_later(lambda: async_chat.connect(self, address), callback = callback, verbose = False)
            else:
                log.info('\t\terrr you didnt finish')
                pass

    def set_socket(self, sock, map = None):
        async_chat.set_socket(self, sock, map)
        return self

    def GetProxyInfo(self):
        return util.GetProxyInfo()

    def close(self):
        def _doit():
            log.info('closing socket %r', self)
            psck = self.__proxysocket
            if psck is not None:
                log.info('Closing proxy socket: %r', psck)
                psck.close()
            self.__proxysocket = None
            async_chat.close(self)

        AsyncoreThread.call_later(_doit)

    def close_when_done(self):
        AsyncoreThread.call_later(lambda: async_chat.close_when_done(self))

    def collect_incoming_data(self, data):
        self.data += data

    def push_handler(self, h):
        self._handlers.append(h)

    def pop_handler(self):
        self._handlers.pop()

    def found_terminator(self):
        data, self.data = self.data, ''

        return self.handle_data(data)

    def handle_data(self, data):
        if self._handlers:
            return self._handlers[-1](data)
        else:
            return data

    def handle_close(self):
        while self._handlers:
            self.pop_handler()

    def handle_expt(self):
        log.critical('%r: handle_expt (OOB data)...closing', self)
        self.close()


    def handle_error(self, e=None):
        #
        # overridden from asyncore.py in the standard library
        # to allow exception objects to passed here
        #

        nil, t, v, tbinfo = compact_traceback()

        # sometimes a user repr method will crash.
        try:
            self_repr = repr(self)
        except:
            self_repr = '<__repr__(self) failed for object at %0x>' % id(self)

        self.log_info(
            'uncaptured python exception, closing channel %s (%s:%s %s)' % (
                self_repr,
                t,
                v,
                tbinfo
                ),
            'error'
            )
        self.close()

    def _repr(self):
        'extra repr string for use by subclasses'
        return ""

    def __repr__(self):
        try:
            sock = self.socket.getsockname()
        except Exception:
            sock = 'ERROR'
        else:
            sock = '%s:%s' % sock
        try:
            peer = self.socket.getpeername()
        except Exception:
            peer = 'ERROR'
        else:
            peer = '%s:%s' % peer
        return '<%s %s->%s r:%s w:%s %s at 0x%08X>' % (type(self).__name__, sock, peer, self.readable(), self.writable(), self._repr(), id(self))


class AsyncServer(AsyncSocket):
    SocketClass = AsyncSocket
    def __init__(self):
        super(AsyncServer, self).__init__()
        self.socket = None

    def bind(self, host = '', port = 0):
        self._hostport = (host, port)
        self.make_socket(proxy = False)
        super(AsyncServer, self).bind(self._hostport)
        return self.getsockname()

    def getsockname(self):
        return self.socket.getsockname()

    def handle_accept(self):
        accepted = self.accept()
        if accepted is None:
            return

        conn, address = accepted
        sck = self.SocketClass(conn)
        sck.handle_connect_event()

        return sck

from proxysockets import ProxySocket

class AsyncUdpSocket(AsyncSocket):
    def __init__(self, conn = None, family = socket.AF_INET, type = socket.SOCK_DGRAM):
        AsyncSocket.__init__(self, conn, family, type)
        self.connected = False
        self.discard_buffers()

    def on_connect(self):
        if self.connected:
            return
        self.handle_connect_event()

    def make_socket(self, proxy=False, family = socket.AF_INET, type = socket.SOCK_DGRAM):
        return AsyncSocket.make_socket(self, proxy, family, type)

    def sendto(self, data, addr):
        if not data:
            return

        try:
            result = self.socket.sendto(data, addr)
            return result
        except socket.error, why:
            if why[0] == errno.EWOULDBLOCK:
                return 0
            else:
                raise
            return 0

    def recvfrom(self, buffer_size):
        data, addr = '', ('', 0)
        try:
            data, addr = self.socket.recvfrom(buffer_size)
        except socket.error, why:
            if why[0] in (errno.ECONNRESET, errno.EWOULDBLOCK):
                pass
            elif why[0] in (errno.ENOTCONN, errno.ESHUTDOWN):
                self.handle_close()
            else:
                raise

        return data, addr

    def handle_read(self):
        try:
            data, addr = self.recvfrom(self.ac_in_buffer_size)
        except socket.error, why:
            self.handle_error(why)
            return

        if data:
            self.collect_incoming_data(data, addr)

    def push_with_producer(self, prod):
        if type(prod) is str:
            raise TypeError()
        AsyncSocket.push_with_producer(self, prod)

    def push(self, prod):
        if type(prod) is str:
            raise TypeError()
        AsyncSocket.push(self, prod)

    def refill_buffer(self):
        while self.producer_fifo and self.connected:
            first = self.producer_fifo.popleft()
            if not first:
                # handle empty string/buffer or None
                data, addr = first, ('', 0)
            elif isinstance(first, tuple):
                data, addr = first
            else:
                # a producer. this branch will return or continue the loop.
                from_prod = first.more()
                if isinstance(from_prod, tuple):
                    data, addr = from_prod
                else:
                    data, addr = from_prod, self.endpoint

                if data is None:
                    # producer finished
                    pass
                elif data is sentinel:
                    # producer has no data now, but might later.
                    self.producer_fifo.appendleft(first)
                    return
                else:
                    # data is (should be) a string, put it on the front of the queue and go around again
                    self.producer_fifo.appendleft(first)
                    self.producer_fifo.appendleft((data, addr))
                continue

            if data is None:
                self.handle_close()
                return
            else:
                # Got some data for the buffer. We can leave now.
                self.ac_out_buffer.append((data, addr))
                return

    def initiate_send(self):
        if not self.ac_out_buffer:
            self.refill_buffer()

        if not self.ac_out_buffer:
            return

        # send the data
        try:
            num_sent = self.sendto(*self.ac_out_buffer[0])
        except socket.error, e:
            self.handle_error(e)
            return
        else:
            if num_sent:
                del self.ac_out_buffer[0]

    def discard_buffers(self):
        self.ac_in_buffer = []
        self.ac_out_buffer = []

        while self.producer_fifo:
            self.producer_fifo.popleft()

    def readable (self):
        "predicate for inclusion in the readable for select()"
        return self.connected

    def writable (self):
        "predicate for inclusion in the writable for select()"
        # return len(self.ac_out_buffer) or len(self.producer_fifo) or (not self.connected)
        # this is about twice as fast, though not as clear.
        return not (
                (len(self.ac_out_buffer) == 0) and
                (len(self.producer_fifo) == 0) and
                self.connected
                )

