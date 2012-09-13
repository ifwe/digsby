from logging import getLogger

import util
from util.callbacks import callsback
from util.primitives.funcs import isiterable

import msn
from msn.MSNCommands import CommandProcessor, Message

from util.Events import event, EventMixin

log = getLogger('msn.p.ns')

defcb = dict(trid=True, callback=sentinel)

class MSNNotification(CommandProcessor, EventMixin):
    '''
    An MSNNotification object's purpose is to implement handlers for the various message
    types and to implement the interface specifed below. There should be one subclass of
    this class for each variation of the protocol. This implementation holds the basics
    of connection management and stubs for the previously mentioned interface.
    '''
    cid_class = str
    events = EventMixin.events | set((
       'on_conn_error',
       'on_connect',
       'on_require_auth',
       'on_receive_version',
       'on_auth_challenge',
       'disconnect',
       )
    )

    client_name = "MSNMSGR"
    client_software_version = "15.4.3502.0922"
    client_branding = "MSNMSGR"

    versions = \
    [
     #'MSNP21',
     #'MSNP15',
     #'MSNP14',
     #'MSNP13',
     'MSNP12',
     'MSNP11',
     'MSNP10',
     'MSNP9',
     'MSNP8',
     ]

    props = \
    {'phh':'phone_home',
     'phw':'phone_work',
     'phm':'phone_mobile',
     'mob':'allow_mobile',
     'mbe':'enable_mobile',
     'utl':'unknown',
     'wwe':'enable_wireless',
     'wpl':'unknown',
     'wpc':'unknown',
     'mfn':'remote_alias',
     'cid':'unknown',
     'hsb':'has_blog',}

    def __init__(self, SckCls_or_sck, server=None, buddy=None):
        '''
        @param client:         Client instance to report to
        @type  client:         L{msn.Client} (or similar)
        @param server:         Server address (host,port)
        @type  server:         tuple (string,int)

        @param SckCls_or_sck: Type of socket or instance of socket to use for transport
        @type  SckCls_or_sck: Class or instance of socket to use
        '''

        CommandProcessor.__init__(self, log)
        EventMixin.__init__(self)

        self._server = server
        self._sb_class = None
        self._last_bname = None

        self.self_buddy = buddy
        self.allow_unknown_contacts = False

        if type(SckCls_or_sck) is type:
            self.socket    = None
            self._socktype = SckCls_or_sck
        else:
            self.socket    = SckCls_or_sck
            self._socktype = type(self.socket)
            self._server   = self.socket._server
            self.socket.bind('on_message', self.on_message)
            self.socket.bind('on_conn_error', self.on_sck_conn_error)
            self.socket.bind('on_close', self.on_sck_close)

        import mail.passport

        self._authorizers = {
                             'default' : mail.passport.do_tweener_auth_4,
                             'SSO'     : mail.passport.do_tweener_auth_4,
                             'TWN'     : mail.passport.do_tweener_auth_3,
                             }

    def connect(self):
        '''
        Connect the protocol's transport layer
        '''
        if self.socket is None:
            log.info('Creating new %r to connect to %r', self._socktype, self._server)
            self.socket = self._socktype()
            self.socket.bind('on_connect', self.on_sck_connect)
            self.socket.bind('on_conn_error', self.on_sck_conn_error)
            self.socket.bind('on_close', self.on_sck_close)

            conn_args = self.socket.connect_args_for('NS', self._server)
            self.socket._connect(*conn_args)
        else:
            #self.event('on_require_auth')
            pass

    def get_local_sockname(self):
        return self.socket.get_local_sockname()

    def get_token(self, domain):
        return self.tokens[domain].Token

    def set_token(self, domain, token):
        self.tokens[domain].Token = token

    def connected(self):
        return self.socket is not None

    def disconnect(self, do_event = True):
        if self.socket is not None:
            log.info('%r disconnecting socket: %r', self, self.socket)
            sck, self.socket = self.socket, None
            sck._disconnect()
            if do_event:
                self.event('disconnect')

        self.CONNECTED = False

    def close_transport(self, xport, switching = False):
        log.info('Closing transport %r (self.socket is %r)', xport, self.socket)
        if self.socket is xport:
            self.disconnect(do_event = not switching)

        else:
            xport.clear()
            xport.close()

    def get_authorizer(self, auth_type):
        return self._authorizers.get(auth_type, self._authorizers['default'])

    def on_sck_close(self, sck):
        if self.socket not in (None, sck):
            log.info('An old socket got disconnected (%r)', sck)
            sck.clear()
            return

        if self.socket is None:
            log.info('Disconnecting normally %r: %r', self, sck)
            self.event('disconnect')
        else:
            log.info('Disconnecting unexpectedly %r: %r', self, sck)
            self.socket.clear()
            self.disconnect(do_event = False)
            self.event('on_conn_error', self, 'disconnected unexpectedly')

    def on_sck_conn_error(self, sck, e):
        if self.socket is not None:
            self.socket.unbind('on_conn_error', self.on_sck_conn_error)
        self.event('on_conn_error', self, e)

    def on_sck_connect(self, s):

        old_s = self.socket
        self.socket = s

        if old_s not in (self.socket, None):
            self.close_transport(old_s)

        self.socket.unbind('on_connect', self.on_sck_connect)
        self.socket.bind('on_message', self.on_message)

        from common import pref
        user_vers = pref('msn.versions', None)

        if user_vers is not None and isiterable(user_vers) and len(user_vers) > 0:
            self.versions = user_vers

        self.init_ns_connection(self.versions)

    def init_ns_connection(self, versions):
        self.socket.pause()
        self.send_ver(versions)
        self.event('on_require_auth')

    def unhook_socket(self):
        sck, self.socket = self.socket, None
        if sck is not None:
            sck.unbind('on_conn_error', self.on_sck_conn_error)
            sck.unbind('on_message', self.on_message)
            sck.unbind('on_close', self.on_sck_close)
        return sck

    def send_ver(self, versions):
        """
        send_ver(socket)

        Send our supported versions to socket
        """
        self.socket.send(Message('VER', *(versions+['CVR0'])), **defcb)

    def recv_ver(self, msg):
        ver = msg.args[0]
        num = int(ver[4:])

        self.event('on_receive_version', num)

    def build_cvr(self, username):
        msg = Message('cvr', '0x0409', 'winnt', '6.1.0', 'i386',
                      getattr(self, 'client_name', 'WLMSGRBETA'),
                      getattr(self, 'client_software_version', '9.0.1407'),
                      getattr(self, 'client_branding', 'msmsgs'),

                      username)

        log.info("setting up versions: %r", self.versions)
        if self.versions and self.versions[0] == 'MSNP21':
            xfrcount = getattr(self, '_xfrcount', 0)
            if xfrcount == 0:
                msg.args.append('0')
            else:
                msg.args.append(('Version: 1\r\nXfrCount: %s\r\n' % self._xfrcount).encode('b64'))
            self._xfrcount = xfrcount + 1

        return msg


    def send_cvr(self, username):
        self.socket.send(self.build_cvr(username), **defcb)

#        self.socket.send(Message('cvr', '0x0409', 'winnt', '5.1', 'i386',
#                                 'MSNMSGR', '8.5.1302', 'MSMSGS', username),
#                                 **defcb)

    def recv_cvr(self, msg):
        log.info('got cvr')

    def send_usr(self, username, password, auth_type):

        self._username = username
        self._password = password
        self._auth_type = auth_type

        self.socket.send(Message('usr', auth_type, 'I', username),
                         trid    = True,
                         success =self._recv_usr_success,
                         error   =self._recv_usr_error,)

    def _recv_usr_error(self, sck, e):
        log.info('Got an error when waiting for USR response: %r', e)
        self.event('on_conn_error', self, e)

    def _recv_usr_success(self, sck, msg):
        log.info('Got a success when waiting for USR response: %r', msg)
        return True

    def recv_usr(self, msg):
        auth_type = msg[0]
        type_ = msg[1]

        if auth_type == 'OK':
            self.event('on_auth_success')
            return

        if type_ == 'S':
            self.event('on_auth_challenge', auth_type, msg[2:])
        else:
            assert False, (self, msg)

    def recv_xfr(self, msg):
        type_, new_addr = msg.args[:2]

        server = util.srv_str_to_tuple(new_addr, 1863)

        if type_ == 'NS':
            log.info('Switching NS servers to %r', server)
            self.close_transport(self.socket, switching = True)
            self._server = server
            self.connect()
        else:
            assert type_ == 'SB', msg
            cookie = msg.args[3]

            self.switchboard_request(server, cookie)

        if self.versions and self.versions[0] == 'MSNP21':
            try:
                self._xfrcount = int(email.message_from_string(msg.args[-1].decode('base64')).get('XfrCount'))
            except Exception:
                pass

    def recv_xfr_error(self, msg):
        self.sb_request_error(msg)

    def authenticate(self, username, password, auth_type):
        self.send_cvr(username)
        self.send_usr(username, password, auth_type)
        self.socket.unpause()

    def send_png(self):
        return NotImplemented

    def needs_login_timer(self):
        return True

    def _load_contact_list(self):
        return NotImplemented
    def _add_buddy(self, bname, bid, gname, callback):
        return NotImplemented
    def _add_buddy_to_group(self, bname, bid, gid, callback):
        return NotImplemented
    def _remove_buddy(self, lid, buddy, group, callback):
        return NotImplemented
    def _remove_buddy_from_group(self, name, bid, g_id, callback):
        return NotImplemented
    def _authorize_buddy(self, buddy, authorize, callback):
        return NotImplemented
    def _block_buddy(self, buddy, callback):
        return NotImplemented
    def _unblock_buddy(self, buddy, callback):
        return NotImplemented
    def _move_buddy(self, bname, bid, to_groupid, from_groupid, callback):
        return NotImplemented
    def _set_display_name(self, new_alias, callback):
        return NotImplemented
    def _set_remote_alias(self, buddy, new_alias, callback):
        return NotImplemented
    def _get_profile(self, buddy, callback):
        return NotImplemented
    def _rename_group(self, group, name, callback):
        return NotImplemented
    def _set_buddy_icon(self, icon, callback):
        return NotImplemented
    def _get_buddy_icon(self, name, callback):
        return NotImplemented
    def _send_file(self, buddy, filepath, callback):
        return NotImplemented
    def _send_sms(self, phone, message, callback):
        return NotImplemented
    def _set_status(self, code, callback):
        return NotImplemented
    def _set_status_message(self, message, callback):
        return NotImplemented

    def init_p2p(self):
        import msn.P2P as P2P
        import msn.P2P.P2PHandler
        import msn.P2P.SDGBridge
        self.P2PHandler = P2P.P2PHandler.P2PHandler(self)
        self.SDGBridge = P2P.SDGBridge.SDGBridge(self)

        # Registers P2P application types
        import msn.P2P.P2PApplication
        import msn.P2P.P2PActivity
        import msn.P2P.P2PObjectTransfer
        import msn.P2P.P2PFileTransfer
