from pyxmpp.jid import JID
from jabber.objects.shared_status.status import SharedStatus, SHARED_STATUS_NS
import jabber
from logging import getLogger
from common.actions import action
from .gtalkStream import GoogleTalkStream

import util.callbacks as callbacks
import uuid
from common import pref

log = getLogger('gtalk.protocol')

GTALK_SMS = False

status_state_map = {
    'available':      'normal',
    'free for chat':  'normal',
    'do not disturb': 'dnd',
}

GTALK_WAY = True

from jabber import jbuddy
class GtalkBuddy(jbuddy):
    sortservice = 'gtalk'

class GoogleTalk(jabber.protocol):
    name = 'gtalk'
    service = 'gtalk'

    status_state_map = status_state_map

    supports_group_chat = True

    buddy_class = GtalkBuddy

    def __init__(self, username, *a, **k):
        self._idle = None
        self._show = None
        if '@' not in username:
            username += '@gmail.com'
        jabber.protocol.__init__(self, username, *a, **k)
        self.stream_class = GoogleTalkStream
        self._invisible = False

    @jabber.protocol.invisible.getter
    def invisible(self):
        return self._invisible

    @invisible.setter
    def invisible(self, value):
        self._invisible = value

    if not GTALK_WAY:
        def set_idle(self, yes):
            if yes:
                self._idle = self.show
                self.show = 'away'
            else:
                self.show = self._idle
            self.presence_push()

        def set_message(self, message, status, format=None):
            log.info('set_message(%s): %r', status, message)

            state = status_state_map.get(status.lower(), 'dnd')

            # no <show/> tag means normal
            self.show   = state if state != 'normal' else None

#            self.invisible = status.lower() == 'Invisible'.lower()

            self._idle = self.show
            self.status = message
            self.presence_push()
    else:
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

    @action(lambda self: None)
    def change_password(self, *a): pass

    @action(lambda self: None)
    def edit_vcard(self, *a, **k): pass

    if GTALK_SMS:
        def _get_caps(self):
            import common
            return jabber.protocol._get_caps(self) + [common.caps.SMS]
        caps = property(_get_caps)

        @callbacks.callsback
        def send_sms(self, phone_number, message, callback = None):
            jid = jabber.JID(phone_number, 'sms.talk.google.com')
            # TODO: # self.send_message(to = jid, message = message)

    def session_started(self):
        s = self.stream
        s.set_iq_set_handler("query", SHARED_STATUS_NS, self.shared_status_set)
        jabber.protocol.session_started(self)

    def service_discovery_init(self):
        self.disco_init = jabber.disco.DiscoNode(self.cache, JID(self.jid.domain))
        self.disco_init.fetch(self.disco_finished, depth=1, timeout_duration = 1)
        self.disco_init2 = jabber.disco.DiscoNode(self.cache, JID("google.com"))
        self.disco_init2.fetch(super(GoogleTalk, self).disco_finished, depth=1, timeout_duration = 1)

    def disco_finished(self, disco_node):
        from jabber.objects.shared_status import make_get as status_make_get
        i = status_make_get(self)
        self.send_cb(i, success=self.unfreeze_presence,
                        error=self.unfreeze_presence_error,
                        timeout=self.unfreeze_presence_error,
                        timeout_duration=2)
        jabber.protocol.disco_finished(self, disco_node)

    def unfreeze_presence(self, stanza):
        #parse status thing, edit, store on self.
        self.shared_status_set(stanza)
        # pass
        #push presence
        self._presence_push()

    def unfreeze_presence_error(self, *a, **k):
        self._presence_push()

    def presence_push(self):
        pass

    def _presence_push(self):
        self.presence_push = self._presence_push
        shared = getattr(self, 'shared_status', None)
        if shared is not None:
            shared.show = self.show
            shared.status = self.status
            shared.invisible = self.invisible
            i = shared.make_push(self)
            cb = lambda *a, **k: jabber.protocol.presence_push(self)
            self.send_cb(i, success = cb, error = cb, timeout=cb, timeout_duration=5)
        else:
            jabber.protocol.presence_push(self)

    def shared_status_set(self, stanza):
        old_shared = getattr(self, 'shared_status', None)
        new_shared = SharedStatus(stanza.xmlnode)
        for attr in ("status_max", "status_list_max", "status_list_contents_max"):
            val = getattr(new_shared, attr.replace('-', '_'), None)
            if val is None:
                setattr(new_shared, attr, getattr(old_shared, attr, None))
        self.shared_status = new_shared

    def set_invisible(self, invisible = True):
        'Sets invisible.'
        self.invisible = invisible
        self.presence_push()

    def default_chat_server(self):
        return self.confservers[0] if self.confservers else 'groupchat.google.com'

    def _get_chat_nick(self, nick):
        if not nick:
            nick = unicode(self.self_buddy.jid).replace('@', '_')
        return nick

    def _get_chat_room_name(self, room_name):
        if not room_name:
            room_name = u'private-chat-' + unicode(uuid.uuid4())
        return room_name

    def _add_presence_extras(self, pres):
        c = pres.add_new_content("http://jabber.org/protocol/caps", "c")
        c.setProp('node',"http://www.google.com/xmpp/client/caps")
        c.setProp('ver',"1.1")
        c.setProp('ext',"pmuc-v1" + "voice-v1 video-v1 camera-v1" if pref('videochat.report_capability', True) else '')
        return super(GoogleTalk, self)._add_presence_extras(pres)
