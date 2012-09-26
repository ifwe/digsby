'''
A Jabber connection to the Digsby server.
'''
from __future__ import with_statement
from peak.util.imports import lazyModule
import datetime
from digsby.loadbalance import DigsbyLoadBalanceAPI, DigsbyLoadBalanceManager
callbacks      = lazyModule('util.callbacks')
mapping        = lazyModule('util.primitives.mapping')
funcs          = lazyModule('util.primitives.funcs')
error_handling = lazyModule('util.primitives.error_handling')
hook_util      = lazyModule('util.hook_util')
util_threads   = lazyModule('util.threads')
import common
import sys, traceback
from common import pref, netcall
from hashlib import sha256
import jabber
from jabber import JID
from pyxmpp.presence import Presence
from pyxmpp.roster import RosterItem
from operator import itemgetter
import digsby
from .digsbybuddy import DigsbyBuddy
import random
import string
import blobs

import simplejson

from logging import getLogger
log = getLogger('digsbylogin')

def_cb = lambda *a, **k:None

LOAD_BALANCE_ADDRS = [
                      ('login1.digsby.org', 80),
                      ('login2.digsby.org', 80)
                     ]

JABBER_SRVS_FALLBACK = [
                        'api1.digsby.org',
                        'api2.digsby.org',
                        ]

from jabber.JabberConversation import get_message_body, Conversation,\
    get_message_timestamp

class DigsbyProtocol(jabber.protocol):
    buddy_class = DigsbyBuddy

    bots = jabber.protocol.bots | set((JID('digsby.org'),))

    class Statuses(jabber.protocol.Statuses):
        SYNC_PREFS = _('Synchronizing Preferences...')
        #LOAD_SKIN  = _('Loading Skin...')
        AUTHORIZED = _('Synchronizing...')

    name = 'digsby'

    status_state_map = {
        'available':      'normal',
        'away':           'dnd',
        'free for chat':  'chat',
        'do not disturb': 'dnd',
        'extended away':  'xa'
    }

    def get_login_servers(self, username=''):
        srvs = list(LOAD_BALANCE_ADDRS)
        load_server = getattr(getattr(sys, 'opts', None), 'loadbalancer', None)
        if load_server is not None:
            ls = load_server.split(':')
            if len(ls) != 2:
                ls = (load_server, 80)
            else:
                ls = (ls[0], int(ls[1]))
            srvs = [ls]
        random.shuffle(srvs)
        #idle
        DigsbyLoadBalanceManager(profile = self.profile, username=username, servers=srvs, success=self.lb_success, error=self.lb_error,
                                 load_server=load_server, initial=self.initial).process_one()

    def lb_success(self, lb_mgr, balance_info):
        loadbalanced_servers = balance_info.addresses
        strategy = balance_info.reconnect_strategy
        if strategy:
            self.offline_reason = self.Reasons.CONN_FAIL
            self.profile.balance_info = balance_info
            self.connect_opts['on_fail']()
        else:
            self.lb_finish(lb_mgr, loadbalanced_servers)

    def lb_error(self, lb_mgr):
        self.lb_finish(lb_mgr)

    def lb_finish(self, lb_mgr, loadbalanced_servers=None):
        #do fallback
        if not loadbalanced_servers:
            hosts = list(JABBER_SRVS_FALLBACK)
            random.shuffle(hosts)
            log.error("could not get server information from HTTP load interface. falling back to %r", hosts)
            ret = hosts
        else:
            ret = loadbalanced_servers
        #inject commandline
        opts_server = getattr(getattr(sys, 'opts', None), 'server', None)
        #commandline lb answer preempts commandline server
        opts_server = [opts_server] if (opts_server and not lb_mgr.load_server) else []
        self.finish_init(opts_server + ret)

    thread_id = 0
    def __init__(self, username, password, profile, user, server, login_as='online',
                 resource="Digsby", priority=5,
                 **opts):
        self.login_opts = l = mapping.Storage()
        self.initial = opts.pop('initial', None)
        #'#("digsby.org",5555)
        l.cid = "foo"
        l.jid = JID(username + "@digsby.org")
        l.username = username

        l.password = sha256(password.encode('utf-8')).digest()

        self.profile  = profile

        #initialize the OneShotHook
        hook_util.OneShotHook(self.profile, 'digsby.accounts.released.async').check_registered()

        l.user = user
        l.server = server
        l.login_as = login_as
        alphanum = string.letters + string.digits
        l.resource = resource + "." + "".join(random.choice(alphanum) for x in xrange(6))
        l.priority = priority
        l.opts = opts

        common.StateMixin.__init__(self)

        jabber.protocol.__init__(self, l.jid.as_utf8(), "fakepw", l.user, ('fakehost', 1337),
                                 login_as = l.login_as,
                                 resource = l.resource,
                                 priority = l.priority,
                                 **l.opts)
        self.blobhashes = {}

        self.video_chats = {}
        self.video_chat_buddies = {}

        self._idle = None

    def message(self, message):
        if self.video_widget_intercept(message):
            # Messages from special resource IDs on guest.digsby.org are routed to
            # video chat IM windows.
            return
        else:
            return jabber.protocol.message(self, message)

    def add_video_chat(self, resource, video_chat):
        log.info('associating video widget resource %r with %r', resource, video_chat)
        self.video_chats[resource] = video_chat
        self.video_chat_buddies[video_chat.buddy_info] = video_chat

    def remove_video_chat(self, resource):
        log.info('removing video resource %r', resource)

        try:
            video_chat = self.video_chats.pop(resource)
            del self.video_chat_buddies[video_chat.buddy_info]
        except KeyError:
            log.warning('tried to remove video chat token %s, but not found', resource)

    def send_message_intercept(self, buddy, message):
        if not self.video_chat_buddies: return

        from contacts.buddyinfo import BuddyInfo
        binfo = BuddyInfo(buddy)

        if binfo in self.video_chat_buddies:
            log.debug('intercepted outgoing videochat message')
            video_chat = self.video_chat_buddies[binfo]
            video_chat.send_im(message)

    def video_widget_intercept(self, message):
        'Reroutes messages from video widgets.'

        video_buddy = self._video_buddy_for_message(message)
        if video_buddy is None:
            return False
        elif video_buddy is True:
            return True

        body = get_message_body(message)
        log.info('intercepted video widget message')
        log.info_s('message is %r', body)

        if body:
            buddy = video_buddy.buddy()
            if buddy is None:
                log.critical('got video widget message, but linked buddy is gone')
                log.critical('buddy info was %r', video_buddy)
                return True

            convo = buddy.protocol.convo_for(buddy)
            if convo.received_message(buddy, body):
                Conversation.incoming_message(convo)

        return True # TODO: typing notifications?

    def _video_buddy_for_message(self, message):
        'Returns a video buddy info for a message object.'

        _from = message.get_from()

        # Video widgets are always on the guest server.
        if _from.domain != 'guest.digsby.org':
            return log.info('not a video widget: domain is %r', _from.domain)

        # Video widgets' resources always start with "video."
        resource = _from.resource
        if not resource.startswith('video.'):
            return log.info("resource does not start with video: %s", resource)
        else:
            # strip off the video. part
            resource = resource[6:]

        # Do we have a matching resource ID for a video widget?
        video_chat = self.video_chats.get(resource, None)
        if video_chat is None:
            log.info('ignoring video widget message--no video chat open client side (resource=%s)' % resource)
            return True

        # set the JID in the video chat object so it can forward messages to the widget as well
        video_chat.widget_jid = _from

        video_buddy = video_chat.buddy_info
        if video_buddy is None:
            log.info('ignoring message from unknown video widget: JID=%s, message=%r', _from, get_message_body(message))
            return None

        return video_buddy

    def remove_widget_buddies(self, widget):
        '''
        Removes all JIDs in the group specified by the given widget.
        '''
        group = widget.title

        try:
            buddies = self.buddies.values()
            for buddy in buddies:
                try:
                    if getattr(buddy, 'iswidget', False) and group in buddy.groups:
                        buddy.remove()
                except Exception:
                    pass
        except Exception:
            pass

    def finish_init(self, sock):
        self.hosts = sock
        lh = len(self.hosts)
        self.alt_connect_opts = alt_ops = []
        self.on_alt_no = 0

        add   = lambda **k: alt_ops.append(k)
        if getattr(getattr(sys, 'opts', None), 'start_offline', False) \
          and not pref('debug.reenable_online', type=bool, default=False):
            self.offline_reason = self.Reasons.CONN_FAIL
            return self.connect_opts['on_fail']()

#         add lots of places to connect
        for host in self.hosts:
            add(server = (host, 443),
                do_tls = True,
                require_tls = False,
                verify_tls_peer = False,
                do_ssl = False)

        for host in self.hosts:
            add(server = (host, 5222),
                do_tls = True,
                require_tls = False,
                verify_tls_peer = False,
                do_ssl = False)

        for host in self.hosts:
            add(server = (host, 5223),
                do_tls = False,
                require_tls = False,
                verify_tls_peer = False,
                do_ssl = True)

        l = self.login_opts
        getLogger('digsbylogin').info('got potential servers: %r', self.hosts)
        self.password = l.password
        self.finish_Connect()

    def filter_group(self, group):
        # Filter groups with all video widgets.

        # May be the root group--which might have Contacts and Groups.
        return group and all(getattr(contact, 'is_video_widget', False) for contact in group)

    def filter_contact(self, contact):
        return getattr(contact, 'is_video_widget', False)

    def Connect(self, register = False, on_success = None, on_fail = None, invisible = False):
        self.change_state(self.Statuses.CONNECTING)

        def on_fail(err=None, fail_cb=on_fail):
            log.info('on_fail in Connect')
            self.offline_reason = self.Reasons.CONN_FAIL
            self.setnotifyif('state', self.Statuses.OFFLINE)
            if fail_cb is not None:
                fail_cb()

        self.connect_opts = c = mapping.Storage(register = register,
                                        on_success = on_success,
                                        on_fail = on_fail,
                                        invisible = invisible)
        l = self.login_opts

        # Go find the load balancer; if you cannot, call on_fail
        self.get_login_servers(l.username)

    def finish_Connect(self):
        c = self.connect_opts
        on_fail = c.on_fail

        invisible = c.invisible
        #don't start with the defaults, start with the list created in finish_init
        return jabber.protocol._reconnect(self, invisible=invisible, do_conn_fail=False, error=on_fail)

    def session_started(self):
        #register/init blobs
        s = self.stream
        funcs.do(s.set_iq_set_handler("query", ns, self.profile.blob_manager.blob_set)
         for ns in blobs.ns_to_name.keys())
        s.set_iq_set_handler("query", digsby.accounts.DIGSBY_ACCOUNTS_NS, self.profile.account_manager.accounts_set)
        s.set_iq_set_handler("query", digsby.widgets.DIGSBY_WIDGETS_NS, self.incoming_widgets)

        s.set_message_handler('normal', self.conditional_messages_handler,
                              namespace = 'http://www.digsby.org/conditions/v1.0',
                              priority = 98)
        jabber.protocol.session_started(self)
        #simulates conditions in ticket #3186
        #if this is uncommented and the "have_connected" property below is removed
        #the connection will fail.

#        assert not getattr(self.profile, 'kill', False)
#        if not getattr(self, 'test_conn_killed', False): #see ticket #3186
#            self.test_conn_killed = 1
#            assert False

    def profile_has_connected(self):
        return getattr(self.profile, '_have_connected', False)

    @property
    def want_try_again(self):
        '''
        True if we've never started a session and we have other places left to try.
        '''
        #auth error == failed to connect for digsbyprotocol
        # auth error means the server is having trouble talking to it's database, or you
        # logged in from two places at once (race condition w/ login server)
        if not self.have_connected and bool((self.on_alt_no + 1) <= len(self.alt_connect_opts)):
            return True
        if self.offline_reason == self.Reasons.BAD_PASSWORD:
            return self.profile_has_connected()
        return False

    def auth_failed(self, reason=''):
        if reason in ('bad-auth', 'not-authorized'):
            self._auth_error_msg = reason
            self.setnotifyif('offline_reason', self.Reasons.BAD_PASSWORD)
            self._failed_hosts.add(self.stream.server)
        elif reason:
            self.error_txt = reason
        self.fatal_error()

    def fatal_error(self):
        if getattr(self.stream, '_had_host_mismatch', False) and not self.offline_reason:
            log.error('there was a host mismatch, interpreting it as auth error...')
            self.setnotifyif('offline_reason', self.Reasons.BAD_PASSWORD) # technically it's a bad username, but auth error regardless

        return jabber.protocol.fatal_error(self)

    @property
    def service(self):
        return 'digsby'

    @callbacks.callsback
    def set_blob(self, elem_name, data, force = False, callback = None):
        assert False
        blob = blobs.name_to_obj[elem_name](data=data)

        if self.blobhashes.get(elem_name, sentinel) == self.calc_blob_hash(blob) and not force:
            log.info('set_blob %s: no change', elem_name)
            return callback.success()

        # send blob out to network.
        iq = blob.make_push(self)

        log.info('%s: changed, sending stanza %r', elem_name, iq)
        self.send_cb(iq, success = lambda s: self.set_blob_success(s, blob._data, callback = callback),
                         error   = callback.error,
                         timeout = callback.timeout)

    @callbacks.callsback
    def set_blob_success(self, stanza, data, callback = None):
        assert False
        ns   = stanza.get_query_ns()
        name = blobs.ns_to_name[ns]

        blob = blobs.ns_to_obj[ns](stanza.get_query())
        blob._data = data

        self.blob_cache(blob)
        callback.success()


    def incoming_blob(self, blob):
        useful_data = blob.data
        name = blobs.ns_to_name[blob.xml_element_namespace]
        self.profile.update_blob(name, useful_data)

    @callbacks.callsback
    def get_blob_raw(self, elem_name, tstamp='0', callback=None):
        try:
            blob = blobs.name_to_obj[elem_name](tstamp)
            blob._data = None
            iq = blob.make_get(self)
        except Exception:
            blob = blobs.name_to_obj[elem_name]('0')
            blob._data = None
            iq = blob.make_get(self)
        self.send_cb(iq, callback = callback)

    @callbacks.callsback
    def set_account(self, account, action='add', order=None, callback=None):
        account = digsby.accounts.Account(account.id if action == 'delete' else account, action=action)
        self.set_accounts([account], order, callback=callback)

    @callbacks.callsback
    def set_accounts(self, accounts=[], order=None, callback=None):
        if not order:
            order = self.profile.account_manager.order
        daccts = digsby.accounts.Accounts(accounts, order)
        log.debug('setting accounts: %r with order: %r', [(a.action, a.id, a.protocol, a.username) for a in daccts], order)
        iq = daccts.make_push(self)
        self.send_cb(iq, callback=callback)

    @callbacks.callsback
    def get_accounts(self, callback=None):
        iq = digsby.accounts.Accounts().make_get(self)
        self.send_cb(iq, callback = callback)

    def get_widgets(self):
        iq = digsby.widgets.make_get(self)
        self.send_cb(iq, success=self.incoming_widgets)

    def incoming_widgets(self, stanza):
        widgets = digsby.widgets.Widgets(stanza.get_query())
        self.profile.incoming_widgets(widgets)

    def set_profile(self, *a, **k):
        pass

    def subscription_requested(self, stanza):
        'A contact has requested to subscribe to your presence.'

        assert stanza.get_type() == 'subscribe'

        to_jid=stanza.get_from()
        if to_jid.domain in pref('digsby.guest.domains', ['guest.digsby.org']):
            from_jid = stanza.get_to()
            groups = jabber.jabber_util.xpath_eval(stanza.xmlnode, 'd:group', {'d':"digsby:setgroup"})
            if groups:
                group = groups[0].getContent()
                item = RosterItem(node_or_jid = to_jid,
                                  subscription = 'none',
                                  name = None,
                                  groups = (group,),
                                  ask = None)
                q = item.make_roster_push()
                self.send(q)
            pr2=Presence(stanza_type='subscribe', from_jid=from_jid,
                         to_jid=to_jid)
            self.send(pr2)
            self.send(stanza.make_accept_response())
            return True
        else:
            return jabber.protocol.subscription_requested(self, stanza)

    def stream_error(self, err):
        if err.get_condition().name == "pwchanged":
            self.change_reason(self.Reasons.BAD_PASSWORD)
            self.profile.signoff(kicked=True)
        else:
            jabber.protocol.stream_error(self, err)

    def set_buddy_icon(self, icon_data):
        pass

    def get_buddy_icon(self, screenname):
        pass

    photo_hash = property(lambda *a: None, lambda *a: None)

    def conditional_messages_handler(self, stanza):
        # bind profile.account_manager.all_accounts and sys.REVISION to the conditional_messages function
        from common import profile
        import sys

        ret = conditional_messages(stanza,
                                   revision = sys.REVISION)

        if ret in (None, True): #None = not a conditional message, True = filtered for cause
            return ret
        log.critical('got a conditional message. accttypes = %r', ret)

        if ret == []: #no account types, no reason to filter it here.
            return None
        accttypes = ret

        message = stanza
        from_jid = message.get_from()
        log.critical('from_jid = %r', from_jid)
        if from_jid != 'digsby.org':
            return None

        buddy = self.get_buddy(from_jid)

        body = get_message_body(message)
        log.critical('body = %r', body)
        if not body: #no message
            return

        timestamp = get_message_timestamp(message)
        if not timestamp:
            timestamp = datetime.datetime.utcnow()

        content_type = 'text/html'
        #delay call based on accounts having shown up, then:

        messageobj = common.message.Message(buddy = buddy,
                                 message = body,
                                 timestamp = timestamp,
                                 content_type = content_type)

        import hooks
        def do_acct_math(*a, **k):
            has_accts = set(a.protocol for a in self.profile.all_accounts)
            if (has_accts & set(accttypes)): #user has accounts we're targeting
                log.critical('sending message obj to hook')
                hooks.notify('digsby.server.announcement', messageobj)
            else:
                log.critical('filtering conditional message for no accounts in common')

        log.critical('one shot next')
        if not hook_util.OneShotHook(self.profile, 'digsby.accounts.released.async')(do_acct_math, if_not_fired=True):
            log.critical('no one shot, calling now')
            do_acct_math()

        return True

    def presence_push(self, status=None):
        assert status is None
        status = self.status
        import hooks
        if status:
            status = hooks.reduce('digsby.status.tagging.strip_tag', status, impl='text')
        return super(DigsbyProtocol, self).presence_push(status)

    def set_idle(self, yes):
        self._idle = bool(yes)
        self.presence_push()

    def set_message(self, message, status, format=None, default_status='dnd'):
        jabber.protocol.set_message(self, message, status, format, default_status)

    def __set_show(self, state):
        self._show   = state

    def __get_show(self):
        if self._idle:
            return 'away'
        else:
            return self._show

    show = property(__get_show, __set_show)

def conditional_messages(stanza, **opts):
    '''
    Returns True (meaning stanza was handled) if special conditions are met.

    opts must have
      all_accounts - usually profile.account_manager.all_accounts
      revision     - sys.REVISION
    '''

    d = dict(x = 'http://www.digsby.org/conditions/v1.0')
    conditions = stanza.xpath_eval('x:x/x:condition', d)
    if not conditions:
        return

    num_conds = len(conditions)
    num_handled = 0

    accttypes = error_handling.try_this(lambda:
                         [str(n.getContent().strip()) for n in stanza.xpath_eval("x:x/x:condition[@type='has-account-type']", d)],
                         [])

    num_handled += len(accttypes)

    try:
        below_conds = stanza.xpath_eval("x:x/x:condition[@type='revision-below-eq']", d)
        if below_conds:
            rev_below = int(below_conds[0].getContent().strip())
        else:
            rev_below = None
    except Exception:
        rev_below = None

    try:
        above_conds = stanza.xpath_eval("x:x/x:condition[@type='revision-above-eq']", d)
        if above_conds:
            rev_above = int(above_conds[0].getContent().strip())
        else:
            rev_above = None
    except Exception:
        rev_above = None

    try:
        not_understood_conds = stanza.xpath_eval("x:x/x:condition[@type='if-not-understood']", d)
        if not_understood_conds:
            not_understood = not_understood_conds[0].getContent().strip()
        else:
            not_understood = None
    except Exception:
        not_understood = None

    if not_understood is not None:
        num_handled += 1

    if rev_above is not None:
        num_handled += 1

    if rev_below is not None:
        num_handled += 1

    sysrev = error_handling.try_this(lambda: int(opts['revision']), None)

    if rev_below is not None and rev_above is not None and sysrev is not None:
        if rev_below <= rev_above:
            if sysrev > rev_below and sysrev < rev_above:
                log.critical('filtering conditional message for revision not in range')
                return True
        else:
            if sysrev > rev_below or sysrev < rev_above:
                log.critical('filtering conditional message for revision in range')
                return True

    if num_handled != num_conds and not_understood == "don't-show":
        log.critical('filtering conditional message for not understood')
        return True

    return accttypes

if __name__ == '__main__':
    pass
