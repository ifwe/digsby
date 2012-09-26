from util.net import UrlQuery
from util.primitives.mapping import odict
from contacts.Group import Group
from facebook.fbacct import pstr_to_list, pstring
from facebook.fbconnectlogin import LOGIN_SUCCESS_PAGE
from facebook.facebookapi import db_rows_to_dict
import traceback
import jabber
from logging import getLogger
from util.callbacks import callsback
from common.actions import action
from pyxmpp.all import JID, Iq
from common import profile
import common
from facebook.facebookprotocol import not_logged_in
import services.service_provider as service_provider
from provider_facebook.facebook_service_provider import FacebookLogin
log = getLogger('xmppfb.protocol')

from pyxmpp.exceptions import ClientError

from jabber import jbuddy, jcontact, resource as JabberResource
from util.primitives.error_handling import traceguard, try_this
from util.threads.timeout_thread import Timer
nullaction = common.action(lambda self, *a, **k: None)

UID_PREPEND = '-'

class FacebookContact(jcontact):
    @nullaction
    def remove(self): pass

    @callsback
    def remove_from_group(self, callback = None):
        assert False

    @callsback
    def replace_group(self, new_group, callback = None):
        assert False

    @nullaction
    def block(self): pass
    @nullaction
    def unblock(self): pass
    @nullaction
    def send_email(self): pass
    @nullaction
    def send_sms(self): pass
    @nullaction
    def send_file(self): pass

    @nullaction
    def subscribed(self):
        'Send Authorization'

    @nullaction
    def unsubscribed(self):
        'Send Removal of Authorization'

    @nullaction
    def subscribe(self):
        'Re-send Subscription Request'

    @nullaction
    def unsubscribe(self):
        'Send Unsubscription Request'

class FacebookResource(JabberResource):
    away_is_idle = True

class FacebookBuddy(jbuddy):
    service = 'fbchat'

    _get_image_min_once = True

    away_is_idle = True

    resource_class = FacebookResource

    def __init__(self, jabber_, jid, rosteritem=None):
        super(FacebookBuddy, self).__init__(jabber_, jid, rosteritem)
        #get icons on login for buddies without presence (but only if the icon is visible)
#        self.icon_hash = True
        # Facebook sends us messages like
        #   "You are now Online to Chat. Please note that this also marks
        #   you as Online on facebook.com."
        if jid == u'chat.facebook.com':
            self._set_isbot(True)

    def _set_username(self):
        #the following needs to be cleaned up
        self.username = self.id
        #if you change name or id, be sure to create an updated info_key method
        self.name     = self.id

    @property
    def id(self):
        #if you change name or id, be sure to create an updated info_key method
        if self.jid.node is not None and len(self.jid.node) and self.jid.node[0] == UID_PREPEND:
            try:
                return unicode(int(self.jid.node[1:]))
            except ValueError:
                pass
        return self.jid.as_unicode()

    @property
    def nice_name(self):
        return self.remote_alias or self.name

    @property
    def pretty_profile(self):
        links = (
#                 (_('View Profile'), 'profile'),
#                 (_('Write on Wall'),'wall'),
                 (_('Send Message'), 'message'),
                 (_('Send Poke'),    'poke'),
                 (_('View Photos'),  'photo_search'),
                )

        link_tups = [
                     ('http://www.facebook.com/profile.php?id=%s&v=info' % self.id, _('View Profile')),
                     ('http://www.facebook.com/profile.php?id=%s&v=wall' % self.id, _('Write on Wall')),
                     ]
        link_tups.extend(('"http://www.facebook.com/%s.php?id=%s"' % (page, self.id), name) for name, page in links)

        final = []
        for link in link_tups:
            final.append('\n')
            final.append(link)

        return {_('Links:'):  final }

    @nullaction
    def block(self): pass
    @nullaction
    def unblock(self): pass
    @nullaction
    def send_email(self): pass
    @nullaction
    def send_sms(self): pass
    @nullaction
    def send_file(self): pass
    @nullaction
    def remove(self): pass

    @nullaction
    def subscribed(self):
        'Send Authorization'

    @nullaction
    def unsubscribed(self):
        'Send Removal of Authorization'

    @nullaction
    def subscribe(self):
        'Re-send Subscription Request'

    @nullaction
    def unsubscribe(self):
        'Send Unsubscription Request'

    def _presence_updated(self, presence):
        pass #don't go get the vCard all the time on facebook.

class FaceBookChatXMPP(jabber.protocol):
    name = protocol = service = 'fbchat'

    buddy_class = FacebookBuddy
    contact_class = FacebookContact

    supports_group_chat = False

    def __init__(self, email, password, *a, **k):
        self.email_in = email
        k['fb_login'] = True
        self.uid = k.get('uid')
        self.session_key, self.secret = (None, None)
        jabber.protocol.__init__(self, email, password, *a, **k)

        self.status_messages = {}

    @action(lambda self, *a, **k: True if self.state == self.Statuses.OFFLINE else None)
    @callsback
    def Connect(self, register=False, on_success=None, on_fail=None, invisible = False,
                do_conn_fail = True, callback=None):
        self.change_state(self.Statuses.CONNECTING)

        def login_error(*a, **k):
            log.info('on_fail in Connect')
            self.offline_reason = self.Reasons.BAD_PASSWORD
            self.setnotifyif('state', self.Statuses.OFFLINE)
            if on_fail is not None:
                on_fail()

        def login_success(_check, did_login = False, *a, **k):
            self.finish_init(did_login, callback, register, on_success, login_error, invisible, do_conn_fail)

        with FacebookLogin(common.profile.find_account(self.username, self.protocol)) as fl:
            fl.do_check(login_success=login_success,
                        login_error=login_error)

    def finish_init(self, did_login, callback, *a):
        my_account = common.profile.find_account(self.username, self.protocol)
        api=uid=None
        with FacebookLogin(my_account) as fl:
            self.api = api = fl.loginmanager.digsby
            self.uid = uid = fl.loginmanager.digsby.uid

        if did_login:
            self.access_token = self.api.access_token
            acct = common.profile.find_account(self.username, self.protocol)
            if acct is not None:
                acct.uid = self.api.uid
                acct.access_token = self.api.access_token
                acct.update()
        self.jid = JID(UID_PREPEND + str(self.api.uid), 'chat.facebook.com', 'Digsby')
        common.netcall(lambda: super(FaceBookChatXMPP, self).Connect(*a, callback=callback))

    def session_started(self):
        self.get_buddy_icon(self.self_buddy.username)
        self.status_messages_start()
        super(FaceBookChatXMPP, self).session_started()

    def perm_fail(self, register, on_success, on_fail, invisible, do_conn_fail, callback, *a, **k):
        if not a:
            pass #we already weren't logged in
        elif (isinstance(a[0], dict) or not_logged_in(a[0])):
            pass #we don't have permissions or we're not logged in
        else:
            return self.finish_init(False, callback) #we're not sure of anything, go for it!

        next=LOGIN_SUCCESS_PAGE
        url = UrlQuery(DIGSBY_LOGIN_PERMS, next=next, skipcookie='true', req_perms=','.join(['xmpp_login', 'offline_access']))
        window = FBLoginWindow(self.email_in, acct=self)

        def on_nav(e = None, b = None, url=None, *a, **k):
            if not window.ie:
                e.Skip()
                #careful with name collision
                url = e.URL
            try:
                parsed = UrlQuery.parse(url)
            except Exception:
                traceback.print_exc()
            else:
                log.info('url: %r', url)
                log.info('in: %r', 'session' in parsed['query'])
                if 'session' in parsed['query']:
                    #not sure how to clean this up right now.
                    session = parsed['query'].get('session')
                    log.info('parsed: %r', parsed)
                    parsed_base = dict(parsed)
                    parsed_base.pop('query')
                    self.api.set_session(session)
                    self.api.logged_in = True
                    if not getattr(self, 'dead', False):
                        self.dead = True
                        self.finish_init(True, callback, register, on_success, on_fail, invisible, do_conn_fail)
                    return

        def on_close(*a, **k):
            if not getattr(self, 'dead', False):
                on_fail()

        window.set_callbacks(on_nav, None, on_close)
        window.LoadURL(url)
        window._browser_frame.Show()


    def _get_buddy_name(self, name):
        try:
            int(name)
        except ValueError:
            jid = JID(name)
        else:
            jid = JID(UID_PREPEND + name + '@chat.facebook.com')
        return jid

    def get_buddy(self, name):
        return super(FaceBookChatXMPP, self).get_buddy(self._get_buddy_name(name))

    def get_buddy_icon(self, name):
        return super(FaceBookChatXMPP, self).get_buddy_icon(self._get_buddy_name(name))

    def set_buddy_icon(self, icon_data):
        pass

    @callsback
    def request_vcard(self, jid, callback=None):
        i = Iq(stanza_type='get');
        if jid: i.set_to(JID(jid).bare())

        _q = i.add_new_content('vcard-temp', 'vCard');
        #Facebook chat servers don't like the below two items
#        q.setProp('prodid', '-//HandGen//NONSGML vGen v1.0//EN')
#        q.setProp('version', '2.0');

        self.send_cb(i, callback=callback)

    def add_new_buddy(self, *a, **k):
        raise NotImplementedError

    def rename_group(self, gid, new_name):
        group = self.get_group(gid)
        for buddy in group:
            profile.set_contact_info(buddy, 'group', new_name)
        self.rebuild_root()

    @callsback
    def move_buddy(self, buddy, to_group, from_group=None, pos=0, callback=None):
        profile.set_contact_info(buddy, 'group', to_group)
        self.rebuild_root()
        callback.success()

    @callsback
    def remove_group(self, group, callback = None):
        pass

    def rebuild_root(self):
        self.roster_updated()

    def roster_updated(self, item=None):
        with traceguard:
            roster = self.roster
            from util.primitives.structures import oset
            with self.root_group.frozen():
                jcontact   = self.contact_class
                buddies    = self.buddies
                root_group = self.root_group

                del root_group[:]

                groups = odict({None: self.root_group})
    #
                for item in roster:
                    #roster groups
                    i_groups = oset(filter(None, item.groups))
                    #profile group
                    p_groups = oset(filter(None, (profile.get_contact_info(self.buddies[item.jid], 'group'),)))
                    #plus default group
                    group = (p_groups | i_groups | oset([None]))[0]
                    #CAS: optimize this to not create a group every time.
                    g = groups.setdefault(group, Group(group, self, group))
                    contact = jcontact(self.buddies[item.jid](item), group)
                    g.append(contact)

                for _gid, g in groups.iteritems():
                    if not self.filter_group(g):
                        if g is not root_group:
                            root_group.append(g)
                    g[:] = [c for c in g if not self.filter_contact(c)]

    def status_messages_start(self):
        cbs = dict(success = self.status_messages_success, error   = self.status_messages_repeat)
        if self.status_messages:
            self.api.query('select uid, status from user where uid in (SELECT uid2 FROM friend WHERE uid1 = me()) and status.time > %d'\
                           % max(self.status_messages, key=lambda s: try_this(lambda: (s.get('status', {}) or {}).get('time', 0), 0)),
                           **cbs
                           )
        else:
            self.api.query('select uid, status from user where uid in (SELECT uid2 FROM friend WHERE uid1 = me())',
                           **cbs
                           )


    def status_messages_success(self, result):
        try:
            if isinstance(result, list):
                results = db_rows_to_dict(result, 'uid')
                self.status_messages.update(results)
        except Exception:
            traceback.print_exc()
        else: #timing is a little weird, just update them all
            for uid, status in self.status_messages.iteritems():
                msg = try_this(lambda: (status.get('status', {}) or {}).get('message', ''), '')
                self.get_buddy(str(uid)).set_status_message(msg)
        finally:
            self.status_messages_repeat()

    def status_messages_repeat(self, *a, **k):
        with self.lock:
            if getattr(self, 'status_update_timer', False) is not None:
                t = self.status_update_timer = Timer(15 * 60, self.status_messages_start)
                t.start()

    def stop_status_update_loop(self):
        with self.lock:
            status_update_timer, self.status_update_timer = getattr(self, 'status_update_timer', None), None
        if status_update_timer is not None:
            status_update_timer.stop()
        del self.status_update_timer

    def stop_timer_loops(self):
        super(FaceBookChatXMPP, self).stop_timer_loops()
        self.stop_status_update_loop()

    @property
    def icon(self):
        from gui import skin
        from util import try_this
        return try_this(lambda: skin.get('serviceicons.%s' % self.protocol), None)

    @property
    def console(self):
        return self.api.console()

#===============================================================================
# jabber overrides
#===============================================================================

    def _add_presence_extras(self, pres):
        pass

    def service_discovery_init(self):
        pass

    def _Client__roster_push(self,iq):
        #uberHAX: need to ignore this sort of garbage from facebook.
        #they've broken their server to compensate for broken behavior
        #in pidgin, so we have to compensate for that broken server behavior.
        #http://wiki.developers.facebook.com/index.php/XMPP_Release_Notes
        #should have been removed in the "next release",
        #seems to not be true
        try:
            super(FaceBookChatXMPP, self)._Client__roster_push(iq)
        except ClientError:
            traceback.print_exc()
        resp=iq.make_result_response()
        self.send(resp)

    def message(self, message):
        from_ = message.get_from()
        if from_ is not None and from_.as_unicode() == u"chat.facebook.com" and \
            message.get_subject() == u'You are now Online to Chat' and \
            message.get_body() == u'You are now Online to Chat. Please note that this also marks you as Online on facebook.com.':
            return
        else:
            return super(FaceBookChatXMPP, self).message(message)

    status_state_map = {}
    _idle = None

    def set_idle(self, yes):
        self._idle = bool(yes)
        self.presence_push()

    def __set_show(self, state):
        pass

    def __get_show(self):
        if self._idle:
            return 'away'
        else:
            return None

    show = property(__get_show, __set_show)

    def set_message(self, message, status, format = None, default_status='normal'):
        return super(FaceBookChatXMPP, self).set_message(message = None,
                                                         status  = '',
                                                         format = format,
                                                         default_status = \
                                                           default_status)

def do_call(callable):
    callable()

def get_call_wrapper(*a, **k):
    return do_call

#we've got some stuff to do before the actual socket.connect, so we'll be
#responsible for what thread things are on, not jabber

import protocols
protocols.declareAdapterForType(protocols.protocolForURI("http://www.dotsyntax.com/protocols/connectcallable"),
                                get_call_wrapper, FaceBookChatXMPP)
