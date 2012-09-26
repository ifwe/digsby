'''
Menus in the IM window.
'''
import traceback

import wx
from common import pref
import gui.toolbox
from gui import clipboard

# Create all the menu items for each button in the capabilities bar.
buttons = [('info',     _('Buddy Info')),
           ('im',       _('Send IM')),
           ('files',    _('Send File')),
           #('pictures', _('Send Pictures')),
           ('email',    _('Send Email')),
           ('sms',      _('Send SMS'))]

#class ImWinMenuMixin(object):

def add_menus(ctrl):
    from new import instancemethod

    t = type(ctrl)
    t.GetTextCtrlMenu = GetTextCtrlMenu
    t.TextCtrlMenu = property(GetTextCtrlMenu)
    t.GetMenu = instancemethod(GetMenu, None, t)
    t._onpopupshown = instancemethod(_onpopupshown, None, t)

def GetTextCtrlMenu(self):
    from gui.uberwidgets.umenu import UMenu

    m, tc = UMenu(self), self.input_area.tc

    # spelling suggestions and options
    from gui.spellchecktextctrlmixin import add_spelling_suggestions
    if add_spelling_suggestions(tc, m):
        m.AddSep()

    m.AddItem(_('Copy'),  id = wx.ID_COPY,  callback = tc.Copy) # todo: disable if "not tc.CanCopy()" when shown.
    m.AddItem(_('Paste'), id = wx.ID_PASTE, callback = tc.Paste)
    m.AddSep()

    m.AddPrefCheck('messaging.show_actions_bar',    _('Show &Actions Bar'))
    m.AddPrefCheck('messaging.show_formatting_bar', _('Show &Formatting Bar'))
    m.AddPrefCheck('messaging.show_send_button',    _('Show Send Button'))
    m.AddSep()
    gui.toolbox.add_rtl_checkbox(tc, m)

    return m

def GetMenu(self):
    try:
        self._menu.Destroy()
    except AttributeError:
        pass

    from gui.uberwidgets.umenu import UMenu
    m = UMenu(self, onshow = self._onpopupshown)

    self._menu = m
    self._topid = id(self.Top)

    self.keep_on_top = m.AddCheckItem(_('&Keep on Top'), callback = self.Top.ToggleOnTop)
    self.view_past_chats_item = m.AddItem(_('&View Past Chats'), callback = self._on_view_past_chats)

    m.AddSep()

    add, addcheck, setmode = m.AddItem, m.AddCheckItem, self.set_mode

    c = self.capsbuttons = {}
    buddy = self.Buddy
    for bname, caption in buttons:
        if bname == 'files':
            c[bname] = add(caption, callback = lambda: self.Buddy.send_file())
        else:
            if buddy is None or (bname == 'sms' and 'SMS' not in buddy.caps):
                continue

            c[bname] = addcheck(caption, callback = lambda b = bname: setmode(b, toggle_tofrom = b == 'im'))

    m.AddSep()

    self.edit_items = {}
    self.edit_items['Copy'] = add(_('Copy\tCtrl+C'), id = wx.ID_COPY)

    # add a "Copy Link" item if the mouse is hovering over a link
    message_area = getattr(self, 'message_area', None)
    if message_area is not None: # may not be created yet.
        ctrl = wx.FindWindowAtPointer()
        if ctrl is message_area:
            info = ctrl.HitTest(ctrl.ScreenToClient(wx.GetMousePosition()))
            if info.Link:
                add(_('Copy &Link'), callback = lambda: clipboard.copy(info.Link))

    self.paste_item = self.edit_items['Paste'] = add(_('Paste\tCtrl+V'), id = wx.ID_PASTE)
    self.paste_index = len(self._menu) - 1

    if pref('debug.message_area.show_edit_source', False):
        add(_('Edit Source'), callback = lambda: self.message_area.EditSource())
    if pref('debug.message_area.show_jsconsole', False):
        from gui.browser import jsconsole
        add(_('&Javascript Console'), callback = lambda: jsconsole.show_console())

    # text size menu
    if message_area is not None and message_area.IsShownOnScreen():
        textsize_menu = UMenu(self)
        self.textbigger  = textsize_menu.AddItem(_('&Increase Text Size\tCtrl+='),
                                                 callback = message_area.IncreaseTextSize)
        self.textsmaller = textsize_menu.AddItem(_('&Decrease Text Size\tCtrl+-'),
                                                 callback = message_area.DecreaseTextSize)
        textsize_menu.AddSep()
        textsize_menu.AddItem(_('&Reset Text Size\tCtrl+0'), callback = message_area.ResetTextSize)


        m.AddSubMenu(textsize_menu, _('&Text Size'))

    m.AddSep()

    # these checkboxes affect a global preference that immediately takes effect in
    # all open ImWins
    self.roomlist_item   = m.AddCheckItem(_('Show &Room List'), callback = self.toggle_roomlist)
    self.actions_item    = m.AddPrefCheck('messaging.show_actions_bar',    _('Show &Actions Bar'))
    self.formatting_item = m.AddPrefCheck('messaging.show_formatting_bar', _('Show &Formatting Bar'))

    return self._menu

def _onpopupshown(self, menu):
    'Invoked just before the conversation area menu is shown.'

    # Should we show the paste item?
    ctrl = wx.FindWindowAtPointer()

    # Retarget "edit" menu items
    for name, item in self.edit_items.iteritems():
        #TODO: why does removing "Paste" cause a hard crash?
        method = getattr(ctrl, name, None)

        capable_method = getattr(ctrl, 'Can%s' % name, None)
        try:
            should_enable = False
            if capable_method is not None:
                should_enable = capable_method()
        except Exception:
            traceback.print_exc()
            item.Enable(method is not None and (ctrl is not getattr(self, 'message_area', None) or name != 'Paste'))
        else:
            item.Enable(should_enable)

        if method is not None:
            item.SetCallback(method)

    # "always on top" checkbox: checked if on top
    self.keep_on_top.Check(self.Top.OnTop)

    # menu items for capabilities (Info, IM, SMS, ...)
    # "active" if ImWin is in that mode
    Button = self.capsbar.GetButton
    buddy  = self.Buddy

    from common import caps

    for bname, menuitem in self.capsbuttons.iteritems():
        if menuitem.IsCheckable():
            menuitem.Check(self.mode == bname)

        if bname == 'files':
            menuitem.Enable(buddy is not None and buddy.online and caps.FILES in buddy.caps)
        elif bname == 'sms':
            menuitem.Enable(buddy is not None and caps.SMS in buddy.caps)
        elif bname == 'email':
            menuitem.Enable(buddy is not None and caps.EMAIL in buddy.caps)

    self.roomlist_item.Check(self.is_roomlist_shown())
