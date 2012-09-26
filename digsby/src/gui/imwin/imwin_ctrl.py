'''

IM window logic and interaction

'''
from __future__ import with_statement



import sys
import wx
from wx import EVT_BUTTON, MessageBox, PyTimer

from operator import attrgetter
from traceback import print_exc
from logging import getLogger; log = getLogger('imwinctrl'); info = log.info; info_s = getattr(log, 'info_s', log.info)

from util import traceguard
from common import profile, prefprop, pref
from common.message import Message

from gui.infobox.htmlgeneration import GetInfo
from imwin_tofrom import IMControl, EmailControl, SMSControl
from gui.toolbox import check_destroyed, calllimit
from common.sms import SMS_MAX_LENGTH

class ImWinCtrl(object):
    '''
    IM window logic.

    - incoming messages and new conversations go to the "message" function
    - the on_mode_change[d] functions are called when changing modes
    '''

    def __init__(self):
        # "controllers" in charge of the contents of the To/From combos
        self.IMControl = IMControl(self, self.capsbar, self.To, self.From)
        self.IMControl.OnSelection += self.FocusTextCtrl
        self.IMControl.OnSwitchContact += lambda c: self.set_conversation(c.protocol.convo_for(c))

        self.EmailControl = EmailControl(self.To, self.From)
        self.EmailControl.OnLoseFocus += lambda: self._emailpanel.subject_input.SetFocus()

        self.SMSControl   = SMSControl(self.To,   self.From)
        self.SMSControl.OnLoseFocus += self.FocusTextCtrl

        self.controllers = {'im': self.IMControl,
                            'email': self.EmailControl,
                            'sms': self.SMSControl}

        self.mode   = None
        self.convo  = None

        self.typing = None            # buddy's typing state
        self.typing_status = None     # your typing state
        self.typing_timer = None      # timer for keeping track of your typing state
        self.clear_typing_timer = wx.PyTimer(self.on_clear_typing_timer)

        self.GetButton('im').Bind(EVT_BUTTON, lambda e: self.set_mode('im', toggle_tofrom = True))

        for mode in ('email', 'sms', 'info'):
            self.GetButton(mode).Bind(EVT_BUTTON, lambda e, mode=mode: self.set_mode(mode))

        self.GetButton('video').Bind(EVT_BUTTON, lambda e: self.on_video())

        multichat = self.GetButton('multichat')
        if multichat is not None:
            multichat.Bind(wx.EVT_TOGGLEBUTTON, lambda e: self.toggle_roomlist())

    send_typing = prefprop('privacy.send_typing_notifications', True)
    typed_delay = prefprop('messaging.typed_delay', 5)

    def message(self, messageobj, convo = None, mode = 'im', meta = None):
        "Called by imhub.py with incoming messages."

        info('%r', self)
        info_s('  messageobj: %r', messageobj)
        info('       convo: %r', convo)
        info('        mode: %r', mode)
        info('        meta: %r', meta)

        assert wx.IsMainThread()

        if messageobj is None:
            # starting a new conversation--no message
            self.set_conversation(convo)
            self.set_mode(mode)
            self.IMControl.SetConvo(convo)
            if convo.ischat:
                self.show_roomlist(True)

        elif (messageobj.get('sms', False) or getattr(convo.buddy, 'sms', None)) and not profile.blist.on_buddylist(convo.buddy):
            # an incoming SMS message
            if self.convo is None:
                self.set_conversation(convo)

            if self.mode != 'sms':
                self.set_mode('sms')

            # just show it
            self.show_message(messageobj)
        else:
            convo = messageobj.conversation

            if self.mode is None:
                self.set_mode(mode)
            self.show_message(messageobj)
            self.set_conversation(convo)
#            self.IMControl.SetConvo(convo)

    def set_mode(self, mode, toggle_tofrom = False):
        with self.Frozen():
            oldmode = getattr(self, 'mode', None)
            self.on_mode_change(oldmode, mode, toggle_tofrom)
            self.show_controls(mode)
            self.on_mode_changed(mode)

    Mode = property(attrgetter('mode'), set_mode)

    def on_mode_change(self, oldmode, mode, toggle_tofrom = False):
        'Invoked before the GUI is shown for a new mode.'

        # To/From showing and hiding
        if oldmode != mode and mode in ('email', 'sms'):
            self.ShowToFrom(True)
        elif mode == 'info':
            self.ShowToFrom(False)

        # Enabling/disabling formatting buttons
        if mode == 'sms' and oldmode != 'sms':
            wx.CallAfter(lambda: self.input_area.tc.SetMaxLength(SMS_MAX_LENGTH))
        elif oldmode == 'sms' and mode != 'sms':
            wx.CallAfter(lambda: self.input_area.tc.SetMaxLength(0))

        # If going to IM, Email, or SMS--show that mode's to/from combo
        for m in ('im', 'email', 'sms'):
            if mode == m and oldmode != m:
                wx.CallAfter(self.controllers[mode].Apply)
                break

        # If going to IM mode...
        if mode == 'im':
            # toggle if clicking IM button
            #   or
            # ask IM control if there is more than one choice for the To/From choices.
            if self.convo.ischat:
                self.ShowToFrom(False)
            elif oldmode != 'im':
                self.ShowToFrom(self.IMControl.HasChoices)
            elif toggle_tofrom:
                self.ShowToFrom(not self.capsbar.ToFromShown)


            #show = self.IMControl.HasChoices if oldmode != 'im' else not self.capsbar.ToFromShown
            #self.ShowToFrom(show)

        if oldmode is not None:
            self.GetButton(oldmode).Active(False)

        self.GetButton(mode).Active(True)

    def on_mode_changed(self, mode):
        'Invoked after the GUI is shown for a new mode.'

        if mode in ('im', 'sms'):
            self.on_message_area_shown()
            if self.IsActive():
                # for some reason, if we don't use wx.CallAfter on Mac, the call happens to early.
                if sys.platform.startswith('darwin'):
                    wx.CallAfter(self.FocusTextCtrl)
                else:
                    self.FocusTextCtrl()

        elif mode == 'info':
            self.set_profile_html(self.Buddy)
            self.profile_html.SetFocus()       # so mousewheel works immediately

        elif mode == 'email':
            self._emailpanel.subject_input.SetFocus()

    def on_send_message(self):
        if getattr(self, 'on_send_message_' + self.mode, lambda a: None)():
            self.Top.on_sent_message(self.mode, self)

    def on_send_message_im(self):
        'Invoked when enter is pressed in the message input box during IM mode.'

        val = self.input_area.GetFormattedValue()

        # Early exit if there is no message to send.
        if not val.format_as('plaintext'):
            return

        self.history.commit(val.format_as('plaintext'))

        # If the user has selected different to/from accounts, change
        # our conversation object.
        if self.set_conversation_from_combos():
            self.convo.send_message(val)
            self.ClearAndFocus()
            return True

    def on_send_email(self, *a):
        'Invoked when the "Send" button is pressed. (For Emails)'

        to, frm = self.EmailControl.ToEmail, self.EmailControl.FromAccount

        if to is None:
            return wx.MessageBox(_('Please add an email address for this buddy by '
                                   'clicking the "To:" box.'),
                                 _('Compose email to {name}').format(name=self.Buddy.name))

        epanel = self._emailpanel

        def success(*a):
            log.info('Email send success')
            # store history
            profile.blist.add_tofrom('email', to, frm)

            epanel.Clear()
            epanel.SetStatusMessage(_('Message Sent'))
            epanel.send_button.Enable(True)
            epanel.openin.Enable(True)

            import hooks
            hooks.notify('digsby.statistics.email.sent_from_imwindow')

        def error(*a):
            log.info('Email send error')
            epanel.SetStatusMessage(_('Failed to Send Email'))
            epanel.send_button.Enable(True)
            epanel.openin.Enable(True)

        epanel.SetStatusMessage(_('Sending...'))
        epanel.send_button.Enable(False)
        epanel.openin.Enable(False)

        subject = self._get_email_subject()
        body = self._get_email_body()

        frm.OnClickSend(to      = to,
                        subject = subject,
                        body    = body,
                        success = success,
                        error   = error)

    def _get_email_subject(self):
        return self._emailpanel.subject_input.Value

    def _get_email_body(self):

        body = self._emailpanel.email_input_area.Value
        if pref('email.signature.enabled', type = bool, default = False):
            footer = u'\r\n' + pref('email.signature.value', type = unicode,
                                    default = u'\r\n_______________________________________________________________'
                                               '\r\nSent using Digsby - http://email.digsby.com')
        else:
            footer = ''

        return body + footer

    def on_send_message_sms(self):
        'Invoked when enter is pressed in the message input box during SMS mode.'

        # Early exit if there is no message to send.
        if not self.input_area.Value: return

        to, frm = self.SMSControl.ToSMS, self.SMSControl.FromAccount
        if to is None:
            MessageBox(_('Please add an SMS number first.'),
                       _('Send SMS Message'))
        elif frm is None:
            MessageBox(_('You are not signed in to any accounts which can send SMS messages.'),
                       _('Send SMS Message'))
        else:

            message = self.input_area.Value

            def on_success():
                self.show_message(Message(buddy = frm.self_buddy,
                                          message = message[:SMS_MAX_LENGTH],
                                          conversation = self.convo,
                                          type = 'outgoing'))
                self.ClearAndFocus()

            def on_error(errstr=None):
                if errstr is not None:
                    more = '\n' + _('The error message received was:') + '\n\t%s' % errstr
                else:
                    more = ''

                MessageBox(_('There was an error in sending your SMS message.') + more,
                           _('Send SMS Message Error'),
                           style = wx.ICON_ERROR)

            # Check the length--even though we limit the number of characters in SMS mode, the input box
            # may already have had too many characters.
            if len(message) > SMS_MAX_LENGTH:
                sms_line1 = _('Only the first {max_length:d} characters of your message can be sent over SMS:').format(max_length=SMS_MAX_LENGTH)
                sms_line2 = _('Do you want to send this message now?')
                                
                if wx.NO == wx.MessageBox(u'%s\n\n"%s"\n\n%s' % (sms_line1, message, sms_line2),
                                          _('Send SMS - Character Limit'), style = wx.YES_NO):
                    return

            import hooks
            hooks.notify('digsby.statistics.sms.sent')
            frm.send_sms(to, message[:SMS_MAX_LENGTH], success = on_success, error = on_error)

    def on_edit_email(self):
        '''
        Uses the email account's mail client to edit the currently entered email.

        Invoked when the "Edit In..." button is clicked in the email panel.
        '''

        to, frm = self.EmailControl.ToEmail, self.EmailControl.FromAccount

        if to is not None and frm is not None:
            frm.OnComposeEmail(to      = to,
                               subject = self._emailpanel.subject_input.Value,
                               body    = self._emailpanel.email_input_area.Value)

    def set_conversation_from_combos(self):
        '''
        If our current conversation doesn't match the to and from accounts
        chosen by the combos, obtains a new conversation.

        Returns False if there are no accounts to send the IM with.
        '''
        if self.ischat:
            return self.convo.protocol.connected

        to, frm = self.IMControl.Buddy, self.IMControl.Account

        # If IMControl's Account object is None, all accounts which can message
        # the buddy we're talking to have signed off. We can't send the message.
        if frm is None: return False

        convo = self.convo
        if convo.protocol is not frm or convo.buddy is not to:
            log.info('asking protocol %r for a new convo for buddy %r with service %r', frm, to, to.service)
            convo = frm.convo_for(to)
            log.info('got conversation %r with buddy/service %r %r:', convo, convo.buddy, convo.buddy.service)
            self.set_conversation(convo)

        return True

    def on_close(self):
        if getattr(self, '_closed', False):
            log.warning('FIXME: imwin_ctrl.on_close was called more than once!!!')
            return

        self._closed = True

        del self.capsbar.buddy_callback
        del self.capsbar

        import hooks
        hooks.notify('digsby.overlay_icon_updated', self)

        from plugin_manager import plugin_hub

        plugin_hub.act('digsby.im.conversation.close.async', self.convo)

        self.unlink_observers()
        if self.convo is not None:
            self.unwatch_conversation(self.convo)
            try:
                self.convo.explicit_exit()
            except Exception:
                print_exc()

    @property
    def Conversation(self):
        return self.convo

    @property
    def Buddy(self):
        return self.IMControl.Buddy

    @property
    def SMS(self):
        return self.SMSControl.get_contact_sms()

    def set_conversation(self, convo, meta = None):
        if convo is self.convo:
            return

        # watch/unwatch
        shouldShowToFrom = False
        if self.convo is not None:
            self.unwatch_conversation(self.convo)
            self.convo.exit()
            if not self.convo.ischat:
                shouldShowToFrom = True

        self.convo = convo
        self.watch_conversation(convo)

        if self.is_roomlist_constructed():
            self.roomlist.SetConversation(convo)

        contact = meta if meta is not None else convo.buddy

        self.capsbar.ApplyCaps(convo=convo)
        self.IMControl.SetConvo(convo, meta)
        if shouldShowToFrom and not self.convo.ischat:
            self.ShowToFrom(shouldShowToFrom)

        self.EmailControl.SetContact(contact)
        self.SMSControl.SetContact(contact)
        self.update_icon()
        self.update_title()

        self.choose_message_formatting()
        self.convo.play_queued_messages()

        if convo.ischat:
            @wx.CallAfter
            def after():
                self.show_roomlist(True)

    def _update_caps_and_title(self, *a):
        @wx.CallAfter
        def after():
            self.capsbar.ApplyCaps(convo=self.convo)
            self.update_title()

            if self.convo.ischat and not getattr(self, 'roomlist_has_been_shown', False):
                log.info("showing roomlist...")
                self.toggle_roomlist()

    def watch_conversation(self, convo):

        from plugin_manager import plugin_hub

        plugin_hub.act('digsby.im.conversation.open.async', convo)

        convo.typing_status.add_observer(self.typing_status_changed)
        convo.add_observer(self._update_caps_and_title, 'ischat')

        buddy = convo.buddy

        buddy.add_observer(self.buddy_status_changed, 'status')
        buddy.add_observer(self.buddy_info_changed)

        if convo.ischat:
            convo.room_list.add_observer(self.chat_buddies_changed)
            convo.conversation_reconnected.add_unique(self.on_conversation_reconnected)

        convo.protocol.add_observer(self._on_convo_proto_state_change, 'state')

        #profile.account_manager.buddywatcher.watch_status(buddy, self.on_status_change)

    def on_conversation_reconnected(self, convo):
        @wx.CallAfter
        def gui():
            log.warning('on_conversation_reconnected: %r', convo)
            self.set_conversation(convo)
            convo.system_message(_('Reconnected'))

    def chat_buddies_changed(self, *a):
        wx.CallAfter(self.update_title)

    def unwatch_conversation(self, convo = None):
        if convo is None: convo = self.convo
        if convo is not None:
            buddy = convo.buddy

            convo.remove_observer(self._update_caps_and_title, 'ischat')
            convo.typing_status.remove_observer(self.typing_status_changed)
            if buddy is not None:
                buddy.remove_observer(self.buddy_status_changed, 'status')
                buddy.remove_observer(self.buddy_info_changed)

            convo.room_list.remove_observer(self.chat_buddies_changed)
            convo.conversation_reconnected.remove_maybe(self.on_conversation_reconnected)

            convo.protocol.remove_observer(self._on_convo_proto_state_change, 'state')
            #profile.account_manager.buddywatcher.unwatch_status(buddy, self.on_status_change)

    def _on_convo_proto_state_change(self, proto, attr, old, new):
        @wx.CallAfter
        def after():
            if self.convo.ischat and new == proto.Statuses.OFFLINE:
                # chats include roomlist count, and need to be updated on disconnect.
                self.update_title()

    def show_status(self, update, ondone=None):
        cb = lambda u=update: self.show_message(u, ondone)

        try:
            timer = self._statustimer
        except AttributeError:
            timer = self._statustimer = wx.PyTimer(cb)
        else:
            timer.SetCallback(cb)

        if not self._statustimer.IsRunning():
            self._statustimer.Start(250, True)

    @calllimit(1)
    def buddy_info_changed(self, *a):
        '''
        This method is called anytime the buddy's information changes.

        If we're in "info" mode, the HTML profile box is updated.
        '''
        if self.mode == 'info':
            self.set_profile_html(self.Buddy)

    def buddy_status_changed(self, *a):
        wx.CallAfter(self._buddy_status_changed)

    def _buddy_status_changed(self):
        if check_destroyed(self):
            return

        if self.convo.ischat:
            return

        # if the buddy's online status changes, we may need to add/remove the
        # Files button
        self.capsbar.ApplyCaps(self.Buddy)

        # if we're showing the buddy's status orb in the tab/window title,
        # update those icons now.
        if self.icontype == 'status':
            self.update_icon()

    def typing_status_changed(self, *a):
        "Called when the conversation's typing status changes."

        typing = self.convo.typing_status.get(self.convo.buddy, None)

        # this pref indicates how long after not receiving typing notifications
        # we wait until clearing them, in seconds. 0 means never clear.
        typing_clear_time_secs = pref('messaging.typing_notifications.clear_after', default=30, type=int)
        if typing_clear_time_secs > 0:
            if typing is not None:
                self.clear_typing_timer.StartOneShot(1000 * typing_clear_time_secs)
            else:
                self.clear_typing_timer.Stop()

        self.on_typing(typing)

    def on_typing(self, typing):
        self.typing = typing
        self.update_title()
        self.update_icon()

    def on_clear_typing_timer(self):
        '''
        Called after a set period of time with no typing updates.
        '''

        if not wx.IsDestroyed(self):
            self.on_typing(None)

    def choose_message_formatting(self):
        '''
        Gives a chance for both the conversation and the protocol to expose
        an attribute "message_formatting", which if set to 'plaintext'
        will cause us only to extract (and send as IMs) text from the input
        box, not HTML.
        '''
        plain = False
        conv  = self.convo

        try: plain = conv.message_formatting == 'plaintext'
        except AttributeError:
            try: plain = conv.protocol.message_formatting == 'plaintext'
            except AttributeError: pass

        self.plainttext = plain

    def show_message(self, messageobj, ondone=None):
        "Shows a message object in the message area."

        c = messageobj.conversation
        b = messageobj.buddy
        t = messageobj.type

        # used to remember incoming<->outgoing for whether to "glue"
        # consecutive messages together visually
        buddyid = (b.idstr(), messageobj.type) if b is not None else None

        if buddyid is None:
            next = False
        else:
            next = getattr(self, 'last_buddy', None) == buddyid
        self.last_buddy = buddyid

        self.message_area.format_message(t, messageobj, next = next)

        if ondone is not None:
            #ondone()
            pass

    def set_profile_html(self, buddy):
        "Sets the HTML info window's contents to buddy's profile."

        profilewindow = self.profile_html

        # don't generate HTML for the same buddy twice.
        try:
            html = GetInfo(self.Buddy,
                           showprofile = True,
                           showhide = False,
                           overflow_hidden = False)
        except Exception:
            print_exc()
            html = buddy.name

        # freeze/thaw since HTML window is flickery when updating contents
        with self.Frozen():
            profilewindow.SetHTML(html)

    def on_text_changed(self, e):
        'Called when the main text input box changes.'

        e.Skip()

        # change conversations if we need to
        oldConvo = self.convo
        if not self.send_typing  or self.Mode != 'im' or not self.set_conversation_from_combos():
            return

        # end typing notifications for the old conversation
        if oldConvo is not None and oldConvo is not self.convo:
            with traceguard:
                oldConvo.send_typing_status(None)

        txt = self.input_area.Value

        if len(txt) == 0:
            if self.typing_status != None:
                self.typing_status = None
                self.convo.send_typing_status(None)

            if self.typing_timer:
                self.typing_timer.Stop()
                self.typing_timer = None

        else:
            if self.typing_status != 'typing':
                self.typing_status = 'typing'
                self.convo.send_typing_status(self.typing_status)

            self.cancel_timer()
            self.typing_timer = PyTimer(self.send_typed)
            self.typing_timer.Start(self.typed_delay * 1000, True)

    def send_typed(self, *e):
        if self.typing_status != 'typed':
            self.typing_status = 'typed'
            self.convo.send_typing_status(self.typing_status)

    def cancel_timer(self):
        if self.typing_timer:
            self.typing_timer.Stop()
            self.typing_timer = None

    def on_message_area_shown(self):
        'Sets up the MessageStyle for the IM area.'

        if hasattr(self, 'message_area') and not self.message_area.inited:
            if hasattr(self, 'convo'):
                self.init_message_area(self.convo.name, self.convo.buddy, show_history = not self.convo.ischat)
            else:
                self.init_message_area('', None)

            self.input_area.tc.Bind(wx.EVT_TEXT, self.on_text_changed)

            from gui.imwin.imwindnd import ImWinDropTarget
            self.SetDropTarget( ImWinDropTarget(self) )

    def on_video(self):

        import hooks
        hooks.notify('digsby.video_chat.requested')

        buddy = self.Buddy

        from gui.video.webvideo import VideoChatWindow

        if VideoChatWindow.RaiseExisting():
            self.convo.system_message(_('You can only have one audio/video call at a time.'))
            log.info('video window already up')
        else:
            log.info('requesting video chat')

            from digsby.videochat import VideoChat
            VideoChat(buddy)
