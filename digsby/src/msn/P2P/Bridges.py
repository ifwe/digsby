from util.packable import Packable
from util import Events
import asynchat
import socket
import random
import collections
import struct
import common
import logging

import util
import util.net as net
import util.Events as events
import util.callbacks as callbacks

log = logging.getLogger('msn.p2p.bridges')

def simplest_producer(data):
    yield data
    yield None

class Bridge(events.EventMixin):
    coolness = -1
    bridge_name = None

    def get_connecter_factory(self, serving):
        raise NotImplementedError

    def get_socket_factory(self):
        raise NotImplementedError

    def set_ips(self, addrlist):
        pass

class TcpBridge(Bridge):
    bridge_name = 'TCPv1'
    coolness = 10

    def get_connecter_factory(self, serving):
        if serving:
            return MSNTcpServer
        else:
            return MSNTcpClient

    def get_socket_factory(self):
        return MSNDirectTcpSocket

class UdpBridge(Bridge):
    coolness = 5
    bridge_name = 'TRUDPv1'

    events = Bridge.events | set((
        'on_message',
        'on_close',
        'on_error',
        'on_send',
    ))

    def __init__(self):
        pass

    def get_connecter_factory(self, serving):
        if serving:
            return MSNUdpServer
        else:
            return MSNUdpClient

    def get_socket_factory(self):
        # TODO: Return UdpBridge instance?
        def fac(connecter, data):
            log.info('udp socket factory got %r, socket = %r', connecter, connecter.socket)
            return connecter.socket

        return fac

class MSNDCSocket(common.socket, events.EventMixin):
    events = events.EventMixin.events | set((
        'on_message',
        'on_close',
        'on_error',
        'on_send',
    ))

    def __init__(self, conn, prev_data = ''):
        common.socket.__init__(self, conn)
        self.set_terminator(self.hdr_size)
        self.ac_in_buffer = prev_data
        events.EventMixin.__init__(self)
        self.data = ''
        self.getting_hdr = True

    def collect_incoming_data(self, data):
        self.data += data

    def handle_close(self):
        self.event('on_close')
        common.socket.handle_close(self)
        self.close()

    def handle_expt(self):
        self.event('on_error')
        common.socket.handle_expt(self)

    def handle_error(self, e=None):
        import traceback; traceback.print_exc()
        self.event('on_error')
        self.close()
        common.socket.handle_error(self, e)

    @property
    def localport(self):
        try:
            return self.socket.getsockname()[1]
        except:
            return 0

    def __repr__(self):
        pn = None
        try:     pn = self.socket.getpeername()
        finally: return "<%s connected to %r>" % (self.__class__.__name__,pn)

class MSNDirectUdpSocket(MSNDCSocket, common.AsyncSocket.AsyncUdpSocket):
    send_delay_base = .2
    send_delay_min  = .00001
    timeout = 45

    p2p_overhead = 68
    p2p_max_msg_size = 1384

    @property
    def send_delay(self):
        delay = self.send_delay_base
        if self._last_ack_time:
            dt_last_ack = util.default_timer() - self._last_ack_time
            delay = self.send_delay_base * dt_last_ack

            if dt_last_ack > self.timeout:
                self._do_timeout = True

        return max(self.send_delay_min, delay)

    def build_data(self, header, body, footer):
        return ''.join((header, body))

    events = MSNDCSocket.events | set((
        'on_udp_message',
    ))
    class Header(Packable):
        class Flags(object):
            SYN     = 0x00010020
            ACK     = 0x00010080
            SYN_ACK = SYN | ACK

        fmt = (
               'sender_seq',    'I',
               'recver_seq',    'I',
               'flags',         'I',
               'sender_msg_id', 'I',
               'recver_msg_id', 'I',
        )
        byteorder = "<"

    hdr_size = Header.size

    def __init__(self, conn = None):
        self._ips = None
        self._connected = False

        MSNDCSocket.__init__(self, None)
        common.AsyncSocket.AsyncUdpSocket.__init__(self, conn)
        self.re_init()

    def re_init(self, sender_seq = None):
        log.info('initializing %r', self)
        self.state = self.Header(
                                 sender_seq    = 0,
                                 recver_seq    = 0,
                                 flags         = self.Header.Flags.SYN,
                                 sender_msg_id = 0,
                                 recver_msg_id = 0,
                            )
        self._do_timeout = False
        self._current_sending = None
        self._last_send = 0
        self._next_msgid_incr = 484
        self.state.sender_seq    = sender_seq or random.randint(0, 0x7FFFFFFF)
        self.state.sender_msg_id = random.randint(0, 0x7FFFFFFF)
        self.discard_buffers()
        log.info('%r initialized. self.state = %r', self, self.state)

    def on_session_completed(self):
        self.re_init()

    def close(self):
        log.info('Closing %r', self)
        self.connected = False
        self.discard_buffers()
        common.AsyncSocket.AsyncUdpSocket.close(self)

    def _send(self, data):
        if data and self._current_sending and not self._current_sending[0][1]:
            #log.info('Got data to send, NOT clearing old non-data packet from queue')
            #self._current_sending = None
            pass

        while self.ac_out_buffer and self.ac_out_buffer[0][0] == '':
            if data:
                oldpkt = self.ac_out_buffer.pop(0)
                log.info('old packet %r will not be sent because of data: %r', oldpkt, data)
            elif data == '':
                return

        x = self.push_with_producer(net.GeneratorProducer(simplest_producer(data)))
        return x

    def set_ips(self, iplist):
        if not self._ips:
            self._ips = iplist
        else:
            raise ValueError("Can't set IPs again", self, self._ips, iplist)

    @property
    def endpoint(self):
        try:
            return self._ips[0]
        except Exception:
            return None

    def discard_buffers(self):
        self._last_ack_time = util.default_timer()
        common.AsyncSocket.AsyncUdpSocket.discard_buffers(self)

    def readable(self):
        return bool(self._ips) and common.AsyncSocket.AsyncUdpSocket.readable(self)

    def writable(self):
        if (util.default_timer()  - self._last_send) < self.send_delay:
            return False
        return bool(self._ips) and common.AsyncSocket.AsyncUdpSocket.writable(self)

    @callbacks.callsback
    def connect(self, callback = None):
        log.info('%r.connect() called', self)
        self._connect_cb = callback

        try:
            log.info('binding udp socket')
            self.socketbind(('', 0))
        except Exception, e:
            log.info('omg it broke: %r', e)
            callback.error(e)
            return
        else:
            log.info('bind worked')
            callback.success(self)
            self.on_connect()

    def getsockname(self):
        log.info('Getting socket name for %r: %r', self, self.socket.getsockname())
        return self.socket.getsockname()

    def collect_incoming_data(self, data, addr):
        if addr not in self._ips:
            log.error("Ignoring data from unexpected source %r", addr)
            return

        if len(self._ips) > 1:
            old_ips = self._ips[:]

            try:
                old_ips.remove(addr)
            except ValueError:
                pass

            self._ips[:] = [addr]
            log.info('Made initial contact with peer: %r. current_sending was: %r', addr, self._current_sending)
            while self.ac_out_buffer and self.ac_out_buffer[0][1] != self.endpoint:
                self.ac_out_buffer.pop(0)
            self._current_sending = None

        self._process_data(data, addr)

    def get_next_message_id(self, hdr):
        return hdr.sender_msg_id + self._next_msgid_incr

    def _process_data(self, _data, addr):
        hdr, data = _data
        #log.info('_process_data: hdr = %r, data = %r', hdr, data)
        self.state.recver_msg_id = hdr.sender_msg_id

        if self.state.recver_seq == 0 or \
            (self.state.recver_seq <= hdr.sender_seq and
             self.state.sender_seq <= hdr.recver_seq):
            is_new_message = True
        else:
            is_new_message = False

        self.state.recver_seq = hdr.sender_seq

        self._next_msgid_incr = 15 if self._next_msgid_incr == 16 else 16

        if is_new_message:
            self.state.flags = hdr.Flags.ACK

            if hdr.recver_seq == 0:
                self.state.flags |= hdr.flags

        self.ack_message(hdr, data)

        if not is_new_message:
            # probably just an ack of what we're sending, or it could be a retransmission
            #log.debug('Received a message again (header = %r, data = %r)', hdr, data)
            return

        self.event('on_udp_message', hdr, data)
        if data:
            self.event('on_message', data)

    def ack_message(self, hdr, data):
        if data or hdr.flags != hdr.Flags.ACK:
            self._send('')

    def close_when_done(self):
        self.close()

    def initiate_send(self):
        if self._do_timeout:
            self._do_timeout = False
            raise socket.timeout()

        if not self.ac_out_buffer:
            self.refill_buffer()

        if self._current_sending:
            (hdr, data), addr = self._current_sending
            if addr not in self._ips:
                self._current_sending = None
                return
            if not data and self.ac_out_buffer:
                self._current_sending = None
                return
        else:
            data = addr = None
            while addr not in self._ips and self.ac_out_buffer:
                data, addr = self.ac_out_buffer[0]
                if addr not in self._ips:
                    self.ac_out_buffer.pop(0)
                    data = addr = None

            if not self.ac_out_buffer:
                return

            data, addr = self.ac_out_buffer.pop(0)
            hdr = None

        if not data and self.ac_out_buffer:
            return

        if data is None:
            data = ''

        header, final_data = self.build_packet(hdr, data)

        if hdr is None:
            self._current_sending = (header, data), addr

        if not final_data:
            return

        #log.info('sendto(%r, (%r, %r))', addr, header, data)
        try:
            num_sent = self.sendto(final_data, addr)
        except socket.error, why:
            self.handle_error(why)
            return
        else:
            self._last_send = util.default_timer()

    def build_packet(self, header, data):
        if header is None:
            if data:
                self.state.sender_seq += 1
            header = self.state.copy()

        header.recver_msg_id = self.state.recver_msg_id
        header.sender_msg_id = self.state.sender_msg_id = self.get_next_message_id(header)

        #log.info('build_packet: %r + %r', header, data)
        return header, header.pack() + data

    def handle_read(self):
        if self._do_timeout:
            self._do_timeout = False
            raise socket.timeout()

        try:
            data, addr = self.recvfrom(8192)
        except socket.error, why:
            self.handle_error(why)
            return

        if not data:
            return

        header, pktdata = self.Header.unpack(data)
        #log.info('recvd  %r: %r + %r', addr, header, pktdata)
        self.check_ack(header, addr)
        self.collect_incoming_data((header, pktdata), addr)

    def check_ack(self, header, addr):
        if self._current_sending is None:
            #log.info('no current sending, but got an ack: %r (self.state = %r)', header, self.state)
#            if self.ac_out_buffer:
#                log.info('assuming ack, current_sending is None. popping %r', self.ac_out_buffer[0])
#                self.ac_out_buffer.pop(0)
#            else:
#                log.info('No current sending and no out buffer, but got an ack. producer_fifo = %r', self.producer_fifo)
            return

        (myhdr, mydata), dest = self._current_sending

        if header.flags == header.Flags.ACK:
            self.state.flags = myhdr.flags = header.flags

        if dest == addr and header.recver_seq == myhdr.sender_seq:
            # ack!
            #log.info('got ack for %r: %r', (myhdr, mydata), header)
            try:
                self.ac_out_buffer.remove((mydata, dest))
            except ValueError:
                pass

            self._last_send = 0
            self._last_ack_time = util.default_timer()
            self._current_sending = None
            self.event('on_send')
        else:
            if header.recver_seq < myhdr.sender_seq:
                #log.info('got old ack. recvd: %r, mystate: %r', header, myhdr)
                pass
            else:
                log.info('bad ack: %r != %r or (recvd %r) != (expected %r)', dest, addr, header.recver_seq, myhdr.sender_seq)

    def handle_error(self, e=None):
        import traceback; traceback.print_exc()
        self.on_error()
        self.event('on_error')
        self.close()
        common.AsyncSocket.AsyncUdpSocket.handle_error(self, e)

    def on_error(self, e=None):
        ccb, self._connect_cb = self._connect_cb, None
        if ccb is not None:
            ccb.error(e)

class MSNDirectTcpSocket(MSNDCSocket):
    hdr_size = 4
    p2p_overhead = 52
    p2p_max_msg_size = 1400

    def build_data(self, header, body, footer):
        return ''.join((struct.pack('<I', len(header) + len(body)), header, body))

    def found_terminator(self):
        data, self.data = self.data, ''
        #print 'IN2<<<',repr(data)
        self.getting_hdr = not self.getting_hdr

        if not self.getting_hdr:
            next_term, = struct.unpack('<I', data)
            #sock_in.log(15, 'Socket waiting for %d bytes', next_term)
            if next_term:
                self.set_terminator(next_term)
            else:
                self.found_terminator()
        else:
            #sock_in.info('Received %d bytes', len(data))
            #sock_in.log(5, '    MSNDCSocket Data in: %r', data[:100])
            self.set_terminator(self.hdr_size)
            self.event('on_message', data)

    def _send(self, data):
        log.log(5, '    MSNDirectTcpSocket Data out: %r', data[:100])
        real_data = struct.pack('<I', len(data)) + data
        return common.socket.push(self, real_data)

class MSNDCConnecter(events.EventMixin):
    events = events.EventMixin.events | set ((
        'timeout',
        'connected',

        'on_message',
        'on_close',
        'on_error',
        'on_send',
        'on_local_ip',
    ))

    def __init__(self, ips = ()):
        events.EventMixin.__init__(self)
        self._ips = ips

        self.data = ''

    def connect(self):
        raise NotImplementedError

    def collect_incoming_data(self, data):
        self.data += data

    def bind(self, *a, **k):
        return events.EventMixin.bind(self, *a, **k)

    @property
    def _timeout(self):
        from common import pref
        return pref('msn.direct.timeout', type=int, default=5)

    @property
    def localport(self):
        try:
            return self.socket.getsockname()[1]
        except:
            return 0

class MSNTcpServer(common.TimeoutSocket, MSNDCConnecter):
    bind = MSNDCConnecter.bind

    def __init__(self):
        common.TimeoutSocket.__init__(self, False)
        MSNDCConnecter.__init__(self, ())
        self.set_terminator(0)

    @callbacks.callsback
    def connect(self, callback=None):
        self.tryaccept(('',0), callback.success, callback.error, self._timeout)

    def cleanup(self):
        self.del_channel()
        self.close()

    def set_ips(self, ips):
        pass

class MSNTcpClient(common.HydraSocket, MSNDCConnecter):
    def __init__(self, ips = ()):
        common.HydraSocket.__init__(self)
        MSNDCConnecter.__init__(self, ips)

    @callbacks.callsback
    def connect(self, callback=None):
        self._callback = callback
        self.tryconnect(self._ips, self.connected, callback.error, self._timeout, cls=BufferedTimeoutSocket)

    def connected(self, sck):
        data = 'foo\0'
        if sck.send(struct.pack('<I', len(data)) + data) != (4+len(data)):
            sck.close()
            self.on_fail()
            log.warning('Send of "foo" failed')
            return
        else:
            log.warning ('Sent "foo"')
            self._callback(sck)

    def cleanup(self):
        pass

class MSNUdpConnecter(MSNDCConnecter):
    events = MSNDCConnecter.events | set((
        'on_message',
        'on_close',
        'on_error',
        'on_send',
        'on_local_ip',
    ))

    class Phases:
        START = 'start'
        INITIAL_CONTACT = 'initial contact'
        SYNCHRONIZE = 'sync'
        DATA = 'data'

    def __init__(self, ips = ()):
        MSNDCConnecter.__init__(self, ips)
        self._connect_cb = None

        self.socket = MSNDirectUdpSocket()
        self._waiting_for = 'start'

    def set_ips(self, iplist):
        self._ips = iplist
        self.socket.set_ips(iplist)

    @callbacks.callsback
    def connect(self, callback = None):
        self._connect_cb = callback
        self.socket.connect(success = self._on_connect, error = self._on_error)

    def _on_message(self, hdr, data):
        #log.info('got message from socket: %r, %r', hdr, data)

        initial = False
        if self._waiting_for == self.Phases.INITIAL_CONTACT:
            initial = True
            self._waiting_for = self.Phases.SYNCHRONIZE

        #log.info('_connected = %r, hdr.flags = %r, _waiting_for = %r', getattr(self, '_connected', False), hdr.flags, self._waiting_for)
        if hdr.flags & hdr.Flags.SYN and self._waiting_for == self.Phases.SYNCHRONIZE:
            if not initial:# or hdr.flags & hdr.Flags.ACK:
                self._waiting_for = self.Phases.DATA
                self._on_udp_sync()

        #log.info('_connected = %r, hdr.flags = %r, _waiting_for = %r', getattr(self, '_connected', False), hdr.flags, self._waiting_for)
        if data:
            self.event('on_message', data)

    def _on_error(self, e = None):
        ccb, self._connect_cb = self._connect_cb, None
        if ccb is not None:
            ccb.error(e)

    def attempt_contact(self):
        pass

    def _on_udp_sync(self):
        log.info('udp sync')
        self._connected = True
        self._connect_cb, ccb = None, self._connect_cb

        if ccb is not None:
            log.info('calling %r', ccb.success)
            ccb.success(self)

        self.event('connected')

    def _on_connect(self, sck):
        log.info('udp bridge on_connect. self._ips = %r, self.socket._ips = %r', self._ips, self.socket._ips)
        self.socket.bind_event('on_udp_message', self._on_message)
        self._waiting_for = self.Phases.INITIAL_CONTACT

    def _init_gen(self):
        while self._waiting_for == self.Phases.INITIAL_CONTACT:
            for addr in self._ips:
                yield '', addr

class MSNUdpClient(MSNUdpConnecter):
    def set_ips(self, iplist):
        MSNUdpConnecter.set_ips(self, iplist)
        log.info('Got ips for MSNUdpClient (%r). _waiting_for = %r', iplist, self._waiting_for)
        if self._waiting_for == self.Phases.INITIAL_CONTACT:
            self.attempt_contact()

    def _on_connect(self, sck):
        MSNUdpConnecter._on_connect(self, sck)
        self.event('on_local_ip', self, self.socket.getsockname())
        self.attempt_contact()

    def attempt_contact(self):
        #self.socket.re_init()
        for ip in self._ips:
            _header, data = self.socket.build_packet(None, '')
            self.socket.sendto(data, ip)

class MSNUdpServer(MSNUdpConnecter):
    def attempt_contact(self):
        pass

    def set_ips(self, iplist):
        MSNUdpConnecter.set_ips(self, iplist)
        log.info('Got ips for MSNUdpServer (%r). _waiting_for = %r', iplist, self._waiting_for)
        if self._waiting_for == self.Phases.INITIAL_CONTACT:
            self.attempt_contact()

class BufferedTimeoutSocket(common.TimeoutSocket):
    def __init__(self, *a, **k):
        common.TimeoutSocket.__init__(self, *a, **k)
        self.set_terminator(0)
        self._data = ''

    def collect_incoming_data(self, data):
        #print 'IN4<<<', repr(data)
        self._data += data

    def recv(self, bytes):
        if self._data:
            data, self._data = self._data[:bytes], self._data[bytes:]
        else:
            data = self.socket.recv(bytes)

        return data

    def handle_close(self):
        self.socket.close()
