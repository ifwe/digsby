'''
Main preferences dialog.
'''
from __future__ import with_statement

import wx
import metrics

from gui.textutil import default_font
from gui.toolbox import build_button_sizer, snap_pref, persist_window_pos, AutoDC, calllimit
from gui.validators import LengthLimit
from gui.pref.prefstrings import all as allprefstrings, tabnames

from util import import_function, traceguard
from util.primitives.funcs import Delegate
from common import profile

from logging import getLogger; log = getLogger('prefsdialog')

EXPAND_ALL = wx.EXPAND | wx.ALL

wxMac = 'wxMac' in wx.PlatformInfo

def show(tabname='accounts'):
    '''
    Displays the Preferences dialog with the specified tab active.

    For tab names, see "prefstrings.py"
    '''

    if not isinstance(tabname, str):
        raise TypeError('prefsdialog.show takes a tab name')

    import hooks; hooks.notify('digsby.statistics.prefs.prefs_opened')

    tabindex = [c[0] for c in tabnames].index(tabname)
    return show_prefs_window(None, tabindex)

def show_prefs_window(parent, tab = 0):
    win = PrefsDialog.RaiseExisting()
    if win is not None:
        win.show_tab(tab)
        return win

    # Show the dialog (NOT modal)
    pdiag = PrefsDialog(None, initial_tab = tab)
    persist_window_pos(pdiag, position_only = True)
    wx.CallAfter(pdiag.Show)
    wx.CallAfter(pdiag.ReallyRaise)
    return pdiag

#TODO:
# - focus indication on tabs

class PrefsSearch(wx.SearchCtrl):
    'A search textfield.'

    def __init__(self, parent):
        wx.SearchCtrl.__init__(self, parent, -1, style = wx.TE_PROCESS_ENTER, validator=LengthLimit(128))
        self.ShowSearchButton(True)

class PrefsTabs(wx.VListBox):
    'Custom drawn preference tabs.'

    item_height = 27

    def __init__(self, parent):
        wx.VListBox.__init__(self, parent, size=(130,-1))
        self.ItemCount = len(tabnames)

        self.spotlight_indices = set()

        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKey)


        self.UpdateSkin()

        self.tab_indices = dict((modname, i)
                                for i, (modname, nicename) in enumerate(tabnames))
        self.hoveridx = -1

    def OnKey(self, e):
        e.Skip()
        if e.KeyCode == wx.WXK_ESCAPE:
            self.Top.Close()

    def OnLeave(self, e):
        self.Hover = -1
        e.Skip(True)

    def OnMotion(self, e):
        self.Hover = self.HitTest(e.Position)
        e.Skip(True)


    def get_hover(self):
        return self.hoveridx

    def set_hover(self, i):
        old = self.hoveridx
        self.hoveridx = i

        if i != old:
            if old != -1: self.RefreshLine(old)
            if i   != -1: self.RefreshLine(i)

    Hover = property(get_hover, set_hover)

    def UpdateSkin(self):
        from gui import skin
        self.bgs = skin.get('AppDefaults.preftabs.backgrounds')

        self.BackgroundColour = wx.Colour(*self.bgs.normal)

    def tabname(self, index):
        return tabnames[index][1]

    def spotlight(self, tab_names):
        old = self.spotlight_indices
        self.spotlight_indices = set(self.tab_indices[name] for name in tab_names)


        self.RefreshAll()

    def OnMeasureItem(self, n):
        return self.item_height

    def OnDrawItem(self, dc, rect, n):
        selected = self.GetSelection() == n


        font = default_font()
        if selected:
            font.SetWeight( wx.FONTWEIGHT_BOLD )

        fh = font.Height
        dc.Font = font
        dc.TextForeground = wx.BLACK

        pt = wx.Point(*rect[:2]) + (5, self.item_height / 2 - fh / 2)
        dc.DrawText(self.tabname(n), *pt)

    def OnDrawBackground(self, dc, rect, n):
        selected = self.Selection == n
        hover    = self.Hover == n
        dc.Pen   = wx.TRANSPARENT_PEN

        if n in self.spotlight_indices:
            self.bgs.search.Draw(dc, rect, n)
        elif selected:
            self.bgs.selected.Draw(dc, rect, n)
        elif hover:
            self.bgs.hover.Draw(dc, rect, n)
        else:
            self.bgs.normal.Draw(dc, rect, n)


prefs_dialog_style = wx.DEFAULT_FRAME_STYLE & ~(wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX)

class PrefsDialog(wx.Frame):
    'The main Preferences window.'

    border = 5
    default_selected_tab = 1
    default_size = (700, 525)

    def __init__(self, parent, initial_tab = default_selected_tab):
        wx.Frame.__init__(self, parent, title = _('Digsby Preferences'),
                           size = self.default_size,
                           style = prefs_dialog_style,
                           name = 'Preferences Window')

        self.loaded_panels = {}
        self.SetMinSize(self.default_size)

        metrics.event('Prefs Dialog Opened')

        self.create_gui()
        self.bind_events()
        self.layout_gui()
        self.exithooks = Delegate()

        with traceguard:
            from gui import skin
            self.SetFrameIcon(skin.get('AppDefaults.TaskbarIcon'))

        if not wxMac:
            self.BackgroundColour = wx.WHITE
            self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

        # Fake a first selection
        self.tabs.SetSelection(initial_tab)
        self.on_tab_selected(initial_tab)

        self.tabnames = names = [module_name for module_name, nice_name in tabnames]

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self._loaded = 0

        # Obey the windows.sticky prreference
        snap_pref(self)

        profile.prefs.add_observer(self.incoming_network_prefs)

        from gui.uberwidgets.keycatcher import KeyCatcher
        k = self._keycatcher = KeyCatcher(self)
        k.OnDown('ctrl+w', self.Close)
        k.OnDown('escape', self.Close)

    def OnPaint(self, e):
        dc = AutoDC(self)

        crect    = self.ClientRect

        if not wxMac:
            dc.Brush = wx.WHITE_BRUSH
            dc.Pen   = wx.TRANSPARENT_PEN
            dc.DrawRectangleRect(crect)

        self.tabs.bgs.normal.Draw(dc, wx.Rect(0, 0, self.tabs.ClientRect.width, crect.height))

    def incoming_network_prefs(self, src, *a):
        wx.CallAfter(self._gui_incoming_network_prefs, src)

    @calllimit(2)
    def _gui_incoming_network_prefs(self, src):
        if src.isflagged('network'):
            wx.CallAfter(self.reload)

    def on_close(self, e):
        self.Hide()
        e.Skip() # will Destroy the dialog

        from common import profile
        profile.prefs.remove_observer(self.incoming_network_prefs)

        self.exithooks()

        for panel in self.loaded_panels.itervalues():
            if hasattr(panel, 'on_close'):
                with traceguard:
                    panel.on_close()

        profile.save('prefs')
        profile.save('notifications')

        from gui.native import memory_event
        memory_event()

    def create_gui(self):
        self.tabs = PrefsTabs(self)        # The Tab list on the left
        #self.content = wx.Panel(self)      # Panel
        self.search = PrefsSearch(self)    # Search text box
        self.search.Bind(wx.EVT_TEXT, self.search_text)
        self.search.Bind(wx.EVT_TEXT_ENTER, self.search_enter)

        if False: #not wxMac:
            self.save_button = wx.Button(self, wx.ID_SAVE, _('&Done'))
            self.save_button.SetDefault()
            self.save_button.Bind(wx.EVT_BUTTON, lambda e: self.Close())

    def search_enter(self, e):
        if len(self.tabs.spotlight_indices) == 1:
            i = self.tabs.spotlight_indices.copy().pop()
            self.tabs.SetSelection(i)
            self.on_tab_selected(i)

    #@calllimit(.45)
    def search_text(self, e):
        wx.CallAfter(self._search)

    def get_prefstrings(self):
        try:
            return self._prefstrings
        except AttributeError:
            self._prefstrings = dict(
                (name, ' '.join(s.lower().replace('&', '') for s in strings))
                 for name, strings in allprefstrings.iteritems())

            return self._prefstrings

    def _search(self):
        val     = self.search.Value
        if val == _('Search'): return
        val = val.lower()
        if val == '': return self.tabs.spotlight([])

        tab_highlights = set()

        for module_name, stringset in self.get_prefstrings().iteritems():
            if val in stringset:
                tab_highlights.add(module_name)

        self.tabs.spotlight(tab_highlights)


    def bind_events(self):
        self.tabs.Bind(wx.EVT_LISTBOX, self.on_tab_selected)

    def layout_gui(self):
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)

        hz = wx.BoxSizer(wx.HORIZONTAL)
        hz.Add(self.build_tab_sizer(), 0, EXPAND_ALL)
        hz.Add(self.content_sizer, 1, EXPAND_ALL)

        v  = wx.BoxSizer(wx.VERTICAL)
        v.Add(hz, 1, EXPAND_ALL)

        if getattr(self, 'save_button', False):
            v.Add(build_button_sizer(self.save_button, border = self.border),
                  0, wx.EXPAND | wx.SOUTH | wx.EAST, 4)
        self.Sizer = v

    def build_tab_sizer(self):
        sz = wx.BoxSizer(wx.VERTICAL)
        sz.Add(self.search, 0, EXPAND_ALL, self.border)
        if wxMac:
            sz.AddSpacer(6)
        sz.Add(self.tabs, 1, EXPAND_ALL)
        return sz

    def on_tab_selected(self, e):
        'A preference tab has been selected.'

        index = e if isinstance(e, int) else e.Int
        if index != -1:
            # paint the new tab selection before loading the panel
            self.tabs.Update()
            wx.CallAfter(self.show_panel, self.panel_for_tab(index))

    def show_tab(self, n):
        log.info('show_tab %d', n)
        self.tabs.SetSelection(n)
        self.show_panel(self.panel_for_tab(n))

    def reload(self):
        log.info('reloading Prefs dialog')
        with self.Frozen():
            assert not wx.IsDestroyed(self.content_sizer)
            child = self.content_sizer.Children[0]
            child.Show(False)
            self.content_sizer.Detach(0)
            assert len(self.content_sizer.Children) == 0

            for panel in self.loaded_panels.itervalues():
                try: panel.on_close()
                except AttributeError: pass
                panel.Destroy()

            self.loaded_panels.clear()
            del self.exithooks[:]

            self.show_tab(self.tabs.GetSelection())

    def show_panel(self, panel):
        if not isinstance(panel, wx.WindowClass):
            raise TypeError('show_panel takes a Window, you gave %r' % panel)

        with self.FrozenQuick():
            s = self.content_sizer
            if len(s.GetChildren()) > 0:
                s.Show(0, False)
                s.Detach(0)
            s.Add(panel, 1, EXPAND_ALL, 10)
            assert len(s.Children) == 1
            self.SetMaxSize(self.default_size)
            self.Layout()
            self.Fit()
            self.SetMaxSize((-1,-1))

        on_show = getattr(panel, 'on_show', None)
        if hasattr(on_show, '__call__'):
            on_show()

        def later():
            panel.Show()
            panel.Parent.Layout()

        wx.CallAfter(later)

    def panel_for_tab(self, i):
        'Returns the preference panel for the ith tab.'

        module_name = tabnames[i][0]

        if not module_name in self.loaded_panels:
            log.info('loading panel "%s"', module_name)
            func = import_function('gui.pref.pg_%s.panel' % module_name)
            panel = self._construct_sub_panel(func)
            self.loaded_panels[module_name] = panel

        return self.loaded_panels[module_name]

    def _construct_sub_panel(self, func):
        # preference panel setup that is common to all tab panels.
        from gui.pref.prefcontrols import PrefsPanel
        p = PrefsPanel(self)
        p.Sizer = sz = wx.BoxSizer(wx.VERTICAL)
        szAdd = sz.Add

        from gui.uberwidgets.PrefPanel import PrefPanel,PrefCollection
        def addgroup(titleortuple, *workers,**options): # given as a shortcut to each pref page
            if isinstance(titleortuple,tuple):
                title,prefix = titleortuple
            else:
                title = titleortuple
                prefix = ''
            group = PrefCollection(*workers,**options)
            panel = PrefPanel(p, group, title, prefix = prefix)
            szAdd(panel, 0, EXPAND_ALL, 3)
            return panel

        return func(p, sz, addgroup, self.exithooks)
