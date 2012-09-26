'''

Logic for routing incoming messages to the correct IM window, and to the
notification system.

SMS messages are a special case, see window_for_sms

         on_message
        /          \
fire_notifications   window_for -> (resulting ImWin).message
                        /   \
          window_for_sms     create_imwin
'''
from __future__ import with_statement

import hooks
import wx
from wx import GetTopLevelWindows, GetTopLevelParent, WXK_CONTROL, GetKeyState, CallLater
FindFocus = wx.Window.FindFocus
import threading

import gui.native.helpers as helpers
from util import strip_html2, odict, traceguard
from util.primitives.funcs import Delegate
from util.primitives.fmtstr import fmtstr
from util.lrucache import lru_cache
from common.notifications import fire
from common.sms import normalize_sms as smsize
from common.sms import validate_sms
from common import profile, pref
from gui.imwin.imwin_gui import ImWinPanel
from traceback import print_exc
from logging import getLogger; log = getLogger('imhub')
LOG = log.debug
from gui.uberwidgets.formattedinput import get_default_format

strip_html2 = lru_cache(80)(strip_html2)

def is_system_message(messageobj):
    return messageobj is not None and messageobj.buddy is None and \
            not getattr(messageobj, 'system_message_raises', False)

def is_announcement(message):
    buddy = getattr(message, 'buddy', None)
    return buddy is not None and buddy.service == 'digsby' and buddy.name == 'digsby.org'

def on_status(status, on_done=None):
    for imwin in ImWinPanel.all():
        if imwin.Buddy == status.buddy:
            wx.CallAfter(imwin.show_status, status, on_done)
            break

def show_announce_window(message):
    from gui.imwin.imwin_gui import AnnounceWindow
    announce = AnnounceWindow(wx.FindWindowByName('Buddy List'))
    announce.message(message)
    wx.CallAfter(announce.Show)

def show_announce_window_After(message):
    wx.CallAfter(show_announce_window, message)

hooks.register('digsby.server.announcement', show_announce_window_After)

def pre_message_hook(message):
    if is_announcement(message):
        # only show announcement windows to users with accounts (so new users
        # aren't shown an update changelog on first login)
        if profile.account_manager.all_accounts:
            show_announce_window(message)

        # If the user is new, ignore the message.
        return False

im_show = Delegate()

def frame_show(frame, show, no_activate=False):
    assert isinstance(show, bool)

    # wxMSW has a bug where frames created with wxMINIMIZE and then shown with ::Show()
    # do not have frame.m_iconize = true, and therefore don't send a wxIconizeEvent
    # for the first restore. showing the window with Iconize keeps m_iconized = true
    # and avoids the problem.
    if show and getattr(frame, '_starting_minimized', False):
        frame.Iconize(True)

        # there's a wx bug where Iconize(True) to show a window as minimized does not set IsShown()
        # to be true. so call Show(True) manually here.
        frame.Show(True)

        frame._starting_minimized = False
    else:
        if no_activate:
            frame.ShowNoActivate(show)
        else:
            frame.Show(show)


def on_message(messageobj = None, convo = None, raisenow = False, meta = None, mode = 'im', firenots=True):
    '''
    Called with IM messages or conversations.

    messageobj has "buddy" and "message" and "conversation" (at least)
    '''
    thread_check()
    from gui.imwin.imtabs import ImFrame

    convo = messageobj.conversation      if messageobj is not None else convo
    sms   = messageobj.get('sms', False) if messageobj is not None else False
    sms   = sms or getattr(getattr(convo, 'buddy', None), 'sms', False)

    if pre_message_hook(messageobj) is False:
        return

    system_message = is_system_message(messageobj)

    if not raisenow:
        should_hide, isnew = hide_message(messageobj, meta, sms, system_message)
        if should_hide:
            if firenots:
                fire_notifications(messageobj, None, isnew, mode, hidden=True)
            return

    win, isnew = window_for(convo, meta = meta, sms = sms,
                            system_message = system_message,
                            focus = True if raisenow else None,
                            mode = mode)
    if win is None:
        return

    # inform notification system
    if firenots:
        fire_notifications(messageobj, win, isnew, mode)

    flashnow = True
    frame    = GetTopLevelParent(win)
    focusedImFrame = isinstance(focused_top(), ImFrame)

#    print 'frame          ',  frame
#    print 'frame.IsShown()', frame.IsShown()
#    print 'focused_top    ' , focused_top()
#    print 'raisenow       ',  raisenow
#    print 'focusedImFrame ',  focusedImFrame
    global im_show

    # Find out if the window's tab is currently being dragged
    if isnew:
        if raisenow and not focusedImFrame:
            im_show += lambda: log.info('calling frame.Show on frame at %r', frame.Rect)
            im_show += lambda: wx.CallAfter(lambda: frame_show(frame, True))
        else:
            if not frame.IsShown():
                im_show += lambda: log.info('calling frame.ShowNoActivate on frame at %r', frame.Rect)
                im_show += lambda: wx.CallAfter(lambda: frame_show(frame, True, no_activate=True))

    if not focusedImFrame and (raisenow or (isnew and 'stealfocus' == new_action())):
        im_show += lambda: log.info('raising existing IM frame at %r', frame.Rect)
        im_show += lambda: raise_imwin(frame, win)
    else:
        if flashnow and messageobj is not None and not win.IsActive():
            bud = messageobj.buddy
            if bud is not None and bud is not messageobj.conversation.self_buddy:
                im_show += lambda: wx.CallAfter(win.Notify)

    if not (pref('fullscreen.hide_convos', True) and helpers.FullscreenApp()): #@UndefinedVariable
        im_show.call_and_clear()
    else:
        log.info('im_hub.on_message ignoring for now because of fullscreen (delegate is %d messages long)', len(im_show))
        helpers.FullscreenAppLog()

    # hand the message object off to the IM window
    win.message(messageobj, convo, mode, meta)

    return win

def focused_top():
    focused    = FindFocus()
    return focused.Top if focused is not None else None

def raise_imwin(frame, imwin):
    'Obtrusively raise an ImWin/ImFrame pair.'

    log.info('raise_imwin: %r %r', frame, imwin)

    if frame.IsIconized():
        frame.Iconize(False)

        #HAX: For some reason Iconize(False) doesn't throw an IconizeEvent, fixed
        event = wx.IconizeEvent(frame.Id, False)
        frame.AddPendingEvent(event)

    frame.ReallyRaise()

    tab = imwin.Tab
    if tab is not None: tab.SetActive(True)

def open(idstr):
    '''Opens an IM window (or raises an existing one) for a buddy id string.'''

    contact = profile.blist.contact_for_idstr(idstr)
    if contact is not None:
        return begin_conversation(contact)

def begin_conversation(contact, mode = 'im', forceproto = False):
    '''
    Invoked for actions like double clicking a buddy on the buddylist,
    i.e. starting a conversation with someone without messaging them
    yet.
    '''
    thread_check()

    from contacts.metacontacts import MetaContact, OfflineBuddy
    if isinstance(contact, OfflineBuddy):
        log.info('cannot open an IM window for OfflineBuddy %r', contact)
        return

    # are we asking for a metacontact?
    meta = contact if isinstance(contact, MetaContact) else None

    # decide on a to/from
    if forceproto:
        proto = contact.protocol
    else:
        contact, proto = profile.blist.get_from(contact)

    if proto is None:
        log.info('cannot open an IM window for %r, no compatible protocols?', contact)
        return

    convo = proto.convo_for(contact)

    # open the window
    if contact.sms and not profile.blist.on_buddylist(contact):
        mode = 'sms'

    # pop any hidden_messages from this contact
    pop_any_hidden(contact)

    return on_message(convo = convo, raisenow = True, meta = meta, mode = mode)

def window_for(convo, meta = None, sms = False, system_message = False, focus = None, mode = 'im'):
    win, meta = find_window_for(convo, meta, sms, system_message)

    if win is not None:
        return win, False

    if sms and not profile.blist.on_buddylist(convo.buddy):
        # is this SMS number associated with a buddy? then open a window for
        # that buddy, not for the number
        convo = window_for_sms(convo)

    if system_message:
        return None, None

    win = create_imwin(convo, meta, sms, focus, mode)
    return win, True

def find_window_for(convo, meta = None, sms = False, system_message = False):
    '''
    Finds the best IM tab for the given conversation.

    Returns two objects, an ImWin and a boolean value indicating if the window
    is "new" or not.

    If "system_message" is True, then a window will not be created on demand.
    '''

    thread_check()

    # the "meta" argument signifies to look only for the specified metacontact.
    if meta is None:
        metas = profile.metacontacts.forbuddy(convo.buddy) if not convo.ischat else []
        if metas:
            meta = list(metas)[0]
    else:
        metas = [meta]

    return search_for_buddy(metas, convo, sms), meta

def search_for_buddy(metas, convo, sms):
    for win in ImWinPanel.all():
        with traceguard:
            c = win.Conversation

            # already talking to this buddy?
            if c is convo:
                LOG('direct conversation object match: win: %r, convo: %r', win, convo)
                return win

            # is this an SMS message?
            if validate_sms(convo.buddy.name):
                for num in win.SMS:
                    if validate_sms(num):
                        if smsize(num) == smsize(convo.buddy.name):
                            return win

            # chat messages will go only to windows with matching conversation objects.
            if convo.ischat != win.convo.ischat:
                continue

            # is there a window already open talking to another contact in this
            # contact's metacontact?
            winbud = win.Buddy
            if winbud is None:
                continue

            for meta in metas:
                for contact in meta:
                    if winbud == contact:
                        LOG('matched %r with %r', winbud, contact)
                        return win

                # a looser match--one that might not match "From:" but only "To:"
                for contact in meta:
                    if winbud.name == contact.name and winbud.protocol.name == contact.protocol.name:
                        LOG('loosely matched %r with %r', winbud, contact)
                        return win

            if winbud.info_key == convo.buddy.info_key:
                return win

def window_for_sms(convo):
    '''
    For a conversation with an SMS number, looks up contact infos for a buddy
    that matches and returns a conversation with that buddy.
    '''
    log.info('window_for_sms: %r', convo)
    thread_check()

    buddy_sms = smsize(convo.buddy.name)

    keys = []

    # 'aim_dotsyntax1': {'alias': '',
    #                    'sms': [u'4567891000', u'17248406085']},
    for infokey, infodict in profile.blist.info.iteritems():
        try:
            sms_numbers = infodict['sms']
        except KeyError:
            pass
        else:
            for s in list(sms_numbers):
                try:
                    sms = smsize(s)
                except ValueError:
                    log.critical("invalid SMS number in infodict[%r]['sms']: %r", infokey, s)
                    sms_numbers.remove(s)
                else:
                    if buddy_sms == sms:
                        keys += [infokey]
    if not keys:
        log.info('no matching sms numbers found')
        return convo

    conn = convo.protocol

    for key in keys:
        if key.startswith('Metacontact #'):
            continue #TODO: metacontact-sms association

        buddyname, proto  = info_key_tuple(key)

        #TODO: use something SERVICE_MAP in buddyliststore.py to make sure
        # digsby/jabber and aim/icq work correctly.
        if conn.protocol == proto and conn.has_buddy(buddyname):
            return conn.convo_for(conn.get_buddy(buddyname))

    return convo

def new_action():
    return pref('conversation_window.new_action')

def create_imwin(convo, meta, sms, focus = None, mode = 'im'):
    '''
    Logic for where to place a new IM tab.

    Spawns a a new ImWin object, placing it as a new tab in _some_ window
    somewhere, and returns the ImWin.
    '''
    thread_check()

    from gui.imwin.imtabs import ImFrame
    f = None

    hooks.notify('imwin.created')

    focus = new_action() == 'stealfocus' if focus is None else focus

    # if tabs are enabled, search for the oldest living ImFrame and place
    # the new message there--unless CTRL is being held down.
    ctrlDown = pref('messaging.tabs.ctrl_new_window', True) and GetKeyState(WXK_CONTROL)

    if not ctrlDown and pref('messaging.tabs.enabled', True):
        for win in GetTopLevelWindows():
            if isinstance(win, ImFrame):
                f = win
                if f.IsActive():
                    focus = False
                break

    # if the focused control is an IM win's input box, don't steal focus.
    if isinstance(focused_top(), ImFrame):
        focus = False

    if getattr(wx.Window.FindFocus(), 'click_raises_imwin', False) and wx.LeftDown():
        focus = True

    # if we haven't found an ImFrame to put the tab in, create a new one
    if f is None:
        if pref('messaging.tabs.enabled', True):
            id = ''
        else:
            id = meta.idstr() if meta is not None else convo.buddy.idstr()
        f = ImFrame(startMinimized = not focus, posId = id)

    w = ImWinPanel(f)

    if convo is not None:
        w.set_conversation(convo, meta)

    if focus:
        global im_show
        im_show += lambda: raise_imwin(f, w)
        im_show += lambda: w.FocusTextCtrl()

    tab = f.AddTab(w, focus = focus)
    # NOTE: the native IM window doesn't use Page objects so we need to check
    # for it before adding to it.
    # FIXME: tab.OnActive seems to always be called by tab.SetActive, and tab.SetActive
    # also calls FocusTextCtrl on its text control, so is this needed still?
    if hasattr(tab, "OnActive"):
        tab.OnActive += w.FocusTextCtrl

    hooks.notify('digsby.statistics.imwin.imwin_created')

    return w



def fire_notifications(msg, win, isnew, mode, hidden=False):
    '''
    Relays message information to the notifications system, for things like
    popups and sound effects.

    msg     a message object storage
    win     the ImWin about to show this message
    isnew   a bool indicating if the ImWin is "new"
    '''

    if msg is None or msg.buddy is None: return []

    convo = msg.conversation
    bud = msg.buddy

    def stop_notify(win=win):
        if win:
            try:
                win.Unnotify()
            except wx.PyDeadObjectError:
                pass
            else:
                if not win.Top.AnyNotified and pref('conversation_window.notify_flash'):
                    win.Top.StopFlashing()
        if hidden and pref('messaging.popups.close_dismisses_hidden', False):
            _remove_hidden_message(bud, msg)

    if msg.get('content_type', 'text/html') in ('text/html', 'text/xhtml'):
        try:
            popup_message = strip_html2(msg.message).decode('xml')
        except Exception:
            print_exc()
            popup_message = msg.message
    else:
        popup_message = msg.message

    # decide on options to pass to the popup
    fire_opts = dict(buddy = bud,
                     onuserclose = stop_notify)

    ischat = convo is not None and convo.ischat
    if ischat:
        from gui import skin
        fire_opts.update(header = _('Group Chat ({chat.chat_member_count:d})').format(chat=convo),
                         msg = _('{alias:s}: {message:s}').format(alias=bud.alias, message=popup_message),
                         icon = skin.get('ActionsBar.Icons.RoomList', None),
                         popupid = 'chat!!!%r!!!%r' % (convo.protocol.name, convo.chat_room_name))
    else:
        fire_opts.update(msg = popup_message,
                         icon = bud.buddy_icon if bud is not None else convo.icon,
                         popupid = msg.buddy.idstr())


    # Clicking on the popup should open that buddy's message window.
    #  - if there is text entered in the popup and not the IM window,
    #    copy it there
    if bud is not None:
        def click_popup(text):
            if pop_any_hidden(bud):
                return

            if convo.ischat:
                on_message(convo = convo, raisenow = True)
            else:
                begin_conversation(bud)

            if win:
                try:
                    val = win.input_area.Value
                except wx.PyDeadObjectError:
                    pass
                else:
                    if not val:
                        win.input_area.Value = text
                        wx.CallAfter(win.TextCtrl.SetInsertionPointEnd)

        fire_opts.update(onclick = click_popup)

    notification = _get_notification_types(bud, convo, win, hidden, isnew)

    def send_from_popup(text, options, convo = convo, win = win, opts = fire_opts.copy()):
        if not text: return

        CallLater(200, stop_notify)

        # if the window's still around, use its formatting
        convo.send_message(fmtstr.singleformat(text, format=_get_format(win)))

        if not wx.GetKeyState(wx.WXK_CONTROL):
            # returning a string appends it to the popup's content.
            return '> ' + text

        # returning None results in the popup closing

    fire_opts['input'] = send_from_popup

    return fire(notification, **fire_opts)

def _get_notification_types(bud, convo, win, hidden, isnew):
    # decide which type of message event to fire
    if bud is convo.self_buddy:
        notification = 'message.sent'
    elif hidden:
        # hidden messages get message.received.hidden, and also .initial if they are new
        notification = ['message.received.hidden']
        if isnew: notification.append('message.received.initial')
    else:
        # New messages have their own event type.
        if isnew:
            notification = 'message.received.initial'

        # If the IM window isn't the active tab, or the "IM" button isn't the active one,
        # then fire a "background" message event.
        elif not win or not win.IsActive() or not wx.GetApp().IsActive() or win.Mode not in ('im', 'sms'):
            notification = 'message.received.background'

        # Otherwise just use message.received.
        else:
            notification = 'message.received'

    return notification

def _get_format(win):
    '''
    returns the formatting dictionary for sending a message given an IM
    window that may or may not already be destroyed
    '''

    format = None

    if win:
        try:
            format = win.input_area.Format
        except wx.PyDeadObjectError:
            pass
        except Exception:
            print_exc()

    if format is None:
        format = get_default_format()

    return format

def show_info(buddy):
    begin_conversation(buddy, mode = 'info')

def thread_check():
    if threading.currentThread().getName() != 'MainThread':
        raise Exception('imhub methods must be called on the main GUI thread')


def info_key_tuple(info_key):
    i = info_key.find('_')
    if i == -1:
        assert False, repr(info_key)
    return info_key[:i], info_key[i+1:]

#
# hidden messages
#

hidden_windows = odict() # { contact: [message1, message2, ..] }

def hidden_count():
    'Returns the number of hidden conversation windows.'

    return len(hidden_windows)

def hidden_convo_contacts():
    'Returns a list of all contacts with hidden conversations.'

    return hidden_windows.keys()

def hide_message(messageobj, meta, sms, system_message):
    'Hides a message.'

    if messageobj is None:
        return False, False

    convo = messageobj.conversation

    # When messageobj buddy is self_buddy, we're sending a message. If there
    # is no existing IM window for the conversation, don't create one.
    if convo.self_buddy == messageobj.buddy:
        win, meta = find_window_for(convo, meta, sms, system_message)
        if not get_any_hidden(convo.buddy, pop=False):
            return win is None, False

    if new_action() != 'hide':
        return False, False

    win, meta = find_window_for(convo, meta, sms, system_message)

    if win is not None:
        return False, False

    ident = (meta or convo.buddy).info_key

    if ident in hidden_windows:
        hidden_windows[ident].append(messageobj)
        isnew = False
    else:
        hidden_windows[ident] = [messageobj]
        isnew = True

    _notify_hidden()
    return True, isnew

def pop_all_hidden():
    'Display all hidden conversations.'

    for contact in list(hidden_windows.keys()):
        pop_any_hidden(contact)

def pop_any_hidden(contact, notify=True):
    # the quiet_log_messages is checked by MessageArea when replaying
    # log messages to see if any messages should be ignored
    from gui.imwin.messagearea import quiet_log_messages

    all_messages = get_any_hidden(contact)

    if not all_messages:
        return

    with quiet_log_messages(all_messages):
        for messageobj in all_messages:
            with traceguard:
                on_message(messageobj, raisenow=True, firenots=False)

    if notify:
        _notify_hidden()

def get_any_hidden(contact, pop=True):
    keys = hidden_windows.keys()
    if not keys:
        return []

    # hidden message may be stored under a metacontact info_key, so look it up here.
    contacts = set()
    if not isinstance(contact, basestring):
        contacts.update(m.info_key for m in
                profile.metacontacts.forbuddy(contact))

    contact = getattr(contact, 'info_key', contact)
    contacts.add(contact)

    all_messages = []
    for message_list in hidden_windows.values():
        all_messages.extend(message_list)

    messages = []
    for c in keys:
        if c in contacts:
            if pop:
                msgs = hidden_windows.pop(c, [])
            else:
                msgs = hidden_windows.get(c, [])

            messages.extend(msgs)

    return messages

def _remove_hidden_message(contact, message):
    contact = getattr(contact, 'info_key', contact)

    try:
        messages = hidden_windows[contact]
    except KeyError:
        return False
    else:
        try:
            messages.remove(message)
        except ValueError:
            return False
        else:
            if len(messages) == 0:
                hidden_windows.pop(contact)
                _notify_hidden()

            return True

def _notify_hidden():
    hooks.notify('digsby.im.message_hidden', hidden_windows)

