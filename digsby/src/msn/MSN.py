from __future__ import with_statement

import logging

import urllib2, socket as socketmodule
import struct
import hashlib
import uuid
import traceback
import time

import hooks
import util
import util.xml_tag
import util.net as net
import common
from common import protocol, action
from common.sms import validate_sms
from common.Buddy import icon_path_for
from util.callbacks import callsback
from util.primitives.funcs import Delegate, get, isint
from util.primitives.error_handling import try_this
from contacts import Group

import msn
import msn.AddressBook as MSNAB

log = logging.getLogger('msn.client')
#log.setLevel(logging.DEBUG)

require_connected = lambda self, *a, **kw : self.state == self.Statuses.ONLINE

def is_circle_name(name):
    try:
        email = net.EmailAddress(name)
        uuid.UUID(email.name)
    except (TypeError, ValueError):
        return False

    return True

class MSNClient(protocol):
    name = 'msn'

    message_format = 'html'

    message_bg = False
    message_sizes = []

    mobile_enable_url = 'http://mobile.live.com/signup'
    mobile_edit_url = 'http://mobile.live.com/signup'

    needs_update = [
                    ('remote_alias', 'set_display_name'),
                    ]

    ROOT_ID = None

    supports_group_chat = True

    __slots__ = \
    '''
    username password hub name server
    status buddies disconnecting logging_on sockets
    version keep_alive_thread gtc_state num_groups
    num_buddies allow_unknown_contacts last_buddy
    forward_list reverse_list allow_list block_list
    pending_list list_types groups root_group
    status_to_code code_to_status self_info
    versions props m_buddies icon_requests
    icon_obj _ft remote_alias
    '''.split()

    auth_type = 'SSO'
    # flags: 1=Forward, 2=Allow, 4=Block, 8=Reverse and 16=Pending
    list_types = \
    {'FL'    :    'forward_list',
     'RL'    :    'reverse_list',
     'AL'    :    'allow_list',
     'BL'    :    'block_list',
     'PL'    :    'pending_list',
     'HL'    :    'hidden_list', }

    status_to_code = \
    {'available' :    'NLN',
     'online'    :    'NLN',
     'busy'      :    'BSY',
     'idle'      :    'IDL',
     'brb'       :    'BRB',
     'away'      :    'AWY',
     'phone'     :    'PHN',
     'lunch'     :    'LUN',
     'invisible' :    'HDN',
     'offline'   :    'FLN'}
    code_to_status = util.dictreverse(status_to_code)
    status_to_code.update({
     'be right back': 'BRB',
     'on the phone':  'PHN',
     'out to lunch':  'LUN',
    })

    client_id = msn.MSNClientID.IM_DEFAULT_CAPABILITIES
    #client_id = 0
    require_connected = require_connected

    message_formatting = 'simple'

    @property
    def SOCKTYPES(self):
        scks = []
        if common.pref('msn.socket.use_direct', True) and not self.use_http_only:
            scks.append(msn.MSNSocket)
        if common.pref('msn.socket.use_http', True) or self.use_http_only:
            scks.append(msn.MsnHttpSocket)

        return scks

    @classmethod
    def email_hint(cls, contact):
        return contact.name # the passport IS an email

    def __init__(self, username, password, user,
                 server, login_as = "invisible", remote_alias = None,
                 use_http_only = False, allow_unknown_contacts = False, **extra_args):

        protocol.__init__(self, username, password, user)
        remote_alias = remote_alias or username

        if '@' not in self.username:
            self.username = self.username + '@hotmail.com'

        self.use_http_only = use_http_only
        self.__socktypes = self.SOCKTYPES[:]
        self._conn_args = ((), {})

        self.server, self.status = server, login_as

        self.allow_unknown_contacts = allow_unknown_contacts

        self.mail = 0
        self.groups_to_add = {}
        self.buddies = msn.MSNBuddies.MSNBuddies(self)
        self.m_buddies = msn.MSNBuddies.MSNBuddies(self) # mobile buddies
        self.circle_buddies = msn.MSNBuddies.CircleBuddies(self)
        self.self_buddy = self.get_buddy(self.username)
        self.self_buddy.client_id = self.client_id
        self.remote_alias = remote_alias
        self.sockets = {}
        self.icon_requests = []
        self.version = None
        self.keep_alive_thread = util.ResetTimer(0, lambda:None)
        self.keep_alive_thread.start()
        self.rl_notify_user = False

        #init groups
        self.root_group = Group('__Root__', self, None)
        self.groups = {'__Root__' : self.root_group, None : self.root_group}

        self.disconnecting = False

        self.add_observer(self.state_change, 'state')

        self._old_status = None

        #init lists
        self.forward_list, \
        self.reverse_list, \
        self.allow_list, \
        self.block_list, \
        self.pending_list, \
        self.hidden_list, \
        self.self_info = set(), set(), set(), set(), set(), set(), dict(),

        self.hub = user.getThreadsafeInstance()

        self._ns_class = msn.Notification
        self._sb_class = None
        self.ns = None
        self.__authenticating = False
        self._conversations = []

        self._waiting_for_sb = []

        self.waiting_for_auth = set()
        self.status_message = ''

        self._requesting_icons = set()
        self._pending_icon_requests = {}

        self.self_buddy.status = self.status

#    def init_p2p(self):
#        self.P2PHandler = P2P.P2PHandler.P2PHandler(self)
#
#        # Registers P2P application types
#        import msn.P2P.P2PApplication
#        import msn.P2P.P2PActivity
#        import msn.P2P.P2PObjectTransfer
#        import msn.P2P.P2PFileTransfer

#        bridges = [
#                   P2P.Bridges.UdpBridge,
#                   P2P.Bridges.TcpBridge,
#                   ]
#
#        for b in bridges:
#            self._p2p_manager.register_bridge(b.bridge_name, b)

#    def get_bridge_names(self):
#        return self._p2p_manager.get_bridge_names()
#
#    def get_bridge_class(self, name):
#        return self._p2p_manager.get_bridge_class(name)

    @property
    def caps(self):
        'Returns the MSN capability list.'

        from common import caps
        return [caps.INFO, caps.IM, caps.FILES, caps.EMAIL, caps.SMS, caps.BLOCKABLE, caps.VIDEO]

    connected = property(lambda self: self.state == self.Statuses.ONLINE)

    def __repr__(self):
        return '<%s %s (%s)>' % (type(self).__name__, self.username, self.state)

    def buddy_dictionaries(self):
        return [self.buddies, self.m_buddies, self.circle_buddies]

    @action(lambda self, *a, **k:
            not any((self.disconnecting,))
            and self.state != self.Statuses.ONLINE)
    def Connect(self, *a, **k):
        """
        Connect()

        Begin the connection process for this protocol
        """

        assert self.ns is None
        self._conn_args = (a, k)

        invisible = k.get('invisible', False)

        self.set_status('invisible' if invisible else 'available', on_ns = False)

        if not self.__socktypes:
            log.info('No more socket types to try.')
            self.on_conn_fail()
            return

        self.__socktype = self.__socktypes.pop(0)

        self.ns = self._ns_class(self.__socktype, self.server, self.self_buddy)
        self.ns.protocol = self

        log.info("self.ns is now: %r", self.ns)

        self.ns.bind('on_connect', self._on_ns_connect)
        self.ns.bind('on_conn_error', self._on_ns_error)
        self.ns.bind('on_require_auth', self._on_ns_needs_auth)
        self.ns.bind('on_receive_version', self._store_new_version)

        if self.ns.needs_login_timer():
            self._cancel_login_check_timer()

            login_timeout = common.pref('msn.login.timeout', default = 60, type = int)
            self._login_check_timer = util.ResetTimer(login_timeout, self._check_login)
            self._login_check_timer.start()
            log.info("Starting login timer for %r", self)

        self.change_state(self.Statuses.CONNECTING)
        self.ns.connect()

    def change_state(self, newstate):
        lct = getattr(self, '_login_check_timer', None)
        if lct is not None:
            lct.reset()

        return protocol.change_state(self, newstate)

    def _store_new_version(self, num):
        self.version = 'MSNP%d' % num
        log.info("Got target protocol version: %r", self.version)

        exec('from msn.p%(num)s import Notification, Switchboard' % locals())
        self._sb_class = Switchboard
        self._ns_class = Notification

    def _cancel_login_check_timer(self):
        timer, self._login_check_timer = getattr(self, '_login_check_timer', None), None
        if timer is not None:
            timer.cancel()
            log.info("Stopping login timer for %r", self)

    def _check_login(self):
        if self.state not in (self.Statuses.ONLINE, self.Statuses.OFFLINE):
            self._on_ns_error(self.ns, Exception('MSN login took more than a minute'))

    def _check_offline(self):
        if (self.ns is None or not self.ns.connected()) and not self._conversations:
            self.set_offline(getattr(self, '_future_offline_reason', self.Reasons.NONE))
            protocol.Disconnect(self)
            log.info('%r is offline', self)
            self.disconnecting = False
        else:
            log.info('%r not offline yet: ns=%r, conversations=%r', self, self.ns, self._conversations)
            if not self.disconnecting:
                return
            for conv in self._conversations:
                conv.exit(force_close = True)
            if self.ns is not None and self.ns.connected():
                self.ns.disconnect()

    def swap_ns(self):
        self.ns.unbind('on_connect', self._on_ns_connect)
        self.ns.unbind('on_conn_error', self._on_ns_error)
        self.ns.unbind('on_require_auth', self._on_ns_needs_auth)
        self.ns.unbind('on_receive_version', self._store_new_version)

        socket = self.ns.unhook_socket()
        self._clean_up_ns()

        if self.disconnecting:
            return

        xfrcount = getattr(self.ns, '_xfrcount', 0)
        self.ns = self._ns_class(socket, buddy = self.self_buddy)
        self.ns.protocol = self
        log.info("self.ns is now: %r", self.ns)
        self.ns._auth_type = self.auth_type
        self.ns._username = self.username
        self.ns._password = self.password
        self.ns._xfrcount = xfrcount

        if not self.ns.needs_login_timer():
            self._cancel_login_check_timer()

        self.ns._sb_class = self._sb_class
        self.ns.bind('on_require_auth', self._on_ns_needs_auth)
        self.ns.bind('on_conn_error', self.on_conn_error)
        self.ns.bind('disconnect', self._on_ns_disconnect)
        self.ns.connect()

    @property
    def P2PHandler(self):
        return self.ns.P2PHandler

    def _on_ns_error(self, ns, error):
        log.error('MSN Disconnecting. Received the following error from transport: %s', error)
        self.on_conn_fail()

    def _clean_up_ns(self):
        if self.ns is not None:
            ns, self.ns = self.ns, None
            if getattr(ns, 'protocol', None) is not None:
                del ns.protocol
            ns.clear()
            ns.disconnect()

    def on_conn_fail(self):
        self._clean_up_ns()
        self.__authenticating = False

        if self.__socktypes:
            conn_args, conn_kwargs = self._conn_args
            self.Connect(*conn_args, **conn_kwargs)
            return

        self.Disconnect(self.Reasons.CONN_FAIL)

    def on_conn_error(self, ns, error = None):
        log.info('Got connection error: %r', error)
        self.Disconnect(self.Reasons.CONN_LOST)

    def _on_ns_disconnect(self):
        log.debug('NS disconnected')
        self._clean_up_ns()
        self._check_offline()

    def _on_ns_connect(self, socket):
        self.__socktypes[:] = []
        self._conn_args = ((), {})
        self.ns.unbind('on_connect', self._on_ns_connect)

    def _on_ns_needs_auth(self, ver = None):
        if ver is not None:
            assert str(ver) in self.version

        self.change_state(self.Statuses.AUTHENTICATING)

        #self.ns.unbind('on_require_auth', self._on_ns_needs_auth)
        self.ns.bind('on_auth_challenge', self.do_tweener_auth)
        self.ns.authenticate(self.username, self.password, self.auth_type)

    @property
    def appid(self):
        return self.ns.client_chl_id

    @property
    def appcode(self):
        return self.ns.client_chl_code

    def get_token(self, domain):
        return self.ns.get_token(domain)

    def set_token(self, domain, token):
        return self.ns.set_token(domain, token)

    def do_tweener_auth(self, auth_type, twn_args):
        self.ns.unbind('on_auth_challenge', self.do_tweener_auth)
        if self.__authenticating:
            return
        self.__authenticating = True

        if not self.ns:
            self.on_conn_fail()
            return

        self.swap_ns()

        tweener = self.get_authorizer(auth_type)
        log.info('authorizer is: %r', tweener)
        tweener(self.username, self.password, twn_args,
                success = self.finish_auth, error = self.auth_error)

    def get_authorizer(self, auth_type):
        return self.ns.get_authorizer(auth_type)

    def finish_auth(self, *ticket):
        log.info('Finishing authorization process')

        if self.ns:
            if self.disconnecting and self.ns is None:
                return
            self.ns.bind('on_auth_success', self._on_ns_authorize)
            self.ns.complete_auth(*ticket)
        else:
            self.on_conn_fail()

    def _on_ns_authorize(self):
        self.ns.unbind('on_require_auth', self._on_ns_needs_auth)
        self.ns.unbind('on_auth_success', self._on_ns_authorize)

        self._bind_ns_events()

        self.ns.init_p2p()

        self.change_state(self.Statuses.LOADING_CONTACT_LIST)
        self.root_group.freeze()
        self.ns._load_contact_list()

    def _bind_ns_events(self):
        evt_table = (
            ('on_recv_profile', self.on_recv_profile),
            ('on_rl_notify', self.got_rlnotify_behavior),
            ('on_blist_privacy', self.got_blp),
            ('recv_prop', self.set_prop),
            ('recv_contact', self.on_contact_recv),
            ('recv_status', self.on_set_status),
            ('recv_clientid', self.on_set_client_id),
            ('group_receive', self.on_recv_group),
            ('on_contact_add', self.on_contact_add),
            ('contact_online_initial', self.on_buddy_status),
            ('contact_online', self.on_buddy_status),
            ('contact_offline', self.on_buddy_status),
            ('contact_alias', self.on_contact_alias_changed),
            ('contact_remove', self.on_contact_remove),
            ('contact_list_details', self.on_blist_info),
            ('contact_id_recv', self.on_contact_id),
            ('contact_status_msg', self.on_buddy_status_msg),
            ('challenge', self.on_challenge),
            ('challenge_success', self.on_challenge_success),
            ('other_user', self.on_other_user),
            ('connection_close', self.on_conn_close),
            ('initial_mail', self.on_init_mail),
            ('subsequent_mail', self.on_more_mail),
            ('group_remove', self.on_group_remove),
            ('group_add', self.on_group_add),
            ('group_rename', self.on_group_name_changed),
            ('ping_response', self.on_ping_response),
            ('switchboard_invite', self.on_switchboard_invite),
            ('switchboard_request', self.on_switchboard_request),
            ('sb_request_error', self.on_switchboard_error),
            ('recv_sms', self.on_recv_sms),
            ('contact_icon_info', self.on_bicon_info),
            ('contact_role_info', self.on_buddy_role_info),
            ('contact_cid_recv', self.on_contact_cid),
            ('contact_profile_update', self.get_profile_for_cid),
            ('received_oims', self.on_received_oims),
            ('soap_info', self.on_soap_info),
            ('contact_btype', self.on_contact_type),
            ('on_connect', self.on_connect),
            ('fed_message', self.on_federated_msg),
            ('buddy_authed', self.on_authorize_buddy),
            ('needs_status_message', self.on_needs_status_message),
            ('needs_self_buddy', self.on_needs_self_buddy),
            ('on_circle_member_joined', self.on_circle_member_joined),
            ('circle_roster_recv', self.on_circle_roster_recv),
            ('circle_roster_remove', self.on_circle_roster_remove),
        )

        events = self.ns.events
        bind = self.ns.bind

        for name, callback in evt_table:
            if name in events:
                bind(name, callback)
            else:
                log.warning('Can\'t bind event %s to %r', name, self.ns)

    def auth_error(self, e):
        log.error('%s exception: %s', self, e)

        try:
            raise e
        except (urllib2.URLError, socketmodule.error):
            reason = self.Reasons.CONN_FAIL
        except util.xml_tag.SOAPException:
            log.debug('SOAPException when trying to authenticate: %r', e.t._to_xml(pretty = False))
            reason = self.Reasons.BAD_PASSWORD
        except Exception:
            log.error("Failed to authenticate %r: %r", self, e)
            reason = self.Reasons.BAD_PASSWORD

        self.Disconnect(reason)
        return True

    def on_init_mail(self, newmail):
        self.setnotifyif('mail', newmail)

    def on_more_mail(self, count):
        self.setnotifyif('mail', self.mail + count)

    def on_conn_close(self):
        log.info('Connection closed. Calling disconnect...')
        if not self.disconnecting:
            self.Disconnect(self.Reasons.CONN_LOST)

    def on_other_user(self):
        log.error('Logged in from another location. Disconnecting...')
        self.Disconnect(self.Reasons.OTHER_USER)

    def on_recv_profile(self, prof):
        for k in prof:
            self.self_buddy.info[k] = prof[k]

        self.ip = self.self_buddy.info.get('clientip', util.myip())
        self.port, = struct.unpack('H', struct.pack
                                   ('!H', int(self.self_buddy.info.get ('clientport', self.server[-1]))))

    def got_rlnotify_behavior(self, value):
        '''
        This is the GTC property. It specifies whether the user should be notified
        of reverse-list additions, or if they should happen silently
        '''
        self.rl_notify_user = value

    def got_blp(self, value):
        if self.version > 'MSNP12':
            self.on_connect()

    def set_blist_privacy(self, allow_unknowns):
        self.ns.send_blp('AL' if allow_unknowns else 'BL')

        self.setnotify('allow_unknown_contacts', allow_unknowns)
        self.account.allow_unknown_contacts, old = self.allow_unknown_contacts, self.account.allow_unknown_contacts
        if old != self.account.allow_unknown_contacts:
            self.account.update()

    @callsback
    def request_sb(self, callback = None):
        if self.ns is not None:
            self._waiting_for_sb.append(callback)
            self.ns.request_sb()
            # Must return a value such that bool(v) == True but v itself cannot be True, due to callsback semantics
            return 1
        else:
            callback.error()
            return False

    #@action(lambda self, *a, **k: not(self.state == self.Statuses.OFFLINE or self.disconnecting))
    def Disconnect(self, reason = None):
        """
        Disconnect()

        Disconnect from all servers
        """

        if self.ns is not None:
            if getattr(self.ns, 'protocol', None) is not None:
                del self.ns.protocol
            self.ns.disconnect()
        else:
            self._check_offline()

        if reason is None:
            reason = self.offline_reason
        elif isinstance(reason, Exception):
            reason = self.Reasons.CONN_FAIL

        if not self.disconnecting:
            log.critical('disconnecting')
            self.disconnecting = True
            self._future_offline_reason = reason
            if self.keep_alive_thread is not None:
                self.keep_alive_thread.cancel()

            if hasattr(self, 'slp_call_master'):
                self.slp_call_master.cancel_all()

            if self._conversations:
                for conv in self._conversations[:]:
                    conv.exit(force_close = True)
            else:
                self._check_offline()

        self._cancel_login_check_timer()

    def reconnect_ns(self, server, version):
        pass

    def authenticate(self, *args):
        self.change_state(self.Statuses.AUTHENTICATING)
        self.do_tweener_auth(self.username, self.password, args,
                             success = self.ns.complete_auth,
                             error = self._auth_error)

    def _auth_error(self, errmsg):

        log.error('msn had an auth error: %r, %r' , type(errmsg), errmsg)

        self.logging_on = False
        self.Disconnect(self.Reasons.BAD_PASSWORD)
        self.hub.get_instance().on_error(errmsg)
        raise Exception(errmsg)

    def on_authenticate(self):
        self.change_state(self.Statuses.LOADING_CONTACT_LIST)
        self.ns._load_contact_list()

    def on_recv_group(self, name, id):
        log.debug('on_recv_group: name=%r, id=%r', name, id)

        if id in self.groups:
            new_group = self.groups[id]
        else:
            new_group = Group(name, self, id)

        rglist = list(self.root_group)
        if new_group not in rglist:
            self.root_group.append(new_group)

        self.groups[id] = new_group

        num_groups = len(self.groups) - 1
        if hasattr(self, 'num_groups'):
            log.debug('Got group %d/%d', num_groups, self.num_groups)
            if num_groups == self.num_groups:
                log.info('Got all groups!')
                self._check_connected()

    def on_blist_info(self, num_buddies, num_groups):
        log.info('Got buddy list information: %d buddies, %d groups', num_buddies, num_groups)

        self.num_buddies = num_buddies
        self.num_groups = num_groups

        self._check_connected()

    def on_soap_info(self, name, typ, soap, role):
        raise Exception
        log.info('Got soap info for buddy: %r', (name, typ, soap, role))

        if typ == 'Passport':
            d = self.buddies
            t = 1
        elif typ == 'Email':
            d = self.buddies
            t = 32
        elif typ == 'Phone':
            d = self.m_buddies
            t = 4

        d[name].mships[role] = soap
        d[name]._btype = t

    def has_buddy_on_list(self, buddy):
        return buddy.name in set(x.name for x in self.forward_list)

    def on_contact_add(self, name, id, flags, groups, soap = None):

        buddy = self.on_contact_id(name, id)

        if soap is not None:
            buddy.contactsoap = soap

        if isint(flags):
            ltypes = self.apply_list_flags(flags, buddy)
        else:
            ltypes = self.apply_list_types(flags, buddy)

#        if buddy is self.self_buddy:
#            log.error('Not putting self buddy in a group, that\'s silly')
#            return buddy

        root_contact = msn.Contact(buddy, self.ROOT_ID)

        if 'FL' in ltypes:
            if groups:
                added = []

                if root_contact in self.root_group:
                    self.root_group.remove(root_contact)

                for id in groups:
                    g = self.groups[id]
                    c = msn.Contact(buddy, id)
                    #if c not in g:
                    g.append(c)
                    added.append(g.name)

                log.info('%s is in groups: %r', buddy.name, added)

            else:
                if buddy in self.forward_list and root_contact not in self.root_group:
                    self.root_group.append(root_contact)

            self.root_group.notify()

        buddy.notify()
        return buddy

    def get_authorization_for(self, buddy):
        bname = getattr(buddy, 'name', buddy)
        buddy = self.get_buddy(bname)
        if buddy not in self.waiting_for_auth:
            buddy.pending_auth = False
            self.waiting_for_auth.add(buddy)
            self.hub.authorize_buddy(self, buddy, message = getattr(self.ns, 'get_auth_message_for', lambda b: u'')(buddy))

    def on_contact_recv(self, name, flags, groups, soap = None, id = None):
        log.debug('on_contact_recv: name=%s, flags=%s, groups=%s', name, flags, groups)

        if self.state == self.Statuses.LOADING_CONTACT_LIST:
            setattr(self, '_recieved_contacts', getattr(self, '_recieved_contacts', 0) + 1)

        try:
            buddy = self.on_contact_add(name, name or id, flags, groups, soap)
        except Exception:
            log.error('Error processing buddy: name = %r, flags = %r, groups = %r, soap = %r, id = %r',
                      name, flags, groups, soap, id)
            traceback.print_exc()
            if hasattr(self, 'num_buddies'):
                self.num_buddies -= 1
            buddy = None
        self._check_connected()

        return buddy

    def on_contact_type(self, name, btype):

        import msn.AddressBook as MSNAB
        buddies = {MSNAB.ClientType.PassportMember : self.buddies,
                   MSNAB.ClientType.PhoneMember : self.m_buddies,
                   MSNAB.ClientType.EmailMember : self.buddies}.get(MSNAB.ClientType(btype), None)

        if buddies is None:
            return

        buddy = buddies[name]
        buddy._btype = int(btype)

    def _check_connected(self):
        num_buddies = getattr(self, '_recieved_contacts', 0)

        self._cancel_login_check_timer()

        if self.state != self.Statuses.ONLINE:
            if not hasattr(self, 'num_buddies'):
                return
            log.debug('Got buddy %d/%d', num_buddies, self.num_buddies)
            if num_buddies >= self.num_buddies:
                log.info('Got all buddies!')
                if (len(self.groups) - 1) >= self.num_groups:

                    log.info('Got all buddies and groups.')

                    if self.version <= 'MSNP12':
                        self.on_connect()

    def on_load_contact_list(self):
        pass

    def on_set_status(self, newstatus):
        sta = self.code_to_status[newstatus]

        if sta == 'online':
            sta = 'available'

        for x in (self, self.self_buddy):
            x.setnotifyif('status', sta)

    def on_set_client_id(self, client_id):
        for x in (self, self.self_buddy):
            x.setnotifyif('client_id', client_id)

    def on_buddy_status(self, name, nick, status, id):
        log.debug('Got status change for %r (%r). newstatus=%r, id=%r', name, nick, status, id)
        buddy = self.get_buddy(name)
        if nick is None:
            nick = buddy.alias
        else:
            self.on_contact_alias_changed(name, nick)

        log.debug('Got buddy %r for status change', buddy)
        sta = self.code_to_status[status]

        if sta == 'online':
            sta = 'available'

        buddy.status = sta
        buddy.client_id = id
        buddy.notify('status'); buddy.notify('client_id')

    def on_buddy_status_msg(self, bname, message):
        log.info('Got Status Message for %s: %r', bname, message)
        b = self.get_buddy(bname)
        b.status_message = message
        b.notify('status_message')

    def on_challenge(self, nonce):
        self.ns.do_challenge(nonce)

    def on_challenge_success(self):
        '''
        yay still connected
        '''
        pass

    def on_contact_id(self, name, guid):

        log.info('Got ID for %r: %r', name, guid)

        if not name:
            for buddy in (self.buddies.values() + self.m_buddies.values()):
                if str(getattr(buddy, 'guid', None)) == str(guid):
                    return buddy
            else:
                raise ValueError("No buddy with %r was found and no name was supplied." % guid)

        if name.startswith('tel:'):
            name = name[4:]
        buddy = self.get_buddy(name)

        if not guid or guid == name:
            return buddy

        try:
            if not isinstance(guid, self.ns.cid_class):
                _guid = self.ns.cid_class(guid)
            else:
                _guid = guid
            buddy.guid = _guid
        except (ValueError, AttributeError, TypeError), e:
            log.info('%r is not a valid ID. (error was %r)', guid, e)

        return buddy

    def on_contact_cid(self, name, cid):
        self.get_buddy(name).CID = cid

    def get_buddy_by_id(self, id_name):
        if id_name not in self.buddies:

            possibles = filter(lambda x: (str(x.id) == str(id_name)) or (x.name == id_name),
                               self.buddies.values() +
                               self.m_buddies.values())

            if len(possibles) > 1:
                log.warning('Found multiple buddies with id %r', id_name)

            if possibles:
                return possibles[0]

        if isinstance(id_name, basestring):

            if not util.is_email(id_name):
                if id_name.startswith('tel:'):
                    return self.m_buddies[id_name[4:]]
                elif id_name.startswith('fed:'):
                    raise Exception
                else:
                    assert False, (type(id_name), id_name)

        else:
            assert False, (type(id_name), id_name)


        assert util.is_email(id_name), (type(id_name), id_name)
        return self.buddies[id_name]

    def on_contact_remove(self, name, l_id, g_id):

        log.info('Contact has been removed: name=%s, lid=%s, gid=%s', name, l_id, g_id)

        buddy = self.get_buddy_by_id(name)
        l_id = MSNAB.MSNList(l_id)
        l = getattr(self, self.list_types.get(l_id.role))

        if not g_id or g_id not in self.groups:
            # Contact is being removed from block, allow, reverse, or pending list

            if buddy in l:
                log.info('removing buddy %s from list %s', name, l_id)
                l.remove(buddy)

            if l_id == MSNAB.MSNList.Forward:
                root_contact = msn.Contact(buddy, self.ROOT_ID)
                if root_contact in self.root_group:
                    self.root_group.remove(root_contact)
                    self.root_group.notify()

            buddy.notify()
            return

        # Contact being removed from forward list -- need to deal with groups

        groups = [self.groups[g_id]]

        log.info('Removing %r from groups %r', buddy, groups)

        for group in groups:
            contact = msn.Contact(buddy, group.id)
            try:
                group.remove(contact)
            except ValueError, e:
                log.info('%r wasn\'t in %r, ignoring. (exception was: %r)', buddy, group, e)


        if not self.groups_containing_buddy(buddy) and l_id == 'FL':
            log.info('%r has been removed from all groups. Removing from forward list.', buddy)
            self.ns._remove_buddy(l_id, buddy, None, service = buddy.service)

        self.root_group.notify()

    def groups_containing_buddy(self, buddy):
        groups = []

        for group in self.groups.values():
            c = msn.Contact(buddy, group.id)
            if c in group:
                groups.append(group)

        return groups

    def on_group_remove(self, g_id):
        group = self.groups.pop(g_id, None)
        if group is not None:
            self.root_group.remove(group)

            for contact in list(group):
                if not self.groups_containing_buddy(contact.buddy):
                    if None in self.groups:
                        self.groups[self.ROOT_ID].append(msn.Contact(contact.buddy, self.ROOT_ID))

            group[:] = []

        self.root_group.notify()

    def on_group_add(self, name, id):
        new_group = Group(name, self, id)
        #new_group.add_observer(self.group_changed)
        self.groups[id] = new_group
        self.root_group.insert(0, new_group)
        self.root_group.notify()
        return new_group

    def on_contact_alias_changed(self, name, nick):
        self.get_buddy(name).setnotifyif('remote_alias', nick)

    def on_group_name_changed(self, id, name):
        g = self.groups[id]
        g.name = name
        self.root_group.notify()

    def on_ping_response(self, next = sentinel):
        if next is sentinel or not next:
            return

        next += 5
        log.debug('next ping in %d seconds', next)
        self.keep_alive_thread.reset(next)

        self.clear_unknown_statuses()

    def on_switchboard_request(self, server, cookie):
        log.info('Got response for switchboard request, creating %r', self._sb_class)
        f = self._waiting_for_sb.pop(0)
        f.success(self.make_sb(server = server, cookie = cookie))

    def make_sb(self, server = None, sessionid = None, cookie = None):
        if self.version < 'MSNP21':
            socktype = self.__socktype
        else:
            socktype = self.ns

        sb = self._sb_class(socktype, server = server, sessionid = sessionid, cookie = cookie)
        return sb

    def make_sb_adapter(self, to_invite = ()):
        if self.version < 'MSNP21':
            return msn.NSSBAdapter(self.ns, to_invite = to_invite)
        else:
            return self._sb_class(self.ns, to_invite = to_invite)

    def on_switchboard_error(self, emsg):
        log.info('Received error for switchboard request: %r', emsg)
        cb = self._waiting_for_sb.pop(0)
        cb.error(emsg)

    def on_switchboard_invite(self, name, session = None, server = None, auth_type = None, cookie = None):
        # verify user ('name') is OK to talk to
        # find conversation

        # if not found:

        sb = self.make_sb(server = server, sessionid = session, cookie = cookie)
        con = self.convo_for(name, sb)
        if not con.connected():
            con.connect()
        return

    def on_federated_msg(self, bname, msg):
        self.convo_for(bname).fed_message(msg)

    @callsback
    def set_status(self, status = None, callback = None, on_ns = True):
        status = status or self.status

        if status == 'online' and status not in self.status_to_code:
            status = 'available'

        if status not in self.code_to_status:
            code = self.status_to_code.get(status, 'AWY')
        else:
            code = status

        log.info('setting status to %s (%s)', status, code)

        if self.status == 'invisible' and status != 'invisible': # If moving from invis to not invis, enable icons again
            for buddy in self.buddies.values():
                buddy.icon_disabled = False

        self.status = self.code_to_status[code]
        self.self_buddy._got_presence = True

        if on_ns:
            self.ns._set_status(code, self.client_id, callback)


###################################


    @callsback
    def connect_socket(self, sock_id, server_tuple, callback = None):
        """
        connect_socket(sock_id, server, connect_func, *args)

        Create a socket, store it as sockets[sock_id], connect it
        to server, and call connect_func(*args) when it has connected.
        """

        if sock_id.startswith('sb'):
            sock_id = server_tuple
            sock_type = 'sb'
        else:
            sock_type = 'ns'
        if sock_id not in self.sockets:
            host, port = server_tuple
            log.info('opening %r', sock_id)
            self.sockets[sock_id] = self.__socktype(self, (host, port), callback = callback)
        else:
            log.fatal("something's broken! see MSNP.connect_socket")
            sck = self.sockets[sock_id]
            assert (sck.server == server_tuple), sock_id

    def close_socket(self, socket):
        """
        This function is called when a socket is closed from the other end.

        If socket is in sockets, it is removed.

        If we not connected to any sockets after this, an alert is sent
        to the GUI.
        """
        log.debug('closing socket %r', socket)
        for k in self.sockets.keys():
            if self.sockets[k] is socket:
                socket.close_when_done()
                del self.sockets[k]

        if (len(self.sockets) == 0 or (self.sockets.get('NS', None) in (socket, None))) and \
           (self.state != self.Statuses.OFFLINE) and \
           (not self.disconnecting):
            log.debug('no sockets left, disconnecting')

            if self.state == self.Statuses.CONNECTING:
                raisin = self.Reasons.CONN_FAIL
            else:
                raisin = self.Reasons.CONN_LOST

            self.Disconnect(raisin)

            #raise msn.GeneralException("%s was disconnected!" % self.username)

    def close_sock_id(self, sock_id):
        if sock_id in self.sockets:
            self.close_socket(self.sockets[sock_id])
#            log.warning('closing and deleting %s', sock_id)
#            try:
#                self.sockets[sock_id].close_when_done()
#                del self.sockets[sock_id]
#            except KeyError:
#                if not self.state != self.state['Disconnecting']: raise

    def apply_list_flags(self, flags, buddy = None):
        """
        Figure out the list flags for specified buddy (or self.last_buddy)
        and put them in the appropriate lists.
        """
        buddy = buddy or self.last_buddy

        # flags: 1=Forward, 2=Allow, 4=Block, 8=Reverse and 16=Pending
        lists = []
        if flags & 1:
            lists.append('FL')
        if flags & 2:
            lists.append('AL')
        if flags & 4:
            lists.append('BL')
        if flags & 8:
            lists.append('RL')
        if flags & 16:
            lists.append('PL')
            buddy.pending_auth = True

        return self.apply_list_types(lists, buddy)

    def apply_list_types(self, types, buddy = None):
        buddy = try_this(lambda: buddy or self.last_buddy, buddy)
        if buddy is None:
            return

        log.debug('Putting %r in the following lists: %r', buddy, types)

        for l in types:
            #log.debug('   adding %r to %r', buddy, self.list_types[l])
            getattr(self, self.list_types[l]).add(buddy)

        #log.debug('   done')

        if self.state == self.Statuses.ONLINE:
            if buddy in self.reverse_list and not (buddy in self.block_list or buddy in self.allow_list):
                #log.debug("Buddy in reverse list but not block or allow. NOT Adding to pending.")
                pass
#                log.debug("Buddy in reverse list but not block or allow. Adding to pending.")
#                self.pending_list.add(buddy)
#                buddy.pending_auth = True

        if buddy in self.pending_list and (buddy in self.allow_list or buddy in self.block_list):
            log.debug("Buddy was in pending list but was already in %s list. Not asking for auth.",
                      ('block' if buddy in self.block_list else 'allow'))
            self.pending_list.discard(buddy)
            buddy.pending_auth = False

        for buddy in self.pending_list:
            #print 'not doing auth thingy', buddy
            log.info('%r is in pending list (apply_list_types). Asking for authorization...', buddy)
            self.get_authorization_for(buddy)

        return types

    def get_buddy_by_sms(self, sms):
        is_sms = validate_sms(sms)
        if not is_sms:
            return None

        if sms in self.m_buddies:
            return self.m_buddies[sms]

        for buddy in self.buddies.values():
            if buddy.sms == sms:
                return buddy

        return self.m_buddies[sms]

    def get_buddy(self, name):
        if isinstance(name, msn.MSNBuddy.MSNBuddy):
            return name

        name = ''.join(name.split()).encode('utf-8')

        is_sms = validate_sms(name)
        if name.startswith('tel:'):
            name = name[4:]

        sms_buddy = self.get_buddy_by_sms(name)
        if sms_buddy is not None:
            return sms_buddy

        if is_circle_name(name):
            buddy = self.circle_buddies.get(name, None)
            ns_circle = self.ns.GetCircle(name)
            if buddy is None:
                buddy = self.circle_buddies[name] = msn.MSNBuddy.CircleBuddy.from_msnab(ns_circle, self)
            else:
                if ns_circle is not None:
                    buddy.update_from_msnab(ns_circle)

            return buddy

        if name.startswith('fed:'):
            raise Exception

        try:
            if not util.is_email(name):
                raise AssertionError('Bad buddy name! %r' % name)
        except AssertionError:
            import traceback;traceback.print_exc()
        return self.buddies[name]

    def on_buddy_role_info(self, name, l_ids, role_id):

        b = self.get_buddy(name)

        self.apply_list_types(l_ids, b)

        for role in l_ids:
            b.role_ids[role] = role_id

    def get_list_flags(self, b):

        buddy = self.get_buddy(getattr(b, 'name', b))

        l_flags = (b in self.forward_list) * 1
        l_flags |= (b in self.allow_list) * 2
        l_flags |= (b in self.block_list) * 4

        # check if b on allow and block lists, if so, don't
        # report as in block list
        if l_flags & 6 >= 6: l_flags -= 4

        return l_flags

    def on_connect(self):
        log.info('on_connect called. setting buddy icon and requesting profiles')
        if self.ns is not None:
            self.ns.unbind('on_connect', self.on_connect)

        if self.state == self.Statuses.ONLINE:
            return

        self.root_group.thaw()
        self.change_state(self.Statuses.ONLINE)

        self.set_blist_privacy(self.allow_unknown_contacts)

        for buddy in self.buddies.values():
            self.get_profile(buddy)

#        if self.rl_notify_user:
#            for buddy in self.pending_list:
#                #print 'not doing auth thingy', buddy
#                log.info('%r is in pending list (on_connect). Asking for authorization...', buddy)
#                self.get_authorization_for(buddy)

        #for buddy in self.buddies.values():
        #    buddy.icon_disabled = False

        log.info('Setting display name')
        self.set_display_name(self.remote_alias)
        log.info('    done setting display name')

        #self.clear_unknown_statuses()
        self.set_status()
        log.info('on_connect done')


    def clear_unknown_statuses(self):
        for buddy in (self.buddies.values() + self.m_buddies.values()):
            if buddy.status != 'unknown':
                continue

            changed = False
            if not buddy._got_presence:
                buddy.status_message = ''
                changed = True
            if buddy._status == 'unknown':
                buddy._got_presence = True
                buddy.status_message = ''
                buddy.status = 'offline'
                changed = True

            if changed: buddy.notify('status')

        log.info('Set all unknown buddies to offline')

    @callsback
    def set_message_object(self, messageobj, callback = None):
        if hasattr(self.ns, 'set_message_object') and getattr(messageobj, 'media', None) is not None:
            log.info('MSN.set_status_object: setting CurrentMedia')
            self.set_status(messageobj.status.lower())
            self.ns.set_message_object(messageobj, callback = callback)
        else:
            log.info('MSN.set_status_object: setting PSM')
            return protocol.set_message_object(self, messageobj, callback = callback)

    @callsback
    def set_message(self, message, status, format = None, callback = None):
        self.status = status
        self.status_message = message

        self.set_status(status, callback = callback)
        self.set_status_message(message, callback = callback)

    def on_needs_status_message(self, callable):
        callable(self.status_message)

    def on_needs_self_buddy(self, callable):
        self.self_buddy._got_presence = True
        callable(self.self_buddy)

    def set_invisible(self, invis = True):
        if invis:
            sta = 'HDN'
        else:
            sta = 'NLN'
        self.set_status(sta)

    def stop_keepalive_thread(self):
        kat, self.keep_alive_thread = getattr(self, 'keep_alive_thread', None), None
        if kat is not None:
            kat.stop()

    def send_keepalive(self):
        ns = self.ns
        if ns is not None and ns.connected():
            ns.send_png()
        else:
            log.error('NS is not connected but keepalive timer is still notifying')

    def state_change(self, obj, attr, old, new):
        assert attr is 'state'

        log.debug('%r was %s', self, old)

        if self.state == self.Statuses.ONLINE:
            self._cancel_login_check_timer()
            self.stop_keepalive_thread()
            self.keep_alive_thread = util.RepeatTimer(5, self.send_keepalive)
            self.keep_alive_thread.start()

        if self.state == self.Statuses.OFFLINE:
            self._cancel_login_check_timer()
            self.stop_keepalive_thread()

    def set_prop(self, buddy, prp_type, val, args = ()):
        log.info('Got %r for %r', prp_type, buddy)
        bname = getattr(buddy, 'name', buddy)
        buddy = self.get_buddy(bname)
        attr = self.ns.props[prp_type.lower()]

        if isinstance(val, basestring):
            val = val.decode('url').decode('fuzzy utf8')

        buddy.setnotifyif(attr, val)

        if attr == 'phone_mobile' and args:
            args = list(args)
            try:
                enabled = int(args.pop(0))
                if buddy.allow_mobile is None:
                    buddy.allow_mobile = ('N', 'Y')[enabled]
            except Exception:
                return

    def buddy_for_cid(self, cid):
        for buddy in self.buddies.values():
            if int(buddy.CID) == int(cid):
                return buddy

        assert False, 'CID %d not found! My buddies are: %r' % (cid, self.buddies)

    def get_profile_for_cid(self, cid):
        buddy = self.buddy_for_cid(cid)
        self.get_profile(buddy)

    def set_profile(self, *a, **k):
        pass

    def set_idle(self, since = 0):
        if since:
            self._old_status = self.status
            self.set_status('idle')
        else:
            if self._old_status is not None:
                self.set_status(self._old_status)
            self._old_status = 'idle'

    def group_for_name(self, groupname):
        res = None
        for group in self.groups.values():
            if group.name == groupname:
                res = group

        #log.debug('Group for name %s found %r', groupname, res)
        return res

    def group_for(self, contact):
        gid = contact.id[-1]

        if gid is None:
            return None #self.root_group.name

        return self.groups[gid].name

    get_group = group_for_name

    def get_groups(self):
        'Returns a list of group names.'

        return [g.name for g in self.root_group if type(g) is Group]

    def get_ticket(self, key = None):
        if key is None:
            return self.ticket
        return msn.util.fmt_to_dict('&', '=')(self.ticket)[key]

    @callsback
    def join_chat(self, convo, room_name = None, server = None, callback = None):
        if convo.type == 'sb':
            return callback.success(convo)

        callback.error()

    @action()
    def search_for_contact(self):
        self.hub.launchurl('http://spaces.live.com/Default.aspx?page=Interests&mkt=en-us')

    @action()
    def address_book(self):
        self.hub.launchurl('http://mail.live.com/mail/ContactMainLight.aspx?n=')

    @action()
    def mobile_settings(self):
        self.hub.launchurl('http://mobile.live.com')

    @action()
    def my_profile(self):
        self.hub.launchurl('http://account.live.com')

    @action()
    def save_contact_list(self):
        pass

    @action()
    def load_contact_list(self):
        pass

    def contact_list_to_file(self):
        xml_str = '<?xml version="1.0"?>'
        messenger = util.xml_tag.tag('messenger')
        messenger.service = util.xml_tag.tag('service', name = '.NET Messenger Service')

        for bname in self.buddies:
            messenger.service.contactlist += util.xml_tag.tag('contact', bname)

        return xml_str + messenger._to_xml()

    def file_to_contact_list(self, f_obj):
        s = f_obj.read()
        t = util.xml_tag.tag(s)

        if isinstance(t.service, list):
            messenger = filter(lambda x: x['name'] == '.NET Messenger Service',
                               t.service)
            messenger = messenger[0] if messenger else None
        elif t.service['name'] == '.NET Messenger Service':
            messenger = t.service
        else:
            messenger = None

        if messenger is None: return []
        contacts = messenger.contactlist

        added_contacts = []
        for contact in contacts:
            bname = str(contact)
            b = self.get_buddy(bname)
            # add them all but only if they're not already in the list
            if b not in self.forward_list:
                self.add_buddy(contact)
                added_contacts.append(contact)


        # let caller know which were added
        return added_contacts

    def on_received_oims(self, oims = None):

        if oims is None:
            oims = self.oims

        while oims:
            oim = oims.pop(0)
            b = self.get_buddy(oim.email)
            conv = self.convo_for(b.name)
            conv.received_message(b, unicode(oim.msg), offline = True, timestamp = oim.time, content_type = 'text/plain')

    def on_recv_sms(self, phone, message):
        b = self.get_buddy(phone)
        c = self.convo_for(b)
        c.on_message_recv(b.name, message, sms = True)

    def on_bicon_info(self, name, msnobj):

        buddy = self.get_buddy(name)
        if isinstance(msnobj, basestring):
            buddy.icon_disabled = False
            buddy.setnotifyif('icon_hash', msnobj)
        else:
            buddy.msn_obj = msnobj

            if msnobj is None:
                buddy.icon_disabled = True
                buddy.setnotifyif('icon_hash', '')
            elif int(msnobj.type) == 3:
                buddy.icon_disabled = False
                buddy._icon_disabled_until = 0
                buddy.setnotifyif('icon_hash', msnobj.sha1d.decode('base64'))

    ### Features not supported by MSN

    def send_direct_IM_req(self, *args):
        log.warning('MSN does not support send_direct_IM_req yet')
        print '%s%s' % (util.get_func_name(), repr(args))

    def send_buddy_list_request(self, *args):
        log.warning('MSN does not support send_buddy_list_request yet')
        print '%s%s' % (util.get_func_name(), repr(args))

    ### End unsupported features


    @callsback
    def _get_default_p2p_transport(self, bname, callback = None):
        return self.convo_for(bname, callback = callback)

#############################################################################################
#
#   Determine common signature for the following functions
#
#############################################################################################

    def chat_with(self, buddy):
        ###TODO: Use conversation manager?
        '''
        chat_with(buddy)

        Chat with a buddy. Ensures that a conversation exists that has buddy in it
        (or at least, one that is capable of inviting buddy when appropriate).

        @param buddy: The C{buddy} to chat with
        @type  buddy: L{msn.Buddy}
        '''

        self.convo_for(buddy.name)

    @callsback
    def convo_for(self, bname, sb = None, callback = None):
        '''
        convo_for(bname)

        Returns the conversation for a buddy with name bname, creating it if necessary

        @param bname: name of the buddy to get a conversation for.
        @type  bname: basestring (passport)

        @rtype:   L{msn.Conversation}
        @returns: A conversation for the buddy
        '''
        if sb is None:
            return self._find_sb(bname, sb, callback)
        else:
            return self._create_conv(bname, sb, callback)

    def find_conv(self, bname):
        is_circle = is_circle_name(bname)
        buddy = self.get_buddy(bname)
        for conv in self._conversations[:]:
            if conv.ischat and not is_circle:
                continue
            if conv.ischat and is_circle and buddy.name == conv._chatbuddy:
                return conv

            if buddy.name == getattr(conv, '_chat_target_name', getattr(conv, '_chatbuddy', conv.buddy.name)):
                return conv

            if buddy.name == self.self_buddy.name:
                if len(conv._clean_list()) == 1:
                    return conv
                else:
                    continue

            if buddy in conv.room_list:
                return conv
            elif bname in conv._clean_list():
                return conv

        return None

    def _find_sb(self, bname, sb, callback):
        log.info('Finding conversation for %s', bname)
        bname = getattr(bname, 'name', bname)
        buddy = self.get_buddy(bname)

        conv = self.find_conv(bname)

        if bname == self.self_buddy.name:
            if conv is None:
                return self._create_conv(bname, sb, callback)
            else:
                callback.success(conv)
                return conv

        if conv is not None:
            if conv.ischat:
                callback.success(conv)
                return conv

            if buddy in conv.room_list:
                if sb is not None:
                    conv._set_switchboard(sb)
                    conv.connect(callback = callback)
                    callback.success(conv)
                return conv
            elif bname in conv._clean_list():
                log.info("%r already in %r's clean_list. disconnecting %r", bname, conv, conv)
                self._conversations.remove(conv)
                conv.Disconnect()
                conv.exit()
                conv = None
            else:
                conv = None

        return self._create_conv(bname, sb, callback)

    @callsback
    def rejoin_chat(self, old_conversation, callback = None):
        bud = old_conversation._chatbuddy
        conf = self.convo_for(bud, callback = callback)
        connect = getattr(conf, 'connect', None)
        if connect is not None:
            connect()

    @callsback
    def make_chat_and_invite(self, buddies_to_invite, convo = None, room_name = None, server = None, notify = False, callback = None):
        if convo is None:
            buds = filter(lambda b: b != self.self_buddy, buddies_to_invite)
            conf = self._create_conv_invite(buds, callback = callback)
            conf.connect() # connect now explicitly

            if notify:
                from common import profile
                profile.on_entered_chat(conf)
        else:
            buds = filter(lambda b: b != self.self_buddy and b not in convo.room_list, buddies_to_invite)
            for b in buds:
                self.invite_to_chat(b, convo)


    def get_conversation_class(self):
        if self.version < 'MSNP21':
            return msn.Conversation
        else:
            import msn.p21.MSNP21Conversation as p21
            return p21.MSNP21Conversation

    def _create_conv(self, bname, sb, connect_cb):
        return self._create_conv_invite((bname,), sb = sb, success = connect_cb)

    @callsback
    def _create_conv_invite(self, buddies, sb = None, callback = None):
        buddies = tuple(getattr(b, 'name', b) for b in buddies)
        log.info('_create_conv_invite: buddies=%r, connect_cb=%r', buddies, callback)
        c = self.get_conversation_class()(self, switchboard = sb, to_invite = buddies)
        c._connect_cb = callback
        self.register_conv(c)
        return c

    def register_conv(self, c):
        if c not in self._conversations:
            self._conversations.append(c)

    def unregister_conv(self, c):
        log.info('removing %r from %r', c, self._conversations)
        try:
            while c in self._conversations:
                self._conversations.remove(c)
        except ValueError, e:
            pass

        if not self._conversations and self.disconnecting:
            self._check_offline()

    @callsback
    def add_buddy(self, bname, g_id, pos = 0, service = None, callback = None):
        '''
        @callsback
        add_buddy(bname, gname, pos=0)

        Used to add a buddy to a group

        @param bname:    passport of the buddy to add
        @type  bname:    basestring (passport)

        @param gname:    id of the group to add
        @type  gname:    L{msn.GroupId}

        @param   pos:    Ignored. Present for interface adherence. (Not supported by protocol)
        @type    pos:    int
        @default pos:    0
        '''

        log.debug('add_buddy(%r, %r, %r, %r, %r)', bname, g_id, pos, service, callback)

        if bname == self.self_buddy.name and self.version < "MSNP21":
            log.error('Not adding self buddy, that\'s silly')
            callback.success()
            return

        group = self.groups[g_id]
        buddy = self.get_buddy(bname)

        def setstatus(*a, **k):
            if buddy.status == 'unknown':
                buddy.setnotifyif('status', 'offline')

        real_success = callback.success
        real_success += setstatus
        callback.success = Delegate()
        callback.success += lambda * a, **k: real_success(group)

        if buddy not in self.forward_list:
            success = lambda * a, **k: self.add_buddy(bname, g_id, pos, service = service, callback = callback)
            log.info('Adding %s to forward list and allow list', buddy)
            self.ns._add_buddy_to_list(buddy.name, service = service, success = success, error = callback.error)
            self.ns._add_buddy('AL', buddy.name, buddy.id, None, service = service)
            return

        #check if they're in the group already
        if msn.Contact(buddy, group.id) in group:
            print 'buddy in group already!'
            return callback.success()

        if group.id == None:
            g_id = None

        log.info('Adding %s to group %r', buddy, g_id)

        self.ns._add_buddy_to_group(buddy.name, buddy.id, g_id, service = service or buddy.type, callback = callback)

#    def on_add_buddy(self, buddy, group):
#        '''
#        on_add_buddy(buddy, group)
#
#        Called when a buddy is successfully added to a group
#
#        @param buddy:    Buddy object added to group
#        @type  buddy:    L{msn.Buddy}
#
#        @param group:    Group object buddy was added to
#        @type  group:    L{msn.Group}
#        '''
#        pass

    @callsback
    def remove_buddy(self, buddy_id, callback = None):
        '''
        @callsback
        remove_buddy(contact, group)

        Remove contact from group

        @param contact: the contact to remove from group
        @type  contact: L{msn.Contact}

        @param group:   the group to remove contact from
        @type  group:   L{msn.Group}
        '''

        bname, gid = buddy_id

        if bname == self.self_buddy.name and self.version < 'MSNP21':
            log.error("Not going to try to remove self buddy, that's silly")
            callback.success()
            return

        if gid == None:
            gid = None

        buddy = self.get_buddy(bname)
        bid = buddy.id

        if gid is None:
            return self.ns._remove_buddy('FL', buddy, gid, service = buddy.service)

        # Ugh, fake group. This is really just a display hack so pretend we actually succeeded and just take it out.
        if gid == 'Root':
            g = self.get_group(gid)
            b = get([_b for _b in g if _b.id == buddy_id], 0, None)
            if b is not None:
                print 'removing %r from fake group' % (b,)
                g.remove(b)
            self.root_group.notify()

            buddy = b.buddy
            if not self.groups_containing_buddy(buddy):
                return self.ns._remove_buddy('FL', buddy, None, service = buddy.service, callback = callback)
            else:
                return callback.success()

        return self.ns._remove_buddy_from_group(bname, bid, gid, service = buddy.service, callback = callback)

    def on_remove_buddy(self, contact, group):
        '''
        on_remove_buddy(contact, group)

        contact has been removed from group

        @param contact: the contact that was removed from group
        @type  contact: L{msn.Contact}

        @param group:   the group contact was removed from
        @type  group:   L{msn.Group}
        '''
        pass

    @callsback
    def authorize_buddy(self, bname, authorize = True, username_added = None, callback = None):
        '''
        @callsback
        authorize_buddy(bname, authorize=True)

        Authorize a buddy (or block them), removing them from the pending list.

        @param bname:     name of the buddy to authorize
        @type  bname:     basestring (passport)

        @param   authorize: authorize them?
        @type    authorize: bool
        @default authorize: True
        '''

        buddy = self.get_buddy(bname)
        self.ns._authorize_buddy(buddy, authorize, callback = callback)

    def on_authorize_buddy(self, buddy, authed):
        '''
        on_authorize_buddy(buddy, authed)

        Called when a buddy is authorized (or de-authorized)

        @param buddy:   buddy who was (de)authorized
        @type  buddy:   L{msn.Buddy}

        @param authed:  True if they were authorized, False otherwise
        @type  authed:  bool
        '''
        self.waiting_for_auth.discard(buddy)

    @callsback
    def block_buddy(self, buddy, block = True, callback = None):
        '''
        @callsback
        block_buddy(buddy, block=True)

        Block buddy if block is True else unblock

        @param buddy:  the buddy to block/unblock
        @type  buddy:  L{msn.Buddy}

        @param   block:  Block them?
        @type    block:  bool
        @default block:  True
        '''
        if block: return self.ns._block_buddy  (buddy, callback = callback)
        else:     return self.ns._unblock_buddy(buddy, callback = callback)

    @callsback
    def unblock_buddy(self, buddy, callback = None):
        '''
        @callsback
        unblock_buddy(buddy)

        Unblock buddy. Equivalent to block_buddy(buddy, False)

        @param buddy: the buddy to unblock
        @type  buddy: msn.Buddy
        '''
        return self.block_buddy(buddy, False, callback = callback)

    def on_block_buddy(self, bid, blocked):
        '''
        on_block_buddy(buddy, blocked)

        Called when a buddy is blocked or un-blocked

        @param buddy:   buddy who was (un-)blocked
        @type  buddy:   L{msn.Buddy

        @param blocked:  True if they were blocked, False otherwise
        @type  blocked:  bool
        '''
        self.get_buddy(bid).notify('blocked', not blocked, blocked)

    @callsback
    def move_buddy(self, contact, to_groupname, from_groupname = None, pos = 0, callback = None):
        '''
        @callsback
        move_buddy(contact, to_groupname, from_groupid=None, pos=0)

        Move a buddy to group with name to_groupname, creating if necessary. The buddy
        is moved from group with id from_groupid (if it is provided), else the root group
        (or is added if buddy is not in root group and from_groupid is not provided)

        @param contact:       Contact to be moved
        @type  contact:       L{msn.Contact}

        @param to_groupname:  Name of the group to move contact to
        @type  to_groupname:  basestring

        @param from_groupid:  GroupId of the group the contact is moving from
        @type  from_groupid:  L{msn.GroupId}

        @param   pos:        Ignored. Present for interface adherence. (Not supported by protocol)
        @type    pos:        int
        @default pos:        0
        '''

        togroup = self.get_group(to_groupname)
        fromgroup = self.get_group(from_groupname)

        buddy = self.get_buddy(contact.name)

        if buddy.name == self.self_buddy.name and self.version < 'MSNP21':
            log.error("Not going to try to move self buddy, that's silly")
            callback.success()
            return

        if fromgroup and ((fromgroup is not self.root_group) or from_groupname is not None):
            def success(*a, **k):
                self.remove_buddy(contact.id, callback = callback)
        else:
            success = callback.success

        self.add_buddy(buddy.name, togroup.id,
                       success = success,
                       error = callback.error)

    @callsback
    def set_display_name(self, new_alias, callback = None):
        '''
        @callsback
        @set_display_name(new_alias)

        Set the friendly name other clients will see.

        @param new_alias: the new alias to set
        @type  new_alias: basestring
        '''
        return self.ns._set_display_name(new_alias or self.username, callback)

    def on_set_display_name(self, alias):
        '''
        on_set_display_name(new_alias)

        Called when display name has been set.

        @param alias: the C{alias} that was set
        @type  alias: basestring
        '''

        log.info('Got response for display name set')

    @callsback
    def set_remote_alias(self, buddy, new_alias, callback = None):
        '''
        @callsback
        set_remote_alias(buddy, new_alias)

        Set the remote alias of a buddy.

        @param buddy:     The C{buddy} whose alias to set
        @type  buddy:     L{msn.Buddy}

        @param new_alias: Alias to set for C{buddy}
        @type  new_alias: basestring
        '''
        return self.ns._set_remote_alias(buddy, new_alias, callback)

    def on_set_remote_alias(self, buddy, alias):
        '''
        on_set_remote_alias(buddy, alias)

        Called when the remote C{alias} of C{buddy} has been set.

        @param buddy: The buddy whose alias was set
        @type  buddy; L{msn.Buddy}

        @param alias: The alias that was set
        @type  alias: basestring
        '''
        pass

    @callsback
    def add_group(self, gname, callback = None):
        '''
        @callsback
        add_group(gname, callback)

        Add a group of name C{gname} to the buddy list

        @param gname: name of group to add
        @type  gname: basestring
        '''
#        self.groups_to_add[gname] = callback.success
#        callback.success = lambda group: (log.debug('received response for adding group %r: %r', gname, group)
        return self.ns._add_group(gname, callback = callback)

# This is unused currently
#    def on_add_group(self, group):
#        '''
#        on_add_group(group)
#
#        Called when a group is added to the buddylist
#
#        @param group: The C{group} object that was added
#        @type  group: L{msn.Group}
#
#        '''
#        f = self.groups_to_add.pop(group.name, lambda g:None)
#        f(group)

    @callsback
    def remove_group(self, group_id, callback = None):
        '''
        @callsback
        remove_group(group)

        Remove group from the buddylist, pushing any buddies in it to the root group

        @param group: The C{group} to be removed
        @type  group: L{msn.Group}
        '''


        from util import CallCounter
        from util.callbacks import Callback

        group = self.groups[group_id]

        if group_id in ('Root', None):
            log.info('It\'s a fake root group! Removing all buddies from it and then wiping it out.')
            for contact in list(group):
                if len(self.groups_containing_buddy(contact.buddy)) == 1:
                    self.remove_buddy((contact.buddy.name, None))

            group[:] = []
            self.groups[None].remove(group)
            self.groups.pop(group_id)
            return callback.success()

        log.info('Going to remove group %r with id %r', group, group_id)

        if not len(group):
            log.info('    that group is already empty. Removing....')
            return self.ns._remove_group(group_id, callback = callback)

        log.info('    that group has %d things in it, going to make a call counter and remove all of them seperately', len(group))
        cc = CallCounter(len(group), lambda * a, **k: self.ns._remove_group(group_id, callback = callback))

        cb = Callback(success = (lambda * a, **k: cc()), error = callback.error)

        for contact in list(group):
            __, gid = contact.id
            bid = str(contact.buddy.guid)
            name = contact.buddy.name
            log.info('    Removing buddy %r (name=%r, id=%r) from group %r (id=%r)', contact.buddy, name, bid, group, group_id)
            if gid is None:
                self.ns._remove_buddy('FL', contact.buddy, None, service = contact.buddy.service, callback = cb)
            else:
                self.ns._remove_buddy_from_group(name, bid, gid, service = contact.buddy.service, callback = cb)

    def on_remove_group(self, group):
        '''
        @callsback
        on_remove_group(group)

        Called when a group is removed from the buddylist

        @param group: The C{group} that was removed
        @type  group: L{msn.Group}
        '''
        self.groups.pop(group.id, None)
        if group in self.root_group:
            self.root_group.remove(group)
        self.root_group.notify()

    @callsback
    def set_status_message(self, message, callback = None):
        '''
        @callsback
        set_status_message(message)

        Sets status message to C{message}

        @param message: Status message to set.
        @type  message: basestring
        '''
        return self.ns._set_status_message(message, callback = callback)

    def on_set_status_message(self, message):
        '''
        on_set_status_messaage(message)

        Called when status message is successfully set

        @param message: the message that has been set
        @type  message: basestring
        '''
        pass

    @callsback
    def get_profile(self, buddy, callback = None):
        '''
        @callsback
        get_profile(buddy)

        Retrieve buddy's profile

        @param buddy: The buddy whose profile to get
        @type  buddy: L{msn.Buddy}
        '''
        return self.ns._get_profile(buddy, callback)

    def on_get_profile(self, buddy, profile):
        '''
        on_get_profile(buddy)

        Called when a buddy's profile is retrieved

        @param buddy:   The buddy whose profile was retrieved
        @type  buddy:   L{msn.Buddy}

        @param profile: The profile that was retrieved
        @type  profile: The raw data that was received
        '''
        pass

    @callsback
    def rename_group(self, groupid, name, callback = None):
        '''
        @callsback
        rename_group(group, name)

        Change the name of a group

        @param group: Group to be renamed
        @type  group: L{msn.Group}

        @param name:  new name of the group
        @type  name:  basestring
        '''

        return self.ns._rename_group(groupid, name, callback = callback)

    def on_rename_group(self, groupid, name):
        '''
        on_rename_group(group, name)

        Called when a group has been renamed

        @param group: Group that was renamed
        @type  group: L{msn.Group}

        @param name:  The current name of the group
        @type  name:  basestring
        '''
        self.groups[groupid].setnotifyif('name', name)

    @callsback
    def set_buddy_icon(self, icon = None, callback = None):
        '''
        @callsback
        set_buddy_icon(icon=None)

        Sets the client's buddy icon to icon
        If icon is None, there will be an attempt to retreive the cached icon
        for self_buddy from disk. If it is not found, then the icon is cleared.

        This function resizes and re-formats the icon to a 96x96 png, as per
        MSN "spec". It will be saved to disk temporarily for this operation.

        @param   icon: The icon to set
        @type    icon: NoneType or string (binary data)
        @default icon: None
        '''

        import os.path
        import io
        log.info('setting buddy icon: %d bytes', len(icon or ''))
        pth = icon_path_for(self.self_buddy)
        icon_data = icon
        if icon_data is None:
            if os.path.exists(pth):
                icon_file = open(pth, 'rb')
            else:
                icon_file = None

        else:
            icon_file = io.BytesIO(icon_data)

        if icon_file is None:
            self.icon_obj = None
            icon_data = None

        if (icon_file, icon_data) != (None, None): # make sure both aren't None

            if icon_file is not None:
                import wx
                icon_img = wx.ImageFromString(icon_file.read())
                if not icon_img.IsOk(): return

                if (icon_img.Size.x, icon_img.Size.y) > (96, 96):
                    icon_img.Rescale(96, 96, wx.IMAGE_QUALITY_HIGH)
                    if not icon_img.IsOk(): return

                if not os.path.exists(os.path.split(pth)[0]):
                    os.makedirs(os.path.split(pth)[0])
                temp_fn = os.path.join(os.path.split(pth)[0], 'temp_resize')
                icon_img.SaveFile(temp_fn, wx.BITMAP_TYPE_PNG)

                with open(temp_fn, 'rb') as f:
                    icon_data = f.read()

                os.remove(temp_fn)

            if icon_data is not None:
                hash = hashlib.sha1(icon_data).digest()
                self.self_buddy.cache_icon(icon_data, hash)

        sta = self.status_to_code.get(self.status, 'AWY')
        cli = self.client_id
        return self.ns._set_buddy_icon(sta, cli, icon_data, callback)

    def on_set_buddy_icon(self, icon):
        '''
        on_set_buddy_icon(data)

        Called when the buddy icon has been set

        @param data: The image data the icon has been set to
        @type  data: string (binary data)
        '''
        pass

    @callsback
    def get_buddy_icon(self, name, callback = None):
        '''
        @callsback
        get_buddy_icon(name)

        Get the buddy icon for buddy with name C{name}

        @param name: The name of the buddy whose icon to get
        @type  name: string (passport)
        '''
        buddy = self.get_buddy(name)

        if buddy is self.self_buddy:
            log.debug("Not requesting self-buddy icon")
            return

        if not buddy.online:
            callback.error()
            log.debug("Not requesting offline buddy icon")
            return

        if getattr(buddy, 'icon_disabled', False) and getattr(buddy, '_icon_disabled_until', 0xffffffff) > time.time():
            callback.error()
            log.debug("Not requesting disabled buddy icon")
            return

        bname = buddy.name

        log.info('Adding %r to pending icon requests', bname)
        self._pending_icon_requests[bname] = callback
        self._process_icon_request()

    def _process_icon_request(self):
        if len(self._requesting_icons) >= common.pref('msn.max_icon_requests', type = int, default = 2):
            log.info('Too many active buddy icon requests')
            return

        try:
            bname, callback = self._pending_icon_requests.popitem()
        except KeyError:
            log.info('No pending buddy icon requests')
            return

        buddy = self.get_buddy(bname)

        if bname in self._requesting_icons:
            log.info('already requesting icon for %r, trying then next one.', buddy)
            return self._process_icon_request()

        def _request_resolved():
            self._requesting_icons.discard(bname)
            self._pending_icon_requests.pop(bname, None)
            self._process_icon_request()

            if buddy._getting_image:
                cancel_get('timeout')

        def on_icon_receive(objtrans, data):
            if data is not None:
                buddy.cache_icon(data, hashlib.sha1(data).digest())
                log.info('Got buddy icon for %r', buddy)

        callback.success += on_icon_receive

        def cancel_get(objtrans = None, by_who = None):
            log.info('Failed to get buddy icon for %r: transfer object: %r', buddy, objtrans)
            if not buddy.icon_disabled:
                buddy.icon_disabled = True
                # Don't try again for 10 minutes
                buddy._icon_disabled_until = time.time() + (10 * 60)
            buddy.icon_bitmap = None
            buddy._cached_hash = None
            buddy._getting_image = False

            #_request_resolved()

        callback.error += cancel_get
        failsafe_timer = util.Timer(60, _request_resolved)
        failsafe_timer.start()

        self._requesting_icons.add(bname)
        log.info('Requesting icon for %r', buddy)

        self.P2PHandler.RequestMsnObject(getattr(buddy, 'contact', buddy), buddy.msn_obj, callback = callback)


    def on_get_buddy_icon(self, buddy, icon):
        '''
        on_get_buddy_icon(buddy, icon)

        @param buddy: The buddy object whose icon we got
        @type  buddy: L{msn.Buddy}

        @param icon:  The icon data we found for buddy
        @type  icon:  string (binary data)
        '''
        pass

    @callsback
    def send_file(self, buddy, fileinfo, callback = None):
        '''
        @callsback
        send_file(buddy, filepath)

        Begins a file transfer session with buddy to send file located at
        filepath to them.

        @param buddy:    The buddy to send the file to
        @type  buddy:    L{msn.Buddy}

        @param filepath: Absolute path to the file
        @type  filepath: string (filepath)
        '''

        bname = get(buddy, 'name', buddy)
        buddy = self.get_buddy(bname)
        if buddy == self.self_buddy:
            callback.error()

        return self.P2PHandler.SendFile(buddy.contact, fileinfo.path, fileinfo.obj)

    def on_send_file(self, buddy, filepath):
        '''
        on_send_file(buddy, filepath)

        @param buddy:    The buddy the file was sent to
        @type  buddy:    L{msn.Buddy}

        @param filepath: the local address of the file
        @type  filepath: string (filepath)
        '''
        pass

    @callsback
    def send_sms(self, phone, message, callback = None):
        '''
        @callsback
        send_sma(phone, message)

        @param phone:   The phone number to send the message to
        @type phone:    string (Phone number - all digits, may start with '+')
        @param message: The message to send
        @type message:  string (may have length limitations)
        '''
        #TODO: See revision 6350 for reference

#        print 'Totally not sending sms to %s (message was %s)' % (phone, message)
#        return

        self.ns._send_sms(phone, message, callback)

#        for convo in self.conversations:
#            if convo.type == 'sms' or phone in (convo.buddy.name, convo.buddy.phone_mobile):
#                convo.buddy_says(convo.buddy, message)
#                break
#        else:
#            #somehow we sent an sms without a conversation?!
#            pass

    def on_send_sms(self, phone, message):
        '''
        on_send_sms(phone, message)

        @param phone:   Phone number message was sent to
        @type phone:    string
        @param message: The message that was sent
        @type message:  string
        '''
        pass

    @callsback
    def add_to_block(self, buddy, callback = None):
        if isinstance(buddy, basestring):
            buddy = self.get_buddy(buddy)

        self.ns.add_to_block(buddy, callback = callback)

    @callsback
    def rem_from_block(self, buddy, callback = None):
        if isinstance(buddy, basestring):
            buddy = self.get_buddy(buddy)

        self.ns.rem_from_block(buddy, callback = callback)

    @callsback
    def add_to_allow(self, buddy, callback = None):
        if isinstance(buddy, basestring):
            buddy = self.get_buddy(buddy)

        self.ns.add_to_allow(buddy, callback = callback)

    @callsback
    def rem_from_allow(self, buddy, callback = None):
        if isinstance(buddy, basestring):
            buddy = self.get_buddy(buddy)

        self.ns.rem_from_allow(buddy, callback = callback)

    def add_new_buddy(self, buddyname, groupname, service = None, alias = None):
        if service == 'yahoo' and self.version < 'MSNP14':
            return False

        if service == 'yahoo' and not '@yahoo' in buddyname:
            buddyname = buddyname + '@yahoo.com'
        return protocol.add_new_buddy(self, buddyname, groupname, service, alias)

    def get_local_sockname(self):
        return self.ns.get_local_sockname()

    def allow_message(self, buddy, mobj):
        super = protocol.allow_message(self, buddy, mobj)
        if super: # Don't want to catch None or False here
            return super

        if buddy is None:
            return True

        if buddy.blocked:
            return False

        if super is None:
            return True

    def get_contact_info(self, name):
        contact_list = getattr(self.ns, 'contact_list', None)
        if contact_list is None:
            return self.get_buddy(name)
        else:
            return contact_list.GetContact(name)

    def get_machine_guid(self):
        return self.ns.get_machine_guid()

    def on_circle_member_joined(self, circle_id, buddy_name):
        members = self.circle_buddies[circle_id].Members
        if buddy_name not in members:
            members.append(buddy_name)

        log.info("Got new member for circle: %r in %r", buddy_name, circle_id)

    def on_circle_roster_remove(self, circle_id, ctype, name):
        circle = self.circle_buddies[circle_id]

        if name in circle.Members:
            circle.Members.remove(name)
        if name in circle.Pending:
            circle.Pending.remove(name)

        convo = self.find_conv(circle_id)

        bname = name.split(':', 1)[-1]

        if convo is not None:
            convo.invite_failure(bname)
            convo.on_buddy_leave(bname)

    def on_circle_roster_recv(self, circle_id, ctype, names, pending_names, nonpending_names, full):
        circle = self.circle_buddies[circle_id]
        if full:
            circle.Members = names
            circle.Pending = pending_names
        else:
            circle.Members = list(set(circle.Members) | set(names))
            circle.Pending = list(set(circle.Pending) | set(pending_names))

        conv = self.find_conv(circle_id)
        for name in nonpending_names:
            if name in circle.Pending:
                circle.Pending.remove(name)

        if conv is not None:
            bnames_in_room = [x.name for x in conv.room_list]
            log.debug("Names in room: %r / circle names: %r", bnames_in_room, circle.buddy_names)
            for name in circle.buddy_names:
                if name not in bnames_in_room:
                    conv.buddy_join(name)

        my_id = '1:%s' % self.self_buddy.name

        from common import netcall
        def on_yes():
            netcall(lambda: (common.profile.on_entered_chat
                             (convo = self.accept_circle_invite(circle_id = circle_id, ctype = ctype))))

        def on_no():
            netcall(lambda: self.reject_circle_invite(circle_id = circle_id, ctype = ctype))

        log.debug("Got names for circle %r roster: %r", circle_id, names)
        if my_id in pending_names and full and len(names) > 1:
            # on chat invite
            common.profile.on_chat_invite(protocol = self,
                                          buddy = None,
                                          message = None,
                                          room_name = circle_id,
                                          on_yes = on_yes,
                                          on_no = on_no)

        elif my_id in pending_names and full and len(names) == 1:
            # This is the result from our room creation. "accept" it
            on_yes()

    def accept_circle_invite(self, circle_id, ctype):
        self.ns.JoinCircleConversation(circle_id)
        return self.convo_for(circle_id)

    def reject_circle_invite(self, circle_id, ctype):
        self.ns.leave_temp_circle(circle_id)

    @action(lambda self, *a, **k: (self.state == self.Statuses.ONLINE) or None)
    def CreateCircle(self):
        hooks.notify("digsby.msn.circle_create_prompt", success = self.DoCreateCircle)

    def DoCreateCircle(self, name):
        self.ns.CreateCircle(name)

    def LeaveCircle(self, circle_id_pair):
        circleId, _gid = circle_id_pair
        circle_contact = self.ns.GetCircle(circleId)
        circle_buddy = self.circle_buddies.get(circle_contact.account)

        abid = circle_contact.abid

        admins = circle_buddy.get_role_names('Admin')
        if len(admins) == 1 and self.self_buddy.name in admins:
            url_cid = ''.join(abid.split('-'))[-16:]
            self.hub.launchurl('http://cid-%s.groups.live.com/options/deletegroup/' % url_cid)
        else:
            self.ns.LeaveCircle(abid)

    def appear_offline_to(self, name):
        self.ns.appear_offline_to(name)

    def appear_online_to(self, name):
        self.ns.appear_online_to(name)

    def OnInvitationReceived(self, session):
        import msn.P2P.P2PFileTransfer as FT
        activity = session.App
        log.info("OnInvitationReceived(session = %r)", session)
        if activity.EufGuid == FT.FileTransfer.EufGuid:
            self.hub.on_file_request(self, activity)
