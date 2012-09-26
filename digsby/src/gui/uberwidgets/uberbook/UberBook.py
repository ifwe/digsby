from __future__ import with_statement
import wx
from containers import PageContainer
from dragtimer import WinDragTimer
from OverlayImage import SimpleOverlayImage
from tab import MultiTab
from tabbar import TabBar
from tabmanager import TabManager
from common import pref, profile, setpref
from logging import getLogger; log = getLogger('uberbook')

splitStyle = wx.SP_NOBORDER | wx.SP_LIVE_UPDATE

wdt = WinDragTimer()
tabman = TabManager()

import config

if config.platform == 'win':

    import cgui
    class UberBookTabController(cgui.TabController):
        def OnTabClosed(self, tab):
            ubertab = tab.Window.Tab
            ubertab.CloseTab()


        def OnTabActivated(self, tab):
            ubertab = tab.Window.Tab
            ubertab.SetActive(True)

            tlw = tab.Window.Top
            tlw.Show()
            if tlw.IsIconized():
                tlw.Iconize(False)

                # fake an EVT_ICONIZE to the im window here
                if hasattr(tlw, 'OnIconize'):
                    from util import Storage as S
                    tlw.OnIconize(S(Skip=Null, Iconized=lambda: False))

            tlw.Raise()

def install_taskbar_tabs(notebook, preview_type):
    import gui.native.win.taskbar as tb

    nb = tb.get_tab_notebook(notebook.Top)
    notebook.did_add       += lambda win: nb.CreateTab(win, preview_type())
    notebook.did_remove    += nb.DestroyTab
    notebook.did_rearrange += nb.RearrangeTab
    notebook.did_activate  += nb.SetTabActive
    notebook.did_seticon   += lambda page, icon: nb.SetTabIcon(page, icon) if icon is not None else wx.NullBitmap
    notebook.did_settitle  += nb.SetTabTitle

    if False: # debugging
        def foo(s):
            def handler(*a, **k):
                print '#'*80
                print notebook, s
                print a, k
            return handler

        notebook.did_add       += foo('did_add')
        notebook.did_remove    += foo('did_remove')
        notebook.did_rearrange += foo('did_rearrange')

class NoteBook(wx.SplitterWindow):
    '''
    This is a redesign of wxWidgets NoteBook class, specially designed with
    skinning amd customizability in mind.  Also introduces many new features
    such as close buttons on the tab and bar, drag and drop rearranging and
    the ability to be broken out into other windows (already existing or spawned)
    '''

    def __init__(self, parent, skinkey, preview=None):
        """
            parent  - Direct ascendant
            skinkey - String key for the skin
        """
        #wx.Panel.__init__(self, parent, style = 0)
        wx.SplitterWindow.__init__(self, parent, style = splitStyle)

        self.window  = parent.Top

        #These notebooks share a singular tabmanager that handels moving tabs between windows
        #TODO: This should probably be passed in so there can be other tabbed windows that aren't interchangeable
        global tabman
        self.manager = tabman

        self.winman = None
        self.manager.Register(self)

        self.tabbar        = TabBar(self, skinkey)
        self.pagecontainer = PageContainer(self)

        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e:None)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.Bind(wx.EVT_LEFT_UP, self.OnSplitMove)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.side_tabs_width = pref('tabs.side_tabs_width', 100)
        profile.prefs.link('tabs.side_tabs', self.OnSideTabsSwitch)

        from util.primitives.funcs import Delegate
        self.did_add = Delegate()
        self.did_remove = Delegate()
        self.did_rearrange = Delegate()
        self.did_activate = Delegate()
        self.did_seticon = Delegate()
        self.did_settitle = Delegate()

        if config.platform == 'win':
            install_taskbar_tabs(self, preview)

    def OnClose(self, event):
        'Disconnect us and prepare for shutdown.'
        self.manager.UnRegister(self)
        event.Skip()

    @property
    def ActiveTab(self):
        'Returns the currently active tab in this notebook.'

        return self.tabbar.ActiveTab

    def GetTabCount(self):
        'Returns the number of tabs.'

        return self.tabbar.GetTabCount()

    def Pages(self):
        return [t.page for t in self.tabbar.tabs if t and not wx.IsDestroyed(t)]

    def NextTab(self):
        return self.tabbar.NextTab()

    def PrevTab(self):
        return self.tabbar.PrevTab()

    def UpdateSkin(self):
        pass

    def Split(self, val):
        if val:
            if self.Window2 is None:
                self.OnSideTabsSwitch(pref('tabs.side_tabs'))
        else:
            if self.Window2 is not None:
                self.Unsplit(self.tabbar)

    def OnSideTabsSwitch(self, val):
        self.side_tabs = val
        split = getattr(self, 'Split' + ('Horizontally' if not val else 'Vertically'))

        if self.IsSplit():
            self.Unsplit()

        pos = self.side_tabs_width if val else self.tabbar.MinSize.height
        split(self.tabbar, self.pagecontainer, pos)

        self.SetSashSize(5 if val else 0)


    def OnSplitMove(self, event):
        'Invoked when the left mouse button is up on the splitter.'

        event.Skip()

        if self.side_tabs and self.IsSplit() and self.IsShownOnScreen():
            pos = self.SashPosition

            self.side_tabs_width = pos
            log.info("saving side tabs sash pos of %s", pos)
            setpref('tabs.side_tabs_width', pos)


    def __repr__(self):
        return '<Notebook with %r>' % self.tabbar

    def Add(self, panel, focus = None):
        """
            Add a panel to the notebook, just call this and the rest of the process
            of displaying should be automated

            panel - the panel that will be added to a page in the notebook
            focus - should that page take focus away from the current page
        """
        with self.Frozen():
            if focus or not self.tabbar.GetTabCount():
                focus = True

            elif not focus:
                focus = False

            page = self.pagecontainer.Append(panel)
            s = self.tabbar.Add(page, focus)
            self.did_add(panel)
            if page.icon:
                self.did_seticon(panel, page.icon)
            self.pagecontainer.Layout()

        return s

    def Insert(self, page, resort = True):
        """
            Insert a pre-existing page into the notebook
        """
        self.pagecontainer.Append( page )
        self.tabbar.Add(page, True, resort)
        self.tabbar.dragorigin = page.tab
        self.did_add(page.panel)
        self.tabbar.DragFinish(True)

    def Remove(self, page):
        'Remove the specified page from the notebook.'
        with self.Frozen():
            if self.ActiveTab == page.tab:
                self.tabbar.PrevTab()
            self.tabbar.Remove(page.tab)
            self.pagecontainer.Layout()

    def CloseTab(self, tab):
        'Remove the specified page from the notebook.'
        with self.Frozen():
            if self.ActiveTab == tab:
                self.tabbar.PrevTab()
            tab.CloseTab()
            self.pagecontainer.Layout()

    def StartWindowDrag(self):
        'Called when the window is moved to prep for merging into another window.'

        if wx.LeftDown():
            global wdt
            if not wdt.IsRunning():
                self.preview = SimpleOverlayImage(self, MultiTab(self.tabbar.tabs))
                wdt.Start(self)

            self.manager.ReadyBook(self, wx.GetMousePosition())
