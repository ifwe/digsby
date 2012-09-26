import wx
import wx.lib.sized_controls as sc

from gui import skin
from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.simplemenu import SimpleMenuItem
from gui.anylists import AnyList

from common import profile, pref
from util.Events import EventMixin

from logging import getLogger; log = getLogger('chatgui')

class ConnectedAccountsCombo(UberCombo, EventMixin):
    no_connections_label = _('No Connections')
    events = set(('account_changed',))

    def __init__(self, parent, skinkey='AppDefaults.PrefCombo'):
        EventMixin.__init__(self)
        UberCombo.__init__(self, parent, self.no_connections_label, False,
                           valuecallback=self._on_account_changed, skinkey=skinkey)

        profile.account_manager.connected_accounts.add_observer(self._on_connaccts_changed)
        self._on_connaccts_changed()

    def _on_account_changed(self, *a):
        self.event('account_changed', self.Value.id)

    def ChooseProtocol(self, proto):
        for item in self:
            if item.id.connection is proto:
                break
        else:
            return

        self.Value = item

    def _get_accounts(self):
        accts = profile.account_manager.connected_accounts

        # filter out Protocols without supports_group_chat
        accts = [a for a in accts
                 if getattr(getattr(a, 'connection', None), 'supports_group_chat', False)]

        p = profile()
        if pref('digsby.allow_add', False):
            if p not in accts:
                accts.insert(0, p)
        else:
            if p in accts:
                accts.remove(p)

        return accts

    def _on_connaccts_changed(self, *a):
        self.SetItems(self._make_proto_items())
        if not self.Value in self:
            if len(self): self.SetSelection(0)
            else: self.Value = ConnectedAccountsCombo.no_connections_label

    def _make_proto_items(self):
        items = []
        for acct in self._get_accounts():
            icon = skin.get('serviceicons.%s' % acct.protocol, None)
            if icon is not None: icon = icon.Resized(16)
            items.append(SimpleMenuItem([icon, acct.name], id=acct))

        return items

from gui.toolbox import NonModalDialogMixin
from gui.pref.prefcontrols import PrivacyListRow
from gui.imwin import roomlist

class InviteRow(PrivacyListRow):
    def get_text(self):
        return roomlist.contact_display_str(self.data)

class InviteList(AnyList):
    SelectionEnabled = False
    def remove_row(self, data):
        self.data.remove(data)

class JoinChatDialog(sc.SizedDialog, NonModalDialogMixin):

    @property
    def Account(self):
        return self.account.Value.id

    def __init__(self, parent=None, protocol=None):
        sc.SizedDialog.__init__(self, parent, title=_('Join Chat Room'),
                style=wx.DEFAULT_DIALOG_STYLE | wx.FRAME_FLOAT_ON_PARENT | wx.RESIZE_BORDER)

        p = self.GetContentsPane()
        p.SetSizerType('form')
        self.SetButtonSizer(self.CreateButtonSizer(wx.OK | wx.CANCEL))

        ok = self.FindWindowById(wx.ID_OK, self)
        ok.SetLabel(_('Join Chat'))
        ok.SetDefault()

        R_CENTER = dict(halign='right', valign='center')
        R_TOP    = dict(halign='right', valign='top')

        Text = lambda label: wx.StaticText(p, wx.ID_ANY, label)

        def TextItem(label, align=R_CENTER):
            t = Text(label)
            t.SetSizerProps(**align)
            return t

        TextItem(_('Account:'))
        self.account = account = ConnectedAccountsCombo(p)
        account.bind_event('account_changed', self._on_account_changed)
        if protocol is not None: account.ChooseProtocol(protocol)
        account.SetSizerProps(expand=True)

        TextItem(_('Invite:'), dict(
            halign='right', valign='top',
            border=(('top',), 6),
        ))

        combo_panel = wx.Panel(p)

        from gui.imwin.roomlist import ContactCombo, RoomListModel

        self.model = RoomListModel([])
        self.active_account = None
        self.combo = ContactCombo(combo_panel,
                                  contacts = {},
                                  inviteCallback = self._on_invite_buddy,
                                  accountCallback = lambda: self.Account,
                                  model = self.model,
                                  use_confirm_dialog=False)

        self.invited_buddies = self.model.pending_contacts

        border = wx.Panel(combo_panel)
        border.SetBackgroundColour(wx.Color(153, 153, 153))
        self.list = InviteList(border, data=self.invited_buddies,
                               row_control=InviteRow, style=8,
                               draggable_items=False)
        self.list.SetBackgroundColour(wx.WHITE)
        self.list.SetMinSize((-1, 100))

        border.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        border.Sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 1)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.AddMany([(self.combo, 0, wx.EXPAND),
                        (1, 6),
                        (border,     1, wx.EXPAND)])
        combo_panel.SetSizer(vsizer)
        combo_panel.SetSizerProps(expand=True)

        self.server_label = TextItem(_('Server:'))
        self.server = wx.TextCtrl(p)
        self.server.SetSizerProps(expand=True)
        self.server.Bind(wx.EVT_TEXT, self._on_server_text)

        self.room_label = TextItem(_('Room Name:'))
        room = self.room = wx.TextCtrl(p)
        room.SetSizerProps(expand=True)

        self.SetMinSize((350, 250))
        self.FitInScreen()


    can_specify_roomname = True

    def _on_server_text(self, e=None):
        if e: e.Skip()

        # HACK: cannot specify a roomname on gtalk's default server.
        self.can_specify_roomname = self.protocol_name != 'gtalk' or self.server.Value.strip() != u'groupchat.google.com'

        self.room.Enable(self.can_specify_roomname)

    def _on_invite_buddy(self, b):
        if self.model.add_pending_contact(b):
            return True

    def _on_account_changed(self, account):
        print '_on_account_changed', account
        print '  protocol', account.protocol

        self.protocol_name = account.protocol
        self._on_server_text()

        connection = getattr(account, 'connection', None)
        visible = getattr(connection, 'can_specify_chatserver', False)

        for ctrl in (self.server, self.server_label, self.room, self.room_label):
            ctrl.Show(visible)

        self.server.Value = getattr(connection, 'default_chat_server', lambda: '')()

        self.combo.contacts = connection.buddies if connection is not None else {}

        # clear pending contacts
        self.model.pending_contacts[:] = []
        self.model.fire_contacts_changed()

        self.FitInScreen()

def join_chat(protocol=None, cb=None):
    if JoinChatDialog.RaiseExisting():
        return

    diag = JoinChatDialog(protocol=protocol)

    def cb(ok):
        if not ok: return

        acct = diag.Account
        if acct is not None:
            if acct.connection is not None:
                room_name = None
                if diag.room.IsShown() and diag.room.IsEnabled():
                    room_name = diag.room.Value.strip() or None

                server = None
                if diag.server.IsShown():
                    server = diag.server.Value.strip() or None

                acct.connection.make_chat_and_invite(
                                diag.model.pending_contacts,
                                room_name=room_name,
                                server=server,
                                notify=True)

    diag.ShowWithCallback(cb)

def main():
    JoinChatDialog().Show()

if __name__ == '__main__':
    main()
