'''
Jabber Protocol.
'''

from __future__ import with_statement
from common import profile
from common import netcall
import wx
import pyxmpp
from util.callbacks import do_cb_na
from jabber.threadstream import ThreadStream
#from jabber.tlslitestream import TLSLiteStream
from jabber.objects.iq_privacy import List, Privacy
from pyxmpp.utils import to_utf8
from jabber.JabberResource import JabberResource
from jabber.objects.si_filetransfer import SI_FILETRANSFER_NS
from jabber.filetransfer.socketserver import JabberS5BServerSocket
import common

from pyxmpp.all import JID, Iq, Presence, Message
from pyxmpp.jabber.client import JabberClient
from pyxmpp.roster import RosterItem

from util import odict, callsback, CallLater, callany, threaded
from util.primitives.funcs import Delegate, do
from util.primitives.structures import enum
from util.xml_tag import tag_parse
from contacts import Group
from util.observe import observable_dict
import jabber
from pyxmpp.jabber import muc
from common import action
from pyxmpp.jabber.register import Register
from pyxmpp.streamtls import TLSSettings
from jabber.filetransfer.S5BFileXferHandler import S5BRecvHandler
from jabber.objects.bytestreams import BYTESTREAMS_NS
from hashlib import sha1
from traceback import print_exc
import random, sys
import hooks

from logging import getLogger
log = getLogger('jabber.protocol')
methods_dict = odict(dict(digsby_login="sasl:DIGSBY-SHA256-RSA-CERT-AES", sasl_md5="sasl:DIGEST-MD5", sasl_plain="sasl:PLAIN",
                     use_md5="digest", plain="plain"))
methods_dict._keys = ['digsby_login', 'sasl_md5', "sasl_plain", "use_md5", "plain"]

NAPTIME = 8

MUC_URI = 'http://jabber.org/protocol/muc'

def fmtstanza(stanza):
    stanza.xml_node

class JabberProtocol(common.protocol, JabberClient):
    buddy_class   = jabber.jbuddy
    buddies_class = jabber.jbuddies
    contact_class = jabber.jcontact

    name = 'jabber'

    thread_id = 0

    message_sizes = [10, 12, 14, 18]

    states = enum('Disconnected',
                  'Authenticating',
                  'Connected')

    status_state_map = jabber.status_state_map

    can_specify_chatserver = True

    bots = common.protocol.bots | set((JID('twitter@twitter.com'),))

    supports_group_chat = True

    def __init__(self, username, password, user, server, login_as='online',
                 do_tls=False, require_tls=False, verify_tls_peer=False,
                 do_ssl=False, alt_conn_lock=None,
                 resource="Digsby", priority=5, block_unknowns=False,
                 hide_os=False, alt_connect_opts = [],
                 dataproxy = None,
                 **authmethods):

#        from pprint import pprint
#        pprint(dict(user=user, server=server, login_as=login_as,
#                 do_tls=do_tls, require_tls=require_tls,
#                 verify_tls_peer=verify_tls_peer,
#                 authmethods=authmethods))
#        authmethods = dict(sasl_md5=False, sasl_plain=False,
#                            use_md5=False, plain=True)
#assert only: in **authmethods
#        sasl_md5=True, sasl_plain=True,
#                 use_md5=True, plain=True,

        servr, port = server
        jid = JID(username)
        jid = JID(jid.node, jid.domain, resource)
        if isinstance(username, unicode):
            username = username.encode('utf8')
        if isinstance(password, unicode):
            password = password.encode('utf8')

        common.protocol.__init__(self, username, password, user)

        def printargs(ok, store):
            return True
            return wx.YES == wx.MessageBox(str(store.get_current_cert().as_text()), str(ok),  style=wx.YES_NO)

        jkwargs = dict(jid          = jid,
            password     = password,
            keepalive    = 45,
            disco_name   = username, # should be fullname?
            disco_type   = "DigsbyUser",)

        self.alt_connect_opts = alt_connect_opts
        self.alt_conn_lock = alt_conn_lock
        self.on_alt_no = 0
        self.have_connected = False
        self._failed_hosts = set()

        assert not (do_ssl and do_tls)
        if do_tls:
            tlsset = TLSSettings(require=require_tls, verify_peer=verify_tls_peer,
                                 verify_callback=printargs)
            jkwargs.update(tls_settings = tlsset)

        if servr:  jkwargs.update(server = servr)
        if port:   jkwargs.update(port = port)

        self.do_ssl = do_ssl

        jkwargs.update(auth_methods = tuple(methods_dict[k]
                        for k in
                        methods_dict.keys() if authmethods.has_key(k)
                        and authmethods[k]))
#        def __init__(self,jid=None, password=None, server=None, port=5222,
#            auth_methods=("sasl:DIGEST-MD5","digest"),
#            tls_settings=None, keepalive=0,
#            disco_name=u"pyxmpp based Jabber client", disco_category=u"client",
#            disco_type=u"pc"):
        JabberClient.__init__(self, **jkwargs)
        self.stream_class = ThreadStream
        self.addrcache = {}

        #------------------------------------------------------------------------------
        # Contact List
        #------------------------------------------------------------------------------
        self.root_group = Group('Root', self, 'Root')
        self.fakegroups = set()
        self.buddies = self.buddies_class(self)
        self.conversations = observable_dict()
        self.block_unknowns = block_unknowns
        #------------------------------------------------------------------------------
        # Presence
        #------------------------------------------------------------------------------
        self.show     = ''
        self.status   = ''
        self.priority = priority
        self.photo_hash = None

        self.hide_os = hide_os
        self.invisible = False

        self.connect_killed = False

        #------------------------------------------------------------------------------
        # Multi User Chat
        #------------------------------------------------------------------------------
        self.room_manager = None
        self.known_s5b_proxies = odict()
        if dataproxy:
            try:
                dataproxy = JID(dataproxy)
            except ValueError:
                print_exc()
            else:
                self.known_s5b_proxies[dataproxy] = set()
        custom_conf_server = authmethods.get('confserver', '').strip()
        self.confservers = [custom_conf_server] if custom_conf_server else []

        do(self.register_feature(feature) for feature in jabber.features_supported)
        hooks.notify('digsby.jabber.initialized', self)

    @property
    def invisible(self):
        return False

    @invisible.setter
    def invisible(self, value):
        pass

    @property
    def service(self):
        return 'jabber'


    def _get_caps(self):
        'Returns the Jabber capability list.'
        from common import caps
        return [caps.INFO, caps.IM, caps.FILES, caps.EMAIL, caps.VIDEO]

    caps = property(_get_caps)

    def set_invisible(self, invisible = True):
        'Sets invisible.'
        return
#        self.invisible = invisible
#        self.presence_push()

    @action(lambda self, *a, **k: True if self.state == self.Statuses.OFFLINE else None)
    @callsback
    def Connect(self, register=False, on_success=None, on_fail=None, invisible = False,
                do_conn_fail = True, callback=None):

        self.silence_notifications(NAPTIME)
        self.register = register
        self.change_state(self.Statuses.CONNECTING)

        self.connect_callback = callback

        self.invisible = invisible
        self.do_conn_fail = do_conn_fail
        self.connect_killed = False

        def conn_attmpt_failed():
            log.debug('conn_attmpt_failed')
            if register:
                #if we were trying to register, don't try again.
                return callback.error()
            if do_conn_fail and not self.want_try_again:
                #nowhere else to go, + report conn fail
                self.set_offline(self.Reasons.CONN_FAIL)
                callback.error()
                raise
            elif not self.want_try_again:
                #nowhere else to go
                callback.error()
                raise
            else:
                #go somewhere else and try again
                return self._reconnect(invisible = invisible,
                                       do_conn_fail = do_conn_fail, callback=callback)
        self.connect_attempt_failed = conn_attmpt_failed
        try:
            self.connect(register=register, on_success=on_success, on_fail=on_fail)
        except Exception, e:
            print_exc()
            self.connect_attempt_failed()
        else:
            self.connect_attempt_succeeded()

    def connect_attempt_succeeded(self):
        log.debug('connect_attempt_succeeded')
        with self.lock:
            self.idle_loop = Delegate()
            self.idle_loop += self.idle
            self.idle_looper = jabber.IdleLoopTimer(1, self.idle_loop)

    def connect_attempt_failed(self):
        raise AssertionError('connection attempt cannot fail before it is attempted')

    def connected(self):
        with self.lock:
            if self.state == self.Statuses.CONNECTING:
                self.change_state(self.Statuses.AUTHENTICATING)

    def disconnected(self, want_try_again = False):
        log.debug('disconnected 1')
        with self.lock:
            log.debug('disconnected 2')
            if not want_try_again and not self.want_try_again:
                log.debug('disconnected 3')
#                assert False
                self.change_state(self.Statuses.OFFLINE)
            JabberClient.disconnected(self)

    def _get_stream(self):
        return getattr(self, '_stream', None)

    def _set_stream(self, stream):
        new = stream
        if new is None:
            old = self.stream
            if old is not None:
                netcall(old.close)
                for attr in ('process_stream_error', 'state_change', 'owner'):
                    setattr(old, attr, Null)
        self._stream = new

    stream = property(_get_stream, _set_stream)

    def auth_failed(self, reason=''):
        if reason:
            self._auth_error_msg = reason
        self.setnotifyif('offline_reason', self.Reasons.BAD_PASSWORD)
        self.Disconnect()

    def _should_attempt_connect(self, opts):
        return opts['server'][0] not in self._failed_hosts

    def _get_next_connection_options(self):
        opts = None
        while opts is None:
            try:
                opts = self.alt_connect_opts[self.on_alt_no].copy()
            except IndexError:
                break

            self.on_alt_no += 1

            if not self._should_attempt_connect(opts):
                opts = None

        return opts

    @callsback
    def _reconnect(self, invisible = False,
                   do_conn_fail = True, callback=None):
        log.info('jabber _reconnect!')
        getattr(getattr(self, 'idle_looper', None), 'stop', lambda: None)()

        #grab next set of connection opts
        opts = self._get_next_connection_options()
        if opts is None:
            return self.fatal_error()

        self.change_state(self.Statuses.CONNECTING)
        self.setup_deleted_attrs()

        self.server, self.port = opts.pop('server')
        do_tls=opts.pop('do_tls')
        require_tls=opts.pop('require_tls')
        verify_tls_peer=opts.pop('verify_tls_peer')
        self.do_ssl = do_ssl = opts.pop('do_ssl')
        assert not (do_ssl and do_tls)
        if do_tls:
            self.tls_settings = tlsset = TLSSettings(require=require_tls, verify_peer=verify_tls_peer)
        else:
            self.tls_settings = None
        #collect $200
        threaded(lambda: JabberProtocol.Connect(self, invisible = invisible,
                                       do_conn_fail = do_conn_fail, callback=callback))()

    def setup_deleted_attrs(self):
        if self.root_group is None:
            self.root_group = Group('Root', self, 'Root')

        self.fakegroups = set()

        self.setup_buddies_dict()

        if getattr(self, "interface_providers", None) is None:
            self.interface_providers = [self]

    def setup_buddies_dict(self):
        if self.buddies is None:
            self.buddies = self.buddies_class(self)

    def fatal_error(self):
        if not self.want_try_again:
            reason = self.offline_reason or self.Reasons.CONN_LOST
            log.info('Out of connection options. Changing to %r', reason)
            self.set_offline(reason)
            return False
        else:
            #connection lost, go somewhere else and get a new one.
            log.info('Connection failed, trying another option')
            self._reconnect(invisible = self.invisible,
                            do_conn_fail = self.do_conn_fail,
                            callback=self.connect_callback)
            return True

    @property
    def want_try_again(self):
        '''
        True if we should continue trying to connect
        '''
        with self.lock:
            if self.offline_reason == self.Reasons.BAD_PASSWORD:
                return False

            return (not self.connect_killed) and self.want_retry_connect

    @property
    def want_retry_connect(self):
        '''
        True if we've never started a session and we have other places left to try.
        '''
        with self.lock:
            return (not self.have_connected) and bool((self.on_alt_no + 1) <= len(self.alt_connect_opts))

    def connect(self, register = False, on_success=None, on_fail=None):
        """Connect to the server and set up the stream.

        Set `self.stream` and notify `self.state_changed` when connection
        succeeds. Additionally, initialize Disco items and info of the client.
        """
        JabberClient.connect(self, register)
        if register:
            s = self.stream
            s.registration_callback = self.process_registration_form
            s.registration_error_callback = on_fail
            s.registration_success_callback = lambda: (self.disconnect(), on_success())

    @action()
    def Disconnect(self):
        netcall(self._Disconnect)

    def stop_idle_looper(self):
        idle_looper, self.idle_looper = getattr(self, 'idle_looper', None), None
        if idle_looper is not None:
            idle_looper.stop()

        del self.idle_looper

    def stop_timer_loops(self):
        self.stop_idle_looper()

    def _Disconnect(self):
        log.debug('logging out %r', self.want_try_again)
        with self.lock:
            pres = Presence(stanza_type="unavailable",
                            status='Logged Out')
            try:
                self.stream.send(pres)
            except AttributeError:
                pass
            self._failed_hosts = set()
            self.connect_killed = True
            self.disconnect()
            try:
                self.stop_timer_loops()
            except AttributeError:
                print_exc()

            if getattr(self, 'idle_loop', None) is not None:
                del self.idle_loop[:]

            if self.root_group is not None:
                self.root_group.observers.clear()
                self.root_group.protocol = None
                self.root_group = None

            if self.buddies is not None:
                self.buddies.protocol = None
                self.buddies = None

            if self.interface_providers is not None:
                del self.interface_providers[:]
                self.interface_providers = None

            if self.stream is not None:
                self.stream = None

            log.debug('1logged out %r', self.want_try_again)
            self.offline_reason = None
#            self.disconnected()
        log.debug('1logged out %r', self.want_try_again)

        common.protocol.Disconnect(self)

    def session_started(self):
        '''
        Called when the IM session is successfully started (after all the
        neccessery negotiations, authentication and authorizasion).
        '''
        with self.lock:
            self.idle_looper.start()
        log.info('session started')
        self.service_discovery_init()
        self.request_roster()

        s = self.stream

        newstate = self.Statuses.AUTHORIZED if self.name == 'digsby' else self.Statuses.ONLINE
        #when this is true, don't try to start a new connection on conn_lost
        self.have_connected = True

        if self.alt_connect_opts:
            #there may/may not be a lock
            if self.alt_conn_lock:
                self.alt_conn_lock.acquire()
            #really only helpful for gtalk reconnect.  Put the working connection at the top of the options.
            working_opts = self.alt_connect_opts.pop(self.on_alt_no-1)
            self.alt_connect_opts.insert(0, working_opts)
            if self.alt_conn_lock:
                self.alt_conn_lock.release()

        # set up handlers for supported <iq/> queries
        s.set_iq_get_handler("query", "jabber:iq:version", self.get_version)

        # set up handlers for <presence/> stanzas
        do(s.set_presence_handler(name, func) for name, func in [
            (None,           self.buddies.update_presence),
            ('unavailable',  self.buddies.update_presence),
            ('available',    self.buddies.update_presence),
            ('subscribe',    self.subscription_requested),
            ('subscribed',   self.presence_control),
            ('unsubscribe',  self.presence_control),
            ('unsubscribed', self.presence_control),
        ])

        self.s5b_handler = S5BRecvHandler(self)
        self.s5b_handler.register_handlers()

        # set up handler for <message stanza>
        s.set_message_handler("normal", self.message)

        self.si_handler = jabber.filetransfer.StreamInitiationHandler(self)
        self.si_handler.set_profile_handler(SI_FILETRANSFER_NS, jabber.filetransfer.StreamInitiation.FileTransferSIHandler)

        self.si_handler.set_stream_handler(BYTESTREAMS_NS, self.s5b_handler)
        self.s5bserver = JabberS5BServerSocket()

        self.si_handler.register_handlers()

        self.session_started_notify(s)

        self.connect_callback.success()
        self.change_state(newstate)
        log.info('session started done')

    def session_started_notify(self, s):
        '''
        whatever needs to be done after most setup and before the callback/state change happens.
        usually that will be plugins doing their own setup.
        allows notify to be overridden in subclass
        '''
        hooks.notify('digsby.jabber.session_started', self, s)

    def authorized(self):
        log.info('authorized1')
        JabberClient.authorized(self) # required!
        log.info('authorized2')
        jabber.objects.bytestreams.register_streamhost_cache_fetchers(self.cache, self.stream)
        log.info('authorized3')
        self.self_buddy = self.buddies[self.stream.me]
        log.info('authorized4')
        log.info('self buddy is: %r', self.self_buddy)

    def get_version(self,iq):
        """Handler for jabber:iq:version queries.

        jabber:iq:version queries are not supported directly by PyXMPP, so the
        XML node is accessed directly through the libxml2 API.  This should be
        used very carefully!"""
        iq = iq.make_result_response()
        q = iq.new_query("jabber:iq:version")
        q.newTextChild( q.ns(), "name", "Digsby Client" )
        q.newTextChild( q.ns(), "version", ('%s %s' % (sys.REVISION, sys.TAG)).strip()) # strip because sometimes TAG is ''
        if not self.hide_os:
            import platform
            platform_string = platform.platform()
            # for some reason, on my XP box, platform.platform() contains both
            # the platform AND release in platform.platform(). On Ubuntu, OS X,
            # and I believe older versions of Windows, this does not happen,
            # so we need to add the release in all other cases.
            if platform_string.find("XP") == -1:
                platform_string += " " + platform.release()

            q.newTextChild( q.ns(), "os", platform_string )
        self.send(iq)
        return True

    def message(self, stanza):
        _from = stanza.get_from()
        buddy = self.buddies[_from]
        _to = stanza.get_to()
#        if _to.resource is None: #send from bare to bare
#            _from = _from.bare()
#        tup = (buddy, _from, _to, stanza.get_thread())
        tup = (buddy,)
        if tup in self.conversations:
            convo = self.conversations[tup]
        else:
#            convo = jabber.conversation(self, *tup)
            convo = jabber.conversation(self, buddy, _from)
            self.conversations[tup] = convo
            convo.buddy_join(self.self_buddy)
            convo.buddy_join(buddy)
#        message = Message(stanza.get_node())
        convo.incoming_message(buddy, stanza)
        return True

    def convo_for(self, contact):
        return self.chat_with(contact)

    def chat_with(self, buddyobj_or_jid):
        buddy_or_jid = getattr(buddyobj_or_jid, 'buddy', buddyobj_or_jid)
        jid = getattr(buddy_or_jid, 'jid', buddy_or_jid)
        buddy = self.buddies[jid]

#        tup = (buddyobj, jid, self.stream.me.bare(), None)
        tup = (buddy,)
        if tup in self.conversations:
            convo = self.conversations[tup]

            if isinstance(buddyobj_or_jid, jabber.resource):
                # asked for a resource specifically.
                convo.jid_to = jid
        else:
            convo = self.conversations.setdefault(tup,
                         jabber.conversation(self, buddy, jid))
            convo.buddy_join(self.self_buddy)
            convo.buddy_join(buddy)
        return convo

    def set_message(self, message, status, format = None, default_status='away'):
        log.info('set_message(%s): %r', status, message)

        state = self.status_state_map.get(status.lower(), default_status)

        # no <show/> tag means normal
        self.show   = state if state != 'normal' else None

        self.status = message
        self.presence_push()

    def presence_push(self, status=None):
        if status is None:
            status = self.status

        pres = Presence(#stanza_type = 'invisible' if self.invisible else None,
                        show     = self.show     or None,
                        status   = status        or None,
                        priority = self.priority or None)
        self._add_presence_extras(pres)
        self.send_presence(pres)
        try:
            self.self_buddy.update_presence(pres, buddy=self.stream.me)
        except AttributeError:
            if self.stream is not None:
                print_exc()

    def _add_presence_extras(self, pres):
#    xmlns="http://jabber.org/protocol/caps"/>
#        c = pres.add_new_content("http://jabber.org/protocol/caps", "c")
#<c node="http://www.google.com/xmpp/client/caps"
#        c.setProp('node',"http://www.google.com/xmpp/client/caps")
#    ver="1.0.0.104"
#        c.setProp('ver',"1.0.0.104")
#    ext="share-v1 voice-v1"
#        c.setProp('ext',"share-v1 voice-v1")

        x = pres.add_new_content("vcard-temp:x:update", "x")

        if self.photo_hash is not None:
            x.newChild(None,to_utf8("photo"),self.photo_hash)

    def email_hint(self, buddy):
        return unicode(buddy.jid.bare())

    def has_buddy(self, buddyname):
        assert isinstance(buddyname, basestring)
        jid = JID(buddyname)
        return jid in self.buddies

    def get_buddy_icon(self, screenname):
        unique = JID(screenname).bare()
        buddy = self.buddies[unique]
        if getattr(buddy, '_vcard_incoming', False):
            return

        self.request_vcard(unique, success=buddy.set_vcard)

        buddy._vcard_incoming = True

    @callsback
    def request_vcard(self, jid, callback=None):
        i = Iq(stanza_type='get');
        if jid: i.set_to(JID(jid).bare())

        q = i.add_new_content('vcard-temp', 'vCard');
        q.setProp('prodid', '-//HandGen//NONSGML vGen v1.0//EN')
        q.setProp('version', '2.0');

        self.send_cb(i, callback=callback)

    def set_buddy_icon(self, icon_data):
        '''
        this will wipe your profile!

        @param icon_data:
        '''
        i = Iq(stanza_type="get");
        q = i.add_new_content('vcard-temp', 'vCard');
        q.setProp('prodid', '-//HandGen//NONSGML vGen v1.0//EN'); q.setProp('version', '2.0');

        self.send_cb(i, success = lambda stanza: self.set_icon_stage2(stanza, icon_data))

    def set_icon_stage2(self, stanza, icon_data=None):
        assert icon_data is not None
        q = stanza.get_query()
        try:
            vcard = jabber.VCard(q or "")
        except ValueError:
            vcard = jabber.VCard("")
        photo = jabber.VCardPhotoData(icon_data)
        vcard.content['PHOTO'][0:1] = [photo]
        i = Iq(stanza_type='set')
        n = i.xmlnode
        n.addChild(vcard.as_xml(n))
        self.vcard = vcard
        self.send_cb(i, success = lambda stanza: self.set_icon_stage3(stanza, icon_data))

    def set_icon_stage3(self, stanza, icon_data=None):
        self.photo_hash = sha1(icon_data).hexdigest()
        self.presence_push()

#    def presence(self,stanza):
#        """Handle 'available' (without 'type') and 'unavailable' <presence/>."""
#
#        log.info('presence info received for ' + stanza.get_from())
#        return self.buddies[JID(stanza.get_from())].update_presence(stanza)
#
#
#        msg = u"%s has become " % (stanza.get_from())
#        t = stanza.get_type()
#        if t=="unavailable":
#            msg += u"unavailable"
#        else:
#            msg += u"available"
#
#        show=stanza.get_show()
#        if show:
#            msg+=u"(%s)" % (show,)
#
#        status=stanza.get_status()
#        if status:
#            msg += u": " + status
#        print msg

    def subscription_requested(self, stanza):
        'A contact has requested to subscribe to your presence.'

        assert stanza.get_type() == 'subscribe'

        # Grab XML on this threads
        from_jid  = stanza.get_to()
        to_jid    = stanza.get_from()
        stanza_id = stanza.get_id()

        log.info('subscription requested from %s to %s', from_jid, to_jid)

        def send_reponse(contact, authorize):
            stanza_type = pyxmpp.presence.accept_responses['subscribe'] \
                if authorize else pyxmpp.presence.deny_responses['subscribe']
            pr = Presence(stanza_type = stanza_type, from_jid = from_jid,
                        to_jid = to_jid, stanza_id = stanza_id)

            self.send_presence(pr)

            if authorize:
                pr2 = Presence(stanza_type = 'subscribe', from_jid = from_jid,
                               to_jid = to_jid)
                self.send_presence(pr2)

        contact = stanza.get_from()
        self.hub.authorize_buddy(self, contact, callback = lambda contact, authorize, _username_added=None: netcall(lambda: send_reponse(contact, authorize)))
        return True


    def presence_control(self,stanza):
        '''
        Handle subscription control <presence/> stanzas -- acknowledge
        them.
        '''
        msg = unicode(stanza.get_from()) + presence_messages.get(stanza.get_type(), '')
        log.info(msg)

        return True

    def print_roster_item(self,item):
        if item.name:
            name=item.name
        else:
            name = u""
        print (u'%s "%s" subscription=%s groups=%s'
                % (unicode(item.jid), name, item.subscription,
                    u",".join(item.groups)) )

    def filter_contact(self, contact):
        return False

    def filter_group(self, group):
        return False

    def roster_updated(self, item=None):
        roster = self.roster

        with self.root_group.frozen():

            jcontact   = self.contact_class
            buddies    = self.buddies
            root_group = self.root_group

            del root_group[:]

            groups = set(roster.get_groups())
            self.fakegroups -= groups
            groups |= self.fakegroups
            groups.add(None)

            for group in groups:
                if group is None:
                    g = root_group
                else:
                    g = Group(group, self, group)

                for item in roster.get_items_by_group(group):
                    contact = jcontact(buddies[item.jid](item), group)
                    g.append(contact)

                if not self.filter_group(g):
                    if g is not root_group:
                        root_group.append(g)

                g[:] = [c for c in g if not self.filter_contact(c)]

    def has_buddy_on_list(self, buddy):
        try:
            return self.roster.get_item_by_jid(JID(buddy.name))
        except (KeyError, AttributeError):
            return None

    @callsback
    def add_group(self, groupname, callback = None):
        self.fakegroups.add(groupname)
        self.roster_updated()
        callback.success(groupname)

    @callsback
    def remove_group(self, group, callback = None):

        log.info('Removing group: %r', group)

        self.fakegroups.discard(group)
        self.roster_updated()
        cbs = []
        for buddy in self.buddies.values():
            if group in buddy.groups:
                if len(buddy.groups) == 1:
                    log.info('Buddy %r will be removed from list', buddy)
                    cbs.append(buddy.remove)
                else:
                    item = self.roster.get_item_by_jid(buddy.jid).clone()
                    log.info('Buddy %r will be removed from group', buddy)
                    g = item.groups
                    if (group in g):
                        g.remove(group)
                        query = item.make_roster_push()

                        @callsback
                        def sendit(query=query, callback = None):
                            self.send_cb(query, callback = callback)

                        cbs += [sendit]

        do_cb_na(cbs, callback = callback)


    @callsback
    def move_buddy(self, contact, to_group, from_group=None, pos=0, callback = None):
        contact.replace_group(to_group, callback=callback)

    @callsback
    def send_cb(self, query, timeout_duration=None, callback=None):
        '''
        Given a callback object with callable attributes success, error, and timeout,
        sends out a query with response handlers set.
        '''

        def free_stanza(st):
            stream = self.get_stream()
            with stream.lock:
                if stream.doc_out is not None:
                    st.free()
                else:
                    if st._error:
                        st._error.xmlnode = None
                    st.xmlnode = None

        def my_super_callback_success(stanza):
            stanza.handler_frees = True
            if not isinstance(callback.success, list):
                from util import funcinfo
                try:
                    log.info("WTF, callback was %r", funcinfo(callback.success))
                except Exception:
                    log.error('bad callback.success %r', callback.success)
                    return free_stanza(stanza)
            if len(callback.success) == 0:
                return free_stanza(stanza)

            try:
                f = callback.success[0].cb
                _call_free = CallLater(lambda:free_stanza(stanza))
                def my_hyper_callback_success(st):
                    try: f(st)
                    except Exception:
                        log.error('error processing %r', f)
                        print_exc()
                    finally: _call_free()
                callback.success[0].cb = my_hyper_callback_success
                callany(callback.success, stanza)
            except Exception:
                print_exc()
                log.error('failed to set up success stanza.free for %r, %r', callback, stanza)

        def my_super_callback_error(stanza):
            stanza.handler_frees = True
            if not isinstance(callback.error, list):
                from util import funcinfo
                try:
                    log.info("WTF, callback was %r", funcinfo(callback.error))
                except Exception:
                    log.error('bad callback.error %r', callback.error)
                    return free_stanza(stanza)
            if len(callback.error) == 0:
                return free_stanza(stanza)

            try:
                f = callback.error[0].cb
                _call_free = CallLater(lambda:free_stanza(stanza))
                def my_hyper_callback_error(st):
                    try: f(st)
                    except Exception:
                        log.error('error processing %r', f)
                        print_exc()
                    finally: _call_free()
                callback.error[0].cb = my_hyper_callback_error
                callany(callback.error, stanza)
            except Exception:
                print_exc()
                log.error('failed to set up error stanza.free for %r, %r', callback, stanza)

        def my_super_callback_timeout(*a):
            '''
            consume the arguments, they are from ExpiringDictionary and cause problems
            with the number of arguments taken by timeout function,
            which in this case is expected to be 0, since we can store the context in it's closure
            and hardly anything even uses timeouts.
            '''
            return callback.timeout()

        s = self.get_stream()
        if s is not None:
            try:
                if timeout_duration is not None:
                    self.stream.set_response_handlers(query, my_super_callback_success,
                                                         my_super_callback_error,
                                                         my_super_callback_timeout,
                                                         timeout = timeout_duration)
                else:
                    self.stream.set_response_handlers(query, my_super_callback_success,
                                                         my_super_callback_error,
                                                         my_super_callback_timeout)
            except Exception, e:
                print_exc()
                log.critical("couln't set stream handlers")
                return callany(callback.error)
            try:
                self.stream.send(query)
            except Exception, e:
                print_exc()
                log.critical("couln't send query")
                try:
                    return callany(callback.error)
                except Exception:
                    log.critical("couln't call callany(callback.error) %r", callback)

    def send_presence(self, pres):
        assert isinstance(pres, Presence)
        self.send(pres)

    def send_message(self, message):
        assert isinstance(message, Message)
        self.send(message)

    def send_iq(self, iq):
        assert isinstance(iq, Iq)
        self.send(iq)

    def send(self, stanza):
        s = self.get_stream()
        if s is not None:
            try:
                self.stream.send(stanza)
            except Exception, e:
                print_exc()
                log.critical("couln't send stanza")

    @callsback
    def add_buddy(self, jid, group_id=None, _pos=None, service = None, callback = None):
        jid = JID(jid).bare()
        try:
            item = self.roster.get_item_by_jid(jid).clone()
        except KeyError, _e:
            item = RosterItem(node_or_jid=jid,
                              subscription='none',
                              name=None,
                              groups=(group_id,),
                              ask=None)
            #print item
            q = item.make_roster_push()
            p = Presence(to_jid=item.jid, stanza_type='subscribe')

            self.send_cb(q, callback=callback)
            self.send_presence(p)
        else:
            #testing subclipse retardedness, again?
            self.buddies[jid].add_to_group(group_id)

    def add_new_buddy(self, buddyname, groupname, service = None, alias = None):
        buddy = self.get_buddy(buddyname)
        if alias:
            profile.set_contact_info(buddy, 'alias', alias)
        self.add_buddy(buddyname, groupname, service = service)

    @callsback
    def rename_group(self, oldname, newname, callback = None):
        # If oldname is a fake group, rename it.
        if oldname in self.fakegroups:
            self.fakegroups.remove(oldname)
            self.fakegroups.add(newname)
            self.roster_updated()

        items = []
        for buddy in self.buddies.values():
            if oldname in buddy.groups:
                item = self.roster.get_item_by_jid(buddy.jid).clone()

                g = item.groups
                if (oldname in g):     g.remove(oldname)
                if (newname not in g): g.append(newname)
                items.append(item)

        if items:
            iq = items.pop(0).make_roster_push()
            q = iq.get_query()
            for item in items:
                item.as_xml(q)
            self.send_cb(iq, callback = callback)
        else:
            callback.success()



    #debug function
    def send_display(self, stanza, title=None):
        from util.TagViewer import TagViewer
        def stanza_print(s):
            t = tag_parse(s.xmlnode.serialize())
            self.hub.call_later(TagViewer, t, expand=True, title=title)
            self.last_displayed = Iq(s.get_node())
            return True
        self.send_cb(stanza, success=stanza_print, error=stanza_print)

    #debug function
    def stanza_display(self, stanza, title=None):
        from util.TagViewer import TagViewer
        self.last_displayed = Iq(stanza.get_node())
        t = tag_parse(stanza.xmlnode.serialize())
        self.hub.call_later(TagViewer, t, expand=True, title=title)
        return True

    #debug function
    def disco(self, place=None, type_=None):
        if not place:
            place = self.jid.domain
        if not type_ or type_ == 'b':
            i1 = Iq(stanza_type='get'); i1.set_to(place)
            i1.add_new_content('jabber:iq:browse', 'query')
            self.send_display(i1,'browse')

        if not type_ or type_ == 'm':
            i2 = Iq(stanza_type='get'); i2.set_to(place)
            i2.add_new_content('http://jabber.org/protocol/disco#items', 'query')
            self.send_display(i2,'items')

        if not type_ or type_ not in ('b','m'):
            i3 = Iq(stanza_type='get'); i3.set_to(place)
            i3.add_new_content('http://jabber.org/protocol/disco#info', 'query')
            self.send_display(i3,'info')

    def service_discovery_init(self):
        self.disco_init = jabber.disco.DiscoNode(self.cache, JID(self.jid.domain))
        self.disco_init.fetch(self.disco_finished, depth=1, timeout_duration = 30)

    def default_chat_server(self):
        return self.confservers[0] if self.confservers else 'conference.jabber.org'

    #@action(needs = ((unicode, "Chat Server", 'conference.jabber.org'),
                     #(unicode, 'Room Name', lambda: 'Digsby' + str(random.randint(0, sys.maxint))),
                     #(unicode, 'Your Nickname', lambda self: self.self_buddy.name)))
    @callsback
    def join_chat(self, server = None, room_name = None,
                  nick = None, convo = None, notify_profile=True, callback = None):

        chat_server_jid = server
        if not chat_server_jid:
            chat_server_jid = self.default_chat_server()

        room_name = self._get_chat_room_name(room_name)

        nick = self._get_chat_nick(nick)

        chat_server_jid = JID(room_name, domain = JID(chat_server_jid).domain)

        if not self.room_manager:
            self.room_manager = muc.MucRoomManager(self.stream)
            self.room_manager.set_handlers()

        if notify_profile:
            callback.success += profile.on_entered_chat

        convo = jabber.chat(self, chat_server_jid, callback)
        self.room_manager.join(chat_server_jid, nick, convo)

#        callback.success(convo)
#        profile.on_entered_chat(convo = convo)

    def _get_chat_nick(self, nick):
        if not nick:
            nick = self.self_buddy.jid.node
        return nick

    def _get_chat_room_name(self, room_name):
        if not room_name:
            room_name = 'Digsby%s' % random.randint(0, sys.maxint)
        return room_name

    def join_chat_jid(self, jid, nick = None):
        log.info('join_chat_jid %r with nick %s', jid, nick)

        jid = JID(jid)
        self.join_chat(jid.domain, jid.node, nick)

    def set_priority(self, priority):
        self.priority = priority
        self.presence_push()

    def send_file(self, buddy, filestorage):
        '''
        Sends a file to a buddy.

        fileobj must be a file like object.
        '''
        if isinstance(buddy, JabberResource):
            jid = buddy.jid
        else:
            jid = buddy.get_highest_priority_resource().jid
        log.info('sending file to %r', jid)
        xfer = jabber.filetransfer.initiateStream.SIsender(self, jid, filestorage)
        xfer.send_offer()
        return xfer

    def disco_finished(self, disco_node):
        log.info('got disco_node %s', disco_node)
        self.known_s5b_proxies.update((node.jid, set())
                                      for node in
                                      disco_node.find_feature(BYTESTREAMS_NS,
                                                              depth=1))

        # find conference nodes
        for node in disco_node.find_feature(MUC_URI, depth=1):
            self.confservers += [node.jid.as_unicode()]

        self.get_streamhosts()

    def get_streamhosts(self):
        for address in self.known_s5b_proxies:
            self.cache.request_object(jabber.objects.bytestreams.ByteStreams,
                                      (address, None), state='old',
                                      object_handler  = self.update_streamhost_result,
                                      error_handler   = self.update_streamhost_error,
                                      timeout_handler = self.update_streamhost_error)

    def update_streamhost_result(self, address, bytestreams_, _state):
        print "STREAMHOSTS:",bytestreams_.hosts
        try:
            proxy= self.known_s5b_proxies[address[0]]
        except KeyError:
            proxy= self.known_s5b_proxies[address[0]] = set()
        finally:
            from pprint import pprint
            pprint(bytestreams_.hosts)
            proxy.update(bytestreams_.hosts)

    def update_streamhost_error(self, address, bytestreams_=None):
        if bytestreams_:
            print "STREAMHOSTS ERROR:", bytestreams_
        else:
            print "STREAMHOSTS TIMEOUT"
        try:
            self.known_s5b_proxies[address[0]] = set()
        except KeyError:
            pass

    def get_privacy_lists(self):
        i = Iq(to_jid = self.jid.domain, stanza_type="get")
        q = Privacy()
        q.as_xml(i.xmlnode)
        self.send_cb(i, success=self.got_privacy_lists, error=self.privacy_list_fail);

    def got_privacy_lists(self, stanza):
        q = Privacy(stanza.get_query())
        self.default_list_name = q.default or "Digsby"
        self.default_list_exists = True if q.default else False
        if q.default or "Digsby" in [list_.name for list_ in q]:
            i = Iq(to_jid = self.jid.domain, stanza_type="set")
            q2 = Privacy()
            q2.default = q.default or "Digsby"
            q2.as_xml(i.xmlnode)
            self.send(i)
        if self.default_list_exists:
            self.get_default_list()
        log.info("got privacy lists:\n%s", q)

    def get_default_list(self):
        i = Iq(to_jid = self.jid.domain, stanza_type="get")
        q = Privacy()
        q.append(List(self.default_list_name))
        q.as_xml(i.xmlnode)
        self.send_cb(i, success=self.handle_default_list_response,
                                          error=self.privacy_list_fail)

    def handle_default_list_response(self, stanza):
        q = Privacy(stanza.get_query())
        self.default_list = q[0]

    def privacy_list_fail(self, stanza):
        log.info("failed to get privacy lists")

    def set_idle(self, *a, **k):
        pass

    @callsback
    def change_password(self, password, callback=None):
        reg = Register()
        reg.username = self.jid.node
        reg.password = password
        i = Iq(stanza_type="set")
        reg.as_xml(i.xmlnode)

        log.info('changing password for %s', self)
        self.send_cb(i, callback=callback)

    @action(lambda self: True if getattr(sys, 'DEV', False) else None)
    def xml_console(self):
        from gui.protocols.jabbergui import show_xml_console
        print show_xml_console
        show_xml_console(self)

    def delete_account(self, on_success, on_fail):
        reg = Register()
        reg.remove = True
        i = Iq(stanza_type="set")
        reg.as_xml(i.xmlnode)
        self.send_cb(i, success=(lambda *a, **k: on_success()), error=(lambda *a, **k: on_fail))

    def group_for(self, contact):
        return contact.group

    def get_groups(self):
        return [g.name for g in self.root_group if type(g) is Group]

    def get_group(self, groupname):
        for group in self.root_group:
            if type(group) is Group and group.name.lower() == groupname.lower():
                return group

    def idle(self):
        try:
            JabberClient.idle(self)
            if not self.stream.socket or self.stream.eof:
                raise AssertionError, "if the stream is dead or gone, we can't really send a keep-alive"
        except Exception:
            self.stop_timer_loops()
        else:
            self.cache.tick()

    def stream_error(self, err):
        if err.get_condition().name == "conflict":
            self.change_reason(self.Reasons.OTHER_USER)
        else:
            self.change_reason(self.Reasons.CONN_LOST)
            JabberClient.stream_error(self, err)

    @action(callable_predicate = lambda self: hasattr(self, 'vcard') if self.is_connected else None)
    def edit_vcard(self, *a, **k):
        import gui.vcard
        gui.vcard.vcardgui.VCardGUI(protocol = self)

    @action()
    def view_vcard(self):
        pass

    @action()
    def service_discovery(self):
        pass

    @action()
    def server_info(self):
        pass

    def save_vcard(self, vcard):
        i = Iq(stanza_type='set')
        n = i.xmlnode
        n.addChild(vcard.as_xml(n))
        self.vcard = vcard
        self.send_cb(i)

    def allow_message(self, buddy, mobj):
        super = common.protocol.allow_message(self, buddy, mobj)
        if super in (True, False):
            return super

        if not self.block_unknowns:
            return True

        jid = JID(buddy.jid).bare()

        try:
            item = self.roster.get_item_by_jid(jid)
        except KeyError:
            return False
        else:
            return True


presence_messages = dict(
    subscribe    = u" has requested presence subscription.",
    subscribed   = u" has accepted your presence subscription request." ,
    unsubscribe  = u" has canceled their subscription of our presence.",
    unsubscribed = u" has canceled our subscription of their presence.",
)



#    def block_jid(self, jid):
#        utf8 = JID(jid).as_utf8()
#        if not self.default_list_exists:
#            self.default_list = List("Digsby")
#        found = [item for item in self.default_list if item.type=="jid" and item.value==utf8]
#        if found and not found[0].all_blocked():
#            found[0].message      = False
#            found[0].presence_in  = False
#            found[0].presence_out = False
#            found[0].iq           = False
#        else:
#            self.default_list.append(ListItem(type="jid", value=utf8, action="Deny", order=?))
#        if not found or not found[0].all_blocked():
#            i = Iq(to_jid = self.jid.domain, stanza_type="set", stream=self.stream)
#            self.default_list.as_xml(i)
#            self.stream.send(i)
#
#        if not self.default_list_exists:
#            i2 = Iq(to_jid = self.jid.domain, stanza_type="set", stream=self.stream)
#            q2 = Privacy()
#            q2.default = q.default or "Digsby"
#            q2.as_xml(i2.xmlnode)
#            self.stream.send(i2)
#            self.default_list_exists = True


def do_threaded(callable):
    threaded(callable)()

def get_threaded_wrapper(*a, **k):
    return do_threaded

import protocols
protocols.declareAdapterForType(protocols.protocolForURI("http://www.dotsyntax.com/protocols/connectcallable"),
                                get_threaded_wrapper, JabberProtocol)

if __name__ == "__main__":
    j = JabberProtocol()
