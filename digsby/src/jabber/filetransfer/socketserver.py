from struct import unpack, pack
from jabber.filetransfer.S5BFileXferHandler import SocketEventMixin
import functools
import common
from socket import AF_INET, SOCK_STREAM
import AsyncoreThread
from hashlib import sha1
from functools import partial
from threading import RLock
from util import lock, get_ips_s

from logging import getLogger
log = getLogger('jabber.filetransfer.s5bserver')

class ProxyFailure(StopIteration):
    pass

def this(f):
    @functools.wraps(f)
    def wrapper1(self,*args, **kw):
        return f(self(), *args, **kw)
    return wrapper1

class JabberS5BServerSocket(common.socket):
    '''

    '''
    _this = None
    started = False
    _lock = RLock()
    bind_addr  = ('', 0)
    waiting_hashs   = []
    connected_hashs = {}

    def __init__(self, addr=None):
        '''
        @param addr: the address to bind to
        '''
        if self() is None:
            if addr is not None:
                type(self).bind_addr = ('', 0)
            common.socket.__init__(self, False)
            type(self)._this = self

    def __call__(self):
        return type(self)._this

    @this
    @lock
    def start(self):
        '''
        turns this server on, if not already
        '''

        if not self.started:
            self.started = True
            self.create_socket(AF_INET, SOCK_STREAM)
            try:
                self.bind( self.bind_addr )  # GET IP ADDRESS
            except Exception, e:
                self.log_info("failed to bind on (%r, %r)" % self.bind_addr)
                raise e
            self.listen(5)
            AsyncoreThread.start()

    @this
    @lock
    def stop(self):
        '''
        turns this server off, if not already
        '''

        if self.started:
            self.started = False
            self.close()

#    @this  can't be called anywhere else
    def handle_accept(self):
        '''
        handle incoming connection, calls _on_accept with the new socket
        and its address
        '''

        log.info('handle_accept')
        accepted = self.accept()
        self.listen(5)
        connected_socket, address = accepted

        self._on_accept(connected_socket, address)

#    @this  can't be called anywhere else
    def _on_accept(self, sock, addr):
        '''
        function called when a new
        @param sock:
        @param addr:
        '''

        log.info("accept from (%r, %r)", sock, addr)
        S5BIncomingSocket(sock, addr, self)

#    @this  doesn't require self
    def conn_id(self, stream_id, initiator_jid, target_sid):
        '''
        creates the connection id used in Jabber SOCKS 5 Bytestream connections
        @param stream_id:  the stream id (a string)
        @param initiator_jid: the stream initiator JID
        @param target_sid:    the stream target JID
        '''

        return sha1(stream_id + initiator_jid.as_unicode() + target_sid.as_unicode()).hexdigest()

    @this
    def __del__(self):
        self.stop()
        superdel = getattr(common.socket, '__del__', None)
        if superdel is not None:
            superdel(self)

    @this
    @lock
    def add_hash(self, hash):
        '''
        append the hash to the list of connection ids that we expect
        to be incomming
        @param hash: the expected connection id
        '''

        log.info('adding hash: %s', hash)
        self.waiting_hashs.append(hash)
        if not self.started: self.start()

    @this
    @lock
    def hash_waiting(self, hash, conn):
        '''
        this function stores a new connection by connection id
        when the connection has finished socks5 negotiation

        @param hash: the connection id
        @param conn: the S5Bserver instance
        '''

        log.info('waiting hash: %s', hash)
        self.waiting_hashs.remove(hash)
        if not self.waiting_hashs:
            self.stop()
        self.connected_hashs[hash] = conn

    @this
    @lock
    def check_hash(self, hash):
        return hash in self.connected_hashs

    @this
    @lock
    def retrieve_hash(self, hash):
        '''
        @param hash: the connection id to retrieve

        @return False if we are still waiting for the hash
                None  if we know nothing about it
                the S5Bserver: if everything is ok
        '''

        log.info('retrieving hash: %s', hash)
        if hash in self.connected_hashs:
            return self.connected_hashs.pop(hash)
        else:
            try:
                self.waiting_hashs.remove(hash)
                return False
            except ValueError:
                return None
            finally:
                if not self.waiting_hashs:
                    self.stop()

    #CAS: fix this to return values from the socket
    @property
    @this
    def hosts(self):
        '''
        a list of (host, port) that we are bound to.
        '''
        port = self.socket.getsockname()[1]
        return [(ip, port) for ip in get_ips_s()]

class S5BIncomingSocket(common.socket, SocketEventMixin):
    '''
    handle an incoming socks5 request

    '''
    def __init__(self, sock, addr, server):
        SocketEventMixin.__init__(self)
        common.socket.__init__(self, sock)
        self.server = server
        self.data = None
        self.proc( self.s5b_ok() )

    def s5b_ok(self):
        '''
        input and output for the jabber socks5 process.
        '''

        greeting = yield (2, None)

        _head, num_authmethods = unpack('BB', greeting)
        methods = yield(num_authmethods, '')
        authmethods = unpack('%dB' % num_authmethods, methods)

        if 0 not in authmethods:
            yield (0, pack('BB', 0x05, 0xFF))
            raise ProxyFailure('bad auth methods')
        else:
            auth = yield (4, pack('BB', 0x05, 0x00))

        _head, tcp, reserved, type_ = unpack('4B', auth)

        if not _head == 0x05 and tcp == 0x01 \
         and reserved == 0x00 and type_ == 0x03:
            raise ProxyFailure('bad address header')

        (len_,) = unpack('B', (yield (1, '')))
        addr, _port = unpack('%dsH' % len_, (yield (len_ + 2, '')))
        self.hash = addr

        if self.server.check_hash(self.hash):
            raise ProxyFailure('hash already connected')

        #HAX: oh, check more stuff, but I just want it to work!
        #hack:
#        send 0x05
#        send 0x00 (good status)
#        senc 0x00 reserved
#        send 0x02 address type
#        send pascal address
#        send 0x0000 port number
        self.collect_incoming_data = lambda _data: None

        strng = pack('=4B%dpH' % (len_+1,), 5,0,0,3,addr,0)
        yield (False, strng)

    def proc(self, gen):
        '''
        process s5b_ok
        continue untill the generator is exhausted

        upon success, the retrieved hash is added to those waiting for more info
        @param gen:
        '''

        try:
            to_read, out_bytes = gen.send(self.data)
        except ProxyFailure:
            self.close()
            return
        except StopIteration:
            try:
                self.handle_expt = self.post_connect_expt
                self.handle_error = self.post_connect_error
                self.handle_close = self.post_connect_close
                self.do_disconnect = self.post_connect_disconnect
                self.server.hash_waiting(self.hash, self)
            except ValueError:
                self.close()
            return
        bytes = str(out_bytes)
        print 'out_bytes', out_bytes, 'bytes', bytes
        if out_bytes:
            self.push(bytes)
        self.data = ''
        self.found_terminator = partial(self.proc, gen)

        if to_read is False:
            log.info('found to_read is False, generator exhausted')
            self.found_terminator = lambda: None
            self.collect_incoming_data = lambda _data: None
            self.set_terminator(0)
            try:
                self.handle_expt = self.post_connect_expt
                self.handle_error = self.post_connect_error
                self.handle_close = self.post_connect_close
                self.do_disconnect = self.post_connect_disconnect
                self.server.hash_waiting(self.hash, self)
            except ValueError:
                self.close()
        elif isinstance(to_read, int):
            self.set_terminator(to_read)
        else:
            self.set_terminator(to_read._size())

    def collect_incoming_data(self, data):
        self.data += data

    def __del__(self):
        self.close()
        common.socket.__del__(self)
