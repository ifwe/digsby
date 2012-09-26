'''

IM window GUI construction

'''
from __future__ import with_statement

try: _
except: import gettext; gettext.install('Digsby')

import wx, sys
import metrics, hooks
import traceback

from wx import EXPAND, EVT_BUTTON, VERTICAL, BoxSizer, \
    GetTopLevelParent, EVT_CONTEXT_MENU
from wx.lib import pubsub

from logging import getLogger; log = getLogger('imwingui')

from common import profile, pref, prefprop
from util import InstanceTracker

from gui.skin import get as skinget
from gui.imwin.imwin_ctrl import ImWinCtrl
from gui.imwin.imwin_email import ImWinEmailPanel
from gui.imwin.imwin_roomlist import RoomListMixin
from gui.imwin.messagearea import MessageArea
from gui.imwin import imwinmenu
from gui.imwin.styles import get_theme_safe
from gui.capabilitiesbar import CapabilitiesBar
from gui.uberwidgets.formattedinput2.iminput import IMInput
from gui.validators import LengthLimit
from gui import clipboard
from gui.toolbox.toolbox import Frozen

from gui.addcontactdialog import AddContactDialog


# these strings are placed next to the buddy name
# in the window title when they're typing
typing_status_strings = {
    'typing': _('Typing'),
    'typed':  _('Entered Text'),
}

from gui.browser.webkit import WebKitWindow
class ImHtmlWindow(WebKitWindow):
    '''
    Implements [Can]Copy so the right click menu can "just work" with this
    control.
    '''

    def __init__(self, *a, **k):
        WebKitWindow.__init__(self, *a, **k)
        self.Bind(wx.EVT_KEY_DOWN, self.__OnKey)

    def __OnKey(self, e):
        if e.KeyCode == ord('C') and e.Modifiers == wx.MOD_CMD:
            self.Copy()
        else:
            e.Skip()

    def SelectionToText(self):
        return self.RunScript('window.getSelection()')

    def CanCopy(self):
        return bool(self.SelectionToText())

    def Copy(self):
        return clipboard.copy(self.SelectionToText())

class AnnounceWindow(wx.Frame):
    def __init__(self, parent = None):
        wx.Frame.__init__(self, parent, -1, _('Digsby Announcement'), size = (400, 330))
        self.SetFrameIcon(skinget('AppDefaults.TaskbarIcon'))

        self.message_area = MessageArea(self, header_enabled = False, prevent_align_to_bottom=True)
        self.inited = False
        self.CenterOnScreen()

    def message(self, messageobj):
        if not self.inited:
            self.inited = True
            theme, variant = pref('appearance.conversations.theme'), pref('appearance.conversations.variant')
            buddy = messageobj.buddy

            # initialize the message area, not showing history
            self.message_area.init_content(get_theme_safe(theme, variant),
                                           buddy.name, buddy, show_history = False)
                                           #prevent_align_to_bottom=True) # disable until all skins look correct with this option

        self.message_area.format_message(messageobj.type, messageobj)


class LayoutChange(Frozen):
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.win.Layout()
            self.win.Layout() #CAS: why are there two? see r9728
        finally:
            return super(LayoutChange, self).__exit__(exc_type, exc_val, exc_tb)

class ImWinPanel(wx.Panel, RoomListMixin, ImWinCtrl, InstanceTracker):
    '''
    The main message window GUI.

    Acts mostly like a tabbed interface for the various "modes:" info, im, email, sms

    Tabs are lazily constructed when needed--see the "construct_XXX" methods.
    '''

    def __init__(self, parent, pos = wx.DefaultPosition):
        wx.Panel.__init__(self, parent, pos = (-300, -300))
        InstanceTracker.track(self)

        self.BackgroundStyle = wx.BG_STYLE_CUSTOM
        self.Sizer = BoxSizer(VERTICAL)
        self.showncontrol = None

        self.link_observers()
        self.construct_gui()
        self.setup_delegation()

        ImWinCtrl.__init__(self)
        imwinmenu.add_menus(self)

        metrics.event('IM Window Opened')

        self.UpdateSkin()

        self.IMControl.OnSelection += self.on_im_to_changed

        self.Bind(wx.EVT_SIZE, self.OnSize)

    def on_im_to_changed(self):
        self.capsbar.ApplyCaps()

        # hide roomlist if switching to a protocol without groupchat
        print 'on_im_to_changed'
        print 'RoomListButtonShown', self.capsbar.RoomListButtonShown

        if not self.capsbar.RoomListButtonShown:
            self.show_roomlist(False)

    def OnSize(self, event):
        event.Skip()
        wx.CallAfter(self.Layout)

    def _on_view_past_chats(self, *a):
        if self.convo.ischat:
            from gui.pastbrowser import PastBrowser
            PastBrowser.MakeOrShowAndSelectConvo(self.convo)
        else:
            self.IMControl.Buddy.view_past_chats(self.IMControl.Account)

    def construct_gui(self):
        c = self.capsbar = CapabilitiesBar(self, buddy_callback = lambda: self.convo, showCapabilities = self.show_actions_bar)
        c.OnSendFiles     += lambda:    self.Buddy.send_file()
        c.OnViewPastChats += self._on_view_past_chats
        c.OnAddContact    += lambda *a: AddContactDialog.MakeOrShow(service=self.Buddy.service, name=self.Buddy.name, account = profile.account_manager.get_account_for_protocol(self.IMControl.Account))
        c.OnBlock         += lambda *a: self.Buddy.block(not self.Buddy.blocked)
        self.Sizer.Add(c, 0, EXPAND)


    def construct_infopanel(self):
        self.profile_html = html = ImHtmlWindow(self)
        html.Bind(EVT_CONTEXT_MENU,      lambda e: self.GetMenu().PopupMenu(event = e))
        html.Bind(wx.EVT_RIGHT_UP,       lambda e: self.GetMenu().PopupMenu(event = e))
        html.Hide()
        return html

    def construct_messagepanel(self):
        from gui.uberwidgets.skinsplitter import SkinSplitter
        self.input_splitter = spl = SkinSplitter(self, MSGSPLIT_FLAGS)
        spl.SetMinimumPaneSize(10)
        spl.SetSashGravity(1)
        wx.CallAfter(spl.SetSashPosition, 400)

        msgarea = self.message_area = MessageArea(spl)
        msgarea.SetMouseWheelZooms(True)
        msgarea.MinSize = wx.Size(msgarea.MinSize.width, 100)

        self.IMControl.msgarea = msgarea

        maBind = msgarea.Bind
        maBind(wx.EVT_CONTEXT_MENU, lambda e: self.GetMenu().PopupMenu(event = e))
        # Apparently on Windows a window without focus still gets key events,
        # but this doesn't happen on Mac, meaning the user can't select text unless we get focus.
        if not sys.platform.startswith('darwin'):
            maBind(wx.EVT_SET_FOCUS, lambda e: self.FocusTextCtrl())

        self.input_area   = IMInput(spl,
                                    showFormattingBar = self.show_formatting_bar,
                                    multiFormat = True,
#                                   rtl           = self.rtl_input,
                                    skin="FormattingBar",
                                    entercallback = lambda txtfld: self.on_send_message(),
                                    validator=LengthLimit(10240))
        wx.CallAfter(self.input_area.tc.AutoSetRTL)
        self.input_area.BindSplitter(spl, 'conversation_window.input_base_height')

        text_control = self.input_area.tc
        if not sys.platform.startswith('darwin'):
            text_control.Bind(wx.EVT_CONTEXT_MENU, lambda e: self.GetTextCtrlMenu().PopupMenu(event = e))
        text_control.Bind(wx.EVT_TEXT_PASTE, self._on_text_ctrl_paste)

        def OnToFromShow(event):
            event.Skip()
            text_control.ForceExpandEvent()

        self.capsbar.tfbar.Bind(wx.EVT_SHOW, OnToFromShow)

        #HAX: There has to be a better way...  Besides only works for the first window
        tab = self.Tab
        if tab and hasattr(tab, "OnActive"):
            #TODO: expandhax?
            #tab.OnActive += lambda: self.input_area.expandEvent()
            #self.SupaHax()
            tab.firsttop = self.Top

        self.setup_keys(self.input_area.tc)

        self.do_input_split(msgarea)

        return spl

    def do_input_split(self, ctrl):
        if self.input_splitter.IsSplit():
            self.input_splitter.Unsplit(self.input_splitter.GetWindow1())
        self.input_splitter.SplitHorizontally(ctrl, self.input_area)

    def _on_text_ctrl_paste(self, e):
        e.Skip()

        if not pref('conversation_window.paste.images', default=True):
            return

        # if we have a convo object...
        convo = self.convo
        if convo is None:
            return

        # and if the protocol supports sending files...
        from common import caps
        if caps.FILES not in convo.protocol.caps:
            return


        text = clipboard.get_text()
        # Some forms of text (like excel data) can be sent as images. we'd rather send it as text though.
        if text is not None:
            return

        # and there's a bitmap in the clipboard...
        bitmap = clipboard.get_bitmap()
        if bitmap is None:
            return

        # show a "send image" dialog
        buddy = convo.buddy
        self_name = convo.protocol.self_buddy.name

        from gui.imagedialog import show_image_dialog
        message = _(u'Would you like to send this image to %s?') % buddy.name
        if show_image_dialog(self, message, bitmap):
            import time, stdpaths
            filename = '%s.clipboard.%s.png' % (self_name, time.time())
            filename = stdpaths.temp / filename
            bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG)
            buddy.send_file(filename)

#    def SupaHax(self):
#        top = self.Top
#        def ExpandHax():
#            if self.IsShownOnScreen():
#                self.input_area.expandEvent()
#
#        def OnTopChanged():
#            top.iconizecallbacks.remove(ExpandHax)
#            wx.CallAfter(self.SupaHax)
#
#        top.iconizecallbacks.add(ExpandHax)
#
#
#        self.OnTopChanged = OnTopChanged

    def setup_keys(self, textctrl):
        msgarea = self.message_area

        def key(e):
            # Catch some keys in the input box that should/can be redirected
            # to the IM area
            c = e.KeyCode

            if c == wx.WXK_PAGEUP:
                msgarea.ScrollPages(-1)
            elif c == wx.WXK_PAGEDOWN:
                msgarea.ScrollPages(1)
            elif c == ord('C') and e.GetModifiers() == wx.MOD_CMD:
                # catch Ctrl+C in the formatted input. If there is selected
                # text in the IM area, then that will be copied. otherwise,
                # the event is skipped and the text control will copy its
                # text
                if not self.Copy(): e.Skip()
            else:
                e.Skip()

        msgarea.BindWheel(textctrl)
        msgarea.BindWheel(msgarea)
        msgarea.BindScrollWin(textctrl)
        msgarea.BindScrollWin(msgarea)
        textctrl.Bind(wx.EVT_KEY_DOWN,   key)

        # TextHistory provides Ctrl+Up and Ctrl+Down history support
        from gui.toolbox.texthistory import TextHistory
        self.history = TextHistory(textctrl)

    def Copy(self):
        # If the input area has selection, use that...
        if self.input_area.tc.CanCopy():
            self.input_area.tc.Copy()

        # ...otherwise if the conversation area has selection, use that.
        elif self.message_area.CanCopy():
            self.message_area.Copy()

        else:
            return False

        return True

    def construct_emailpanel(self):
        emailpanel = ImWinEmailPanel(self)

        emailpanel.send_button.Bind(EVT_BUTTON, lambda e: self.on_send_email())
        emailpanel.openin.Bind(EVT_BUTTON,      lambda e: self.on_edit_email())

        # Email panel children need the main IMWin right click menu
        for child in emailpanel.Children:
            child.Bind(EVT_CONTEXT_MENU, lambda e: self.GetMenu().PopupMenu(event = e))
        emailpanel.subject_input.Bind(EVT_CONTEXT_MENU, lambda e: self.GetMenu().PopupMenu(event = e))

        self.EmailControl.OnEmailAccountChanged += emailpanel.SetEmailClient

        return emailpanel

    def show_controls(self, mode):
        if self.showncontrol == mode:
            return

        with self.Frozen():
            # hide old controls, show new ones
            ctrlname = modectrls[mode]

            if self.showncontrol is not None:
                self.showncontrol.Hide()

            ctrl = self.get_panel(ctrlname)
            ctrl.Show()
            self.Layout()

            self.mode = mode
            self.showncontrol = ctrl

    def get_panel(self, ctrlname):
        try:
            return getattr(self, '_' + ctrlname)
        except AttributeError:
            if not hasattr(self, '_' + ctrlname):
                # look up function construct_XXX where XXX is ctrlname
                # and call it to lazily construct the panel
                c = getattr(self, 'construct_' + ctrlname)()

                # set it as _XXX in self
                setattr(self, '_' + ctrlname, c)

                self.Sizer.Add(c, 1, EXPAND)
                return c


    def init_message_area(self, chatName, buddy, show_history=None):
        # apply the MessageStyle if we haven't already.
        self.message_area.init_content(self.theme, chatName, buddy, show_history=show_history)

    @property
    def theme(self):
        theme, variant = pref('appearance.conversations.theme'), pref('appearance.conversations.variant')
        key = '%s__%s' % (theme, variant)

        cls = ImWinPanel


        try:
            if cls.__msgthemename == key:
                return cls.__messagetheme
        except AttributeError:
            pass

        t = cls.__messagetheme = get_theme_safe(theme, variant)
        cls.__msgthemename = key
        return t

    def UpdateSkin(self):
        self.typing_icons = {
            'typing': skinget('statusicons.typing'),
            'typed':  skinget('statusicons.typed'),
        }
        wx.CallAfter(wx.CallAfter, self.Layout)

    @property
    def Tab(self):
        # until reparenting is not necessary for UberBook, tab might
        # be None
        return getattr(self.Parent, 'tab', None)

    @property
    def Notified(self):
        '''Returns True if this IM window's tab is in a "notified" state.'''

        return getattr(self.Tab, 'notified', False)

    def IsActive(self):
        '''
        Returns True if this window is both the active top level window and
        the active tab.
        '''

        # FIXME: TLW.IsActive seems not to be returning the right value...
        if sys.platform.startswith('darwin'):
            return self == self.Parent.ActiveTab
        else:
            tab = self.Tab
            return tab is not None and tab.GetActive() and GetTopLevelParent(self).IsActive()

    def Notify(self):
        'Cause this window/tab to "blink" and grab user attention.'

        # cause the tab to go into the "notify" state
        tab = self.Tab

        if tab is not None and (not tab.active or not self.Top.IsActive()):
            tab.SetNotify(True)

    def Unnotify(self):
        tab = self.Tab
        if tab is not None: tab.SetNotify(False)

    def ClearAndFocus(self):
        'Clears and focuses the input box, and hides the to/from bar.'

        with self.Frozen():
            self.capsbar.ShowToFrom(False)
            self.input_area.Clear()
            self.FocusTextCtrl()
            self.Layout()

    def link_observers(self):
        'Ties GUI preferences to methods that implement them.'

        link = profile.prefs.link
        self.show_formatting_bar = pref('messaging.show_formatting_bar', False)
        self.show_actions_bar    = pref('messaging.show_actions_bar', True)
        self.show_send_button    = pref('messaging.show_send_button', False)
#        self.rtl_input           = pref('messaging.rtl_input', False)

        self.links = [
            link('messaging.show_formatting_bar', self.pref_show_formatting_bar, False),
            link('messaging.show_actions_bar',    self.pref_show_actions_bar,    False),
            link('messaging.show_send_button',    self.pref_show_send_button,    False),
#            link('messaging.rtl_input',           self.pref_rtl_input,           False),
            link('messaging.tabs.icon',           self.pref_tab_icon,            False)
        ]

    def unlink_observers(self):
        'Cleans up observable links.'

        for link in self.links:
            link.unlink()
        del self.links[:]

    def pref_show_formatting_bar(self, val):
        'Invoked when the "show formatting bar" pref changes.'

        self.show_formatting_bar = val

        if hasattr(self, 'input_area'):
            # may not have been constructed yet
            self.input_area.ShowFormattingBar(val)

    def pref_show_send_button(self, val):

        self.show_send_button = val

        if hasattr(self, 'input_area'):
            self.input_area.ShowSendButton(val)


#    def pref_rtl_input(self, val):
#        'Invoked when the "show actions bar" pref changes.'
#        self.rtl_input = val
#
#        with self.Frozen():
#            'Toggles the layout direction of a control between right-to-left and left-to-right.'
#            self.input_area.tc.LayoutDirection = wx.Layout_RightToLeft if val else wx.Layout_LeftToRight
#            self.input_area.tc.Refresh()

    def pref_show_actions_bar(self, val):
        'Invoked when the "show actions bar" pref changes.'

        with self.LayoutChange():
            self.capsbar.ShowCapabilities(val)

    def ShowToFrom(self, show):
        if show != self.capsbar.ToFromShown:
            with self.LayoutChange():
                self.capsbar.ShowToFrom(show)

    def LayoutChange(self):
        return LayoutChange(self)

    def pref_tab_icon(self, val):
        wx.CallAfter(self.update_icon)

    icontype = prefprop('messaging.tabs.icon', 'buddy')

    @property
    def TypingBadge(self):
        return self.typing_icons.get(self.typing, None)

    @property
    def ischat(self):
        return self.convo.ischat

    @property
    def chat_icon(self):
        try:
            bitmap = self.convo.protocol.serviceicon.ResizedSmaller((16,16))
        except Exception:
            traceback.print_exc_once()
            from gui import skin
            bitmap = skin.get('actionsbar.icons.roomlist').Resized((16,16))

        return bitmap

    def update_icon(self):
        # if the buddy is typing, use a typing badge.
        typing_icon = icon = self.TypingBadge

        # otherwise choose based on the pref
        if icon is None:
            if not self.ischat:
                icon = icons.get(self.icontype, 'buddy')(self.Buddy)
            else:
                icon = self.chat_icon

        pubsub.Publisher().sendMessage(('tab', 'icon', 'updated'), (self, icon))

        if self.Page is not None:
            self.Page.SetIcon(icon)

        hooks.notify('digsby.overlay_icon_updated', self)

    title_typing_notifications = prefprop('messaging.typing_notifications.show_in_title', type=bool, default=True)

    def _get_title(self):
        if self.ischat:
            self._last_title = self._get_title_chat()
            return self._last_title

        bud = self.Buddy
        if bud is None: return getattr(self, '_last_title', ('', ''))
        name = bud.alias

        if sys.DEV and not isinstance(name, unicode):
            msg = 'Please only unicode aliases for buddies! (got %r from %r)', name, self.Buddy

            if pref('errors.nonunicode_buddy_names', type=bool, default=False):
                raise TypeError(msg)
            else:
                log.warning(*msg)

        if self.typing is not None and self.title_typing_notifications:
            window_title = '%s (%s)' % (name, typing_status_strings.get(self.typing, self.typing))
        else:
            window_title = None

        self._last_title = name, window_title
        return self._last_title

    def _get_title_chat(self):
        s = u'Group Chat (%d)' % self.convo.chat_member_count
        return (s, )*2

    def update_title(self):
        '''
        Updates the title of this IM window, which shows in it's tab, and
        possibly in the window containing it.
        '''

        assert wx.IsMainThread()

        if wx.IsDestroyed(self):
            return

        name, window_title = self._get_title()

        pubsub.Publisher().sendMessage(('tab', 'title', 'updated'), (self, name, window_title))

        if self.Page is not None:
            self.Page.SetTitle(name, window_title)

    @property
    def Page(self):
        p = self.Parent
        from gui.uberwidgets.uberbook.page import Page
        if isinstance(p, Page):
            return p

    @property
    def TextCtrl(self):
        return self.input_area.tc

    def FocusTextCtrl(self):
        'Gives focus to the input box, if this window has one currently and it is shown.'

        if not self.Top.IsForegroundWindow():
            return

        try: tc = self.input_area.tc
        except AttributeError:
            pass # no input area yet
        else:
            if tc.Shown: tc.SetFocus()

    #
    # delegation to child controls
    #

    def setup_delegation(self):
        self.To   = self.capsbar.cto
        self.From = self.capsbar.cfrom

        for delegate_name, attrs in self.delegation.iteritems():
            delegate = getattr(self, delegate_name)
            for attr in attrs:
                setattr(self, attr, getattr(delegate, attr))



    delegation = {'capsbar': ('GetButton',)}

    ToFromShown = property(lambda self: self.capsbar.ToFromShown)

def budicon(bud):
    from gui.buddylist.renderers import get_buddy_icon
    return get_buddy_icon(bud, round_size = False, meta_lookup=True)


icons = dict(buddy =   budicon,
             status =  lambda bud: skinget('statusicons.' + bud.status_orb),
             service = lambda bud: bud.serviceicon)

# maps "modes" to the GUI panels they use
modectrls = {'info':  'infopanel',
             'im':    'messagepanel',
             'email': 'emailpanel',
             'sms':   'messagepanel'}

MSGSPLIT_FLAGS = wx.SP_NOBORDER | wx.SP_LIVE_UPDATE

