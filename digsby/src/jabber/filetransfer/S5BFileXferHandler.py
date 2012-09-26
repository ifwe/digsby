from jabber.objects.si_filetransfer import SI_FileTransfer
from util.Events import EventMixin
from pyxmpp.expdict import ExpiringDictionary
from common.timeoutsocket import TimeoutSocketMulti
from util.net import SocketEventMixin
import common
import util.primitives.structures as structures
from struct import pack, unpack
from functools import partial
from jabber.objects.si import SI_NS
from jabber.objects.bytestreams import BYTESTREAMS_NS, ByteStreams
from hashlib import sha1
from pyxmpp.jid import JID
from pyxmpp.iq import Iq

import logging


class ProxyFailure(StopIteration):
    pass

class ByteStream(EventMixin):
    '''
    A set of events to be implemented by a any sort of ByteStream.
    Right now there is only the socks5 stuff, but we may attempt other kinds
    of streams in the future.  They may not all (probably not all) use sockets
    so events are used to indicate when things happen (including data arriving).
    '''
    events = EventMixin.events | set(("stream_connected",
                                      "stream_connect_failed",
                                      "stream_rejected",
                                      "stream_data_recieved",
                                      "stream_closed",
                                      "stream_error",
                                      ))

class INByteStream(ByteStream):
    '''
    common class for incoming bytestreams
    '''
    def __init__(self, si_ft, jabber_protocol):
        ByteStream.__init__(self)
        self.si_ft  = si_ft
        self.j      = jabber_protocol

class SOCKS5Bytestream(INByteStream):
    log = logging.getLogger('jabber.filetrans.s5bxferhandler')

    def accept_stream(self, hosts_bytestreams, from_, to_, id):
        self.from_ = from_
        self.to_   = to_
        self.respond_id = id
        self.hosts_bytestreams = hosts_bytestreams
        #print str(hosts_bytestreams)
        self.my_sock = S5BOutgoingSocket(hosts_bytestreams, from_, to_)
        self.my_sock.bind_event("connected", self.on_succ)
        self.my_sock.bind_event("connection_failed", self.on_fail)
        self.my_sock.get_connect()

    def on_fail(self):
        self.log.warning("S5BFileXferHandler connect failed")
        i = Iq(to_jid=self.from_, from_jid = self.to_, stanza_type="error", stanza_id = self.respond_id,
               error_cond=u"item-not-found")
        self.j.send(i)
        self.event("stream_connect_failed")

    def on_succ(self, num_tries_taken, sock):
        host_used = self.hosts_bytestreams.hosts[num_tries_taken-1].jid
        self.my_sock = sock

        i2 = Iq(to_jid=self.from_, stanza_type="result", stanza_id = self.respond_id)

        b = ByteStreams()
        b.host_used = JID(host_used)
        b.as_xml(i2.get_node())

        self.my_sock.found_terminator = self.close
        self.my_sock.collect_incoming_data = self.collect_incoming_data
        self.my_sock.set_terminator(self.si_ft.file.size)
        self.my_sock.bind_event("socket_closed", self.closed)
        self.my_sock.bind_event("socket_error", self.stream_error)

        self.j.send(i2)
        self.log.info("S5BFileXferHandler connect succeeded to %s", host_used)
        self.event("stream_connected")

    def stream_error(self):
        self.event("stream_error")
        self.unbind_all()

    def collect_incoming_data(self, data):
        self.event("stream_data_recieved", data)

    def close(self):
        #if my_sock doesn't exist, we probably haven't accepted the stream yet
        try:
            self.my_sock.close()
        except:
            pass
        self.closed()

    def timed_out(self):
        self.event("stream_connect_failed")
        self.close()

    def closed(self):
        self.event("stream_closed")
        self.unbind_all()

    def unbind_all(self):
        if hasattr(self, 'my_sock'):
            self.my_sock.unbind("connected", self.on_succ)
            self.my_sock.unbind("connection_failed", self.on_fail)
            self.my_sock.unbind("socket_closed", self.closed)
            self.my_sock.unbind("socket_error", self.stream_error)


class S5BRecvHandler(object):
    def __init__(self, j):
        self.d = ExpiringDictionary(60)
        self.j = j

    def register_handlers(self):
        '''
        register so that we'll get incomming s5b requests.
        '''
        self.j.stream.set_iq_set_handler('query',BYTESTREAMS_NS,
                                         self.handleSI)
        self.j.idle_loop += self.d.expire

    def handleSI(self, stanza):
        '''
        someone wants to open a stream with us
        '''
        print 'handleSI called'
        b = ByteStreams(stanza.get_query())
        sid = b.sid
        try:
            s5b = self.d.pop(sid)
        except KeyError:
            return False
        else:
            s5b.accept_stream(b, stanza.get_from(), stanza.get_to(), stanza.get_id())
            return True

    def waitfor(self, stanza):
        '''
        add a new stream to those we're looking for.
        '''
        si_ft = SI_FileTransfer(stanza.xpath_eval('si:si',{'si':SI_NS})[0])
        print 'waiting for stream for ', si_ft
        s5b = SOCKS5Bytestream(si_ft, self.j)
        self.d.set_item(si_ft.sid,s5b,timeout_callback=s5b.timed_out)
        return s5b

    __call__ = waitfor

#make socket subclass that can fit into timeoutsocket
#makc S5BOutgoingSocket return a socket at the end, and the higher up
#should grab the socket from it and inject into the position S5BOutgoingSocket
#occupies now.

class S5BOutgoingSocketOne(common.TimeoutSocketOne, SocketEventMixin):
    def __init__(self, *a, **k):
        SocketEventMixin.__init__(self)
        common.TimeoutSocketOne.__init__(self, *a, **k)

    def succ(self):
        '''
        successful connection, now see if the proxy stuff will connect
        '''
        self.proc( self.s5b_ok() )

    def s5b_ok(self):
        ok = yield (2, pack('BBB', 5,1,0))

        _head, authmethod = unpack('BB', ok)

        if authmethod != 0x00:
            raise ProxyFailure()

        out = pack('!BBBBB40sH', 0x05, 0x01, 0, 3, 40, self.hash, 0)

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

    def proc(self, gen):
        try:
            to_read, out_bytes = gen.send(self.data)
        except ProxyFailure:
            return self.do_fail()
        except StopIteration:
            return common.TimeoutSocketOne.succ(self)
        bytes = str(out_bytes)
        if out_bytes:
            self.push(bytes)
        self.data = ''
        self.found_terminator = partial(self.proc, gen)
        if isinstance(to_read, int):
            self.set_terminator(to_read)
        else:
            self.set_terminator(to_read._size())

class S5BOutgoingSocket(SocketEventMixin):
    '''

    '''
    def __init__(self, hosts_bytestreams, from_, to_):
        SocketEventMixin.__init__(self)
        self.log = logging.getLogger('S5BOutgoingSocket')
        self.log.warning('S5BOutgoingSocket')

        shosts = hosts_bytestreams.hosts
        self.addys = [(host.host, host.port) for host in shosts]
        self.sid = hosts_bytestreams.sid
        self.hash = sha1(self.sid + from_.as_utf8() + to_.as_utf8()).hexdigest()

        self.t = TimeoutSocketMulti()

        self._on_failure = lambda: self.event("connection_failed")

    def provide_data(self, sock):
        sock.hash = self.hash

    def connected(self, sock):
        '''
        pass the socket up to the SOCKS5Bytestream waiting for it
        '''
        sock.reassign()
        self.sock = sock
        self.event("connected", self.t.attempts, sock)

    def get_connect(self):
        self.t.tryconnect(self.addys, self.connected, self._on_failure,
                          2, cls=S5BOutgoingSocketOne, provide_init=self.provide_data)


