from struct import unpack
from jabber.filetransfer.S5BFileXferHandler import SocketEventMixin
import util
import util.primitives.structures as structures
from struct import pack
from jabber.filetransfer.socketserver import ProxyFailure
import common
from functools import partial
from logging import getLogger

log = getLogger('S5B_proxyConnect')


class S5B_proxyConnect(common.socket, SocketEventMixin):
    """Is a 'Socks 5 Bytestream' Outgoing connection."""
    def __init__(self, addr, hash, streamhost):
        SocketEventMixin.__init__(self)
        self.handle_expt = self.post_connect_expt
        self.handle_error = self.post_connect_error
        self.handle_close = self.post_connect_close
        self.do_disconnect = self.post_connect_disconnect
        self.addr = addr
        self.hash = hash
        self.streamhost = streamhost
        self.data = None
        common.socket.__init__(self)

    def get_connect(self):
        self.connect(self.addr)

    def handle_connect(self):
        """start the generator"""
        log.info('connect to %s', self.addr)
        self.proc( self.s5b_ok() )

    def collect_incoming_data(self, data):
        if not self.data:
            self.data = data
        else:
            self.data += data

    def s5b_ok(self):
        """generator conversation for S5B socket 'proxy' bytes.
        This is necessary because it must be done first, and must be done quickly.
        This function is really part of the socket setup, not part of the
        data which flows across."""
        ok = yield (2, pack('BBB', 5,1,0))
        _head, authmethod = unpack('BB', ok)

        if authmethod != 0x00:
            raise ProxyFailure()

        out = pack('!BBBBB40sH', 5,1,0,3, 40,self.hash,0)
        in_fmt = ('!BBBB', 's5head', 'status', 'reserved', 'addrtype')
        in_ = yield (4, out)
        head = structures.unpack_named(*(in_fmt+ (in_,)))
        if head.addrtype == 3:
            head.addrlen = yield (1, '')
            head.addrlen = ord(head.addrlen)
            if head.addrlen > 0:
                address = yield (head.addrlen, '') #@UnusedVariable
            else:
                address = '' #@UnusedVariable
        _port =  yield (2, '')
        if head.status != 0x00:
            raise ProxyFailure()
        log.info('proxy ok, calling on_success')
        self.event("connected")

    def proc(self, gen):
        """This method runs the s5b_ok generator."""
        try:
            to_read, out_bytes = gen.send(self.data)
        except ProxyFailure:
            self.close()
            self.event("connection_failed")
            return
        except StopIteration:
            return
        except:
            pass
        bytes = str(out_bytes)
        if out_bytes:
            self.push(bytes)
        self.data = ''
        self.found_terminator = partial(self.proc, gen)
        if isinstance(to_read, int):
            self.set_terminator(to_read)
        else:
            self.set_terminator(to_read._size())
