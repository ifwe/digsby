'''
GUI for editing contacts, metacontacts.
'''

from __future__ import with_statement
import wx
from wx import VERTICAL, HORIZONTAL, ALIGN_CENTER_HORIZONTAL, EXPAND, ALL, LEFT, RIGHT, TOP, BOTTOM,ALIGN_CENTER_VERTICAL,ALIGN_LEFT
TOPLESS = ALL & ~TOP

from gui.visuallisteditor import VisualListEditorList

from gui.toolbox import build_button_sizer, wx_prop
from gui.textutil import CopyFont
from gui.validators import LengthLimit
from util import Storage as S
from logging import getLogger; log =getLogger('contactdialogs'); info = log.info
from common import profile
from gettext import ngettext

REQUIRE_ALIAS = True

def get_profile():
    from common import profile
    return profile

def contact_string(c):
    return '%s (%s)' % (c.name, c.protocol.name)

def account_string(a):
    return '%s (%s)' % (a.name, a.protocol)

def send_files(parent, buddy, files):
    '''
    parent   wxWindow parent
    buddy    buddy to call send_files on
    files    a list of file paths
    '''
    msg = ngettext(u'Would you like to send "{files[0]}" to {buddy_name:s}?',
                   u'Would you like to send {num_files:d} files to {buddy_name:s}?',
                   len(files)).format(files=files, num_files=len(files), buddy_name=buddy.name)

    if wx.YES == wx.MessageBox(msg, _('Send Files'), style = wx.YES_NO, parent = parent):
        for filename in files:
            buddy.send_file(filename)

class ContactPanel(wx.Panel):
    'GUI for adding a contact.'

    def __init__(self, parent, to_group = None):
        wx.Panel.__init__(self, parent)

        self.construct()
        self.layout()

        # Listen for changes to the connected accounts list.
        from common import profile
        profile.account_manager.connected_accounts.add_observer(self.on_conns_changed)
        self.on_conns_changed(profile.account_manager.connected_accounts, to_group)

    def on_close(self):
        profile.account_manager.connected_accounts.remove_observer(self.on_conns_changed)

    def on_conns_changed(self, connected_accounts, *a):
        'Updates the accounts choice.'

        choice = self.acct_choice
        sel = choice.GetStringSelection()

        with choice.Frozen():
            choice.Clear()
            for acct in connected_accounts:
                proto_str = account_string(acct)
                choice.Append(proto_str)

        choice.SetStringSelection(sel) if sel else choice.SetSelection(0)

    def construct(self):

        self.name_st = wx.StaticText(self, -1, _('Contact &Name:'))
        self.name_txt = wx.TextCtrl(self, -1, validator=LengthLimit(255))

        self.acct_st = wx.StaticText(self, -1, _('Accoun&t:'))
        self.acct_choice = wx.Choice(self, -1)

        self.get_acct = lambda: get_profile().account_manager.connected_accounts[self.acct_choice.Selection]

        # Add and Cancel buttons
        self.save = wx.Button(self, wx.ID_SAVE, _('&Add'))
        self.save.SetDefault()
        self.save.Bind(wx.EVT_BUTTON, self.Parent.on_save)

        self.cancel = wx.Button(self, wx.ID_CANCEL, _('&Cancel'))

    name = wx_prop('name_txt')

    def get_info(self):
        return S(name = self.name,
                 account = self.get_acct())

    def layout(self):
        self.Sizer = sz = wx.BoxSizer(wx.VERTICAL)

        sz.Add(self.name_st, 0, wx.EXPAND | wx.ALL, 5)
        sz.Add(self.name_txt, 0, wx.EXPAND | wx.ALL, 5)

        sz.Add((0,5))

        sz.Add(self.acct_st, 0, wx.EXPAND | wx.ALL, 5)
        sz.Add(self.acct_choice, 0, wx.EXPAND | wx.ALL, 5)

        # Add/Cancel
        sz.Add(build_button_sizer(save=self.save, cancel=self.cancel),
               0, wx.EXPAND | wx.SOUTH | wx.EAST | wx.WEST, 4)


class MetaListEditor(VisualListEditorList):
    def __init__(self, parent, list2sort, listcallback = None):
        VisualListEditorList.__init__(self, parent, list2sort, listcallback = listcallback)

    def OnDrawItem(self,dc,rect,n):

        dc.Font=self.Font

        buddy = self.thelist[n]

        icon = buddy.buddy_icon.Resized(16)
        serv = buddy.serviceicon.Resized(16)

        x = rect.x + 3
        y = rect.y + 3

        textrect = wx.Rect(x + 16 + 3,rect.y,rect.Width - x - 38,rect.Height)

        dc.DrawLabel(buddy.name,textrect,ALIGN_CENTER_VERTICAL|ALIGN_LEFT)

        dc.DrawBitmap(icon,x,y,True)



        dc.DrawBitmap(serv,rect.x + rect.Width - 16 - 3,y,True)

class MetaContactPanel(wx.Panel):
    'GUI for creating or appending to a metacontact.'

    def __init__(self, parent, contacts = [], metacontact = None, order = None):
        wx.Panel.__init__(self, parent)

        self.contacts = contacts
        self.metacontact = metacontact
        self.order = order

        self.construct()
        self.layout()

    def construct(self):

        Text = lambda s: wx.StaticText(self,-1,_(s))

        self.line1 = Text(_('Would you like to merge these contacts?'))
        self.line1.Font = CopyFont(self.line1.Font,weight = wx.BOLD)

        self.line2 = Text(_('They will appear as one item on your buddy list.'))
        self.sep   = wx.StaticLine(self,-1)

        self.alias_label = wx.StaticText(self, -1, _('Alias:'))
        self.alias_label.Font = CopyFont(self.alias_label.Font,weight = wx.BOLD)

        # Decide on an alias: don't use the alias property from the metacontact
        # because that falls through to the best available one.
        alias = self.find_alias_suggestion()
        self.alias_text = wx.TextCtrl(self, -1, alias if alias else '', validator=LengthLimit(255))

        s = self.save = wx.Button(self, wx.ID_SAVE, _('&Save'))    # save
        s.SetDefault()
        s.Bind(wx.EVT_BUTTON, self.Parent.on_save)

        if REQUIRE_ALIAS:
            self.alias_text.Bind(wx.EVT_TEXT, lambda e: self.save.Enable(self.alias_text.Value!=''))
            self.save.Enable(self.alias_text.Value != '')

        self.cancel = wx.Button(self, wx.ID_CANCEL, _('&Cancel'))  # cancel

        self.line4 = Text(_('Drag and drop to rearrange:'))
        self.line4.Font = CopyFont(self.line4.Font,weight = wx.BOLD)
        self.contacts_list = MetaListEditor(self,self.contacts,self.update_contacts_list)


    def find_alias_suggestion(self):
        'Returns a suggestion for the alias for this metacontact.'

        if self.metacontact:
            # Is this already a metacontact? If so, it already has an alias:
            # use that.
            return self.metacontact.alias

        # Otherwise use the first available alias.
        for contact in self.contacts:
            a = profile.get_contact_info(contact, 'alias')
            if a: return a

        # No suggestion.
        return ''


    def update_contacts_list(self,contacts):
        self.contacts = contacts

    def layout(self):
        self.Sizer = sz = wx.BoxSizer(VERTICAL)

        h1 = wx.BoxSizer(VERTICAL)
        h1.Add(self.line1,0,ALIGN_CENTER_HORIZONTAL)
        h1.Add(self.line2,0,ALIGN_CENTER_HORIZONTAL|TOP,3)
        h1.Add(self.sep,0,EXPAND|TOP,6)
        h1.Add(self.alias_label,0,TOP,6)
        h1.Add(self.alias_text,0,EXPAND|TOP,3)

        h1.Add(self.line4,0,TOP,6)
        h1.Add(self.contacts_list,1, EXPAND|TOP,3)

        sz.Add(h1, 1, EXPAND|ALL,6)
        # Save/Cancel
        sz.Add(build_button_sizer(save=self.save, cancel=self.cancel),
               0, EXPAND | TOPLESS, 4)

    def commit(self):
        'Commits changes.'

        blist = get_profile().blist
        mcs = blist.metacontacts

        if self.metacontact:
            self.metacontact.rename(self.alias)
            mcs.edit(self.metacontact, self.contacts, grouppath = self.metacontact.mcinfo.groups)
            return self.metacontact
        else:
            meta = mcs.create(self.alias, self.contacts, update = False)
            meta = mcs.metacontact_objs[meta]
            if self.order is not None:
                order = [(c if c != '__meta__' else meta) for c in self.order]
                blist.rearrange(*order)
            return meta





    alias = wx_prop('alias_text')

class ContactDialog(wx.Dialog):

    def __init__(self, parent, to_group = None):
        wx.Dialog.__init__(self, parent, title = _('Add Contact'))
        self.contact_panel = ContactPanel(self, to_group)
        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)
        s.Add(self.contact_panel, 1, wx.EXPAND)
        self.Fit()

        self.contact_panel.name_txt.SetFocus()
        self.Centre()

    def Prompt(self, callback):
        try:
            if wx.ID_SAVE == self.ShowModal():
                callback(**self.contact_panel.get_info())
        finally:
            self.contact_panel.on_close()
            self.Destroy()

    def on_save(self, e):
        self.SetReturnCode(wx.ID_SAVE)
        if self.IsModal():
            self.EndModal(wx.ID_SAVE)

class MetaContactDialog(wx.Dialog):

    minsize = (290, 290)

    def __init__(self, parent, contacts, metacontact = None, title=None, order = None):
        wx.Dialog.__init__(self, parent, title=title or _('Merge Contacts'), pos=(400,200),
                           style = wx.DEFAULT_DIALOG_STYLE)
        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)
        self.mc_panel = panel = MetaContactPanel(self, contacts, metacontact, order = order)
        s.Add(panel, 1, wx.EXPAND)
#        self.SetMinSize(self.minsize)
#        self.Layout()
        self.Fit()


    @classmethod
    def add_contact(cls, parent, metacontact, contact, position = -1):
        'Creates and returns a dialog for adding a contact to a MetaContact.'

        from contacts.metacontacts import MetaContact
        if not isinstance(metacontact, MetaContact):
            raise TypeError('parent (wxWindow), metacontact (MetaContact), '
                            'contact (Contact), [position (-1 < p < '
                            'len(metacontact))')

        # Append the contact. (position -1 means at the end)
        contacts = list(metacontact)
        if position < 0: contacts.append(contact)
        else:            contacts.insert(position, contact)

        info('contact order for dialog: %r', contacts)

        title = _('Merge Contacts')
        return cls(parent, contacts, metacontact, title = title)

    def on_save(self, e):
        self.SetReturnCode(wx.ID_SAVE)
        if self.IsModal():
            self.EndModal(wx.ID_SAVE)

    def get_info(self):
        return self.mc_panel.get_info()

    def Prompt(self, ondone = None):
        if wx.ID_SAVE == self.ShowModal():
            result = self.mc_panel.commit()
            if ondone: ondone(result)


