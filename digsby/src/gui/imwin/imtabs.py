'''
imtabs.py

Main frame for the tabbed IM window implementation. In order to support the ability to switch between
native and skinned IM windows based on appearance.skin, we needed a design that would allow the ImFrame's
inheritence hierarchy to remain the same while having different implementations for its guts.

So now, ImFrame contains common logic shared by both native and skinned implementations. When loaded,
based on the appearance.skin setting, it will load the platform-specific frame events and notebook
by loading an event handler object (so we can handle events on the frame without binding directly
to ImFrame) and a notebook panel object needed for the selected version.

So, when adding code, here is where things go:

- Common code goes to ImFrame

- Code related to frame events and updating frame elements:
    - Skinned: SkinnedIMFrameEventHandler
    - Native: NativeIMFrameEventHandler
- Code that is specific to the IM window notebook implementation:
    - Skinned: SkinnedNotebookPanel
    - Native: NativeNotebookPanel

Anything else, that may be shared by new notebook-based UIs, should of course go into UberBook or
DigsbyFlatNotebook.

'''
from __future__ import with_statement
from wx import PyDeadObjectError
try: _
except: import gettext; gettext.install('Digsby')

import wx
import hooks
from wx.lib import pubsub

import config

from gui import skin
from gui.uberwidgets.uberbook.tabmanager import TabWindowManager
from gui.uberwidgets.uberbook.UberBook import NoteBook
from gui.toolbox import draw_tiny_text
from PIL import Image
from gui.windowfx import fadein
from common import setpref, pref, profile, bind, prefprop
from util import traceguard, default_timer
from util.primitives.structures import oset
from util.primitives.funcs import Delegate

from gui.uberwidgets.UberEvents import EVT_TAB_NOTIFIED
from gui.toolbox import saveWindowPos, preLoadWindowPos, snap_pref
from gui.native import memory_event

IMWIN_STAT_IDLE_TIME = 5*60*1000 #five minutes == no longer engaged even if we still have focus


CLOSETABS_TITLE   = _('Close IM Window')
CHECKBOX_TEXT     = _('Warn me when I attempt to close multiple conversations')
CLOSETABS_MSG     = _('You are about to close {num_tabs} conversations. Are you sure you want to continue?')
CLOSE_BUTTON_TEXT = _('Close &tabs')

WARN_PREF = 'messaging.tabs.warn_on_close'
IMWIN_ALWAYS_ON_TOP_PREF = 'conversation_window.always_on_top'

def explodeAllWindows():
    # FIXME: if this import is at the module level, we get a recusive import loop w/ImFrame
    from gui.imwin.imtabs import ImFrame
    newtabs = 0
    for win in (w for w in wx.GetTopLevelWindows() if isinstance(w, ImFrame)):
        # create a new IM window for all tabs but the first
        for page in win.notebook.Pages()[1:]:
            newtabs += 1

            win.notebook.Remove(page)
            page.tab.Close()

            pos = wx.Point(30, 30) + (20*(newtabs), 20*(newtabs))
            newwin = win.notebook.winman.NewWindow(pos)
            newwin.notebook.Insert(page, False)


class CloseTabsDialog(wx.Dialog):
    '''
    A confirmation dialog for closing an IM window with more than one tab.
    '''

    @property
    def WarnMe(self):
        return self.panel.warn_cb.Value

    def __init__(self, parent, num_tabs, warn_value = True):
        wx.Dialog.__init__(self, parent, title = CLOSETABS_TITLE)

        self.panel = CloseTabsPanel(self, num_tabs, warn_value)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.panel, 1, wx.EXPAND)

        self.Fit()


class CloseTabsPanel(wx.Panel):
    def __init__(self, parent, num_tabs, warnme_value = True):
        wx.Panel.__init__(self, parent)

        self.Bind(wx.EVT_PAINT, self.OnPaint)

        self.warn_cb = warn_cb = wx.CheckBox(self, -1, CHECKBOX_TEXT)
        warn_cb.SetValue(warnme_value)

        msgsizer = wx.BoxSizer(wx.VERTICAL)
        self.close_msg = wx.StaticText(self, -1, CLOSETABS_MSG.format(num_tabs=num_tabs))
        msgsizer.Add(self.close_msg, 0, wx.EXPAND | wx.SOUTH, 8)
        msgsizer.Add(warn_cb, 0, wx.EXPAND)

        h = wx.BoxSizer(wx.HORIZONTAL)
        self.bitmap  = wx.ArtProvider.GetBitmap(wx.ART_QUESTION)
        self.bitmap.SetMaskColour(wx.BLACK)
        h.Add((self.bitmap.Width, self.bitmap.Height), 0, wx.EXPAND | wx.ALL, 9)
        h.Add(msgsizer, 0, wx.EXPAND | wx.ALL, 12)

        close_button  = wx.Button(self, wx.ID_OK, CLOSE_BUTTON_TEXT)
        close_button.SetDefault()
        close_button.SetFocus()

        cancel_button = wx.Button(self, wx.ID_CANCEL, _('&Cancel'))

        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonsizer.AddStretchSpacer(1)
        buttonsizer.Add(close_button, 0, wx.RIGHT, 6)
        buttonsizer.Add(cancel_button)
        buttonsizer.AddStretchSpacer(1)

        s = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        s.Add(h, 0, wx.EXPAND | wx.ALL)
        s.Add(buttonsizer, 0, wx.EXPAND | wx.BOTTOM, 12)

    def OnPaint(self, e):
        dc = wx.PaintDC(self)
        pos = self.close_msg.Position
        dc.DrawBitmap(self.bitmap, pos.x - self.bitmap.Width - 10, pos.y, True)

from gui.native.toplevel import FlashOnce, Flash

class TitleBarTimer(wx.Timer):
    '''
    Manages titles of tab and window titles for conversations.

    Shows flashing strings like (New IM) and (5 New IMs).
    '''

    shouldFlash  = prefprop('conversation_window.notify_flash')
    cyclePause  = prefprop('conversation_window.unread_cycle_pause')


    def __init__(self, win, tabs):

        wx.Timer.__init__(self)

        self.win = win
        self.tabs = tabs
        self.index = 0



    def Start(self):
        self.title = self.win.Title

        wx.Timer.Start(self, self.cyclePause)

    def Notify(self):
        win  = self.win
        tabs = self.tabs

        if wx.IsDestroyed(win):
            self.Stop()
            return

        # (>")>[New IMs]<("<)
        if not win.IsActive() and len(tabs):
            tabNum = len(tabs)
            if self.index >= tabNum:
                self.index  = 0
            tab = tabs[self.index]
            if not wx.IsDestroyed(tab):
                win.SetTitle('*' + tab.label1)
                self.index += 1
            else:
                tabs.remove(tab)

            if self.shouldFlash:
                FlashOnce(win) # hack until we figure out how to set the title without clearing the notify state
        else:
            self.Stop()


    def Stop(self):
        wx.Timer.Stop(self)
        if not wx.IsDestroyed(self.win):
            self.win.SetTitle(self.title)
        self.index = 0

class SkinnedNotebookPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        preview = kwargs.pop('preview', None)
        wx.Panel.__init__(self, *args, **kwargs)
        self.notebook = NoteBook(self, skinkey = 'Tabs', preview=preview)

        sz = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        sz.Add(self.notebook, 1, wx.EXPAND)

class SkinnedIMFrameEventHandler(wx.EvtHandler):
    '''
    A generic frame that can hold tabs. Sets up the TabManager and WinManager for uberbook

    TODO: move this logic/functionality to uberbook.py where it belongs
    '''

    def __init__(self, frame):
        wx.EvtHandler.__init__(self)

        self.frame = frame
        self.notebook = self.frame.notebookPanel.notebook

        self.mergetimer = None
        self.notifiedtabs = oset()
        self.titletimer = TitleBarTimer(self.frame, self.notifiedtabs)

        self.BindEventsToFrame()

    def BindEventsToFrame(self):
        Bind = self.frame.Bind
        Bind(wx.EVT_CLOSE,    self.OnClose)
        Bind(wx.EVT_MOVE,         self.OnMove)
        Bind(wx.EVT_SIZE,         self.OnSize)
        Bind(wx.EVT_ACTIVATE, self.OnActivate)
        Bind(EVT_TAB_NOTIFIED, self.OnTabNotify)

        publisher = pubsub.Publisher()
        publisher.subscribe(self.OnPageTitleUpdated, 'tab.title.updated')
        publisher.subscribe(self.OnPageIconUpdated, 'tab.icon.updated')

    def OnClose(self, event):
        if self.frame.CloseAndSaveState(event):
            self.frame.Destroy()
        else:
            event.Veto()

    def OnActivate(self, e):
        # when window activates, focus the IM input area
        e.Skip()
        if e.GetActive():
            tab = self.notebook.ActiveTab
            if tab is not None:
                # ensure the active tab becomes unnotified
                tab.SetNotify(False)

                # focus the input area
                tab.page.Content.FocusTextCtrl()

        if self.titletimer.IsRunning():
            self.titletimer.Stop()

    def OnPageIconUpdated(self, message):
        """
        Update the notebook when a convo's icon changes.
        """

        page, icon = message.data
        if not self.frame or wx.IsDestroyed(self.frame):
            return

        assert getattr(self.frame.notebook, "_name", "") != "[unknown]"
        for mypage in self.frame.notebook.Pages():
            # TODO: on windows, this comparison will never be True because
            # we are comparing Pages and ImWinPanels.
            if mypage == page and self.frame.notebook.ActiveTab == mypage.tab:
                self.frame.SetFrameIcon(icon)

    def OnPageTitleUpdated(self, message):
        """
        Update the frame and notebook when a convo's name and/or typing status changes
        """
        if not self.frame or wx.IsDestroyed(self.frame):
            return

        imwin, title, window_title = message.data

        imwin.SetName(title)

        assert getattr(self.frame.notebook, "_name", "") != "[unknown]"

        page = None
        for mypage in self.frame.notebook.Pages():
            if mypage.Content is imwin:
                page = mypage

        if page is None or page.tab is not self.frame.notebook.ActiveTab:
            return

        if window_title is not None:
            frame_title = window_title
        else:
            frame_title = title

        if self.titletimer.IsRunning():
            self.titletimer.title = frame_title
        else:
            self.frame.SetTitle(frame_title)

    flashTime   = prefprop('conversation_window.flash_time')
    flashCount  = prefprop('conversation_window.flash_count')

    def OnTabNotify(self, event):
        tab = event.tab

        if tab.notified:
            self.notifiedtabs.add(tab)
            notify_unread_message_hook()
        elif tab in self.notifiedtabs:
            self.notifiedtabs.remove(tab)
            notify_unread_message_hook()
            return
        else:
            return

        if not self.frame.cycleTitle:
            if self.frame.shouldFlash:
                Flash(self.frame, timeout = self.flashTime, count = self.flashCount)
            return

        if len(self.notifiedtabs) and not self.frame.IsActive():
            if not self.titletimer.IsRunning():
                self.titletimer.Start()
        elif self.titletimer.IsRunning():
                self.titletimer.Stop()

    def OnMove(self, event):
        event.Skip(True)

        # check if we need to move to a window underneath
        if pref('messaging.tabs.enabled', True):

            mt = self.mergetimer
            if mt is None:
                self.mergetimer = wx.CallLater(10, self.notebook.StartWindowDrag)
            else:
                mt.Start(10)

        event.Skip(True)

    def OnSize(self, event):
        mt = self.mergetimer
        if mt is not None:
            # cancel the move check if we're resizing the top left corner
            mt.Stop()

        event.Skip(True)

highlight_color = wx.Color(0xff, 0xd6, 0x48)
_highlight_bitmap = None

def get_highlight_bitmap():
    global _highlight_bitmap
    if _highlight_bitmap is None:
        import PIL.Image
        _highlight_bitmap = PIL.Image.new('RGBA', (5, 5), (0xe2, 0xd6, 0x8b, 255)).WXB
    return _highlight_bitmap

if config.platform == 'win':
    from gui.uberwidgets.uberbook.UberBook import UberBookTabController
    from gui.buddylist.renderers import get_buddy_icon

    def icon_for_tab(tab, width, height):
        window = tab.Window
        if window.ischat:
            return skin.get('actionsbar.icons.roomlist')

        buddy = window.Buddy
        notified = window.Tab.notified
        icon = get_buddy_icon(buddy, size=height, round_size=0, grey_offline=True, meta_lookup=True)
        return icon.WXB

    class ImTabController(UberBookTabController):
        def GetSmallIcon(self, tab):
            bitmap = im_badge(tab.Window)
            window = tab.Window

            if not window.ischat and bitmap is None:
                bitmap = skin.get('statusicons.' + tab.Window.Buddy.status_orb, None).Resized((16,16))
            elif window.ischat:
                bitmap = window.chat_icon

            return wx.IconFromBitmap(bitmap.WXB) if bitmap is not None else wx.IconFromBitmap(wx.NullBitmap)

        def GetIconicHBITMAP(self, tab, width, height):
            import cgui
            icon = icon_for_tab(tab, width, height)
            notified = tab.Window.Tab.notified

            highlight = get_highlight_bitmap() if notified else wx.NullBitmap

            if icon is not None:
                return cgui.getBuddyPreview((width, height), icon, highlight)


        def GetLivePreview(self, tab, rect):
            # TODO: we get a black overlay unless we draw a transparent bitmap
            # onto a DC onto the bitmap. WTF?
            overlay = skin.get('AppDefaults.TaskBarIcon')
            bitmap = wx.EmptyBitmap(rect.width, rect.height, False)
            dc = wx.MemoryDC(bitmap)
            overlay.Resized(1).Draw(dc, wx.Rect(0,0,1,1))
            dc.SelectObject(wx.NullBitmap)

            return bitmap


            #return self.GetIconicBitmap(tab, rect.width, rect.height)
            #return skin.get('serviceicons.digsby').Resized(rect.Size)

class ImFrame(wx.Frame):
    '''
    The frame around conversation tabs.
    '''

    WindowName = u'IM Window'

    def __init__(self, pos = None, size = None, startMinimized = False, posId = ''):
        if pref('imwin.ads', type = bool, default = False):
            defaultSize = wx.Size(490, 470)
        else:
            defaultSize = wx.Size(470, 390)

        wininfo, placement = preLoadWindowPos(ImFrame.WindowName, uniqueId = posId, defaultPos = wx.Point(200, 200), defaultSize = defaultSize)
        wininfo['style'] |= wx.DEFAULT_FRAME_STYLE

        setPos  = pos is not None
        setSize = size is not None

        if setPos or setSize:
            wininfo['style'] &= ~wx.MAXIMIZE

        if startMinimized:
            wininfo['style'] |= wx.ICONIZE
            self._starting_minimized = True # see comment in imhub.py's frame_show function

        wininfo['style'] |= wx.FULL_REPAINT_ON_RESIZE

        wx.Frame.__init__(self, parent = None, name = ImFrame.WindowName, **wininfo)

        self.on_engaged_start = Delegate()
        self.on_engaged_end = Delegate()
        self.on_sent_message = Delegate()

        # FIXME: Currently the IM window appearance is set by a load-time switch, as I want to first test
        # to ensure altering appearance.skin for Mac doesn't have other side-effects.
        if config.nativeIMWindow:
            import gui.imwin.imwin_native
            self.notebookPanel = gui.imwin.imwin_native.NativeNotebookPanel(self, -1)
            self.eventHandler = gui.imwin.imwin_native.NativeIMFrameEventHandler(self)
        else:
            preview = None
            if config.platform == 'win':
                preview = ImTabController
            self.notebookPanel = SkinnedNotebookPanel(self, -1, preview=preview)
            self.eventHandler = SkinnedIMFrameEventHandler(self)

        from gui.imwin.imwin_ads import construct_ad_panel
        ad_panel = construct_ad_panel(self, self.notebookPanel, self.notebookPanel.notebook.did_add)
        self.notebook.winman = TabWindowManager(lambda pos, size=None: ImFrame(pos = pos, size=size))

        if placement is not None and not (setPos or setSize):
            with traceguard:
                from gui.toolbox import SetWindowPlacement
                SetWindowPlacement(self, placement)

        if setPos:
            self.Position = pos
        if setSize:
            self.Size = size

        if not config.nativeIMWindow:
            self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.posId = posId

        self.EnsureInScreen()
        if pos is not None:
            wx.CallAfter(self.EnsureNotStacked)

        # obey always on top and snapping prefs
        profile.prefs.link(IMWIN_ALWAYS_ON_TOP_PREF, self.on_always_on_top, callnow=not startMinimized)
        snap_pref(self)

        self.iconizecallbacks = set()

        Bind = self.Bind
        Bind(wx.EVT_ICONIZE,  self.OnIconize)

        memory_event()

        def gainfocus(e):
            if e.Active:
                self._startengage()
            else:
                self._endengage()

            e.Skip()

        Bind(wx.EVT_ACTIVATE, gainfocus)

        self.register_hooks()

    def register_hooks(self):
        if getattr(ImFrame, 'did_register_hooks', False):
            return

        ImFrame.did_register_hooks = True
        ImFrame.engage_is_idle = False

        def goidle():
            ImFrame.engage_is_idle = True
            for win in all_imframes(): win._endengage()
            return True

        def unidle():
            ImFrame.engage_is_idle = False
            for win in all_imframes():
                if win.IsActive():
                    win._startengage()
            return True

        def idle_ms(ms_idle_time):
            if not ImFrame.engage_is_idle and ms_idle_time > IMWIN_STAT_IDLE_TIME:
                goidle()
            elif ImFrame.engage_is_idle and ms_idle_time < IMWIN_STAT_IDLE_TIME:
                unidle()
            return 15*1000 #request check in 15 second intervals

        hooks.register('digsby.app.idle', idle_ms)

        # win7 taskbar hook
        import cgui
        if config.platform == 'win' and cgui.isWin7OrHigher():
            from gui.native.win.taskbar import set_overlay_icon, get_tab_notebook
            def icon_updated(imwin):
                get_tab_notebook(imwin.Top).InvalidateThumbnails(imwin)

                def later():
                    if wx.IsDestroyed(imwin): return
                    set_overlay_icon(im_badge(), tlw=imwin.Top)
                wx.CallLater(300, later)

            hooks.register('digsby.overlay_icon_updated', icon_updated)

    def _startengage(self):
        self._endengage()
        #CAS: crossplatform?
        self.start_time = default_timer()
        self.on_engaged_start()

    def _endengage(self):
        if hasattr(self, 'start_time'):
            diff = max(int(default_timer() - self.start_time), 0)
            del self.start_time
            hooks.notify('digsby.statistics.imwin.imwin_engage', diff)
            self.on_engaged_end()

    cycleTitle  = prefprop('conversation_window.cycle_unread_ims')
    shouldFlash = prefprop('conversation_window.notify_flash')


    def OnIconize(self, event=None):
        self._didoniconize = True
        if event is not None:
            event.Skip()

        if event is not None and not event.Iconized() and not self.OnTop and pref(IMWIN_ALWAYS_ON_TOP_PREF, False):
            self.OnTop = True

        for callback in set(self.iconizecallbacks):
            try:
                callback()
            except PyDeadObjectError:
                self.iconizecallbacks.remove(callback)

    @property
    def notebook(self):
        if hasattr(self, "notebookPanel") and self.notebookPanel:
            return self.notebookPanel.notebook

        return None

    @property
    def AnyNotified(self):
        return any(iwin.Tab.notified for iwin in self)

    # FIXME: These iter methods aren't compatible with the native IM Window, and IMHO if we use
    # them somewhere we should replace them with a ImFrame.Tabs accessor rather than making the
    # frame itself an iterator for its tabs.
    def __iter__(self):
        if config.nativeIMWindow:
            assert True # just assert so we know where we hit this from
        return iter(p.Content for p in self.notebook.Pages())

    def __getitem__(self, n):
        if config.nativeIMWindow:
            assert True # just assert so we know where we hit this from
        return self.notebook.Pages()[n].Content

    def GetTabCount(self):
        return self.notebook.GetTabCount()

    def AddTab(self, ctrl, focus = None):
        return self.notebook.Add(ctrl, focus = focus)

    @bind('ImFrame.Tabs.CloseIfNotLast')
    def CloseTabIfNotLast(self):
        if self.notebook.GetTabCount() > 1:
            tab = self.notebook.ActiveTab
            self.notebook.CloseTab(tab)

    @bind('ImFrame.Tabs.CloseActive')
    def CloseActiveTab(self):
        tab = self.notebook.ActiveTab
        self.notebook.CloseTab(tab)

        if self.notebook.GetTabCount() < 1:
            self.Close()

    @bind('ImFrame.Tabs.NextTab')
    def NextTab(self):
        self.notebook.NextTab()

    @bind('ImFrame.Tabs.PrevTab')
    def PrevTab(self):
        self.notebook.PrevTab()

    @bind('ImFrame.ChatWindow.IncreaseTextSize')
    def IncreaseTextSize(self):
        self.ActiveMessageArea.IncreaseTextSize()

    @bind('ImFrame.ChatWindow.DecreaseTextSize')
    def DescreaseTextSize(self):
        self.ActiveMessageArea.DecreaseTextSize()

    @bind('ImFrame.ChatWindow.ResetTextSize')
    def ResetTextSize(self):
        self.ActiveMessageArea.ResetTextSize()

    @property
    def ActiveMessageArea(self):
        # TODO: no.
        return self.notebook.ActiveTab.page.Content.message_area

    def CloseAndSaveState(self, e):
        # Confirm multiple tab close
        tabcount = self.GetTabCount()

        if e.CanVeto() and tabcount > 1 and pref(WARN_PREF, True):
            with CloseTabsDialog(self, tabcount, True) as diag:
                diag.CenterOnParent()
                res = diag.ShowModal()

                if not diag.WarnMe:
                    setpref(WARN_PREF, False)

                if res == wx.ID_CANCEL:
                    return False

        self.Hide()
        saveWindowPos(self, uniqueId = self.posId) # Save our window position

        # Call each IMWin's on_close method.
        if not config.nativeIMWindow:
            for page in self.notebook.Pages():
                page.Children[0].on_close()

        memory_event()
        return True

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, id(self))

    def on_always_on_top(self, val):
        'Invoked when "conversation_window.always_on_top" preference changes.'

        self.OnTop = val

    def UpdateSkin(self):
        wx.CallAfter(self.Layout)


def newIMWindow(pos, size):
    win = ImFrame(pos, size)
    win.Show(False)
    fadein(win,'normal')
    return win

def all_imframes():
    return [win for win in wx.GetTopLevelWindows()
            if not wx.IsDestroyed(win) and isinstance(win, ImFrame)]


def notify_unread_message_hook():
    hooks.notify('digsby.im.unread_messages_changed')

def all_unread_convos():
    imwins = []

    for imframe in all_imframes():
        imwins.extend(tab.page.panel for tab in imframe.eventHandler.notifiedtabs)

    return imwins

def im_badge(specific_page=None):
    '''typing status and unread count badge for Win7 taskbar'''

    imwins = []

    typing_statuses = dict((s, i) for i, s in enumerate([None, 'typed', 'typing']))
    max_typing = None
    unread_count = 0
    needs_bubbles = False

    if specific_page is None:
        for imframe in all_imframes():
            notified_wins = set(tab.page.panel for tab in imframe.eventHandler.notifiedtabs)

            for page in imframe.notebook.Pages():
                imwin = page.panel
                if typing_statuses[imwin.typing] > typing_statuses[max_typing]:
                    max_typing = imwin.typing

                if imwin in notified_wins:
                    unread_count += 1
    else:
        max_typing = specific_page.typing
        needs_bubbles = specific_page.Notified

    bubble_icon = None
    if max_typing is not None:
        bubble_icon = skin.get('statusicons.' + max_typing, None)
    if bubble_icon is None and (unread_count or (specific_page is not None and needs_bubbles)):
        bubble_icon = skin.get('AppDefaults.UnreadMessageIcon', None)
    if bubble_icon is not None:
        bubble_icon = bubble_icon.PIL.ResizeCanvas(16, 16)
    if unread_count:
        if bubble_icon is None:
            bubble_icon = Image.new('RGBA', (16, 16))
        bubble_icon = draw_tiny_text(bubble_icon, str(unread_count))
    if specific_page is None and bubble_icon is not None:
        bubble_icon = bubble_icon.WXB

    return bubble_icon

from gui.input import add_class_context; add_class_context(_('IM Windows'), 'ImFrame', cls = ImFrame)


