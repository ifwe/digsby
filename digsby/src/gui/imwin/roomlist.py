'''

IM window roomlist/multichat management

'''

if __name__ == '__main__':
    import gettext; gettext.install('Digsby')

import wx
from time import time
from gui.textutil import default_font
from util.primitives.mapping import Storage
from util.primitives.error_handling import try_this
from gui.buddylist.renderers import get_buddy_icon
from util.observe import ObservableList
from gui.skin.skinobjects import SkinColor
from gui import skin
from gui.toolbox import update_tooltip
import gui.imwin

from util.Events import EventMixin

from logging import getLogger; log = getLogger('roomlist')

S = Storage

class TextControl(wx.TextCtrl):
    def __init__(self, parent, value=None, empty_text=None):
        wx.TextCtrl.__init__(self, parent)

        self.EmptyText = empty_text
        self.Value = value or ''

        self.defaultcolor = self.GetForegroundColour()
        self.emptycolor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)

        self.BBind(KILL_FOCUS=self.OnLoseFocus,
                   SET_FOCUS=self.OnSetFocus)

    def OnLoseFocus(self, e):
        e.Skip()
        if self.EmptyText and self.Value == '':
            self.SetForegroundColour(self.emptycolor)
            self.Value = self.EmptyText

    def OnSetFocus(self, e):
        e.Skip()
        if self.EmptyText and self.ForegroundColour == self.emptycolor:
            self.SetForegroundColour(self.defaultcolor)
            self.Value = ''

class SkinVListBox(wx.VListBox):
    def __init__(self, *a, **k):
        wx.VListBox.__init__(self, *a, **k)
        syscol = wx.SystemSettings.GetColour

        self.colors = Storage(textfg=Storage(selected=syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT),
                                               normal=syscol(wx.SYS_COLOUR_WINDOWTEXT)))

        self.bg = Storage(selected=SkinColor(syscol(wx.SYS_COLOUR_HIGHLIGHT)),
                              normal=SkinColor(syscol(wx.SYS_COLOUR_LISTBOX)))

        self.fonts = Storage(text=default_font())

        self.BBind(LEFT_DOWN=self._OnLeftDown)

    def GetSelections(self):
        item, cookie = self.GetFirstSelected()

        yield item
        while item != -1:
            item, cookie = self.GetNextSelected(cookie)
            yield item

    def IsSelected(self, n):
        if self.HasMultipleSelection():
            return n in self.GetSelections()
        else:
            return self.Selection == n

    def OnDrawItem(self, dc, rect, n):
        selected = self.IsSelected(n)

        textfg = getattr(self.colors.textfg, 'selected' if selected else 'normal')

        dc.SetTextForeground(textfg)
        dc.SetFont(self.fonts.text)

        self._draw(dc, rect, n, selected)

    def OnDrawBackground(self, dc, rect, n):
        selected = self.IsSelected(n)

        bg = getattr(self.bg, 'selected' if selected else 'normal')
        bg.Draw(dc, rect, n)

        try:
            self._drawbg(dc, rect, n, selected)
        except AttributeError:
            pass

    def OnMeasureItem(self, n):
        try:
            measure = self._measure
        except AttributeError:
            return 20
        else:
            return measure(n)

    def _OnLeftDown(self, e):
        'Makes clicking a blank area of the list deselect.'

        e.Skip()
        i = self.HitTest((e.GetX(), e.GetY()))
        if i == -1:
            self.SetSelection(-1)


class RoomListModel(EventMixin):
    events = set((
        'contacts_changed',
    ))

    def __init__(self, contacts):
        EventMixin.__init__(self)
        self.contacts = None
        self.offline = False
        self.set_contacts(contacts)

    def _init_contacts(self):
        self.contacts_view = []
        self.contact_enter_times = {}
        self.contact_leave_times = {}
        self.pending_contacts = ObservableList()

    def set_contacts(self, contacts):
        if hasattr(self.contacts, 'remove_observer'):
            self.contacts.remove_observer(self._on_contacts_changed)

        self.contacts = contacts
        self._init_contacts()
        for contact in contacts:
            self.contact_enter_times[contact] = 0

        if hasattr(self.contacts, 'add_observer'):
            self.contacts.add_observer(self._on_contacts_changed)

        self._on_contacts_changed()

    def _on_contacts_changed(self, *a, **k):
        self._update_pending()
        self._update_view()
        self.fire_contacts_changed()

    def fire_contacts_changed(self):
        self.event('contacts_changed')

    TIME_LEAVING = 4

    def _update_view(self):
        self.leaving_contacts = view = []
        now = time()
        for gone_contact, t in list(self.contact_leave_times.items()):
            if now - t > self.TIME_LEAVING:
                self.contact_leave_times.pop(gone_contact, None)
            else: #leaving
                view.append(gone_contact)

        old_length = len(self.contacts_view)
        self.contacts_view = sorted(list(self.contacts) + view)
        return len(self.contacts_view) != old_length

    def _update_pending(self):
        for pending_contact in list(self.pending_contacts):
            for contact in self.contacts:
                if pending_contact.equals_chat_buddy(contact):
                    self.pending_contacts.remove(pending_contact)

        contacts = set(self.contacts)
        now = time()
        for contact in list(self.contact_enter_times.keys()):
            if contact not in contacts:
                self.contact_enter_times.pop(contact, None)
                self.contact_leave_times.setdefault(contact, now)

        for contact in contacts:
            if contact not in self.contact_enter_times:
                self.contact_enter_times.setdefault(contact, now)

    def contact_is_new(self, contact):
        time_joined = self.contact_enter_times.get(contact, None)
        if time_joined is None:
            return False
        TIME_NEW = 2
        now = time()
        return now - time_joined < TIME_NEW

    def contact_is_leaving(self, contact):
        time_left = self.contact_leave_times.get(contact, None)
        return time_left is not None and time() - time_left < self.TIME_LEAVING

    def add_pending_contact(self, contact):
        if contact not in self.pending_contacts:
            self.pending_contacts.append(contact)
            self.event('contacts_changed')
            return True

    def remove_pending_contact(self, contact):
        try:
            self.pending_contacts.remove(contact)
        except ValueError:
            return False
        else:
            self.event('contacts_changed')
            return True

    @property
    def length_including_pending(self):
        return self.length + len(self.pending_contacts)

    @property
    def length(self):
        return len(self.contacts_view)

    def get_contact(self, n): return self.contacts_view[n]

    def get_pending_contact(self, n): return self.pending_contacts[n]

class ContactListCtrl(SkinVListBox):
    'Shows contacts and their status icons in a list.'

    click_raises_imwin = True

    def __init__(self, parent, model):
        SkinVListBox.__init__(self, parent, style=wx.LB_MULTIPLE)
        self.model = model
        self.show_pending = True
        self.model.bind_event('contacts_changed', lambda * a, **k: wx.CallAfter(self.update_count))
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_left_dclick)

        self.contact_timer = wx.PyTimer(self._on_contact_timer)
        self.UpdateSkin()

    def _on_contact_timer(self):
        if wx.IsDestroyed(self):
            return
        if self.model._update_view():
            self.update_count()
        self.Refresh()

    def UpdateSkin(self):
        getattr(SkinVListBox, 'UpdateSkin', lambda self: None)(self)

        # "X" remove icon for pending contacts
        self.x_icon = skin.get('appdefaults.removeicon').ResizedSmaller(16).WXB
        self.pad_x = 2

    def _on_left_down(self, e):
        i = self.HitTest(e.Position)
        if i != -1:
            info = self._contact(i)
            if info.pending:
                if e.Position.x > self.Size.width - self.x_icon.Width - self.pad_x * 2:
                    self.model.remove_pending_contact(info.contact)
        e.Skip()

    def _on_left_dclick(self, e):
        i = self.HitTest(e.Position)
        if i == -1:
            return e.Skip()

        chat_buddy = self.model.get_contact(i)
        if hasattr(chat_buddy, 'private_message_buddy'):
            chat_buddy = chat_buddy.private_message_buddy()

        gui.imwin.begin_conversation(chat_buddy)

    def _on_motion(self, e):
        e.Skip()
        i = self.HitTest(e.Position)
        if i == -1:
            tip = None
        else:
            tip = self._contact_str(i)

        update_tooltip(self, tip)

    def SetContacts(self, contacts):
        self.model.set_contacts(contacts)

    def update_count(self):
        if wx.IsDestroyed(self):
            print 'error: update_count still being called'
        else:
            if self.model.offline:
                count = 0
            elif self.show_pending:
                count = self.model.length_including_pending
            else:
                count = self.model.length

            self.SetItemCount(count)
            self.RefreshAll()

    iconsize = 16
    padding = 3

    def _contact(self, n):
        try:
            contact = self.model.get_contact(n)
            icon = get_buddy_icon(contact, self.iconsize, False)
            pending = False
        except IndexError:
            contact = self.model.get_pending_contact(n - self.model.length)
            #TODO: This is not in skin anymore
            icon = None#skin.get('miscicons.smallspinner')
            pending = True

        leaving = self.model.contact_is_leaving(contact)

        return S(contact=contact, icon=icon, pending=pending, leaving=leaving)

    def _contact_str(self, n):
        return contact_display_str(self._contact(n).contact)

    def _draw(self, dc, rect, n, selected):
        _contact = self._contact(n)
        contact, icon = _contact.contact, _contact.icon
        contact_str = self._contact_str(n)

        # draw icon
        rect.Subtract(left=self.padding)
        if icon:
            dc.DrawBitmap(icon, rect.X, rect.Y + (rect.Height / 2 - icon.Size.height / 2))

        # draw buddy name text
        rect.Subtract(left=self.iconsize + self.padding)

        bold = not _contact.pending and self.model.contact_is_new(contact)
        if (bold or _contact.leaving) and not self.contact_timer.IsRunning():
            self.contact_timer.StartOneShot(1000)

        f = dc.Font
        if not _contact.pending:
            color = wx.BLACK if not _contact.leaving else wx.Colour(128, 128, 128)
            f.SetStyle(wx.FONTSTYLE_NORMAL)
        else:
            color = wx.Colour(128, 128, 128)
            f.SetStyle(wx.FONTSTYLE_ITALIC)
            rect.width -= self.x_icon.Width + self.pad_x * 2

        f.SetWeight(wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL)
        dc.Font = f

        dc.SetTextForeground(color)
        dc.DrawTruncatedText(contact_str, rect, wx.ALIGN_CENTER_VERTICAL)

        if _contact.pending:
            dc.DrawBitmap(self.x_icon, rect.Right + self.pad_x, rect.Top + (rect.Height / 2 - self.x_icon.Height / 2))

    def _measure(self, n):
        return 22 #TODO: fontsize

    def OnGetItemImage(self, item):
        return item

from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.simplemenu import SimpleMenuItem

def item_for_contact(contact):
    alias, name = contact.alias, contact.name

    icon = skin.get('statusicons.' + contact.status_orb)

    if alias == name:
        smi = SimpleMenuItem([icon, name])
    else:
        smi = SimpleMenuItem([icon, "%s (%s)" % (alias, name)])

    smi.buddy = contact
    return smi


class ContactCombo(UberCombo):
    def __init__(self, parent,
                 skinkey=None,
                 contacts=None,
                 inviteCallback=None,
                 accountCallback=None,
                 model=None,
                 use_confirm_dialog=True):

        if skinkey is None:
            skinkey = skin.get('RoomListComboSkin')

        UberCombo.__init__(self, parent, typeable=True,
                           skinkey=skinkey,
                           editmethod=self.EditField,
                           selectioncallback=self.on_selection,
                           maxmenuheight=10,
                           minmenuwidth=230,
                           empty_text=_('Invite Buddy'))

        self.TextField.Bind(wx.EVT_KEY_DOWN, self.OnKey)

        self.contacts = contacts if contacts is not None else {}
        self.inviteCallback = inviteCallback
        self.accountCallback = accountCallback
        self.model = model
        self.use_confirm_dialog = use_confirm_dialog

        #from util import trace
        #from gui.uberwidgets.simplemenu import SimpleMenu
        #trace(SimpleMenu)

        def EditField():
            if not self.display.txtfld.IsShown():
                self.display.TypeField()

        self.menu.BeforeDisplay += lambda: self.update_menu(self.TextField.Value)
        self.menu.BeforeDisplay += EditField

    def Active(self, active):
        pass

    def buddy_sort(self, c):
        # show online buddies first, alphabetically
        return (-int(c.online), c.alias)

    def OnKey(self, e):
        k = e.GetKeyCode()
        m = self.menu

        if k == wx.WXK_DOWN:
            m.Selection = (m.Selection + 1) % m.Count
        elif k == wx.WXK_UP:
            if m.Selection == -1:
                m.Selection = m.Count - 1
            else:
                m.Selection = (m.Selection - 1) % m.Count
        elif k == wx.WXK_RETURN:
            if m.IsShown() and m.Selection >= 0:
                item = m.GetItem(m.Selection)
                m.Hide()
                m.Selection = -1
                self.on_selection(item)
            else:
                self.on_selection(self.TextField.Value)
                #m.Hide()
                self.GrandParent.SetFocus()
                #self.ShowMenu()

        elif k == wx.WXK_ESCAPE:
            self.TextField.Value = ''
            m.Hide()
        else:
            e.Skip()

    def update_menu(self, val=None):
        m = self.menu
        m.RemoveAll()

        for item in self.get_dropdown_items(val):
            m.AppendItem(item)

        if m.Count:
            m.spine.CalcSize()
            m.Selection = -1
            m.Refresh()
        else:
            m.Selection = -1
            m.Hide()

    def get_dropdown_items(self, prefix=None):
        return [item_for_contact(c) for c in self.get_dropdown_contacts(prefix)]

    def get_dropdown_contacts(self, prefix=None):
        val = prefix.lower() if prefix is not None else ''

        #print '-'*80
        #from pprint import pprint
        #pprint(self.contacts)

        filtered_contacts = []

        contacts_inviting = set(self.model.contacts)
        is_self = lambda b: try_this(lambda: b is b.protocol.self_buddy, False)

        for contact in sorted(self.contacts.itervalues(), key=self.buddy_sort):
            if contact not in contacts_inviting and not is_self(contact) and getattr(contact, 'supports_group_chat', False):
                # search "name" and "alias" fields
                n, a = contact.name.lower(), contact.alias.lower()
                if n.startswith(val) or a.startswith(val):
                    filtered_contacts.append(contact)

        return filtered_contacts

    @property
    def ActiveConnection(self):
        acct = self.accountCallback()
        if acct is not None:
            return getattr(acct, 'connection', None)

    def on_selection(self, item):
        if self.model.offline:
            return

        if isinstance(item, basestring):
            buddy = None
            if item.strip():
                connection = self.ActiveConnection
                if connection is not None:
                    buddy = connection.get_buddy(item)
        else:
            buddy = item.buddy

        if buddy is None:
            return

        if not self.use_confirm_dialog or \
                wx.YES == wx.MessageBox(_('Do you want to invite {name} to this chat?').format(name=contact_display_str(buddy)),
                                   _('Chat Invite'),
                                   wx.YES | wx.NO):

            cb = self.inviteCallback
            if cb is None:
                cb = lambda * a, **k: log.warning('inviteCallback(%r, %r)', a, k)

            if cb(buddy):
                self.SetValue('')

    def EditField(self):
        if self.display.txtfld.IsShown():
            wx.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            self.OpenMenu()


class RoomListPanel(wx.Panel):
    def __init__(self, parent, buddies=None, inviteCallback=None, accountCallback=None):
        wx.Panel.__init__(self, parent)

        self._obs_link = None
        self.roomlist = None
        self.model = RoomListModel([])
        self.list = ContactListCtrl(self, model=self.model)
        self.combo = ContactCombo(self,
                                     contacts=buddies,
                                     inviteCallback=inviteCallback,
                                     accountCallback=accountCallback,
                                     model=self.model)

        s = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        s.Add(self.combo, 0, wx.EXPAND | wx.ALL)
        s.Add(self.list, 1, wx.EXPAND | wx.ALL)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)

    # when the following properties of contacts change, they are updated in
    # the list
    contact_attrs = ('status', 'alias')

    def UpdateSkin(self):
        self.combo.SetSkinKey(skin.get('RoomListComboSkin'))

    def SetConversation(self, convo):
        self.model.offline = False
        self._watch_protocol(convo)

        self.SetRoomList(convo.room_list)
        self.combo.contacts = convo.protocol.buddies
        convo.pending_contacts_callbacks.add(self.on_pending_contacts)
        self.list.show_pending = getattr(convo, 'contact_identities_known', True)

    proto = None

    def _watch_protocol(self, convo):
        if self.proto is not None:
            self.proto.remove_observer(self._on_state_change, 'state')
        self.proto = convo.protocol
        self.proto.add_observer(self._on_state_change, 'state')

    def _on_state_change(self, protocol, attr, old, new):
        offline = self.model.offline
        self.model.offline = new == protocol.Statuses.OFFLINE
        if offline != self.model.offline:
            self.list.update_count()

    def on_pending_contacts(self, contacts):
        added = False
        for c in contacts:
            if c not in self.model.pending_contacts:
                self.model.pending_contacts.append(c)
                added = True

        if added:
            self.model.event('contacts_changed')

    def SetRoomList(self, obslist):
        self.roomlist = obslist
        self.list.SetContacts(obslist)

    RoomList = property(lambda self: self.roomlist,
                        SetRoomList,
                        lambda self: self.SetRoomList(None),
                        "Sets or gets this panel's roomlist.")

    def on_list_changed(self, src, attr, old, new):
        pass

    def on_contact_changed(self, contact, attr, old, new):
        pass

def contact_display_str(contact):
    alias, name = contact.alias, contact.name
    return alias if alias == name else u'%s (%s)' % (alias, name)
