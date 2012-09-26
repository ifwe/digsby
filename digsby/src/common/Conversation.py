from __future__ import with_statement
from logging import getLogger
from actions import ActionMeta
from Buddy import get_bname
from common import pref, profile, netcall, urlhandler
from datetime import datetime
from util.observe import Observable, ObservableList, observable_dict
from util import traceguard


log = getLogger('common.conversation')
AUTORESP = _('[Auto-Response] {message}')


class Conversation( Observable ):
    __metaclass__ = ActionMeta

    def __init__(self, protocol):

        Observable.__init__(self)

        self.room_list = ObservableList()

        self.protocol      = protocol
        self.autoresponded = False
        self.typing_status = observable_dict()
        self.just_had_error = False

        self.pending_contacts_callbacks = set()

        self.start_time_utc = datetime.utcnow()

        self._bind_reconnect()
        self.protocol.add_observer(self.__on_proto_state, 'state')

        self.videochat_urlhandler = None


    def _bind_reconnect(self):
        if self.protocol is not None:
            self.protocol.when_reconnect(self.__on_account_reconnect)

    def __on_proto_state(self, src, attr, old, new):
        if new == src.Statuses.OFFLINE and self.ischat:
            import wx
            wx.CallLater(500, lambda: self.system_message(_('Disconnected')))
            self.protocol.remove_observer(self.__on_proto_state, 'state')

    @property
    def conversation_reconnected(self):
        try:
            d = self._conversation_reconnected
        except AttributeError:
            from util.primitives.funcs import Delegate
            d = self._conversation_reconnected = Delegate()
        return d

    def __on_account_reconnect(self, new_connection):
        def foo():
            log.warning('on_account_reconnect - connection: %r', new_connection)
            log.warning('  ischat: %r', self.ischat)

            if self.ischat:
                def success(convo):
                    log.warning('rejoin_chat success: %r', convo)
                    self.conversation_reconnected(convo)

                log.warning('rejoin_chat')
                new_connection.rejoin_chat(self, success=success)

        def later(): netcall(foo)
        import wx
        wx.CallLater(1000, later)

    def add_pending_contacts(self, contacts):
        for cb in self.pending_contacts_callbacks:
            cb(contacts)

    def maybe_send_typing_status(self, status):
        '''sends typing status if enabled in prefs'''

        if pref('privacy.send_typing_notifications', False):
            self.send_typing_status(status)

    @property
    def icon(self):
        if self.ischat:
            from gui import skin
            return skin.get('serviceicons.digsby')
        else:
            return self.buddy.icon

    def send_plaintext_message(self, message):
        return self._send_message(default_formatted_text(message))

    def send_message(self, message, *args, **kwargs):

        # allow plugins to modify the message
        import hooks
        message = hooks.reduce('digsby.im.msg.send', message)

        echonow = pref('messaging.echo_immediately', type=bool, default=True)
        # Call Protocol Conversation's send message.

        def error(e=None):
            log.info('Error sending message: %r', message.format_as('plaintext'))
            log.info('Message error callback received %r: %r', type(e), e)
            if self.just_had_error:
                return
            emsg = getattr(e, 'error_message', '')
            if emsg:
                self.system_message(emsg, content_type = 'text/plain')
            else:
                self.system_message(_("Some of the messages you sent may not have been received."), content_type = 'text/plain')
            self.just_had_error = True

        def message_sent():
            self.just_had_error = False

        def echo_message(msg=None):
            echomsg = msg or message
            if kwargs.get('auto', False):
                #echomsg = AUTORESP.format(message = echomsg)
                if 'has_autotext' not in kwargs:
                    kwargs.update(has_autotext = True)

            self.sent_message(echomsg, **kwargs)

        if echonow:
            def success(msg=None):
                message_sent()

            echo_message()
        else:
            def success(msg=None):
                message_sent()
                echo_message(msg)

        conn = profile.connection
        if conn is not None:
            conn.send_message_intercept(self.buddy, message.format_as('plaintext'))

        netcall(lambda: self._send_message(message, success=success, error=error, *args, **kwargs))

        if not self.ischat:
            # If this is a normal one-on-one chat, record an entry in the
            # "to-from" list
            b = self.buddy
            if b is not None and b is not self.protocol.self_buddy:
                profile.blist.add_tofrom('im', b, self.protocol)

    def system_message(self, message, **opts):
        log.debug('System message: message=%r, opts=%r', message, opts)
        opts['buddy'] = None
        opts['type'] = 'status'
        return self._message(message = message, **opts)

    def important_system_message(self, message, **opts):
        opts['system_message_raises'] = True
        return self.system_message(message, **opts)

    def buddy_says(self, buddy, message, **options):
        '@return: True if the message was allowed'
        if not isinstance(message, unicode):
            raise TypeError, 'buddy_says needs unicode got type %r: %r' % (type(message), message)

        try:
            timestamp = options.get('timestamp', None)
            if timestamp is None:
                timestamp = datetime.utcnow()

            content_type = options.pop('content_type', 'text/plain')

            from common.message import Message
            messageobj = Message(buddy = buddy,
                                 message = message,
                                 timestamp = timestamp,
                                 content_type = content_type)

            from plugin_manager import plugin_hub
            msgtype = options.get('type', None)

            # Allow plugins to make changes to the messageobj
            plugin_hub.act('digsby.im.msg.pre', messageobj, msgtype)

            if messageobj.message != '':
                # TODO: pass entire (potentially) changed messageobj to self._message
                return self._message(buddy, messageobj.message,
                              content_type = messageobj.content_type,
                              **options)
        except Exception, e:
            log.error("Failed to parse message %r",e)
            # do what it used to do
            return self._message(buddy, message, **options)

    def _message(self, buddy, message, **options):
        '@return: True if the message was allowed'

        # Always use local time for online messages, in case user's clock is wrong.
        if not options.get('offline', True):
            options.pop('timestamp', None)

        if options.get('offline', False):
            self.autoresponded = True # Prevent autoresponse to offline messages

        # if timestamp is None substitute it with UTC now
        timestamp = options.pop('timestamp', None)
        if timestamp is None:
            timestamp = datetime.utcnow()

        from common.message import Message
        messageobj = Message(buddy        = buddy,
                       message      = message,
                       timestamp    = timestamp,
                       conversation = self,
                       **options)
        from plugin_manager import plugin_hub
        plugin_hub.act('digsby.im.msg.async', self, messageobj, options.get('type', None))

        from common import profile
        return profile.on_message(messageobj) is not profile.on_message.VETO

    def received_message(self, buddy, message, **options):
        if not isinstance(message, unicode):
            raise TypeError('message argument must be unicode')

        return self.buddy_says(buddy, message, type = 'incoming', **options)

    def sent_message(self, message, **options):
        self.autoresponded = True
        self.echo_message(message, **options)

    def echo_message(self, message, **options):
        buddy = self.self_buddy
        with traceguard:
            message = message.format_as('xhtml')
            options['content_type'] = 'text/xhtml'

        return self.buddy_says(buddy, message, type = 'outgoing', **options)

    def incoming_message(self, autoresp=True):
        status = profile.status.for_account(self.protocol)

        from common import StatusMessage

        # if our current status is away, not invisible, and auto respond is on,
        # then send an automatic reply...but not when offline (or pretending to be)

        if all((autoresp, status.away, not status.invisible, status != StatusMessage.Offline,
                pref('messaging.when_away.autorespond', False), not self.autoresponded)):

            if status.message:
                self.autoresponded = True

                import wx
                @wx.CallAfter
                def later():
                    if getattr(status, '_a_href', False):
                        content_type = 'text/html'
                    else:
                        content_type = 'text/plain'
                    self.autorespond(status.message, content_type = content_type)


    def __contains__(self, buddy):
        bname = get_bname(buddy)
        buddy = self.buddies[bname]
        return buddy in self.room_list

    def tingle(self):
        self.system_message('Your digsby sense is tingling!')

    @property
    def buddy(self):
        'For non-chat conversations, returns the buddy you are messaging.'

        #TODO: implement this in the protocols correctly instead of "guessing"

        r = self.other_buddies

        if len(r) == 1:
            return r[0]
        else:
            return self.room_list[0] if self.room_list else self.self_buddy

    @property
    def other_buddies(self):
        r = self.room_list[:]
        while True:
            try: r.remove(self.self_buddy)
            except ValueError: break
        return r

    @property
    def chat_member_count(self):
        '''Returns the number of connected members in this chat room, or 0 if disconnected.'''
        if self.protocol.connected:
            return len(self.room_list)
        else:
            return 0

    def send_typing_status(self, status): raise NotImplementedError

    did_explicit_exit = False

    def exit(self):
        'Called by the GUI when a conversation window is closed.'
        self.unregister_videochat_urlhandler()

    def explicit_exit(self):
        self.did_explicit_exit = True
        self.exit()

    def autorespond(self, msg, format=None, **kws):
        if not self.ischat:
            if self.buddy.isbot:
                log.info('Not sending autoresponse to bot: %r', self.buddy)
                return
            if 'has_autotext' not in kws:
                kws.update(has_autotext = True)

            self.send_message(default_formatted_text(AUTORESP.format(message = msg)), auto=True, **kws)

    _inwindow = False

    @property
    def queued_system_messages(self):
        try:
            return self._queued_system_messages
        except AttributeError:
            self._queued_system_messages = []
            return self._queued_system_messages

    def play_queued_messages(self):
        self._inwindow = True
        if hasattr(self, '_queued_system_messages'):
            try:
                for kws in self._queued_system_messages:
                    with traceguard:
                        self.system_message(**kws)
            finally:
                del self._queued_system_messages[:]

    def buddy_join(self, buddy):
        if self.ischat:
            self._presence_message(_(u"{name} joined the group chat").format(name=buddy.name))

    def buddy_leave(self, buddy):
        if self.ischat and buddy is not self.protocol.self_buddy:
            self._presence_message(_(u"{name} left the group chat").format(name=buddy.name))

    def received_native_videochat_request(self, vidoechat_response_callback = None):
        log.info('native_video_chat_request')

        urlarg = 'makeavcall/%s' % id(self)

        if self.videochat_urlhandler is None:
            def videochat_urlhandler():
                if vidoechat_response_callback is not None:
                    vidoechat_response_callback(False)
                self.send_generic_videochat_request()

            self.videochat_urlhandler = (urlarg, videochat_urlhandler)
            urlhandler.register(*self.videochat_urlhandler)

        link = 'digsby://%s' % urlarg

        msg = _('%(name)s wants to have an Audio/Video chat. <a href="%(link)s">Send them an invite.</a>') % dict(
            name=self.buddy.name, link=link)

        self.important_system_message(msg, content_type = 'text/html')

    def send_generic_videochat_request(self):
        from digsby.videochat import VideoChat
        VideoChat(self.buddy)

    def unregister_videochat_urlhandler(self):
        if self.videochat_urlhandler != None:
            urlhandler.unregister(*self.videochat_urlhandler)
            self.videochat_urlhandler = None

    def _presence_message(self, msg):
        kws = dict(message=msg, content_type='text/plain', linkify=False)
        if self._inwindow:
            self.system_message(**kws)
        else:
            self.queued_system_messages.append(kws)

def default_formatted_text(msg):
    'Returns a fmtstr object with the text of msg and the formatting from prefs'

    from util.primitives.fmtstr import fmtstr
    from gui.uberwidgets.formattedinput import get_default_format

    return fmtstr.singleformat(msg, get_default_format())

if __name__ == '__main__':

    convo = Conversation()

    def convo_changed(source, attr, old, new):
        print attr, old, new

    convo.add_observer(convo_changed)

    convo.last_message = 'test message'
