'''
Logic for establishing OSCAR p2p connections.

(follows the model outlined in U{http://gaim.sourceforge.net/summerofcode/jonathan/ft_doc.pdf})

Rendezvous messages used to negotiate the connection travel over the normal
OSCAR socket and are assembled in the send_ch2request function below.
'''

from util import autoassign, removedupes, myip, ip_from_bytes
from util.observe import Observable
from oscar.rendezvous.reactsocket import ReactSocketOne
from common.timeoutsocket import TimeoutSocketMulti
from common.timeoutsocket import iptuples
from util.net import SocketEventMixin
import struct, socket, oscar
from logging import getLogger; log = getLogger('oscar.peer'); info = log.info
from oscar.OscarUtil import tlv_list
from oscar.rendezvous.proxy import ProxyHeader
from pprint import pformat
from common import pref
from oscar.rendezvous.reactsocket import ReactSocket
import oscar.capabilities as capabilities

from oscar.rendezvous.rendezvous import \
    rendezvous_message_types, rendezvous_tlvs, rendezvous_header

import hooks

#
# "public" interface to OscarProtocol
#

_rdv_factories = {}

def get_rdv_factory(rdv_type):
    if len(_rdv_factories) == 0:
        hooks.notify('oscar.rdv.load')

    return _rdv_factories.get(rdv_type, None)

def register_rdv_factory(name, factory):
    '''
    add a new rendezvous handler. returns True if the stored value was changed, False otherwise.
    '''
    if _rdv_factories.get(name, None) is factory:
        return False

    _rdv_factories[name] = factory
    return True

def initialize():
    log.info('loading rendezvous handlers')
    import chat
    import directim
    import icqrelay
    import filetransfer

    register_rdv_factory('livevideo', IncomingVideoChatRequest)

hooks.Hook('oscar.rdv.load').register(initialize)

def handlech2(o, rendezvous_type, screenname, cookie, message_type, data):
    '''
    When OscarProtocol receives an incoming channel 2 message marked as a file
    transfer, it will be passed off to this method.
    '''

    ch2dict = o.rdv_sessions
    info('ch2 %s message from %s', rendezvous_type, screenname)
    info('rendezvous_type = %r, screenname = %r, cookie = %r, message_type = %r, data = %r',
         rendezvous_type, screenname, cookie, message_type, data)

    try:
        conn = ch2dict[cookie]
        info('existing conn = %r', conn)
    except KeyError:
        # No...is it a new request?
        if message_type == rendezvous_message_types.request:
            factory = get_rdv_factory(rendezvous_type)
            # If we don't know about the cookie, and the CH2 message is a
            # request, it must be a new connection.
            ch2dict[cookie] = conn = factory(o, screenname, cookie)
            info('new conn = %r', conn)
        else:
            # Otherwise, it's (hopefully) a stray CANCEL...
            return info('%s sent ch2 %s message, unknown RDV cookie',
                        screenname, rendezvous_message_types[message_type])

    # handle the new message
    conn.handlech2( message_type, data )

nullstr = '\0' * 4

class OscarPeer( Observable ):
    '''Base class for all rendezvous connections between two AIM buddies. Sends
    outgoing and handles incoming rendezvous channel two messages.

    see also: filetransfer.py, direct_im.py'''

    def __init__(self, protocol, screenname, cookie, capability=None):
        Observable.__init__(self)
        self.protocol = protocol
        self.screenname = screenname
        self.cookie = cookie
        if capability is not None:
            self.capability = capability
        assert self.capability
        self.buddy = protocol.buddies[screenname]
        self.stage = 0
        self.proxied = False
        self.accepted = False

    def handlech2(self, message_type, data):
        'An incoming message from the OSCAR server intended for this peer object.'
        info('message_type = %r, data = %r', message_type, data)
        # Dyn dispatch calling ch2TYPE where type is request, cancel, or accept
        postfix = {0: 'request', 1: 'cancel', 2: 'accept'}[message_type]
        info('calling ' + 'ch2' + postfix)
        getattr(self, 'ch2' + postfix)(data)

    def ch2request(self, data):
        # Rendezvous request types have more TLVS...
        rendtlvs, data = oscar.unpack((('rendtlvs', 'named_tlvs', -1,
                                        rendezvous_tlvs),), data)
        request_num = struct.unpack('!H', rendtlvs.request_num)[0]

        info('rendtlvs = %r, data = %r, request_num = %r', rendtlvs, data, request_num)

        # If this is an initial request, send off to subclasses.
        if request_num == 1:
            self.rendtlvs = rendtlvs
            self.handle_request(rendtlvs)

        elif request_num == 2:
            info('received request num. 2: \n%s', pformat(rendtlvs))

            # Is this a stage 3 request?
            if hasattr(rendtlvs, 'client_ip') and rendtlvs.client_ip == nullstr and rendtlvs.proxy_ip == nullstr:
                info(r'received a stage 3 request (\x00\x00\x00\x00)')
                info('connecting and sending an init_send to the proxy server')
                default_proxy = 'ars.oscar.aol.com'
                if self.protocol.icq:
                    default_proxy = 'ars.icq.com'
                proxy_ip = pref('oscar.peer.proxy_server', default_proxy)
                self.stage = 3
                args = ([(proxy_ip, 5190)], self.initialize_proxy_send, self.failed)
            elif hasattr(rendtlvs, 'proxy_flag'):
                info('receiver intervened with a stage 2 proxy')
                self.stage = 2
                self.grabaddrs(rendtlvs)
                self.needs_accept = True
                args = (self.ips, self.initialize_proxy_receive, self.failed)
            else:
                # This must be a redirect.
                info('received req num 2 redirect request')
                self.grabaddrs(rendtlvs)
                self.needs_accept = True
                self.accepted = False
                if self.ips == []: log.warning(rendtlvs)
                args = (self.ips, self.successful_connection, self.sender_establishes_proxy)
            ips, success, error = args
            self.newsock(ips, success, error)

        else: #elif request_num == 3:
            # Stage three request means "you should try connecting to the
            # proxy server at this location and port"
            info('should try proxy now, request_num = 3')
            # Is this a stage 3 request?
            #AIM6.x + iChat don't play nice, so we have to set up the proxy for them.
            if hasattr(rendtlvs, 'client_ip') and rendtlvs.client_ip == nullstr and rendtlvs.proxy_ip == nullstr:
                info(r'received a stage 3 request (\x00\x00\x00\x00)')
                info('connecting and sending an init_send to the proxy server')

                default_proxy = 'ars.oscar.aol.com'
                if self.protocol.icq:
                    default_proxy = 'ars.icq.com'
                proxy_ip = pref('oscar.peer.proxy_server', default_proxy)

                self.stage = 3
                args = ([(proxy_ip, 5190)], self.initialize_proxy_send, self.failed)
            else:
                self.rendtlvs = rendtlvs
                ip = self.ips_from_rdv(rendtlvs)[0]
                self.grabport(rendtlvs)
                args = ([(ip, self.port)], self.initialize_proxy_receive, self.failed)
            ips, success, error = args
            self.newsock(ips, success, error)

    def failed(self):
        log.error("nothing left to try.")

    def establish_out_dc(self, message='<HTML>', extratlvs=[]):
        # Pull IP and port from preferences.
        info('message = %r, extratlvs = %r', message, extratlvs)
        local_ip      = pref('oscar.peer.local_ip', '')
        if not local_ip:
            local_ip = ''
        incoming_port = pref('oscar.peer.incoming_port', 0)
        info('local_ip = %r, incoming_port = %r', local_ip, incoming_port)

        # Are we proxying by default?
        proxy = pref('oscar.peer.always_proxy', None)
        if proxy:
            default_proxy = 'ars.oscar.aol.com'
            if self.protocol.icq:
                default_proxy = 'ars.icq.com'
            proxy = pref('oscar.peer.proxy_server', default_proxy)
        info('proxy = %r', proxy)
        # send first outgoing ch2 rendezvous request message
        self.newsocket().tryaccept((local_ip, incoming_port),
                                   self.incoming_conn,
                                   lambda: info('failed direct connection'),
                                   timeout = 0)

        ip = myip()
        __, port = self.socket.getsockname()

        info('sending channel 2 request asking the receiver to connect to %s:%d', ip_from_bytes(ip), port)
        self.send_ch2request(1, port, ip, proxy=proxy, message=message,
                             extratlvs=extratlvs)

    def establish_dc(self):
        self.grabaddrs(self.rendtlvs)
        info('establish_dc: potential ips %r', self.ips)

        if hasattr(self.rendtlvs, 'proxy_flag'):
            info('STAGE 1. sender sent proxy_flag. connecting to proxy server...')
            self.stage = 1
            success = self.initialize_proxy_receive
            error   = self.stage3_request
            ips = self.ips
        else:
            if pref('oscar.peer.always_proxy', False):
                info('STAGE 2: always_proxy is True')
                self.stage = 2
                ips = [(pref('oscar.peer.proxy_server'), 5190)]
                success = self.initialize_proxy_send
                error   = self.error_proxy
            else:
                info('attempting direct connection to %r', self.ips)
                ips = self.ips
                self.needs_accept = True
                success = self.successful_connection
                error   = self.try_redirect
        self.newsock(ips, success, error)

    def successful_connection(self):
        log.info('successful connection')

        if not self.accepted:
            self.accepted = True

            if getattr(self, 'needs_accept', False):
                info('needs_accept, sending accept')
                self.send_rdv('accept')
            else:
                log.info('not sending accept packet, no "needs_accept"')

            log.info('on_odc_connection')
            self.on_odc_connection()
        else:
            log.info('not calling on_odc_connection, self.accepted is already True')

    def ips_from_rdv(self, rtlvs):
        if hasattr(rtlvs, 'proxy_flag'):
            return [ipstr(rtlvs.proxy_ip)]
        else:
            # Try a direct connection with both the client IP and the verified
            # IP that the OSCAR server thinks the sender has.
            return removedupes([ipstr(rtlvs.client_ip), ipstr(rtlvs.verified_ip)])

    def initialize_proxy_send(self):
        info('initialize_proxy_send, self.cookie = %r', self.cookie)
        self.socket.receive_next(ProxyHeader._struct.size + 6, self.received_proxy_ack)
        self.socket.push( ProxyHeader.initsend(self.protocol.self_buddy.name, self.cookie) )

    def initialize_proxy_receive(self):
        info('sending proxy receive to %r', self.socket.getpeername())
        self.socket.receive_next(ProxyHeader, self.received_proxy_ready)
        proxy_initrecv = ProxyHeader.initreceive(self.protocol.self_buddy.name, self.cookie, self.port)
        self.socket.push( proxy_initrecv )

    def received_proxy_ready(self, data):
        header, data = ProxyHeader.unpack(data)
        if header.command == ProxyHeader.commands.ready:
            info('proxy READY received')
            self.proxied = True
            self.accepted = False
            self.successful_connection()
        elif header.command == ProxyHeader.commands.error:
            log.error('Proxy server indicated ERROR!')
            self.failed()
        else:
            raise AssertionError('Unknown proxy command: %d' % header.command)

    def received_proxy_ack(self, data):
        header, data = ProxyHeader.unpack(data)
        if header.command == ProxyHeader.commands.ack:
            info('received proxy ACK')

            # 6 extra bytes after the proxy header: port and IP of the proxy server
            proxyport, proxyip = struct.unpack('!HI', data)

            info('sending RDV request, req num %d', self.stage)
            self.send_ch2request( self.stage, proxyport, None, proxyip )
            self.socket.receive_next(ProxyHeader, self.received_proxy_ready)
            self.needs_accept = False
        else:
            from pprint import pformat
            log.error('Unexpected proxy packet: %r', pformat(list(iter(header))))
            self.close()

    def sender_establishes_proxy(self):
        self.stage = 3
        ips = [(pref('oscar.peer.proxy_server'), 5190)]
        info('sender_establishes_proxy, ips = %r', ips)
        success = self.initialize_proxy_send
        error   = self.error_proxy
        self.newsock(ips, success, error)

    def error_proxy(self, *_a, **_k):
        log.error('proxy server is being slow :(')

    def stage3_request(self):
        # special stage 3 rdv request has 0s for client and proxy IPs.
        info('STAGE 3 - sending request...')
        self.send_ch2request(2, port=None, client_ip = struct.pack('!I', 0), proxy = 0x00)

    def try_redirect(self, e=None):

        if getattr(self, '_done', False):
            info('try_redirect was called but already done, so not asking for redirect.')
            return

        self.newsocket().tryaccept(('',0), self.incoming_conn, self.stage3_request, 3)
        __, port = self.socket.getsockname()
        info('%r is trying a redirect, listening on port %d', self, port)
        info('sending channel 2 request')
        self.send_ch2request(2, port, myip())

    def incoming_conn(self, socket):
        info('obtained successful incoming connection')
        self.socket = ReactSocket(socket, on_close = self.on_close)
        self.needs_accept = False
        self.accepted = False
        self.successful_connection()

    def grabport(self, rendtlvs):
        if hasattr(rendtlvs, 'external_port'):
            self.port = struct.unpack('!H', rendtlvs.external_port)[0]
        elif not hasattr(self, 'port'):
            self.port = 5190

    def grabaddrs(self, rendtlvs):
        self.grabport(rendtlvs)
        self.ips = [(ip, self.port) for ip in rdv_ips(rendtlvs)]

    # sending
    def channel2(self, rendezvous_data):
        'Sends a channel 2 message over the normal OSCAR connection.'
        info('channel2: rendezvous_data = %r', rendezvous_data)
        rdv_snac = oscar.snac.x04_x06(self.screenname, self.cookie,
                                      2, rendezvous_data)
        self.protocol.send_snac(*rdv_snac)

    def send_rdv(self, type, data=''):
        '''Sends a channel 2 message with a rendezvous block, with optional data
        inside the block.'''

        info('sending RDV %s', type)
        header = rendezvous_header(type, self.cookie, self.capability)
        self.channel2( oscar.OscarUtil.tlv(0x05, header + data ) )

    def send_ch2request(self, reqnum, port, client_ip, proxy = None, message = None, extratlvs=[]):
        # turn addr:port into (a,p) integers
        info('send_ch2request, reqnum = %r, port = %r, client_ip = %r, proxy = %r, message = %r, extratlvs = %r',
             reqnum, port, client_ip, proxy, message, extratlvs,)
        if proxy and not isinstance(proxy, (int, long)):
            proxy = struct.unpack('!I', socket.inet_aton(proxy))[0]

        # build TLV list.
        rz = rendezvous_tlvs
        tlvs =      [(rz.request_num, 2, reqnum)]    # Request number

        if proxy in (None, False):
            tlvs += [(rz.mystery,)]                  # Mystery flag
        else:
            tlvs += [(rz.proxy_ip, 4, proxy),        # Optional proxy IP
                     (rz.proxy_ip_check, 4, ~proxy)] # and proxy IP check (bitwise negation)

        if message is not None:
            tlvs += [(rz.locale, 'en'),
                     (rz.encoding, 'utf-8'),
                     (rz.user_message, message),]

        if client_ip is not None:
            assert len(client_ip) == 4 and isinstance(client_ip, str)
            tlvs += [(rz.client_ip, client_ip)]      # Client IP

        if port is not None:
            tlvs += [(rz.external_port, 2, port),    # External Port
                     (rz.port_check,    2, ~port)]   # external port negated
        if proxy not in (None, False):
            tlvs += [(rz.proxy_flag,)]               # Proxy flag indicates proxy wanted

        if extratlvs:
            tlvs += extratlvs

        info(repr(tlvs))
        self.send_rdv('request', tlv_list(*tlvs))

    def newsock(self, ips, success, error):
        if hasattr(self, 'socket'):
            if isinstance(self.socket, SocketEventMixin):
                self.socket.unbind('socket_closed', self.on_close)
            try:
                self.socket.getpeername()
            except socket.error,e:
                # Socket is not connected.
                info(e)
                pass
            else:
                self.socket.close()
            del self.socket
        def assign_on_close(sock):
            sock.bind_event('socket_closed', self.on_close)
        def succ(sock):
            sock.reassign()
            self.socket = sock
            success()
        TimeoutSocketMulti().tryconnect(iptuples(ips), succ, error,
                                        2, cls=ReactSocketOne, provide_init=assign_on_close)

    def newsocket(self):
        if hasattr(self, 'socket'):
            if isinstance(self.socket, SocketEventMixin):
                self.socket.unbind('socket_closed', self.on_close)
            try:
                self.socket.getpeername()
            except socket.error,e:
                # Socket is not connected.
                info(e)
                pass
            else:
                self.socket.close()
            if isinstance(self.socket, ReactSocket):
                self.socket.cancel_timeout()
            del self.socket
        self.socket = newsock = ReactSocket(on_close = self.on_close)
        info('newsocket: %r', newsock)
        return newsock

#    def newsocket(self):
#        return TimeoutSocketMulti()

#
# utility functions used throughout peer code
#




ipstr = ip_from_bytes

def rdv_ips(rendtlvs):
    'Get a list of possible ips from a rendezvous packet.'

    normal_order = ('client_ip',  'verified_ip', 'proxy_ip')
    proxy_order  = ('proxy_ip',   'client_ip',   'verified_ip')

    # If the proxy_flag is present in the rendezvous TLVs we should try
    # the proxy server first.
    order = proxy_order if hasattr(rendtlvs, 'proxy_flag') else normal_order

    ipif = lambda s: ipstr(rendtlvs[s]) if hasattr(rendtlvs, s) else None
    return removedupes(filter(None, [ipif(s) for s in order]))


class IncomingVideoChatRequest(OscarPeer):
    capability = capabilities.by_name['livevideo']

    def handle_request(self, rendtlvs):

        def VideoChatResponseCallback(accepted = False):
                if not accepted:
                    # cancel the RDV videochat request
                    self.send_rdv('cancel')
                else:
                    log.error("Video Session accepted? But we don't support that yet!")

        # but inform the user that we received one
        self.buddy.protocol.convo_for(self.buddy).received_native_videochat_request(VideoChatResponseCallback)

