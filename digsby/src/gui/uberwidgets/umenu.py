'''

Menus which can be toggled between skinned/native.

'''

from __future__ import with_statement
from gui.skin.skinobjects import SkinColor

import wx
from wx import RectPS, Rect, ITEM_NORMAL, ITEM_SEPARATOR, ITEM_CHECK, \
    ITEM_RADIO, Point, ALIGN_CENTER_VERTICAL, FindWindowAtPoint, \
    MenuItem, CallLater, FindWindowAtPointer, GetMousePosition, wxEVT_MOTION, \
    StockCursor, CURSOR_DEFAULT, GetMouseState, Window
from wx import PyCommandEvent, wxEVT_MENU_OPEN
from gui import skin
from traceback import print_exc

from gui.textutil import default_font
from gui.windowfx import fadein
from gui.vlist.skinvlist import SkinVListBox
from gui.uberwidgets.UberButton import UberButton
from gui.skin.skinobjects import Margins
from gui.uberwidgets.skinnedpanel import SkinnedPanel
from gui.uberwidgets.keycatcher import KeyCatcher
from cgui import SplitImage4
from gui.toolbox import Monitor

import config

from util import traceguard, memoize, Storage as S, InstanceTracker
from util.primitives.funcs import Delegate

from common import prefprop
from weakref import ref

from logging import getLogger; log = getLogger('umenu')

wxMSW = 'wxMSW' in wx.PlatformInfo
WM_INITMENUPOPUP = 0x117

def MenuItem_repr(item):
    text = '(separator)' if item.IsSeparator() else item.Label
    return '<%s %s>' % (item.__class__.__name__, text)

MenuItem.__repr__    = MenuItem_repr
del MenuItem_repr

MenuItem.SetCallback = lambda item, callback: item.Menu.SetCallback(item.Id, callback)

if wxMSW:
    from ctypes import windll
    ReleaseCapture_win32 = windll.user32.ReleaseCapture

class UMenuTrayTimer(wx.Timer):
    'When summonned by the tray icon.'

    def __init__(self, umenu):
        wx.Timer.__init__(self)
        self.umenu = umenu

    def Notify(self):
        try:
            mp = GetMousePosition()
            ms = GetMouseState()
        except Exception:
            return

        if not (ms.LeftDown() or ms.RightDown() or ms.MiddleDown()):
            return

        menu = self.umenu

        while menu != None:
            if menu.ScreenRect.Contains(mp):
                return
            else:
                submenu = menu.menu._childmenu
                menu = submenu.popup.vlist if submenu is not None else None

        self.Stop()

        self.umenu.Dismiss()



class UMenu(wx.Menu, InstanceTracker):

    last_menu = None

    def __init__(self, parent, label = '', id = None, onshow = None, windowless = None):

        if not isinstance(parent, wx.WindowClass):
            raise TypeError('UMenu parent must be a wx.Window')

        wx.Menu.__init__(self, label)

        InstanceTracker.track(self)

        if not isinstance(id, (int, type(None))):
            raise TypeError

        self._parentmenu = self._childmenu = None
        self.Id          = wx.NewId() if id is None else id
        self._window     = ref(parent)
        self.OnDismiss   = Delegate()
        self.cbs = {}

        #self.Bind(wx.EVT_MENU, lambda e: menuEventHandler(self.InvokingWindow).ProcessEvent(e))

        if onshow is not None:
            self.Handler.AddShowCallback(self.Id, lambda menu=ref(self): onshow(menu()))

        if wxMSW:
            self.Handler.hwndMap[self.HMenu] = self

        self.Windowless = windowless

        self.UpdateSkin()

    @property
    def Window(self):
        return self._window()

    def SetWindowless(self, val):
        self._windowless = val

    def GetWindowless(self):
        return self._parentmenu.Windowless if self._parentmenu else self._windowless

    Windowless = property(GetWindowless, SetWindowless)

    def IsShown(self):
        if not self.popup or wx.IsDestroyed(self.popup):
            return False

        try:
            return self.popup.IsShown()
        except AttributeError:
            #TODO: how do we know if a native menu is being shown?
            return False

    def UpdateSkin(self):

        # no specific skinkey means look it up in MenuBar.MenuSkin
        mbskin = skin.get('MenuBar', None)

        if "wxMac" in wx.PlatformInfo or not mbskin or mbskin.get('menuskin', None) is None or mbskin.get('mode', 'skin').lower() == 'native':
            self.skin = S(native = True)
            native = True
        else:
            self.skin = skin.get(mbskin.menuskin)
            native = False
            self.skin.native = False

        if not native and not hasattr(self, 'popup'):
            # create a PopupWindow child for displaying a skinned menu
            self.popup = MenuPopupWindow(self.Window, self)
        elif not native:
            # since UpdateSkin is called on UMenus separately and does not descend the widget tree,
            # do it manually here.
            self.popup.UpdateSkin()
            self.popup.vlist.UpdateSkin()
        elif native:
            if hasattr(self, 'popup'):
                # destroy the skinned PopupWindow if we're in native mode
                self.popup.Destroy()
                del self.popup
            #
            #TODO: native menus need native-sized icons
            #
            # for item in self:
            #     bitmap = item.Bitmap
            #     if bitmap is not None and bitmap.IsOk():
            #
            #         print 'resizing', bitmap, nativesz
            #         item.Bitmap = bitmap.Resized()

    def Display(self, caller = None):
        self.PopupMenu(caller.ScreenRect)

    def dismiss_old(self):
        'Dismiss any currently visible root skinned UMenu.'

        menuref = UMenu.last_menu
        if menuref is None: return

        menu = menuref()

        if menu is not None and not wx.IsDestroyed(menu):
            menu.Dismiss()

        UMenu.last_menu = None

    def PopupMenu(self, pos = None, submenu = False, event = None):
        if not submenu:
            self.dismiss_old()

        if event is not None:
            # mark a WX event as handled
            event.Skip(False)

            self._set_menu_event(event)

        if 'wxMSW' in wx.PlatformInfo and self.Windowless:
            from gui.native.win.wineffects import _smokeFrame
            if _smokeFrame: _smokeFrame.SetFocus()

        self._menuevent = event
        try: onshow = self._onshow
        except AttributeError: pass
        else: onshow(self)
        finally: del self._menuevent

        with traceguard:
            if self.skin.get('native', False):

                if pos is None:
                    pos = GetMousePosition()

                elif len(pos) == 4:
                    # if a rectangle was passed in, get the bottom left coordinate
                    # since we can only pass a point to the native PopupMenu
                    pos = pos.BottomLeft

                # wx.Window.PopupMenu expects coordinates relative to the control
                popup = lambda pos: self.Window.PopupMenu(self, self.Window.ScreenToClient(pos))
            else:
                popup = lambda pos: self.popup.PopupMenu(pos, submenu = submenu)

                # keep a weak reference to the last skinned menu so we can
                # Dismiss it later, if needed.
                UMenu.last_menu = ref(self)

            return popup(pos)

    def Dismiss(self):
        if not self.skin.get('native', False) and not wx.IsDestroyed(self.popup):
            return self.popup.vlist.Dismiss()

    if wxMSW:
        if hasattr(wx.Menu, 'GetHMenu'):
            GetHMenu = wx.Menu.GetHMenu
        else:
            def GetHMenu(self):
                # evil byte offset hack which will almost certainly break on
                # every machine but mine -kevin
                # (remove after wxPython's _menu.i wraps wxMenu::GetHMENU())
                from ctypes import cast, POINTER, c_long
                p = cast(int(self.this), POINTER(c_long))
                return p[25]

        HMenu = property(GetHMenu)

    def AddItem(self, text = '', bitmap = None, callback = None, id = -1):
        return self._additem(text, bitmap, callback, id = id)

    def AddItemAt(self, position, text = '', bitmap = None, callback = None, id = -1):
        return self._additem(text, bitmap, callback, id = id, position = position)

    def Append(self, id, text, bitmap = None, callback = None):
        return self._additem(text, bitmap, callback, id = id)

    def AddCheckItem(self, text, callback = None, id = -1):
        return self._additem(text, callback = callback, kind = ITEM_CHECK, id = id)

    def AddRadioItem(self, text, callback = None):
        return self._additem(text, callback = callback, kind = ITEM_RADIO)

    def AddPrefCheck(self, pref, text, help = '', updatenow = True):
        'Appends a checkbox menu item tied to preference "pref" with label "text."'

        from common import profile; prefs = profile.prefs

        def callback():
            # called when the user checks the item
            prefs[pref] = not prefs[pref]

        item = self._additem(text, callback = callback, kind = ITEM_CHECK)

        # pref changes cause the item to be checked/unchecked
        prefs.link(pref, lambda val: item.Check(val), obj = self)

        return item

    def AppendLazyMenu(self, name, callback, bitmap = None):
        '''
        Append a menu which calls "callback" (with one argument: the menu)
        just before showing.
        '''
        if not callable(callback): raise TypeError, repr(callback)

        menu = UMenu(self.Window)
        return self.AddSubMenu(menu, name, bitmap = bitmap, onshow = lambda menu=menu: callback(menu))

    def _additem(self, text, bitmap = None, callback = None, kind = ITEM_NORMAL, id = -1, position = None):
        item = MenuItem(self, id, text, kind = kind)
        id = item.Id

        if bitmap is not None:
            self.SetItemBitmap(item, bitmap)

        if callback is not None:
            self.SetCallback(id, callback)

        if position is None:
            return self.AppendItem(item)
        else:
            return self.InsertItem(position, item)

#        return item

    def SetCallback(self, id, callback):
        '''
        Sets the callback that is invoked when the menu item identified
        by "id" is clicked.
        '''
        callback = lambda cb=callback: self._refresh_callback(cb)
        self.cbs[id] = callback
        self.Handler.AddCallback(id, callback)

    def _refresh_callback(self, cb):
        # force a repaint underneath the skinned menu
        # before the (potentially lengthy) callback

        m = self._parentmenu
        if m is None:
            m = self
        else:
            while m._parentmenu:
                m = m._parentmenu

        # Refresh followed by Update means "really paint right now"
        if hasattr(m, '_button'):
            if wx.IsDestroyed(m._button):
                del m._button
            else:
                m._button.Refresh()
                m._button.Update()

        self.Window.Refresh()
        self.Window.Update()
        return cb()


    def AddSubMenu(self, submenu, label, bitmap = None, onshow = None):
        submenu._parentmenu = self

        if onshow is not None:
            self.Handler.AddShowCallback(submenu.Id, onshow)

        item = self.AppendSubMenu(submenu, label)
        if bitmap is not None:
            self.SetItemBitmap(item, bitmap)

        return item

    def SetItemBitmap(self, item, bitmap):
        if self.skin.native and bitmap.Ok():
            bitmap = bitmap.ResizedSmaller(16)

        item.SetBitmap(bitmap)


    def AddSep(self):
        return self.AppendItem(MenuItem(self))

    def AddSepAt(self, i):
        return self.InsertItem(i, MenuItem(self))

    def RemoveItems(self, items):
        return [self.RemoveItem(item) for item in items]

    def RemoveAll(self):
        return self.RemoveItems(list(self))

    def DestroyAll(self):
        for item in self.RemoveAll():
            item.Destroy()

    def GetItemById(self, id):
        'Get the position index of a menu item.'

        for i, myitem in enumerate(self):
            if myitem.Id == id:
                return myitem

    def IndexOf(self, item):
        'Get the position index of a menu item.'

        id = item.Id
        for i, myitem in enumerate(self):
            if myitem.Id == id:
                return i

        return -1

    def Break(self):
        raise NotImplementedError('skinned menus cannot break')

    @property
    def Top(self):
        w = self.Window
        while not isinstance(w, wx.TopLevelWindow):
            try:
                w = getattr(w, 'Window', getattr(w, 'ParentWindow', w.Parent))
            except AttributeError:
                print '***', w, '***'
                raise
        return w

    @property
    def Handler(self):
        return menuEventHandler(self.Top)

    def _activate_item(self, item):
        return self.popup.vlist._activate_item(item)

    def __iter__(self):
        return iter(self.GetMenuItems())

    def __getitem__(self, n):
        return self.GetMenuItems()[n % len(self)]

    def __len__(self):
        return self.GetMenuItemCount()

    def __contains__(self, item):
        return any(i.Id == item.Id for i in self)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.Title)

    def __enter__(self):
        self.RemoveAll()
        return self

    def __exit__(self, exc, value, tb):
        if exc is None:
            self.PopupMenu()

    def _set_menu_event(self, e):
        self._menu_event = ref(e)

    @staticmethod
    def Reuse(parent, attr='menu', event=None):
        try:
            menu = getattr(parent, attr)
        except AttributeError:
            menu = UMenu(parent)
            setattr(parent, attr, menu)

        menu._set_menu_event(event)
        return menu

class UMenuBar(wx.MenuBar):
    '''
    A MenuBar subclass which can appear as a native menubar or as a skinned
    menubar. The skinned bar's window can be obtained via the "SizableWindow"
    property.
    '''

    def __init__(self, parent, skinkey = 'MenuBar'):
        wx.MenuBar.__init__(self)
        self.toptitles = {}
        self.skinkey = skinkey
        self.accelremoves = Delegate()

        self.panel   = SkinnedPanel(parent, 'MenuBar',)
        self.panel.UpdateSkin = self.UpdateSkin
        self.panel.Hide()
        self.UpdateSkin()

    def UpdateSkin(self):
        s = self.skin = skin.get(self.skinkey)
        self.native   = s.get('mode', 'skin').lower() == 'native' or "wxMac" in wx.PlatformInfo

        if not hasattr(self, 'panel'):
            return

        if self.native:
            # destroy all skinning GUI elements
            for child in self.panel.Children:
                with traceguard: child.Destroy()

            # hide the skin bar and show the native one
            self.panel.Hide()
        else:
            was_shown = self.panel.IsShown()
            self._constructSkinElements()

            win = self.ParentWindow.Top
            if win.MenuBar is self:
                win.SetMenuBar(None)

            self.panel.Sizer.Layout()
            self.panel.Show(was_shown)


    def Append(self, menu, title, onshow = None):
        self.toptitles[menu] = title

        i = wx.MenuBar.Append(self, menu, title)

        if not self.native: self._constructSkinElements()

        if onshow is not None:
            self.Handler.AddShowCallback(menu.Id, lambda menu=menu: onshow(menu))

        return i

    def _constructSkinElements(self):
        'Creates the buttons that launch menu dropdowns in the bar.'

        s, p = self.skin, self.panel
        p.bg = s.get("background", SkinColor(wx.WHITE))

        pad  = p.padding = s.get("padding",wx.Point(0,0))

        for child in list(p.Children):
            child.Hide()
            child.Destroy()

        v       = wx.BoxSizer(wx.VERTICAL  )
        h       = wx.BoxSizer(wx.HORIZONTAL)
        v.Add(h,1,wx.EXPAND|wx.TOP|wx.BOTTOM,pad.y)

        p.Sizer = s.get('margins', Margins()).Sizer(v)

        # create a button for each item in the menubar
        self.buttons = []
        addb = self.buttons.append
        menus, nummenus = self.Menus, len(self.Menus)
        for i, (menu, label) in enumerate(menus):

            del menu.OnDismiss[:]

            # the API sucks for getting Titles with mnemonic characters
            label = self.toptitles.get(menu, label)

#            (self, parent, id = -1, label='', skin='Button', icon=None,
#                 pos=wx.DefaultPosition, size=None, style=wx.HORIZONTAL,
#                 type=None, menu=None, menubarmode=False, onclick = None):
            button = UberButton(p, -1, skin = s.itemskin, label = label,
                             type = "menu",
                             menu= menu,
                             menubarmode=True)
            addb(button)

            # store some special attributes in the menu, which it will use for
            # keyboard/mouse navigation of the menubar
            menu._next = menus[(i+1) % nummenus][0]
            menu._prev = menus[i-1][0]
            menu._button = button

        # add buttons to the size
        h.AddMany((b, 0, wx.EXPAND | wx.LEFT, pad.x) for b in self.buttons)

        # bind keyboard accelerators
        self._bindAccelerators()

    def Show(self, val):
        'Show or hide the menubar.'
        native = self.native

        if native:
            win = self.ParentWindow.Top
            self.panel.Hide()

            # set or unset the native menubar as needed
            if val and not win.MenuBar is self:
                win.MenuBar = self
            elif not val and win.MenuBar is self:
                win.MenuBar = None
        else:
            self.panel.Show(val)

    def _bindAccelerators(self):
        '''
        Skinned menus need to link their accelerators (keyboard shortcuts)
        manually.
        '''
        accelrems  = self.accelremoves
        parentproc = self.ParentWindow.ProcessEvent
        keybind    = self.KeyCatcher.OnDown

        # remove old first
        accelrems()
        del accelrems[:]

        for menu in self:
            for item in menu:
                accel = GetAccelText(item)
                if accel:
                    # trigger command events in the parent when the KeyCatcher sees the shortcut
                    cb = lambda e, item = item, menu = menu: parentproc(menuevt(item))
                    accelrems.append(keybind(accel, cb))

    @property
    def KeyCatcher(self):
        try: return self.ParentWindow._keycatcher
        except AttributeError:
            k = self.ParentWindow._keycatcher = KeyCatcher(self.ParentWindow)
            return k

    def __len__(self):
        "Returns the number of menus in this menubar."
        return self.GetMenuCount()

    def __iter__(self):
        return iter([self.GetMenu(i) for i in xrange(self.GetMenuCount())])


    @property
    def SizableWindow(self):
        'The window that should be added to a sizer.'
        return self.panel

    @property
    def ParentWindow(self):
        'Returns the Parent window owning the menu.'
        return self.panel.Parent

    @property
    def Handler(self):
        'Returns the event handler for menu accelerators.'
        return menuEventHandler(self.panel.Top)

from wx.lib.pubsub import Publisher

def _activateapp(message):
    '''
    Since windowless menus do not receive capture changed events--we use this as
    an indicator to dismiss instead.
    '''
    is_active = message.data
    vlist = None
    if "_lastvlist" in dir(MenuListBox):
        vlist = MenuListBox._lastvlist()

    if vlist is not None and not wx.IsDestroyed(vlist) and not wx.IsDestroyed(vlist.menu):
        if vlist.menu and vlist.menu.Windowless and not is_active:
            vlist.DismissRoot()

Publisher().subscribe(_activateapp, 'app.activestate.changed')

class MenuListBox(SkinVListBox):
    'VListBox acting as a view for a wxMenu.'

    def __init__(self, parent, menu):
        SkinVListBox.__init__(self, parent, style = wx.NO_BORDER | wx.FULL_REPAINT_ON_RESIZE | wx.WANTS_CHARS)


        self.menu = menu
        self.UpdateSkin()

        self.timer   = wx.PyTimer(self._on_submenu_timer)


        Bind = self.Bind
        Bind(wx.EVT_MOUSE_EVENTS,             self._mouseevents)
        Bind(wx.EVT_MOUSE_CAPTURE_CHANGED,    self._capturechanged)
        Bind(wx.EVT_LISTBOX,                self._listbox)
        Bind(wx.EVT_KEY_DOWN,               self._keydown)

        self.mouseCallbacks = {wx.wxEVT_MOTION    : self._motion,
                               wx.wxEVT_RIGHT_DOWN: self._rdown,
                               wx.wxEVT_LEFT_DOWN : self._ldown,
                               wx.wxEVT_LEFT_UP   : self._lup}

        MenuListBox._lastvlist = ref(self)

    def reassign(self, menu):
        self.menu = menu

    menuOpenDelayMs = prefprop('menus.submenu_delay', 250)

    def __repr__(self):
        return '<%s for %r>' % (self.__class__.__name__, self.menu)

    @property
    def ParentPopup(self):
        pmenu = self.menu._parentmenu
        return None if pmenu is None else pmenu.popup.vlist

    def CalcSize(self):
        'Calculates the width and height of this menu.'

        self.SetItemCount(len(self.menu))

        height     = 0
        dc         = wx.MemoryDC()
        dc.Font    = self.font
        s          = self.skin
        padx       = self.padding[0]
        iconsize   = s.iconsize
        subw       = s.submenuicon.Width
        sepheight  = s.separatorimage.Size.height
        itemheight = self.itemheight
        textExtent = dc.GetTextExtent

        labelw = accelw = 0

        for item in self.menu:
            if item.Kind == ITEM_SEPARATOR:
                height += sepheight
            else:
                height += itemheight

                # keep the heights for the widest label and accelerator
                labelw = max(labelw, textExtent(item.Label)[0])
                accelw = max(accelw, textExtent(item.AccelText)[0])

        # store an x coordinate for where to draw the accelerator
        self.accelColumnX = padx + iconsize + padx + padx + labelw + padx

        # sum those biggest widths with the other elements to come up with a total width
        width = self.accelColumnX + padx + max(accelw, subw) + padx
        self.MinSize = self.Size = (wx.Size(width, height))

    def OnDrawItem(self, dc, rect, n):
        'Invoked by VListBox to draw one menu item'

        item        = self.menu[n]
        kind        = item.Kind
        s           = self.skin
        iconsize    = s.iconsize
        submenuicon = s.submenuicon
        padx        = self.padding.x
        selected    = self.IsSelected(n)

        drawbitmap, drawlabel = dc.DrawBitmap, dc.DrawLabel

        if kind == ITEM_SEPARATOR:
            s.separatorimage.Draw(dc, rect, n)
        else:
            dc.Font = self.font

            if not item.IsEnabled(): fg = 'disabled'
            elif selected:           fg = 'selection'
            else:                    fg = 'normal'
            dc.TextForeground = getattr(s.fontcolors, fg)

            grect = Rect(*rect)
            grect.width = padx + iconsize + padx

            # icon bitmap
            bmap = item.Bitmap
            if bmap and bmap.Ok():
                bmap  = bmap.ResizedSmaller(iconsize)
                drawbitmap(bmap, grect.HCenter(bmap), rect.VCenter(bmap), True)

            # checks and radio circles
            if item.IsCheckable() and item.IsChecked():
                # if there is a menu icon, show the check in the bottom right
                # otherwise center it
                if bmap: checkx = grect.Right - s.checkedicon.Width
                else:    checkx = grect.HCenter(s.checkedicon)

                if kind == ITEM_CHECK:
                    drawbitmap(s.checkedicon, checkx, rect.VCenter(s.checkedicon), True)
                elif kind == ITEM_RADIO:
                    drawbitmap(s.checkedicon, checkx, rect.VCenter(s.checkedicon), True)

            # main label
            rect.Subtract(left = iconsize + 3 * padx)
            drawlabel(item.Label, rect,
                      indexAccel = item.Text.split('\t')[0].find('&'),
                      alignment  = ALIGN_CENTER_VERTICAL)

            # submenu icon
            rect.Subtract(right = submenuicon.Width + padx)
            if item.SubMenu is not None:
                drawbitmap(submenuicon, rect.Right, rect.VCenter(submenuicon), True)

            # accelerator text
            acceltext = item.AccelText
            if acceltext:
                rect.x = self.accelColumnX + padx
                drawlabel(acceltext, rect, alignment = ALIGN_CENTER_VERTICAL)

    def OnDrawBackground(self, dc, rect, n):
        s   = self.skin
        bgs = s.backgrounds

        bgname = 'selection' if self.menu[n].Kind != ITEM_SEPARATOR and self.IsSelected(n) else 'item'
        bg = getattr(bgs, bgname, None)
        if bg: bg.Draw(dc, rect, n)

    def PaintMoreBackground(self, dc, rect):
        'Invoked by SkinnedVList, used to draw the gutter.'

        # draw a gutter down the length of the menu
        g = self.skin.backgrounds.gutter
        if g:
            g.Draw(dc, Rect(rect.x, rect.y,
                            self.skin.iconsize + self.padding.x * 2, rect.height))

    def OnMeasureItem(self, n):
        item = self.menu[n]
        kind = item.Kind

        if kind == ITEM_SEPARATOR:
            return self.sepheight
        else:
            return self.itemheight

    def OnPopup(self):
        parentless = self.TopMenu == self.menu

        if parentless:
            # call ReleaseCapture here on windows to prevent the control that
            # spawned this menu from keeping capture--another right click
            # should open a new menu, not the same menu (see #1995)
            if wxMSW:
                ReleaseCapture_win32()

            if self.menu.Windowless:
                if not hasattr(self,'traytimer'):
                    self.traytimer = UMenuTrayTimer(self)
                self.traytimer.Start(50)

        if not self.menu._parentmenu:
            self._grabkeyboard()

        if wx.LeftDown():
            self._leftbuttondown = True

        if not self.HasCapture():
            self.CaptureMouse()
        self.SetCursor(StockCursor(CURSOR_DEFAULT))
        self.SetFocus()

    def Dismiss(self):

        if hasattr(self,'traytimer'):
            self.traytimer.Stop()

        if self.menu._childmenu:
            self.menu._childmenu.Dismiss()
            self.menu._childmenu = None

        while self.HasCapture():
            self.ReleaseMouse()

        self.Parent.Hide()

        m = self.menu
        if m._parentmenu is None:

            if hasattr(self, 'focusHandler'):
                self.focusHandler.close()
                del self.focusHandler

            wx.CallAfter(self.menu.OnDismiss)

        else:
            m._parentmenu._childmenu = None


    def DismissRoot(self):
        self.TopMenu.Dismiss()

    @property
    def TopMenu(self):
        m = self.menu
        while m._parentmenu is not None:
            m = m._parentmenu

        return m

    def UpdateSkin(self):
        self.SetMargins(wx.Point(0, 0))
        s = self.skin = self.menu.skin
        self.sepheight = s.separatorimage.Size.height

        try: self.font = s.font
        except KeyError: self.font = default_font()

        self.fontheight = s.font.Height

        try:
            self.padding = s.padding
            assert isinstance(self.padding.x, int) and isinstance(self.padding.y, int)
        except Exception:
            self.padding = wx.Point(3, 3)

        self.itemheight = int(self.fontheight + self.padding.y * 2)

        self.Background = s.backgrounds.menu


    @property
    def Window(self):
        return self.menu.Window

    def _grabkeyboard(self):
        if 'wxMSW' in wx.PlatformInfo:
            f = wx.Window.FindFocus()
        elif "wxGTK" in wx.Platform:
            f = self
        else:
            f = None
        if f:
            self.focusHandler = FocusHandler(self, f)

    def _showsubmenu(self, i, highlight = False):
        item    = self.menu[i]
        submenu = item.SubMenu
        child   = self.menu._childmenu

        if child is submenu: # early exit if menu is already open
            return

        if child is not None: # dismiss the current child submenu if there is one
            if child: child.Dismiss()
            self.menu._childmenu = None

        # open the new submenu if there is one
        if i != -1 and submenu is not None:
            r        = self.ClientRect
            r.Y      = self.GetItemY(i)
            r.Height = self.OnMeasureItem(i)
            self.menu._childmenu = submenu
            submenu._parentmenu  = self.menu
            submenu._parentindex = i
            submenu.PopupMenu(r.ToScreen(self), submenu = True)
            if highlight: submenu.popup.vlist.Selection = 0

    def _on_submenu_timer(self):
        'Invoked after a certain duration of mouse hover time over a menu item.'

        i = self.Selection
        if i != -1 and self.IsShown() and FindWindowAtPointer() is self:
            self._showsubmenu(i)

    def _listbox(self, e):
        '''
        Invoked on listbox selection (i.e., the mouse moving up or down the
        list.
        '''

        self.timer.Start(self.menuOpenDelayMs, True)

    def _emit_menuevent(self, id, type = wx.wxEVT_COMMAND_MENU_SELECTED):
        event = wx.CommandEvent(type, id)
        self.menu.Handler.AddPendingEvent(event)

    # mouse handling

    def _mouseevents(self, e, wxEVT_MOTION = wxEVT_MOTION, FindWindowAtPoint = FindWindowAtPoint, UberButton = UberButton):
        rect = self.ClientRect
        pt_original = pt = e.Position

        if not rect.Contains(pt):
            menu = self.ParentPopup

            # forward mouse events to Parent, since we're capturing the mouse
            oldmenu = self
            while menu:
                pt = menu.ScreenToClient(oldmenu.ClientToScreen(pt))

                if menu.ClientRect.Contains(pt):
                    e.m_x, e.m_y = pt
                    return menu._mouseevents(e)

                oldmenu, menu = menu, menu.ParentPopup

            # when mousing over a menubar, we need to trigger other buttons
            try:
                button = self.TopMenu._button
            except AttributeError:
                # not in a menubar
                pass
            else:
                if e.GetEventType() == wxEVT_MOTION:
                    ctrl = FindWindowAtPoint(self.ClientToScreen(e.Position))
                    if ctrl is not None:
                        if getattr(self, '_motionswitch', -1) is ctrl:
                            # use _motionswitch to make sure the mouse actually /moves/
                            # over the button, and we're not just receiving an event for when
                            # it appears.
                            self._motionswitch = None
                            self.DismissRoot()
                            ctrl.menu._showquick = True
                            ctrl.OnLeftDown()
                        elif isinstance(ctrl, UberButton) and ctrl.menubarmode and hasattr(ctrl, 'menu'):
                            # check to see if the button being hovered over is for a menu
                            # on the same menubar
                            if ctrl.Parent is button.Parent and not ctrl is button:
                                self._motionswitch = ctrl


        e.m_x, e.m_y = pt_original
        try:    cb = self.mouseCallbacks[e.EventType]
        except KeyError: pass
        else:   cb(e)

    def _motion(self, e):
        # changes selection as mouse moves over the list
        p = e.Position
        i = self.HitTest(p) if self.ClientRect.Contains(p) else -1
        s = self.Selection

        if i != s:
            # if we're a submenu and our parent's selection doesn't point to us,
            # make it so
            p = self.ParentPopup
            if p is not None:
                pi = getattr(self.menu, '_parentindex', None)
                if pi is not None and p.Selection != pi:
                    p.Selection = pi


            self.SetSelection(i)
            self._emit_lbox_selection(i)

    @property
    def LeafMenu(self):
        s = self.menu

        while s._childmenu:
            s = s._childmenu

        return s

    def _keydown(self, e):
        # keys always go to the deepest child menu
        self = self.LeafMenu.popup.vlist

        code = e.KeyCode
        i, j, m = self.Selection, -1, self.menu

        if code == wx.WXK_DOWN:
            j = (i + 1) % len(m)
            while j != i and m[j].Kind == wx.ITEM_SEPARATOR: j = (j + 1) % len(m)

        elif code == wx.WXK_UP:
            if i == -1: i = len(m)
            j = (i - 1) % len(m)
            while j != i and m[j].Kind == wx.ITEM_SEPARATOR: j = (j - 1) % len(m)

        elif code == wx.WXK_RETURN:
            return self._activate_item(i, submenu = True, highlight = True)

        elif code == wx.WXK_RIGHT:
            if i == -1:
                pass # skip menus
            elif m[i].SubMenu is not None:
                self.timer.Stop()
                return self._showsubmenu(i, highlight = True)

            # see if the top level menu has a "_next" menu
            while m._parentmenu: m = m._parentmenu
            next = getattr(m, '_next', None)

            if next is not None:
                wx.CallAfter(self.DismissRoot)
                next._showquick = True
                wx.CallAfter(next._button.OnLeftDown)

        elif code == wx.WXK_ESCAPE:
            self.Dismiss()

        elif code == wx.WXK_LEFT:
            if m._parentmenu:
                self.Dismiss()
            else:
                prev = getattr(self.menu, '_prev', None)
                if prev is not None:
                    wx.CallAfter(self.DismissRoot)
                    prev._showquick = True
                    wx.CallAfter(prev._button.OnLeftDown)

        elif code < 256:
            self._on_char(unichr(e.UnicodeKey))

        if j != -1:
            self.SetSelection(j)

    def _on_char(self, char):
        '''
        Pressing a printable character on an opened menu...
          a) there is an underlined character--pressing the key immediately activates that item
          b) there is one item that begins with that key--it is immediately activated
          c) there are multiple items beginning with that key--pressing the key repeatedly cycles
             selection between them
        '''
        char  = char.lower()
        items = []

        # Find the first shortcut key preceeded by an &
        for item in self.menu:
            amp_char = GetAmpChar(item)
            if amp_char is not None and char == amp_char.lower():
                return self._activate_item(item, submenu = True, highlight = True)

        # Instead, find all menu items whose first character begins with the
        # one we're looking for.
        items = []

        # Get a range of indexes. If there's already a selection, rotate the
        # range so that we see items underneath the selection first.
        for i in rotated(range(0, len(self.menu)), -self.Selection-1):
            item = self.menu[i]
            label_text = item.GetItemLabelText()
            if label_text and label_text[0].lower() == char:
                items.append(i)

        if len(items) == 1:
            # only one item--activate it immediately
            self._activate_item(items[0], submenu = True, highlight = True)
        elif len(items) > 1:
            # more than one item--select the first.
            self.SetSelection(items[0])

    def _rdown(self, e):
        p, rect = e.Position, self.ClientRect

        # right mouse click outside of any menu dismisses them all
        if not rect.Contains(p): return self.DismissRoot()

    def _ldown(self, e):
        p, rect = e.Position, self.ClientRect

        # a mouse click outside of a menu causes all the menus to close from
        # the top
        if not rect.Contains(p):
            return self.DismissRoot()

        i = self.HitTest(p)

        if i != -1:
            if self.menu[i].SubMenu is not None:
                # if clicking a submenu item, show the submenu
                self.timer.Stop()
                return self._showsubmenu(i)

    def _lup(self, e):
        p = e.Position

        i = self.HitTest(e.Position)
        if self.ClientRect.Contains(p):
            self._activate_item(i)
        else:
            ctrl = FindWindowAtPointer()
            if not isinstance(ctrl, UberButton) or not ctrl.type=='menu':
                self.DismissRoot()

    def _activate_item(self, i, submenu = False, highlight = False):
        'Triggers item i (or item at position i).'

        if isinstance(i, int):
            if i == -1: return
            item = self.menu[i]
        else:
            item = i
            i = self.menu.IndexOf(item)

        if submenu:
            if item.SubMenu is not None:
                # if clicking a submenu item, show the submenu
                self.timer.Stop()
                if not self.Selection == i:
                    self.SetSelection(i)
                return self._showsubmenu(i, highlight = highlight)

        if item.Kind != ITEM_SEPARATOR and item.IsEnabled() and item.SubMenu is None:
            # clicking anything else that's enabled and not a separator
            # emits an event.
            if item.IsCheckable(): item.Check(not item.IsChecked())
            self._emit_menuevent(item.Id)
            self.DismissRoot()

    def _capturechanged(self, e):
        # MouseCaptureChangeEvent never seems to have the captured window...so this
        # hack (check for the active window later) will have to do.

        def active():
            try:
                if self.menu.Windowless or not hasattr(self.menu.Window.Top, 'IsActive'):
                    return True # wx.GetApp().IsActive()
                else:
                    return self.menu.Window.Top.IsActive()
            except Exception:
                print_exc()
                return True

        if not active():
            wx.CallAfter(lambda: self.DismissRoot())


class MenuWindowBase(object):
    def __init__(self, parent, menu):
        self.vlist = MenuListBox(self, menu)
        self.UpdateSkin()

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self._paint)

    def reassign(self, parent, menu):
        self.Reparent(parent)
        self.vlist.reassign(menu)

    def _paint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        self.bg.Draw(dc, self.ClientRect)

    def UpdateSkin(self):
        'Updates frame size margins.'

        s = self.skin = self.vlist.menu.skin

        try:
            if self.Sizer and not wx.IsDestroyed(self.Sizer):
                self.Sizer.Clear()
        except wx.PyDeadObjectError:
            return

        self.framesize = s.get('framesize', skin.ZeroMargins)
        self.Sizer     = self.framesize.Sizer(self.vlist)
        self.bg        = s.frame

    def _guess_position(self):
        # if there's a menu event, and it's Position is equal to 
        # wxDefaultPosition, that means it was spawned by the context menu key
        # so try to guess a good place for the menu:

        # 1) if we're in a text control, use the cursor position.
        if self._was_spawned_via_keyboard():
            p = self.vlist.Top.Parent

            if hasattr(p, 'IndexToCoords'):
                coords = p.IndexToCoords(p.InsertionPoint)
                pt = p.ClientToScreen(coords)
                return pt

            # 2) otherwise, use the bottom right of the focused control.
            ctrl = wx.Window.FindFocus()
            if ctrl is not None:
                return ctrl.ScreenRect.BottomRight

        # 3) or just the mouse position
        return wx.GetMousePosition()

    def _was_spawned_via_keyboard(self):
        menu_event = getattr(self.vlist.menu, '_menu_event', None)
        self.vlist.menu._menu_event = None
        if menu_event is not None:
            menu_event = menu_event()
            if menu_event is not None:
                return menu_event.Position == wx.DefaultPosition

        return False

    def PopupMenu(self, pos = None, submenu = False):
        v = self.vlist
        v.menu.Handler._menu_open(menu = v.menu)

        # fit to the menu size
        v.SetSelection(-1)
        v.CalcSize()
        self.Fit()
        self.Sizer.Layout()

        if isinstance(self.bg, SplitImage4):
            self.Cut(self.bg.GetBitmap(self.Size))
        else:
            self.Cut()

        pos = RectPS(self._guess_position(), wx.Size(0, 0)) if pos is None else pos

        try:
            try:    disp = Monitor.GetFromPoint(pos[:2]).Geometry
            except Exception: disp = Monitor.GetFromPoint(pos.BottomRight, find_near=True).Geometry
        except Exception:
            print_exc()
            log.critical('could not find display for %s, falling back to zero', pos)
            disp = Monitor.All()[0].Geometry

        size = self.Size

        rects = []; add = lambda *seq: rects.extend([RectPS(p, size) for p in seq])

        singlepoint = len(pos) == 2
        # turn a point into a rectangle of size (0, 0)
        offset = 2 if singlepoint else 0
        if singlepoint: pos = wx.RectPS(pos, (0,0))

        w, h, wh   = Point(size.width - offset, 0), Point(0, size.height-offset), Point(size.width - offset, size.height-offset)
        difftop    = Point(0, self.framesize.top)
        diffbottom = Point(0, self.framesize.bottom)

        if submenu:
            add(pos.TopRight    - difftop,
                pos.TopLeft     - w - difftop,
                pos.BottomRight - h + diffbottom,
                pos.BottomLeft  - wh + diffbottom)
        else:
            add(pos.BottomLeft,
                pos.TopLeft     - h,
                pos.BottomRight - w,
                pos.TopRight    - h,
                pos.TopRight    - wh,
                pos.BottomLeft  - h)

        for rect in rects:
            if disp.ContainsRect(rect):
                self._showat(rect)
                return

        rect = rects[0]
        if hasattr(v.menu, '_button'):
            # todo: clean up this.
            brect = v.menu._button.ScreenRect
            if rect.Intersects(brect):
                rect.Offset((brect.Width, 0))

        self._showat(rect)

    def _showat(self, rect, nofade = False):
        self.SetRect(rect)
        self.EnsureInScreen(client_area = False)

        if nofade: self.Show()
        elif getattr(self.vlist.menu, '_showquick', False):
            self.vlist.menu._showquick = False
            self.Show()
        else:
            fadein(self, 'xfast')

        # HACK: solves popup Z-fighting
        if wxMSW: CallLater(1, lambda: self.Refresh() if self else None)

        self.vlist.OnPopup()

class MenuPopupWindow(MenuWindowBase, wx.PopupWindow):
    def __init__(self, parent, menu):
        wx.PopupWindow.__init__(self, parent)
        MenuWindowBase.__init__(self, parent, menu)

class MenuFrameWindow(MenuWindowBase, wx.Frame):
    def __init__(self, parent, menu):
        wx.Frame.__init__(self, parent)
        MenuWindowBase.__init__(self, parent, menu)

from weakref import WeakValueDictionary

class MenuEventHandler(wx.EvtHandler):
    def __init__(self, parentFrame):
        wx.EvtHandler.__init__(self)

        # add this event handler to the frame's list of handlers
        parentFrame.PushEventHandler(self)

        self.Bind(wx.EVT_MENU, self.__menu)
        # once we've totally moved things over to the new menu impl,
        # this will be removed.
        if not 'wxMac' in wx.PlatformInfo:
            self.Bind(wx.EVT_MENU_OPEN, self._menu_open)

        if 'wxMSW' in wx.PlatformInfo and hasattr(parentFrame, 'BindWin32'):
            # EVT_MENU_OPEN is broken and dumb, catch WIN32 messages instead.
            parentFrame.BindWin32(WM_INITMENUPOPUP, self._initmenupopup)

        self.cbs     = WeakValueDictionary()
        self.showcbs = {}

        if wxMSW:
            self.hwndMap = WeakValueDictionary()

    def AddCallback(self, id, callback):
        self.cbs[id] = callback

    def AddShowCallback(self, id, callback):
        self.showcbs[id] = callback

    def __menu(self, e):
        id = e.Id
        try: cb = self.cbs[id]
        except KeyError: e.Skip()
        else: cb()

    def _menu_open(self, e = None, menu = None):
        if e is not None:
            e.Skip()
            menu = e.Menu

        if menu is None: return

        try: cb = self.showcbs[menu.Id]
        except KeyError: pass
        else: cb()


    if wxMSW:
        def _initmenupopup(self, hWnd, msg, wParam, lParam):
            'Invoked when the owner frame gets a WM_INITMENUPOPUP message.'

            try: menu = self.hwndMap[wParam]
            except KeyError: return

            if menu._parentmenu:
                evt = PyCommandEvent(wxEVT_MENU_OPEN, menu.Id)
                evt.Menu = menu
                menu.Handler.ProcessEvent(evt)

class FocusHandler(wx.EvtHandler):
    def __init__(self, menu, ctrl):
        wx.EvtHandler.__init__(self)
        self._menu = menu
        self._ctrl = ctrl

        self.Bind(wx.EVT_KEY_DOWN, self._menu._keydown)
        self.Bind(wx.EVT_NAVIGATION_KEY, self._menu._keydown)

        self.wantschars = bool(ctrl.WindowStyleFlag & wx.WANTS_CHARS)

        if not self.wantschars:
            ctrl.SetWindowStyleFlag(ctrl.WindowStyleFlag | wx.WANTS_CHARS)

        ctrl.PushEventHandler(self)

    def close(self):
        ctrl, self._ctrl = self._ctrl, None
        ctrl.RemoveEventHandler(self)

        f = ctrl.WindowStyleFlag
        if not self.wantschars:
            f = f & ~wx.WANTS_CHARS
            ctrl.SetWindowStyleFlag(f)

        del self._menu



    def SetMenu(self, menu): self._menu = menu
    def OnKeyDown(self, event):   self._menu.OnKeyDown(event)
    #def OnKillFocus(self, event): wx.PostEvent(self._menu, event)

def menuEventHandler(f):
    try:
        return f._menuevthandler
    except AttributeError:
        h = f._menuevthandler = MenuEventHandler(f)
    return h

from gui.toolbox.keynames import keynames, modifiernames

def menuevt(item):
    return wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, item.Id)

#
# functions for menu accelerators
#

def GetAccelText(item):
    a = item.Accel
    return '' if not a else _getacceltext(a.Flags, a.KeyCode)

if not hasattr(wx, '_MenuItem'):
    wx._MenuItem = wx.MenuItem

# give all menu items an "AccelText" property
wx._MenuItem.AccelText = property(GetAccelText)

def GetAmpChar(item):
    "Returns the character after the ampersand in a menu item's text, or None."

    text = item.Text
    amp_index = text.find('&')
    if amp_index != -1 and amp_index < len(text)-1:
        return text[amp_index + 1]

@memoize
def _getacceltext(modifiers, key, joinstr = '+'):
    return joinstr.join([name for mod, name in modifiernames if mod & modifiers] + \
                        [keynames.get(key, chr(key).upper())])

from collections import deque

def rotated(iter, n):
    d = deque(iter)
    d.rotate(n)
    return d

