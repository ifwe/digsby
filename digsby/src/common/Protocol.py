from __future__ import with_statement
from events import ThreadsafeGUIProxy
from actions import ObservableActionMeta
from util import callsback, traceguard
from util.primitives.funcs import get
import util.observe as observe, sys
from common import netcall, profile, prefprop
from cStringIO import StringIO
from PIL import Image

from logging import getLogger; log = getLogger('Protocol')
state_log = getLogger('protostate')


class ProtocolException(Exception): pass
class ChatInviteException(ProtocolException):
    def __init__(self, reason=None):
        self.reason = reason

    REASON_UNKNOWN = 'unknown'
    REASON_OFFLINE = 'offline'
    REASON_GROUPCHAT_UNSUPPORTED = 'unsupported'

class ProtocolStatus:
    ONLINE = N_('Online')
    CONNECTING = N_('Connecting...')
    AUTHENTICATING = N_('Authenticating...')
    LOADING_CONTACT_LIST = N_('Loading Contact List...')
    OFFLINE = N_('Offline')
    CHECKING = N_('Checking Mail...')
    INITIALIZING = N_('Initializing...')

class OfflineReason:
    NONE = ''
    BAD_PASSWORD = N_('Authentication Error')
    OTHER_USER = N_('You have signed in from another location')
    CONN_LOST = N_('Connection Lost')
    CONN_FAIL = N_('Failed to Connect')
    RATE_LIMIT = N_('You are signing in too often')
    NO_MAILBOX = N_('This account does not have a mailbox')
    INIT_FAIL = N_('Failed to Initialize')
    WILL_RECONNECT = N_('Connection Failed. Retry in %s')
    SERVER_ERROR   = N_('Internal Server Error')

from time import time

class StateMixin(observe.Observable):
    Statuses = ProtocolStatus
    Reasons = OfflineReason

    bots = set()

    def __init__(self, initialState = None, **k):
        observe.Observable.__init__(self)
        self.state = self.Statuses.OFFLINE if initialState is None else initialState
        self.state_changed_time = time()
        self.offline_reason = self.Reasons.NONE

    def change_state(self, newval):
        old = self.state
        self.state = newval

        if getattr(self.Statuses, 'OFFLINE', None) not in (self.state,):
            self.change_reason(self.Reasons.NONE)

        if old != newval:
            self.state_changed_time = time()
            self.notify('state', old, newval)

    def change_reason(self, newval):
        old = self.offline_reason
        self.offline_reason = newval
        self.notify('offline_reason', old, newval)

    def set_profile(self, value, format = None):
        pass

    def set_offline(self, reason=None):
        if reason is None:
            reason = self.offline_reason  # Don't change

        self.change_reason(reason)
        self.change_state(getattr(self.Statuses, 'OFFLINE', sentinel))

    def buddy_dictionaries(self):
        if hasattr(self, 'buddies'):
            return [self.buddies]
        else:
            return []

    @property
    def state_desc(self):
        if self.state == self.Statuses.ONLINE:
            return ''

        if self.state == getattr(self.Statuses, 'OFFLINE', sentinel):
            if self.offline_reason == self.Reasons.NONE:
                return ''
            else:
                return self.offline_reason
        else:

            if self.state == self.Statuses.WILL_RECONNECT:
                pass

            return self.state

    @property
    def connected(self):
        return self.state == self.Statuses.ONLINE

    def __getattr__(self, attr):
        try:
            return observe.Observable.__getattribute__(self, attr)
        except AttributeError, e:
            try:
                v = get(get(self, 'Statuses'), attr)
                return v == self.state
            except Exception:
                raise e

class Protocol(StateMixin):
    __metaclass__ = ObservableActionMeta
    __slots__ = ['name',
                 'username',
                 'password',
                 'hub',
                 'self_buddy',
                 'buddies',
                 'rdv_sessions']

    name = 'AbstractProtocol'

    # Gives a possible "best-guess" email address for a contact.
    @classmethod
    def email_hint(cls, contact): return None

    # server-side ordering of buddylist?
    is_ordered = False
    contact_order = False
    supports_group_chat = False

    # Message Formatting Defaults
    message_format = 'html'
    message_fg = True
    message_bg = True
    message_sizes = [8, 10, 12, 14, 18, 24, 36]

    def __repr__(self):
        return '<%s %s (%s)>' % \
               (self.__class__.__name__, self.username, self.state)



    def __init__(self, username, password, msgHub):
        StateMixin.__init__(self)
        self.username, \
        self.password, \
        self.hub       = str(username), \
                         str(password), \
                         ThreadsafeGUIProxy(msgHub)

        self.self_buddy = None
        self.buddies = None
        self.rdv_sessions = observe.ObservableDict()
        self.state = self.Statuses.OFFLINE
        self.offline_reason = self.Reasons.NONE

        self.add_observer(self.connection_status_monitor, 'state')
        self.add_observer(self.connection_status_monitor, 'offline_reason')

    FAKEROOT_NAME = prefprop('buddylist.fakeroot_name', default='Contacts')

    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.service)


    @property
    def service(self):
        '''An overridable property used for displaying to the user, which can
        differ from the "name," which is the impl. (like 'jabber').'''

        return self.name

    def _unregister_buddies(self):
        log.info('_unregister_buddies: %r', self)

        try:
            unregister = profile.account_manager.buddywatcher.unregister
        except AttributeError:
            unregister = lambda b: None

        for bdict in self.buddy_dictionaries():
            if bdict is None:
                continue

            for buddy in bdict.values():
                unregister(buddy)
                try:
                    buddy.setnotifyif('status', 'unknown')
                except Exception:
                    pass # jabber buddies...
                buddy.observers.clear()

            bdict.observers.clear()
            bdict.clear()

        self.remove_observer(self.connection_status_monitor, 'state', 'offline_reason')

    def silence_notifications(self, timeSecs = None):
        'silences notifications on this protocol for timeSecs seconds'

        old_silence_timer = getattr(self, '_silence_notifications_timer', None)
        if old_silence_timer is not None:
            old_silence_timer.stop()

        from common import silence_notifications
        self._silence_notifications_timer = silence_notifications(self, timeSecs)

    def connection_status_monitor(self, src, attr, old, new):
        assert src is self

        if new == self.Statuses.OFFLINE:
            self._unregister_buddies()

        from plugin_manager import plugin_hub
        plugin_hub.act('digsby.protocol.statechange.async', self, attr, old, new)

        state_log.critical('%r: %r changed from <%r> to <%r>', self, attr, old, new)

    def allow_message(self, buddy, mobj):
        if buddy is self.self_buddy:
            return True

        if mobj.type == 'outgoing':
            return True # don't ever block outgoing messages.

        if getattr(mobj, 'sms', False):
            return True #ticket #3869 don't filter sms (which are usually not on a buddy list, nor an allow list).

    def set_and_size_icon(self, icondata):
        '''
        Sets the buddy icon in the protocol.

        icondata should be raw image file data

        If the given data is too big (in bytes or size), the image
        is resized before being passed to the protocol.
        '''

        from gui.toolbox.imagefx import pil_to_white_gif, has_transparency

        img = Image.open(StringIO(icondata)) # will raise IOError if icondata isn't an image

        max     = getattr(self, 'max_icon_bytes', sys.maxint)
        formats = getattr(self, 'icon_formats', ['PNG', 'JPEG', 'BMP', 'GIF'])
        format  = img.format

        needsResize   = len(icondata) > max
        needsReformat = format not in formats

        log.info('set_and_size_icon')
        log.info('  %d bytes of icondata', len(icondata))
        log.info('  format: %s, formats: %r', format, formats)
        log.info('  needs:')
        log.info('    resize: %s', needsResize)
        log.info('    reformat: %s', needsReformat)

        if needsReformat:
            if has_transparency(img) and 'GIF' in formats:
                # img.getcolors returns None if there are more than 256 colors in the image
                # GIF is probably a good guess for images with less than 256 colors
                format = 'GIF'
            else:
                format = formats[0]

        if needsReformat or needsResize:
            if format == 'GIF':
                # reduces dithering by adapting image palette
                icondata = pil_to_white_gif(img)
                imgFile = StringIO(icondata)
                img = Image.open(imgFile)
                imgFile = StringIO(icondata)
            else:
                opts = {'PNG': {'optimize': True}} # for PNGs, optimize for space

                if format == 'BMP':
                    img = img.convert('RGB')

                imgFile = StringIO()
                img.save(imgFile, format, **opts.get(format, {}))
                icondata = imgFile.getvalue()

        if needsResize:
            # too big, we need to resize
            w, h = getattr(self, 'max_icon_size', (48, 48)); assert w == h
            log.info('set_icon got %d bytes but %s only allows %d, resizing to %dx%d...',
                     len(icondata), self.name, max, w, w)
            img = img.Resized(w)
            if format == 'GIF':
                icondata = pil_to_white_gif(img)
                imgFile = StringIO(icondata)

        if needsReformat or needsResize:
            log.info('encoded icon as %s, size %d: %s...', format, len(icondata), repr(icondata[:16]))

            if len(icondata) > max:
                return log.warning('still too big, not setting')

            icondata = imgFile.getvalue()

        import wx
        wx.CallAfter(lambda : self.set_buddy_icon(icondata))


    @property
    def caps(self):
        raise NotImplementedError('"caps" property (a sequence of Buddy '
                                  'capabilities) is not implemented in '
                                  '%s' % self.__class__.__name__)

    def simple_status(self, status_string):
        'Returns a simple status string. (available or away)'

        from common.statusmessage import simple
        return simple(status_string, self)


    def _set_status_object(self, statusobj):
        'Given a status object, sets the status message for this protocol.'

        acctstatus = statusobj.for_account(self)

        # apply default formatting if none was specified in the status message
        if acctstatus.format is None:

            import wx
            @wx.CallAfter
            def gui_thread(st=acctstatus):
                from common import profile
                if profile and profile.prefs:
                    from gui.uberwidgets.formattedinput import get_default_format
                    st = st.copy(editable=None)
                    st.format = get_default_format()

                netcall(lambda: self.set_message_object(st))

            return

        self.set_message_object(acctstatus)

    @callsback
    def set_message_object(self, message, callback = None):
        msg, status, format = message.message, message.status.lower(), message.format
        if message.editable:
            #needs a hook!
            from digsby_status.status_tag_urls import tag_status
            msg = tag_status(msg, self.service, message.status)
        self.set_message(msg, status, format=format)

    @property
    def is_connected(self):
        return self.state == self.Statuses.ONLINE

    def Connect(self):
        raise NotImplementedError

    def Disconnect(self):
        log.info('Protocol.Disconnect')

    def authorize_buddy(self, buddy_obj, allow=True, username_added=None):
        raise NotImplementedError

    def block_buddy(self, buddy_obj):
        raise NotImplementedError

    def unblock_buddy(self, buddy_obj):
        raise NotImplementedError

    def set_remote_alias(self, btuple, new_name):
        raise NotImplementedError

    def chat_with(self, buddyobj):
        raise NotImplementedError

    def send_message(self, bname, msg, formatting):
        raise NotImplementedError

    def send_typing_status(self, bname, status):
        raise NotImplementedError

    def send_im(self, buddyname, message):
        self.convo_for(self.get_buddy(buddyname)).send_message(message)

    def set_status_message(self):
        raise NotImplementedError

    def send_direct_im_req(self, *btuple):
        raise NotImplementedError

    @callsback
    def rejoin_chat(self, old_conversation, callback=None):
        '''
        given a Conversation object belonging to an "old," disconnected
        protocol, joins the same chat room on self (a new, connected protocol).
        '''
        if old_conversation.did_explicit_exit:
            return log.info('not rejoining chat: conversation was exited')

        _original_success = callback.success
        def success(convo):
            if old_conversation.did_explicit_exit:
                log.info('leaving chat: old convo was exited')
                convo.exit()
            else:
                _original_success(convo)
        callback.success = success

        self._do_rejoin_chat(old_conversation, callback=callback)

    @callsback
    def _do_rejoin_chat(self, old_conversation, callback=None):
        self.join_chat(room_name = old_conversation.chat_room_name, notify_profile=False, callback=callback)

    @callsback
    def make_chat_and_invite(self, buddies_to_invite, convo=None, room_name=None, server=None, notify=False, callback=None):
        log.info('make_chat_and_invite')
        log.info('  connection: %r', self)
        log.info('  buddies_to_invite: %r', buddies_to_invite)

        def success(convo):
            callback.success(convo)
            buds = filter(lambda b: b != self.self_buddy, buddies_to_invite)
            convo.add_pending_contacts(buds)
            for b in buds:
                self.invite_to_chat(b, convo)

        self.join_chat(room_name=room_name, server=server, success=success, error=callback.error, notify_profile=notify)

    @callsback
    def invite_to_chat(self, buddy, conversation, callback=None):

        log.warning('invite_to_chat: %r to %r', buddy, conversation)

        orig_error = callback.error
        def on_error(exc=None):
            with traceguard:
                if isinstance(exc, ChatInviteException):
                    name = buddy.name
                    if exc.reason == ChatInviteException.REASON_OFFLINE:
                        msg = _('Error inviting {name}: they are offline').format(name=name)
                    elif exc.reason == ChatInviteException.REASON_GROUPCHAT_UNSUPPORTED:
                        msg = _('Error inviting {name}: they do not support group chat').format(name=name)
                    conversation.system_message(msg)

            orig_error(exc)

        callback.error = on_error
        return conversation.invite(buddy, callback=callback)

    def send_chat_req(self, btuple, room_name, invitemessage):
        raise NotImplementedError

    def send_buddy_list_request(self, btuple):
        raise NotImplementedError

    def set_invisible(self, invisible):
        raise NotImplementedError

    def accept_file(self, file_obj):
        raise NotImplementedError

    def add_buddy(self, bname, group_id=None, pos=0, service=None):
        raise NotImplementedError

    def remove_buddy(self, btuple, group_id=None):
        raise NotImplementedError

    def move_buddy(self, buddy, to_group, from_group=None, pos=0):
        raise NotImplementedError

    def get_group(self, groupname):
        raise NotImplementedError, "should return a Group or None"

    def get_groups(self):
        'Returns a list of group names.'

        return [g.name for g in self.root_group]

    def get_buddy(self, buddyname):
        return self.buddies[buddyname]

    def get_protocol_buddy(self, buddy):
        'Given a buddy, returns the protocol-specific buddy object stored in this Protocol.'
        return self.get_buddy(buddy.name)

    def has_buddy_on_list(self,buddy):
        for group in self.root_group:
            for listbuddy in group:
                if buddy.name == listbuddy.name and buddy.service == listbuddy.service:
                    return True
        return False

    def has_buddy(self, buddyname):
        return buddyname in self.buddies

    def add_new_buddy(self, buddyname, groupname, service = None, alias = None):
        g     = self.get_group(groupname)

        def doit(*res):
            grp = self.get_group(groupname)
            buddy = self.get_buddy(buddyname)
            grp.add_buddy(buddyname, service = service)

            if alias is not None:
                profile.set_contact_info(buddy, 'alias', alias)

        if g is None:
            self.add_group(groupname, success = doit)
        else:
            doit()


    @callsback
    def move_buddy_creating_group(self, contact, groupname, fromgroupname, index = 0, callback = None):
        def do_move():
            self.move_buddy(contact, groupname, fromgroupname, index,
                            callback = callback)

        group = self.get_group(groupname)
        if group is None:
            self.add_group(groupname, success = lambda newgroup,*a,**k: netcall(do_move))
        else:
            do_move()


    def add_contact(self, contactname, group, service = None):
        self.add_buddy(contactname, group, service = service)

    @property
    def protocol(self):
        return self.name

    def should_log(self, messageobj):
        return True

    def when_reconnect(self, callback):
        return self.account.when_reconnect(callback)

if __name__ == '__main__':
    i = Image.open('c:\\digsbybig.png')

    import wx

    r, g, b, a = i.split()
    rgb = Image.merge('RGB', (r,g,b))
    rgb = rgb.convert('P', palette=Image.ADAPTIVE, colors=255, dither=Image.NONE)
    rgb.options['transparency'] = 256


    # invert the alpha channel
    a = a.point(lambda p: 256 if p == 0 else 0)
    rgb.paste(a, a)

    rgb.save('d:\\test.png')


    #from pprint import pprint
    #p = rgb.palette.palette
    #print [ord(c) for c in [p[256], p[256*2], p[256*2]]]

    #pprint(dir(rgb.palette))
    #print rgb.palette.tostring()
    #pprint (len(rgb.histogram()))

    #(255, 0, 255), ()
