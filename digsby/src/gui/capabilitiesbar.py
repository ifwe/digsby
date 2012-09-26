from __future__ import with_statement

import wx
from logging import getLogger; log = getLogger('capsbar')

from common import caps, pref, setpref, profile
from config import nativeIMWindow
from util.primitives.funcs import Delegate

from gui import skin
from gui.textutil import default_font
from gui.filetransfer import FileTransferDialog
from gui.uberwidgets.UberBar import UberBar
from gui.uberwidgets.simplemenu import SimpleMenu,SimpleMenuItem
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.umenu import UMenu
from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.cleartext import ClearText
from cgui import SimplePanel

action_icons_key = 'conversation_window.actions_bar_icons'

#          identifier   GUI label      # tooltip
buttons = [('info',     _('Info'),    _('View buddy information')),
           ('im',       _('IM'),      _('Instant message this buddy')),
           ('video',    _('Video'),   _('Start an audio/video chat')),
           ('files',    _('Files'),   _('Send files to this buddy')),
           #('pictures', _('Pictures')),
           ('email',    _('Email'),   _('Send email')),
           ('sms',      _('SMS'),     _('Send SMS messages')),
           ]

class CapabilitiesBar(SimplePanel):
    '''
    A specialized UberBar used used in the infobox and the IM window
    has a subbar with to/from combos.
    '''

    def __init__(self, parent, buddy_callback,
                 showCapabilities = True,
                 infoboxmode = False):
        SimplePanel.__init__(self, parent)

        self.buddy_callback = buddy_callback

        self.Bind(wx.EVT_PAINT, lambda e: wx.PaintDC(self))

        self.infoboxmode = infoboxmode
        self._lastcaps = None

        self.UpdateSkin()
        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        # create delegates for callbacks
        for action in ('OnSendFiles', 'OnSendFolder', 'OnViewPastChats', 'OnAlert', 'OnBlock', 'OnAddContact'):
            setattr(self, action, Delegate())

        # Create the uberbar for the capabilities.
        self.cbar = bar = UberBar(self, skinkey = self.capabilitiesskin, overflowmode = True)
        # FIXME: we should simply not allow the capabilities bar to be created for native mode
        if not showCapabilities or nativeIMWindow:
            self.cbar.Hide()

        if not infoboxmode:
            self.cbar.Bind(wx.EVT_CONTEXT_MENU, lambda e: self.ActionsBarMenu.PopupMenu(event=e))

        # Create all the buttons for the capabilities bar.

        iconsize = skin.get('ActionsBar.IconSize')
        icons = skin.get('ActionsBar.Icons')

        for attr, title, tooltip in buttons:
            icon = getattr(icons, attr).Resized(iconsize)
            if attr == 'files':
                # "files" has a dropdown menu
                button = UberButton(bar, -1, title, icon = icon,
                                    type = 'menu', menu = self.FileMenu)

                # Change the label and action of the files button when it's overflowed into
                # the menu on the right.
                button.overflow_label    = _('Send File')
                button.overflow_callback = self.OnSendFiles
            else:
                # hack until I fix this :[ -kevin
                if attr == 'video' and infoboxmode: continue

                button = UberButton(bar, -1, title, icon = icon)
                button.overflow_label    = title

            button.SetToolTipString(tooltip)

            setattr(self, 'b' + attr, button)
            bar.Add(button, calcSize = False)

        bar.OnUBSize()

        #TODO Add button logics

#        if not self.infoboxmode:
#            self.badd = UberButton(bar,-1,'',icon = getattr(icons, 'add').Resized(iconsize))
#            bar.AddStatic(self.badd)
#            self.badd.Bind(wx.EVT_BUTTON,lambda e: self.OnAddContact())

        # Create multichat icon for the roomlist
        if pref('messaging.groupchat.enabled', False) and not self.infoboxmode:
            self.bmultichat = UberButton(bar, -1, icon = skin.get('actionsbar.icons.roomlist').Resized(16), type='toggle')
            self.bmultichat.SetToolTipString(_('Group Chat'))
            bar.AddStatic(self.bmultichat)

        self.ihistory = SimpleMenuItem(_('View Past Chats'),  method = self.OnViewPastChats)
        def show_prefs_notifications(a):
            import gui.pref.prefsdialog as prefsdialog
            prefsdialog.show('notifications')
        self.ialert   = SimpleMenuItem(_("Alert Me When..."), method = show_prefs_notifications)
        self.iblock   = SimpleMenuItem(_("Block"),            method = self.OnBlock)

        if not self.infoboxmode:
            self.iadd     = SimpleMenuItem(_("Add Contact"),  method = self.OnAddContact)
            bar.AddMenuItem(self.iadd)
        bar.AddMenuItem(self.ihistory)
        bar.AddMenuItem(self.ialert)

        if not self.infoboxmode:
            bar.AddMenuItem(SimpleMenuItem(id = -1))
            bar.AddMenuItem(self.iblock)

        self.Sizer.Add(bar, 0, wx.EXPAND)

        # create the To/From bar
        self.tfbar = tfbar = UberBar(self, skinkey = self.tofromskin)
        self.tfbar.Hide()

        tofrom_font  = skin.get('tofrombar.font',      default_font)
        tofrom_color = skin.get('tofrombar.fontcolor', wx.BLACK)

        talign = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT

        self.to_label           = ClearText(tfbar, _('To:'), alignment = talign)
        self.to_label.Font      = tofrom_font
        self.to_label.FontColor = tofrom_color
        self.from_label         = ClearText(tfbar, _('From:'), alignment = talign)
        self.from_label.Font    = tofrom_font
        self.from_label.FontColor = tofrom_color

        self.cto        = UberCombo(tfbar, skinkey = self.tofromcomboskin, typeable = False, size = (100, 20), minmenuwidth = 200)
        self.cfrom      = UberCombo(tfbar, skinkey = self.tofromcomboskin, typeable = False, size = (100, 20), minmenuwidth = 200)

        tfbar.Add(self.to_label,     calcSize = False)
        tfbar.Add(self.cto,   True,  calcSize = False)
        tfbar.Add(self.from_label,   calcSize = False)
        tfbar.Add(self.cfrom, True)

        self.Sizer.Add(tfbar, 0, wx.EXPAND)

        profile.prefs.link(action_icons_key, self.UpdateIcons)

        self.cbar.overflowmenu.BeforeDisplay += self.ApplyCaps

    ToCombo   = property(lambda self: self.cto)
    FromCombo = property(lambda self: self.cfrom)


    def UpdateSkin(self):
        'Tells the subbars what skins they should load.'

        sget = skin.get
        self.capabilitiesskin = sget('actionsbar.toolbarskin', None)
        self.tofromskin       = sget('tofrombar.toolbarskin', None)

        self.menuskin         = sget('%s.menuskin'%self.capabilitiesskin,None)

        self.tofromcomboskin = sget("tofrombar.comboboxskin",None)

        self.iconsize  = sget('ActionsBar.IconSize')
        self.icons = sget('ActionsBar.Icons')

        if hasattr(self, 'to_label'):
            tofrom_font  = sget('tofrombar.font', lambda: default_font())
            tofrom_color = sget('tofrombar.fontcolor', lambda: wx.BLACK)

            self.to_label.Font = self.from_label.Font = tofrom_font
            self.to_label.FontColor = self.from_label.FontColor = tofrom_color

        if hasattr(self, 'cbar'):  self.cbar.SetSkinKey(self.capabilitiesskin)
        if hasattr(self, 'tfbar'): self.tfbar.SetSkinKey(self.tofromskin)
        if hasattr(self, 'cto'):   self.cto.SetSkinKey(self.tofromcomboskin)
        if hasattr(self, 'cfrom'): self.cfrom.SetSkinKey(self.tofromcomboskin)

        self.UpdateIcons()

    def UpdateIcons(self, *a):
        'Updates icon sizes for buttons.'

        icons_pref = pref(action_icons_key)
        textonly   = icons_pref == 'text'

        icons = self.icons
        size = self.iconsize
        #TODO: Add Button logics
#        allbuttons = list(buttons)
#        allbuttons.append(('add',''))

        with self.Frozen():
            for attr, title, tooltip in buttons:
                icon = None if textonly else getattr(icons, attr).Resized(size)
                button = getattr(self, 'b' + attr, None)
                if button is not None:
                    button.SetIcon(icon)
                    button.SetAlignment(wx.VERTICAL if icons_pref == 'above' else wx.HORIZONTAL)
                    button.SetLabel('' if icons_pref == 'icons' else title)

        self.Parent.Layout()
        self.Refresh()

    def ShowToFrom(self, show = True):
        'Show or hide the to/from bar.'

        return self.tfbar.Show(show)

    @property
    def RoomListButtonShown(self):
        bmultichat = getattr(self, 'bmultichat', None)
        return bmultichat is not None and bmultichat.IsShown()

    @property
    def ToFromShown(self):
        'Returns True if the To/From bar is shown.'

        return self.tfbar.IsShown()

    def ShowCapabilities(self, show = True):
        'Show/Hide the capabilities bar.'

        return self.cbar.Show(show)
        #self.Layout()

    def CapabilitiesIsShown(self):
        'Returns True if the capabilities bar is shown.'

        return self.cbar.IsShown()

    def GetButton(self, button):
        'Returns one of the butons by name.'

        return getattr(self, 'b' + button, None)

    def ApplyCaps(self, contact = None, convo = None):
        'Those shows and hides options depending on the capabilities the Contact reports.'

        if contact is None and convo is None:
            convo = self.buddy_callback()
            from common.Conversation import Conversation
            if not isinstance(convo, Conversation):
                contact = convo
                convo = None

        c = None
        if convo is not None:
            if convo.ischat:
                c = set([caps.IM])
            elif contact is None:
                contact = convo.buddy

        if c is None:
            c = set(contact.caps)

        if contact is not None:
            c.add(('blocked', contact.blocked))

        # early exit if capabilities are the same.
        if c == self._lastcaps: return

        buttons_caps = [
            ('binfo',     contact is not None and not any((contact.sms and contact.mobile, self.infoboxmode))),
            ('bim',       caps.IM in c),
            ('bfiles',    caps.FILES in c),
            ('bemail',    caps.EMAIL in c),
            ('bsms',      caps.SMS in c),
            ('bvideo',    caps.VIDEO in c)
        ]

        for name, val in buttons_caps:
            ctrl = getattr(self, name, None)
            if ctrl is not None:
                ctrl.Show(ctrl, val, False)

        cbar   = self.cbar
        menu   = cbar.overflowmenu
        count  = menu.spine.items.count
        iblock = self.iblock

        if caps.BLOCKABLE in c and not count(iblock):
            cbar.AddMenuItem(SimpleMenuItem(id = -1))
            cbar.AddMenuItem(iblock)
        elif not caps.BLOCKABLE in c and count(iblock):
            cbar.overflowmenu.RemoveItem(iblock)

        if contact is not None:
            if contact.blocked:
                content = _('Unblock {name}')
            else:
                content = _('Block {name}')

            iblock.content = [content.format(name=contact.name)]

        self.set_groupchat_visibility(contact, convo)

        i = len(menu.spine.items) - 1
        if menu.GetItem(i).id  == -1:
            menu.RemoveItem(i)

        # don't show the dropdown on the right for widgets.
        self.cbar.overflowbutton.Show(not getattr(contact, 'iswidget', False))

        self._lastcaps = c

        cbar.GenWidthRestriction(True)

        self.update_add_contact_shown(convo)

        self.Parent.Layout()

    def update_add_contact_shown(self, convo):
        if not hasattr(self, 'iadd'):
            return

        ischat = convo is not None and convo.ischat
        overflow = self.cbar.overflowmenu

        if ischat:
            if overflow.GetIndex(self.iadd) != -1:
                overflow.RemoveItem(self.iadd)
        else:
            if overflow.GetIndex(self.iadd) == -1:
                overflow.InsertItem(overflow.GetIndex(self.ihistory), self.iadd)

    def set_groupchat_visibility(self, contact, convo):
        if not hasattr(self, 'bmultichat'):
            return

        proto = getattr(contact, 'protocol', getattr(convo, 'protocol', None))
        groupchat = False
        if proto is not None:
            groupchat = getattr(proto, 'supports_group_chat', False) and getattr(contact, 'supports_group_chat', False)
            self.bmultichat.Show(groupchat)

    @property
    def FileMenu(self):

        self._filemenu = SimpleMenu(self,self.menuskin)
        self.send_file_item = SimpleMenuItem(_('Send File'),lambda *a: self.OnSendFiles())
#            if b and b.online:
        self._filemenu.AppendItem(self.send_file_item)
        self._filemenu.AppendItem(SimpleMenuItem(_('Transfer History'),lambda *a: FileTransferDialog.Display()))

        return self._filemenu

#        try:
#            return self._filemenu
#        except AttributeError:
#            self._filemenu = self.build_file_menu()
#            return self._filemenu

    @property
    def ActionsBarMenu(self):
        try:
            return self._actionsbarmenu
        except AttributeError:
            self._actionsbarmenu = self.build_actionsbar_menu()
            return self._actionsbarmenu


    def build_actionsbar_menu(self):
        m = UMenu(self, onshow = self.update_actionsbar_menu)

        c = self._actionsbar_checks = {}
        for name, label in [('icons', _('Icons Only')),
                            ('text',  _('Text Only')),
                            ('next',  _('Icons Next to Text')),
                            ('above', _('Icons Above Text'))]:

            def cb(name=name):
                with self.Frozen():
                    setpref(action_icons_key, name)

            c[name] = m.AddCheckItem(label, callback = cb)

        m.AddSep()
        m.AddItem(_('Hide Actions Bar'), callback = lambda: setpref('messaging.show_actions_bar', False))

        return m

    def update_actionsbar_menu(self, menu):
        p = pref(action_icons_key)
        for name, item in self._actionsbar_checks.iteritems():
            item.Check(p == name)
