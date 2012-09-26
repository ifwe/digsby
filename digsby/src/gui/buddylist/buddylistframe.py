'''

Main buddylist frame GUI

'''

from __future__ import with_statement
import config

from traceback import print_exc
from wx import EXPAND
import wx
import logging; log = logging.getLogger('blist_fr'); warning = log.warning
from util.primitives.error_handling import traceguard, try_this
from util.primitives.funcs import do
from util.primitives.mapping import Storage

import gui

from gui.uberwidgets.panelframe import PanelFrame
from gui.buddylist.accountlist import AccountList
from gui.uberwidgets.connectionlist import ConnectionsPanel
from gui.buddylist.accounttray import AccountTrayIcon
from gui.native import memory_event
from common import profile, bind
from gui.toolbox import AddInOrder, calllimit


from hub import Hub
hub = Hub.getInstance()
from gui.toolbox import saveWindowPos
from gui.toolbox import Monitor
from gui.statuscombo import StatusCombo
from common import pref
from cgui import SimplePanel

# keys which are ignored for starting searches.
_function_keys = [getattr(wx, 'WXK_F' + str(i)) for i in xrange(1, 13)]

platform_disallowed_keys = []
if config.platform == 'win':
    platform_disallowed_keys.extend([wx.WXK_WINDOWS_LEFT, wx.WXK_WINDOWS_RIGHT])

disallowed_search_keys = frozenset([wx.WXK_ESCAPE, wx.WXK_MENU, wx.WXK_TAB,
    wx.WXK_BACK] + platform_disallowed_keys + _function_keys)

import gui.app.menubar as menubar

from config import platformName, newMenubar

class BuddyListFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        # Set the frame icon
        with traceguard:
            from gui import skin
            self.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon'))

        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        # Do snapping if set in the preferences
        from gui.toolbox import snap_pref, loadWindowPos
        snap_pref(self)
        defaultRect = get_default_blist_rect()
        loadWindowPos(self, defaultPos = defaultRect.Position, defaultSize = defaultRect.Size)

        # frame doesn't hide when mouse is over the infobox
        from gui.native.docking import Docker #@UnresolvedImport
        docker = self.docker = Docker(self)

        panel = self.buddyListPanel = BuddyListPanel(self)

        docker.ShouldShowInTaskbar = lambda: pref('buddylist.show_in_taskbar', default=True, type=bool)
        docker.ShouldAlwaysStayOnTop = self.SetAlwaysOnTop
        docker.LinkedWindows += [panel.infobox]
        docker.OnHide += panel.infobox.Hide

        self.userSizeForMaximize = None
        self.inMaximize = False

        Bind = self.Bind
        Bind(wx.EVT_SET_FOCUS, lambda e: panel.buddylist.SetFocus())
        Bind(wx.EVT_CLOSE,     self.on_close)

        def on_show(e):
            # hiding the buddylist triggers paging out RAM
            e.Skip()
            if not e.GetShow(): memory_event()

        Bind(wx.EVT_SHOW, on_show)

        if config.platform == 'win':
            Bind(wx.EVT_ICONIZE,   self.on_iconize)

        if config.platform == 'mac':
            Bind(wx.EVT_MAXIMIZE, self.on_maximize)
            Bind(wx.EVT_SIZE, self.on_size)

    @bind('Buddylist.ToggleAutoHide')
    def ToggleAutoHideWhenDocked(self):
        profile.localprefs['buddylist.dock.autohide'] = not profile.localprefs['buddylist.dock.autohide']


    def SetAlwaysOnTop(self, val = None):
        """
            Adds or removes the STAY_ON_TOP style from the window

            Returns True if the old style had STAY_ON_TOP in it, False otherwise
        """

        stayOnTop = val if val is not None else pref('buddylist.always_on_top', False)

        style = self.GetWindowStyle()
        if stayOnTop: self.SetWindowStyle( wx.STAY_ON_TOP | style)
        else:   self.SetWindowStyle(~wx.STAY_ON_TOP & style)

    def on_size(self, e):
        e.Skip()
        # when the user sizes the window themselves, on Mac we don't want the next
        # 'maximize' call to restore the previous custom size the user set. This
        # ensures the zoom button will save the size the user sets the window to
        # and use that for the next maximize call.
        if not self.inMaximize:
            self.userSizeForMaximize = None

    def on_maximize(self, e):
        self.inMaximize = True
        monitor = Monitor.GetFromWindow(self)
        assert monitor

        if self.userSizeForMaximize:
            self.SetSize(self.userSizeForMaximize)
            self.userSizeForMaximize = None
            return
        else:
            self.userSizeForMaximize = self.Size

        display_size = monitor.GetClientArea()
        max_size_needed = self.buddyListPanel.GetMaxRequiredSize()
        max_size_needed.y += 22 # add the title bar height to the total size

        final_size = max_size_needed
        if max_size_needed.x > display_size.width:
            final_size.x = display_size.width

        if max_size_needed.y > display_size.height:
            final_size.y = display_size.height


        # if our y position + height go below the bottom of the display,
        # move the y position up to help fit it
        pos = self.GetPosition()
        if pos.y + final_size.y > display_size.height - pos.y:
            extra_y = abs(display_size.height - pos.y - final_size.y)
            pos.y -= extra_y

        self.SetPosition(pos)

        print "display_size = %r" % display_size
        print "final_size = %r, max_size_needed = %r" % (final_size, max_size_needed)
        self.SetSize(final_size)
        self.inMaximize = False

    def on_iconize(self, e):
        # Catch a minimize event so that if we're not showing in the taskbar,
        # we can hide the frame. (Otherwise it collapses to a mini
        # window above the taskbar)
        if e.Iconized():
            memory_event()

            if not self.OnTaskbar:
                self.maybe_undock()
                self.Hide()


    def on_destroy(self):
        log.info('BuddylistFrame.OnDestroy()')
        self.buddyListPanel.on_destroy()

    def on_close(self, e=None, exiting = False):
        '''
        Window has been asked to close by the user.

        (Alt-F4 or the X button on Windows.)
        '''
        log.info('BuddylistFrame.on_close')

        autohidden = False
        if not exiting:
            with traceguard:
                autohidden = self.maybe_undock()

        if not autohidden:
            saveWindowPos(self)

            # FIXME: It's probably better for us to set wx.App.SetExitOnFrameDelete based on the
            # setting of this pref. However, for that to work, we need to make sure wx.App.SetTopWindow
            # refers to this window once the splash screen is gone.
            if not exiting and pref('buddylist.close_button_exits', False):
                wx.GetApp().DigsbyCleanupAndQuit()
            else:
                self.Show(False)

        memory_event()

    @property
    def Docked(self):
        return self.docker.Enabled and self.docker.docked

    @property
    def AutoHidden(self):
        return self.Docked and self.docker.autohidden

    def ComeBackFromAutoHide(self):
        if self.AutoHidden:
            self.docker.ComeBack()

    def maybe_undock(self):
        docker = self.docker
        if docker.Enabled and docker.docked:
            autohidden = docker.autohidden
            if docker.AutoHide and not autohidden:
                docker.GoAway()
                autohidden = True
            elif not docker.AutoHide:
                docker.wasDocked = True
                docker.Undock(setFrameStyle=False)

            return autohidden

    def toggle_show_hide(self):
        'Shows or hides the buddy list frame.'

        self.show(not self.Visible)

    def show(self, show=True):
        # TODO: just have the docker catch show events...
        docker = getattr(self, 'docker', None)
        if show and docker is not None and self.IsShown():
            if getattr(docker, 'Enabled', False) and docker.docked:
                if docker.autohidden:
                    docker.ComeBack()

                self.Raise()
                return

        self.Show(show)

        if show:
            if self.IsIconized():
                self.Iconize(False)
            self.EnsureInScreen()
            self.Raise()

class BuddyListPanel(SimplePanel):
    'Holds the buddy list.'

    def __init__( self, parent = None ):
        SimplePanel.__init__(self, parent)
        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        link = profile.prefs.link #@UndefinedVariable

        # setup and layout GUI
        self.tray_icons = []
        self.gui_construct()
        rebuild = self.rebuild_panels
        rebuild()

        # Watch always on top changes
        def ontop_changed(val):
            docker = wx.GetTopLevelParent(self).docker
            if docker.docked and docker.AutoHide:
                return

            p = wx.GetTopLevelParent(self)
            if val: p.WindowStyle = p.WindowStyle | wx.STAY_ON_TOP
            else:   p.WindowStyle = p.WindowStyle & ~wx.STAY_ON_TOP

        self.unlinkers = [link(*a) for a in [
            ('buddylist.always_on_top', ontop_changed, True, self),
            ('buddylist.order', lambda v: self.gui_layout(), False, self),
            ('buddylist.show_status', rebuild, False),
            ('buddylist.show_email_as', rebuild, False),
            ('buddylist.show_social_as', rebuild, False),
            ('buddylist.show_menubar', lambda v: self.gui_layout(), False, self),
            ('social.display_attr', rebuild, False),
            ('email.display_attr', rebuild, False),
            ('buddylist.show_in_taskbar', lambda val: wx.CallAfter(lambda: setattr(self.Top, 'OnTaskbar', val)), True, self)
        ]]

        # link docking preferences
        link = profile.localprefs.link
        docker = wx.GetTopLevelParent(self).docker

        self.unlinkers += [link(*a) for a in [
            ('buddylist.dock.autohide', lambda v: docker.SetAutoHide(bool(v)), True, docker),
            ('buddylist.dock.enabled',  lambda v: docker.SetEnabled(bool(v)), True, docker),
            ('buddylist.dock.revealms', lambda v: setattr(docker, 'RevealDurationMs', try_this(lambda: int(v), 300)), True, docker),
        ]]

        self.unlinkers.append(profile.prefs.link('buddylist.dock.slide_velocity', lambda v: wx.CallAfter(docker.SetVelocity,int(v)), obj = docker)) #@UndefinedVariable
        self.unlinkers.append(Storage(unlink = profile.emailaccounts.add_list_observer (rebuild, rebuild, 'enabled').disconnect))
        self.unlinkers.append(Storage(unlink = profile.socialaccounts.add_list_observer(rebuild, rebuild, 'enabled').disconnect))

        # don't ever let this control take focus
        self.Bind(wx.EVT_SET_FOCUS, lambda e:self.blist.SetFocus())


    def UpdateSkin(self):
        wx.CallAfter(self.Layout)

    @bind('buddylist.infobox.selectnext')
    def SelectNext(self):
        self.blist.RotateContact(forward = True)

    @bind('buddylist.infobox.selectprev')
    def SelectPrev(self):
        self.blist.RotateContact(forward = False)

    def GetMaxRequiredSize(self):
        """
        This method doesn't quite work as it needs to for Mac. buddylist.GetVirtualSize() does
        not give us the right size because we want the size it needs to display without
        scrolling, but the VirtualSize grows as the actual control size grows. i.e. once the
        control size is larger than the virtual size, the virtual size simply returns the control
        size. Also, for some reason, the virtual size reported on Mac is about 20 pixels less than
        what is needed to actually display the contents.
        """
        size = self.buddylist.GetVirtualSize()
        size.y += self.statuscombo.GetSize().y
        size.y += self.elist.GetSize().y
        size.y += self.clist.GetVirtualSize().y

        return size

    def on_blist_thumbtrack(self, event):
        event.Skip()
        if pref('search.buddylist.show_hint', True) and not self.statuscombo.searchHintShown:
            self.statuscombo.ShowSearchHint()

    def on_blist_thumbrelease(self, event):
        event.Skip()
        if self.statuscombo.searchHintShown:
            self.statuscombo.HideSearchHint()

    def gui_construct(self):
        from gui.buddylist.buddylist import BuddyList
        from gui.infobox.infobox import InfoBox

        # the main buddy list
        self.infobox = InfoBox(self)
        self.buddylist = BuddyList(self, self.infobox, keyhandler = self.on_buddylist_char)
        self.buddylist.infobox_scrollers.update([InfoBox, AccountList])
        self.buddylist.Bind(wx.EVT_KEY_DOWN, self.on_buddylist_key)
        self.buddylist.Bind(wx.EVT_SCROLLWIN_THUMBTRACK, self.on_blist_thumbtrack)
        self.buddylist.Bind(wx.EVT_SCROLLWIN_THUMBRELEASE, self.on_blist_thumbrelease)
        self.statuscombo = StatusCombo(self, self.buddylist, profile.statuses)
        self.statuscombo.OnActivateSearch += self.on_activate_search
        self.statuscombo.OnDeactivateSearch += self.on_deactivate_search
        self.status = PanelFrame(self, self.statuscombo, 'statuspanel')

        self.blist   = PanelFrame(self, self.buddylist, 'buddiespanel')

        def labelcallback(a, acctlist):
            if getattr(a, 'alias', None) is not None:
                out = a.alias
            else:
                atypecount = len([acct.protocol_info().name for acct in acctlist if acct.enabled and acct.protocol_info().name == a.protocol_info().name])
                out = a.protocol_info().name if atypecount == 1 else ('%s' % a.display_name)
            if a.state != a.Statuses.CHECKING and profile.account_manager.state_desc(a):
                return out + (' (%s)' % profile.account_manager.state_desc(a))
            else:
                if hasattr(a, 'count_text_callback'):
                    return a.count_text_callback(out)
                elif hasattr(a, 'count') and a.count is not None:
                    return out + (' (%s)' % a.count)
                else:
                    return out

        # panel for all active email accounts
        self.elist   = PanelFrame(self,
                                  AccountList(self, profile.emailaccounts, self.infobox,
                                              skinkey = 'emailpanel',
                                              prefkey = 'buddylist.emailpanel',
                                              onDoubleClick = lambda a: a.OnClickInboxURL(),
                                              labelCallback = lambda a: labelcallback(a, profile.emailaccounts)),
                                  'emailpanel'
                        )

        def foo(a):
            if a.state != a.Statuses.CHECKING:
                bar = profile.account_manager.state_desc(a)
            else:
                bar = a.count
            return '%s (%s)' % (a.display_name, bar)

        # panel for all active social network accounts

        def DoubleClickAction(a):
            url = a.DefaultAction()
            self.infobox.DoubleclickHide()
            if url is not None:
                wx.LaunchDefaultBrowser(url)

        def leave_slist(e):
            # since slist may call infobox.DoubleClickHide, it needs to invalidate
            # it as well.
            e.Skip()
            self.infobox.InvalidateDoubleclickHide()

        self.slist   = PanelFrame(self,
                                  AccountList(self, profile.socialaccounts, self.infobox,
                                              skinkey = 'socialpanel',
                                              prefkey = 'buddylist.socialpanel',
                                              onDoubleClick = DoubleClickAction,
                                              labelCallback = lambda a: labelcallback(a, profile.socialaccounts)),
                                  'socialpanel'
                       )

        self.slist.panel.Bind(wx.EVT_LEAVE_WINDOW, leave_slist)

        self.clist = ConnectionsPanel(self)


        self.infobox.Befriend(self.blist)
        self.infobox.Befriend(self.elist)
        self.infobox.Befriend(self.slist)

        # construct the main menu
        if not newMenubar:
            from gui.buddylist import buddylistmenu
            self.menubar = buddylistmenu.create_main_menu(self)
            if self.menubar.native:
                self.Top.SetMenuBar(self.menubar)
        else:
            asumenu = False
            parent = self.Parent
            if platformName != "mac":
                asumenu = True
                parent = self
            self.menubar = menus.set_menubar(parent, menubar.digsbyWxMenuBar(),umenu=asumenu) #@UndefinedVariable

    @bind('BuddyList.Accounts.ToggleShow')
    def ToggleConnPanel(self):
        self.clist.ToggleState()

    def gui_layout(self, layoutNow = True):
        assert wx.IsMainThread()

        elems = ['status', 'blist','clist', 'slist', 'elist']

        searching   = self.Searching
        panel_order = pref('buddylist.order', elems)
        email_view  = pref('buddylist.show_email_as', 'panel') in ('panel', 'both') and len(self.elist.active)
        social_view = pref('buddylist.show_social_as', 'panel') in ('panel', 'both') and len(self.slist.active)
        status_view = searching or pref('buddylist.show_status', True)

        viewable = Storage()

        with self.Frozen():
            self.Sizer.Clear() # remove all children, but don't delete.

            show_menu = pref('buddylist.show_menubar', True)
            if not config.platform == 'mac':
                if show_menu:
                    self.Sizer.Add(self.menubar.SizableWindow, 0, EXPAND)

                self.menubar.Show(show_menu)

            if searching or (hasattr(self, 'status') and status_view):
                viewable.status = (self.status,  0, EXPAND)

            viewable.blist =     (self.blist,   1, EXPAND)
            viewable.clist =     (self.clist,   0, EXPAND)

            if email_view:
                viewable.elist = (self.elist,   0, EXPAND)

            if social_view:
                viewable.slist = (self.slist,   0, EXPAND)

            AddInOrder(self.Sizer, *panel_order, **viewable)

            self.status.Show(status_view)
            self.elist.Show(email_view)
            self.slist.Show(social_view)

            if layoutNow:
                self.Layout()

    def rebuild_panels(self, *a):
        wx.CallAfter(self._rebuild_panels)

    @calllimit(1)
    def _rebuild_panels(self):
        trayaccts = []
        if pref('buddylist.show_email_as', 'panel') in ('systray', 'both'):
            trayaccts += [a for a in profile.emailaccounts]
        if pref('buddylist.show_social_as', 'panel') in ('systray', 'both'):
            trayaccts += [a for a in profile.socialaccounts]

        with self.Frozen():
            if trayaccts:
                shown   = [a for (a, icon) in self.tray_icons]
                enabled = [a for a in trayaccts if a.enabled]
                icons = dict(self.tray_icons)
                e, s = set(enabled), set(shown)

                # remove tray icons no longer needed
                do(icons.pop(acct).Destroy() for acct in s - e)

                # add new ones, indexed by their positions in the accounts list
                for acct in sorted(e - s, key = lambda a: enabled.index(a), reverse = True):
                    try:
                        icons[acct] = AccountTrayIcon.create(acct, self.infobox)
                    except Exception:
                        print_exc()

                self.tray_icons = icons.items()
            else:
                # destroy all tray icons
                do(icon.Destroy() for acct, icon in self.tray_icons)
                self.tray_icons = {}

            wx.CallAfter(self.gui_layout)

    def on_destroy(self):

        log.info('BuddylistPanel.on_destroy')

        for linker in self.unlinkers:
            linker.unlink()

        self.elist.OnClose()
        self.slist.OnClose()

        log.info('destroying account tray icons')
        for acct, icon in self.tray_icons:
            try:
                log.info("destroying account tray icon %r...", icon)
                icon.Destroy()
                log.info('ok')
            except Exception:
                print_exc()

    #
    # searchbox functionality
    #

    def start_search(self, e = None):
        self.statuscombo.search(e)
        if not self.status.IsShown():
            self.gui_layout()

    def on_buddylist_char(self, e):
        if e.KeyCode not in disallowed_search_keys:
            with self.Frozen():
                # the key event will be emulated on the search box
                self.start_search(e)

        if e is not None:
            e.Skip()

    def on_buddylist_key(self, e):
        if e.Modifiers == wx.MOD_CMD and e.KeyCode == ord('F'):
            self.start_search()
        else:
            e.Skip()

    @property
    def Searching(self):
        'Returns True if the searchbox has focus.'
        status = getattr(self, 'statuscombo', None)
        return status is not None and status.searching

    def on_activate_search(self):
        self.infobox.Hide()

    def on_deactivate_search(self):
        if not pref('buddylist.show_status', True):
            self.gui_layout()

def get_default_blist_rect():
    'Initial buddylist position.'

    r = wx.Display(0).GetClientArea()
    DEF_WIDTH = 220
    r.x = r.Right - DEF_WIDTH
    r.width = DEF_WIDTH
    return r

gui.input.add_class_context(_('Buddy List'), 'BuddyList', cls = BuddyListPanel) #@UndefinedVariable
