'''
Accounts GUI

For displaying accounts (IM, email, and social) in the Preference window.
'''

from __future__ import with_statement
import wx
from contextlib import contextmanager
from gui.uberwidgets.umenu import UMenu
from .anylists import AnyRow, AnyList
from .accountdialog import AccountPrefsDialog
from . import skin
from common import profile, StateMixin

import digsbyprofile
import common

from logging import getLogger; log = getLogger('accountslist'); info = log.info
from .toolbox.refreshtimer import refreshtimer

class AccountRow(AnyRow):

    def __init__(self, *a, **k):
#        self.ChildPaints = Delegate() # for cleartext
        AnyRow.__init__(self, *a, **k)

#    def _paint(self, e):
#        unused_dc = AnyRow._paint(self, e)
#        return unused_dc
#        self.ChildPaints(dc)

    def ConstructMore(self):

        # Extra component--the edit hyperlink
        edit = self.edit = wx.HyperlinkCtrl(self, -1, _('Edit'), '#')
        edit.Hide()
        edit.Bind(wx.EVT_HYPERLINK, lambda e: self.on_edit())

        remove = self.remove = wx.HyperlinkCtrl(self, -1, _('Remove'), '#')
        remove.Hide()
        remove.Bind(wx.EVT_HYPERLINK, lambda e: self.on_delete())

        edit.HoverColour = edit.VisitedColour = edit.ForegroundColour
        remove.HoverColour = remove.VisitedColour = remove.ForegroundColour

    def LayoutMore(self, sizer):
        sizer.AddStretchSpacer()
        sizer.Add(self.edit, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
        sizer.Add(self.remove, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)

class AccountList(AnyList):
    'Base class for IM, Email, and Social account lists.'

    def __init__(self, parent, accounts, row_control, edit_buttons, velocity=None):
        AnyList.__init__(self, parent, accounts,
                         row_control = row_control,
                         edit_buttons = edit_buttons,
                         velocity=velocity,
                         )

        self.show_selected = False

        Bind = self.Bind
        Bind(wx.EVT_LISTBOX_DCLICK, self.on_doubleclick)
        Bind(wx.EVT_LIST_ITEM_FOCUSED,self.OnHoveredChanged)

    @contextmanager
    def create_account_dialog(self, protocol_name):
        with AccountPrefsDialog.create_new(self.Top, protocol_name = protocol_name) as diag:
            diag.CenterOnParent()
            yield diag

    def on_doubleclick(self, e):
        try:
            row = self.rows[e.Int]
        except IndexError:
            return None
        else:
            row.on_edit()

    def on_edit(self, account):
        profile.account_manager.edit(account)

    def OnHoveredChanged(self,e):
        row = self.GetRow(e.Int)

        if row:
            if row.IsHovered():
                row.edit.Show()
                row.remove.Show()
                row.Layout()
                row.Refresh()
            else:
                row.edit.Hide()
                row.remove.Hide()
                row.Layout()

    def on_data_changed(self, *args):
        oldrowcount = len(self.rows)
        AnyList.on_data_changed(self, *args)
        newrowcount = len(self.rows)

        # when adding a new account, scroll to the bottom
        if oldrowcount < newrowcount:
            wx.CallAfter(self.Scroll, 0, self.VirtualSize.height)

link_states = ('Hover', 'Normal', 'Visited')

class IMAccountRow(AccountRow):
    'One row in the accounts list.'

    icon_cache = {}

    def __init__(self, *a, **k):
        refreshtimer().Register(self)

        AccountRow.__init__(self, *a, **k)

    @property
    def popup(self):
        if not hasattr(self,'_menu') or not self._menu:
            self._menu = menu = UMenu(self)
        else:
            menu = self._menu
            menu.RemoveAllItems()

        menu.AddItem(_('&Edit'),   callback = lambda: self.on_edit())
        menu.AddItem(_('&Remove'), callback = lambda: self.on_delete())

        menu.AddSep()
        if self.data.connection:
            common.actions.menu(self, self.data.connection, menu)
            common.actions.menu(self, self.data, menu)
        else:
            menu.AddItem(_('&Connect'), callback = lambda: self.data.connect())

        return menu

    def PopulateControls(self, account):
        # Name label
        self.text = self.acct_text(account)

        # Checkbox
        # if we're not connected or disconnected, we must be somewhere in the middle,
        # so don't alter the checkbox
        conn = account.connection

        if conn is None and account.offline_reason != StateMixin.Reasons.WILL_RECONNECT:
            self.checkbox.Value = False
        elif conn is not None and conn.state == conn.Statuses.ONLINE:
            self.checkbox.Value = True
        else:
            self.checkbox.Set3StateValue(wx.CHK_UNDETERMINED)

    def acct_text(self, account = None):
        if account is None: account = self.data

        text = account.name

        note = profile.account_manager.state_desc(account)
        if note: text = text + (' (%s)' % note)

        return text

    @property
    def image(self):
        return skin.get('serviceicons.%s' % self.data.protocol).PIL.Resized(24).WXB

    @property
    def online_bitmap(self):
        '''
        Returns a red or green light depending on if this account is connected.
        '''

        conn = self.data.connection
        state = 'Online' if conn and conn.is_connected else 'Offline'
        return skin.get(state + '.icon')


    def on_close(self, *a,**k):
        refreshtimer().UnRegister(self)

        AccountRow.on_close(self, *a, **k)

    def Refresh(self, *a, **k):
        self.text = self.acct_text()
        AccountRow.Refresh(self, *a, **k)



class IMAccountsList(AccountList):
    'The accounts list.'

    def __init__(self, parent, accounts, edit_buttons = None):
        AccountList.__init__(self, parent, accounts,
                       row_control = IMAccountRow, edit_buttons = edit_buttons,
                       velocity = 150,
                       )

        # Clicking an account's checkbox toggles its connected state
        Bind = self.Bind
        Bind(wx.EVT_CHECKBOX, self.on_account_checked)
        # And double clicking an element pops up the details dialog
#        Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selected)
#        Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_deselected)
        Bind(wx.EVT_KILL_FOCUS, self.on_kill_focus)


    def on_kill_focus(self, e):
        self.Layout()
        self.Refresh()

    def on_account_checked(self, e):
        'A checkbox next to one of the accounts has been clicked.'

        row = e.EventObject.Parent
        account = row.data

        if row.IsChecked():
            call = account.connect
            row.checkbox.Set3StateValue(wx.CHK_UNDETERMINED)
        else:
            call = lambda: profile.account_manager.cancel_reconnect(account)
            row.checkbox.SetValue(False)

        wx.CallAfter(call)

    def OnNew(self, e = None):
        'Called when the plus button above this list is clicked.'

        self.addmenu.PopupMenu()

    def OnDelete(self, acct):
        'Called when the minus button above this list is clicked.'

#        acct = self.GetDataObject(self.Selection)
        if not acct: return

        # Display a confirmation dialog.
        message = _('Are you sure you want to delete account "{name}"?').format(name=acct.name)
        caption = _('Delete Account')
        style   = wx.ICON_QUESTION | wx.YES_NO
        parent  = self

        import jabber
        if acct.protocol_class() == jabber.protocol:
            from gui.protocols.jabbergui import JabberDeleteConfirmBox
            msgbox = JabberDeleteConfirmBox(acct, message, parent, title=caption)
        else:
            msgbox = wx.MessageDialog(parent, message, caption, style)

        try:
            if msgbox.ShowModal() == wx.ID_YES:
                profile.remove_account(acct)
        finally:
            msgbox.Destroy()

    def add_account(self, protocol_name):
#        protocolinfo = digsbyprofile.protocols[protocol_name]
        with self.create_account_dialog(protocol_name) as diag:
            unusedres = diag.ShowModal()

            if diag.ReturnCode == wx.ID_SAVE:
                # this results in a network operation that may fail...
                profile.add_account(**diag.info())

                # but for now, just show the account
                self.on_data_changed()

    @property
    def addmenu(self):
        try:
            return self.add_popup
        except AttributeError:
            self.add_popup = menu = UMenu(self)

            protocols = common.protocolmeta.protocols
            improtocols = common.protocolmeta.improtocols

            for p in improtocols.keys():
                menu.AddItem(protocols[p].name, callback = lambda p=p: self.add_account(p),
                             bitmap = skin.get("serviceicons." + p, None))
            return menu

# ----------------
class SocialRow(AccountRow):
    checkbox_border = 3
    row_height = 20
    image_offset = (6,0)

    def PopulateControls(self, account):
        self.text = account.display_name
        self.checkbox.Value = bool(account.enabled)

    @property
    def image(self):
        img = skin.get("serviceicons." + self.data.protocol, None)
        return img.Resized(16) if img else None

    @property
    def popup(self):
        if not hasattr(self,'_menu') or not self._menu:
            self._menu = menu = UMenu(self)
        else:
            menu = self._menu
            menu.RemoveAllItems()

        menu.AddItem(_('&Edit'),   callback = lambda: self.on_edit())
        menu.AddItem(_('&Remove'), callback = lambda: self.on_delete())

        if self.data.enabled:
            menu.AddSep()
            common.actions.menu(self, self.data, menu)

        return menu

class SocialList(AccountList):
    def __init__(self, parent, accounts, edit_buttons = None):
        AccountList.__init__(self, parent, accounts,
                             row_control = SocialRow, edit_buttons = edit_buttons,
                             velocity = 100,
                             )

        self.Bind(wx.EVT_CHECKBOX, self.on_account_checked)

    def on_account_checked(self, e):
        account = e.EventObject.Parent.data
        checked = e.EventObject.Value
        account.setnotify('enabled', checked)
        wx.CallAfter(account.update_info)

    def OnDelete(self, acct):
        'Called when the minus button above this list is clicked.'

        if acct is None:
            return

        # Display a confirmation dialog.
        message = _('Are you sure you want to delete social network account "{name}"?').format(name=acct.name)
        caption = _('Delete Social Network Account')
        style   = wx.ICON_QUESTION | wx.YES_NO
        parent  = self

        if wx.YES == wx.MessageBox(message, caption, style, parent):
            log.info('removing account %r' % acct)
            profile.remove_social_account(acct)

    def OnNew(self, e = None):
        'Called when the plus button above this list is clicked.'
        self.addmenu.PopupMenu()

    def add_account(self, protocol_name):
        with self.create_account_dialog(protocol_name) as diag:
            unusedres = diag.ShowModal()
            if diag.ReturnCode == wx.ID_SAVE:
                acct = profile.add_social_account(**diag.info())
                on_create = getattr(acct, 'onCreate', None) #CamelCase for GUI code
                if on_create is not None:
                    on_create()

    @property
    def addmenu(self):
        try:
            return self.add_popup
        except AttributeError:
            self.add_popup = menu = UMenu(self)

            protocols = common.protocolmeta.protocols
            socialprotocols = common.protocolmeta.socialprotocols

            for p in socialprotocols.keys():
                menu.AddItem(protocols[p].name, callback = lambda p=p: self.add_account(p),
                             bitmap = skin.get('serviceicons.' + p))

            return menu

# ----------------

class EmailRow(AccountRow):

    checkbox_border = 3
    row_height = 20
    image_offset = (6, 0)

    def PopulateControls(self, account):
        self.text    = account.display_name
        self.checkbox.Value = bool(account.enabled)

    @property
    def image(self):
        icon = getattr(self.data, 'icon', None)
        if icon is not None:
            icon = icon.Resized(16)

        return icon

    @property
    def popup(self):
        if not hasattr(self,'_menu') or not self._menu:
            self._menu = menu = UMenu(self)
        else:
            menu = self._menu
            menu.RemoveAllItems()

        menu.AddItem(_('&Edit'),   callback = lambda: self.on_edit())
        menu.AddItem(_('&Remove'), callback = lambda: self.on_delete())

        from common.emailaccount import EmailAccount
        if self.data.enabled:
            menu.AddSep()
            common.actions.menu(self, self.data, menu, cls = EmailAccount)

        return menu

class EmailList(AccountList):
    'Email accounts list.'

    def __init__(self, parent, accounts, edit_buttons = None):
        AccountList.__init__(self, parent, accounts,
                         row_control = EmailRow, edit_buttons = edit_buttons,
                         velocity = 100,
                         )

        self.Bind(wx.EVT_CHECKBOX, self.on_account_checked)

    def on_account_checked(self, e):
        eo = e.EventObject
        account, checked = eo.Parent.data, eo.Value
        account.setnotifyif('enabled', checked)
        wx.CallAfter(account.update_info)

    def OnDelete(self, acct):
        'Called when the minus button above this list is clicked.'

#        acct = self.GetDataObject(self.Selection)
        if acct is None: return

        # Display a confirmation dialog.
        message = _('Are you sure you want to delete email account "{account_name}"?').format(account_name=acct.name)
        caption = _('Delete Email Account')
        style   = wx.ICON_QUESTION | wx.YES_NO
        parent  = self

        if wx.MessageBox(message, caption, style, parent) == wx.YES:
            profile.remove_email_account(acct)


    def OnNew(self, e = None):
        'Called when the plus button above this list is clicked.'
        self.addmenu.PopupMenu()

    def add_account(self, protocol_name):
        with self.create_account_dialog(protocol_name) as diag:
            unusedres = diag.ShowModal()
            if diag.ReturnCode == wx.ID_SAVE:
                info = diag.info()
                common.profile.add_email_account(**info)
                import hooks
                hooks.notify('digsby.email.new_account', parent = self.Top, **info)

    @property
    def addmenu(self):
        try:
            return self.add_popup
        except AttributeError:
            self.add_popup = menu = UMenu(self)
            protocols = common.protocolmeta.protocols
            emailprotocols = common.protocolmeta.emailprotocols

            for p in emailprotocols.keys():
                menu.AddItem(protocols[p].name, callback = lambda p=p: self.add_account(p),
                             bitmap = skin.get('serviceicons.' + p, None))
            return menu
