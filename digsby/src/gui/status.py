'''
status message editing GUI
'''

from __future__ import with_statement
from gui.uberwidgets.formattedinput2.formatprefsmixin import StyleFromPref

import wx, sys
from wx import BoxSizer, EXPAND, ALL, LEFT, RIGHT, BOTTOM, TOP

from gui.toolbox import build_button_sizer
from gui import skin

from common.statusmessage import StatusMessage, StatusMessageException, acct_reduce
from common import profile, actions

from gui.uberwidgets.formattedinput2.formattedinput import FormattedInput
from gui.anylists import AnyRow, AnyList
from gui.uberwidgets.umenu import UMenu
from gui.validators import LengthLimit
from cgui import SimplePanel

from util import Storage, removedupes, replace_newlines
from collections import defaultdict
from gui.textutil import default_font

from logging import getLogger; log = getLogger('gui.status'); info = log.info

def new_custom_status(window, save_checkbox = False, init_status=None):
    '''
    Displays the status editor for creating a new custom status.
    '''

    if window is None:
        window = wx.FindWindowByName('Buddy List')

    def onsave(diag):
        status = diag.StatusMessageFromInfo()
        if diag.SaveForLater:
            # only save if the checkbox is checked
            profile.add_status_message(status)

        import hooks; hooks.notify('digsby.statistics.ui.select_status')
        profile.set_status(status)

    # Popup the Status dialog (with a save checkbox!)
    StatusDialog.new(window, save_checkbox = save_checkbox, save_callback = onsave, init_status=init_status)

#
# "digsby" logic for interfacing with the rest of the program
#

def get_account_list():
    'Return the accounts list.'

    return profile.account_manager.accounts

DEFAULT_STATUS_CHOICES = [
    ('Available', _('Available')),
    ('Away',      _('Away'))
]

def get_state_choices(curstatus = None, account = None):
    'Return state choices for all accounts, or just for one.'

    # Status choices come from connected accounts, unless there are none.
    _profile = profile()
    conn  = list(_profile.account_manager.connected_accounts)
    accts = conn
    if accts != [_profile] and _profile in accts:
        accts.remove(_profile)

    # When no accounts are connected, just use sensible defaults.
    if not accts:
        return DEFAULT_STATUS_CHOICES

    # Sort status messages by "category" in the order they appear in the status
    # message lists in protocolmeta.py
    statuses = []
    for acct in (accts if account in (None, False) else [account]):
        if hasattr(acct, 'protocol_info'):
            proto_statuses = acct.protocol_info().get('statuses', [])
            invis = [StatusMessage.Invisible.title]
            if acct.protocol_info().get('has_invisible', False) and invis not in proto_statuses:
                proto_statuses.append(invis)
        else:
            proto_statuses = []

        for cat_i, cat in enumerate(proto_statuses):
            for status_id, status in enumerate(cat):
                for st in cat:
                    statuses += [(cat_i, status_id, st)]
    statuses.sort()

    statuses = removedupes([(s[0], s[2]) for s in statuses])
    status_strings = [(s[1], _(s[1])) for s in statuses]

    # If the status string itself in our accumulated list of statuses, that means
    # it belongs to another protocol. Search for any protocols which have the
    # status, and append an extra status message to the list.

    if curstatus is not None and curstatus not in [c[0] for c in status_strings]:
        # Accumulate Status -> [Acct1, Acct2, ...]
        from common.protocolmeta import protocols
        status_acct_map = defaultdict(list)
        for k, protocol in protocols.iteritems():
            for cat in protocol.get('statuses', []):
                for st in cat:
                    status_acct_map[st].append(protocol.name)

            if protocol.get('has_invisible', False):
                status_acct_map[StatusMessage.Invisible.title].append(protocol.name)

        # add a string like (MSN/ICQ only) to the status
        accounts = sorted(status_acct_map.get(curstatus, []))

        #Translators: Separator when listing multiple accounts, ex: MSN/ICQ only
        account_types = _('/').join(accounts)
        status_strings.append((curstatus, _('{status} ({account_types} Only)').format(status=curstatus, account_types=account_types)))

    return status_strings or DEFAULT_STATUS_CHOICES


#
# GUI
#

status_message_size = (365, 160)


class StatusExceptionRow(AnyRow):
    checkbox_border = 3
    image_offset = (22, 5)
    image_size = (16, 16)

    def __init__(self, parent, data):
        self.account = data
        self.status_msg = parent.exceptions.get(acct_reduce(self.account), None)

        AnyRow.__init__(self, parent = parent, data = data, use_checkbox = True)
        self.text = self.account.name

    def PopulateControls(self, data):
        self.account = self.data = data

        self.text = self.account.name
        self.checkbox.Value = self.status_msg is not None

    @property
    def image(self):
        img = skin.get('serviceicons.%s' % self.account.protocol)
        if self.status_msg is None:
            img = img.Greyed

        return img.Resized(self.image_size)

    def on_edit(self, e):
        self.Parent.CreateOrEdit(self.data)

    def draw_text(self, dc, x, sz):
        '''
        Draws the main text label for this row.
        '''

        status = self.status_msg.status if self.status_msg is not None else None
        message = self.status_msg.message if self.status_msg is not None else None

        dc.Font = self.Font

        DrawExceptionLabels(dc, x, wx.RectS(sz), self.get_text(), _(status), message)

def DrawExceptionLabels(dc, x, rect, accountname, status = None, message = None, isHeader = False, exceptionListWidth = None):

    height = rect.height
    width = rect.width
    paddingx = 5
    alignment = wx.ALIGN_CENTER if isHeader else wx.ALIGN_LEFT

    statuswidth = 60
    sx = (exceptionListWidth if exceptionListWidth is not None else width)/20*9
    accountwidth = sx - paddingx - x
    mx = sx + statuswidth

    dc.SetPen(wx.Pen(wx.Color(200, 200, 200)))
    dc.DrawLine(sx, 0, sx, height)
    dc.DrawLine(mx, 0, mx, height)
    dc.DrawLine(0, height-1, width, height-1)

    dc.TextForeground = wx.BLACK #syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT if self.IsSelected() else wx.SYS_COLOUR_WINDOWTEXT)

    labelheight = height - dc.Font.Descent/2

    accountrect = wx.Rect(x, 0, accountwidth, labelheight)
    dc.DrawTruncatedText(accountname, accountrect, alignment | wx.ALIGN_CENTER_VERTICAL)

    if status is not None and status != "None":
        x = sx + paddingx

        statusrect = wx.Rect(x, 0, statuswidth - 2*paddingx, labelheight)
        dc.DrawTruncatedText(status, statusrect, wx.ALIGN_CENTER | wx.ALIGN_CENTER_VERTICAL)

    if message is not None:
        x = mx + paddingx

        messagerect = wx.Rect(x, 0, width - x - paddingx, labelheight)
        dc.DrawTruncatedText(replace_newlines(message), messagerect, alignment | wx.ALIGN_CENTER_VERTICAL)


class StatusExceptionList(AnyList):
    size = (360,150)
    def __init__(self, parent, statussource, exceptions, edit_buttons = None):

        self.statussource = statussource

        self.accounts = get_account_list()
        self.exceptions = exceptions
        AnyList.__init__(self, parent, data = self.accounts,
                         row_control = StatusExceptionRow, edit_buttons = edit_buttons, draggable_items = False)

        self.show_selected = False
        Bind = self.Bind
        Bind(wx.EVT_LISTBOX_DCLICK, self.on_doubleclick)
        Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_hover_changed)
        Bind(wx.EVT_CHECKBOX, self.on_check)

        self.SetMinSize(self.size)

    def on_check(self, e):
        row = self.GetRow(e.Int)
        if row.checkbox.Value:
            self.CreateOrEdit(row.data, row.checkbox)
        else:
            row.status_msg = None
            self.OnDelete(row.data)


        print self.exceptions

    def on_hover_changed(self, e):
        row = self.GetRow(e.Int)

        if not row:
            return

        row.Layout()
        row.Refresh()

    def on_doubleclick(self, e):
        self.CreateOrEdit(self.GetDataObject(e.Int))

    def OnDelete(self, data):
        self.exceptions.pop(acct_reduce(data), None)
        self.update_data(self.exceptions)
        self.Refresh()

    def CreateOrEdit(self, row_data, checkbox = None):
        'Create or edit an exception for the account.'

        account = row_data
        accountstr = acct_reduce(account)

        # If SAVE is clicked, update this control's exception list.

        # Is there already an exception here?
        if accountstr in self.exceptions:
            diag = StatusDialog.edit(self, self.exceptions[accountstr], is_exception = account,
                                     modal = True)
        else:
            # No, create one.
            diag = StatusDialog.new(self, is_exception = account,
                                    modal = True)

        with diag:
            returncode = diag.ReturnCode
            if returncode == wx.ID_SAVE:
                exception = StatusMessageException(**diag.info())
                self.exceptions[accountstr] = exception
            elif checkbox != None and returncode == wx.ID_CANCEL:
                checkbox.Value = False
                self.OnDelete(row_data)



        self.update_data(self.exceptions)

        self.Refresh()

        return returncode

    on_edit = CreateOrEdit

    def update_data(self, exceptions):
        'Given {account: exception}, update the table.'

        for i, account in enumerate(self.accounts):
            row = self.GetRow(i)
            if row is None:
                continue

            exception_msg = exceptions.get(acct_reduce(row.account), None)
            if exception_msg is not None:
                row.status_msg = exception_msg


            row.PopulateControls(account)

        self.Layout()

    @property
    def Exceptions(self):
        'Returns exceptions which are checked.'

        excs = []
        for i, acct in enumerate(self.accounts):
            acctstr = acct_reduce(acct)
            if self.exceptions.get(acctstr, None) is not None:
                excs.append((acctstr, self.exceptions[acctstr]))
        return dict(excs)

class OutlinePanel(SimplePanel):
    def __init__(self, parent):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.contentSizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.contentSizer, 1, wx.EXPAND|wx.ALL, 1)

        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def AddControl(self, control, scale = 0, flags=wx.EXPAND):
        self.contentSizer.Add(control, scale, flags)

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.Pen(wx.Color(200, 200, 200)))
        dc.DrawRectangleRect(rect)

class StatusExceptionPanel(OutlinePanel):
    def __init__(self, parent):
        OutlinePanel.__init__(self, parent)

    def SetExceptionList(self, excpetionlist):
        self.header = StatusExceptionHeader(self, excpetionlist)
        self.contentSizer.Add(self.header, 0, wx.EXPAND)
        self.contentSizer.Add(excpetionlist, 0, wx.EXPAND)



class StatusExceptionHeader(SimplePanel):
    def __init__(self, parent, excpetionlist):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        self.Font = default_font()

        self.exceptionlist = excpetionlist
        self.MinSize = (-1, self.Font.Height + 10 + self.Font.Descent)
        self.Bind(wx.EVT_PAINT, self.OnPaint)


    def OnPaint(self, event):


        dc = wx.AutoBufferedPaintDC(self)
        dc.Font = self.Font

        rect = wx.RectS(self.Size)

        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.DrawRectangleRect(rect)

        DrawExceptionLabels(dc, 5, rect, _("Account"), _("Status"), _("Message"), True, self.exceptionlist.ClientSize.width)

class StatusChoice(wx.Choice):
    def __init__(self, parent, choices):
        assert isinstance(choices, list) and (isinstance(choices[0], tuple) if len(choices) > 0 else True)
        self.choices = dict(choices)
        self.choices_indicies = dict((i, choice[0]) for i, choice in enumerate(choices))
        wx.Choice.__init__(self, parent, id=-1, choices = [_(c[1]) for c in choices])
        self.Bind(wx.EVT_CHOICE, self.on_choice)

    def SetStatus(self, choice):
        try:
            self.SetStringSelection(self.choices[choice])
        except KeyError:
            choice = self.GetStringSelection()

        self.db_val = choice

    def on_choice(self, e):
        # i -> choice
        self.db_val = self.choices_indicies[self.GetSelection()]

class StatusPanel(wx.Panel):
    '''
    Fields for entering a status message, which include:

    - a title
    - a message
    - optional exceptions for each account
    '''

    def __init__(self, parent, status_message = None, is_exception = False, save_checkbox = False):
        wx.Panel.__init__(self, parent)

        self.save_checkbox = save_checkbox        # True if this dialog needs a "Save" checkbox
        self.is_exception = is_exception          # Is this status dialog editing an exception?
        self.status_message = status_message      # the current status object
        self.title_edited = False                 # has the title text control been edited yet?

        self.construct(is_exception, status_message)
        if status_message is not None:
            self.populate_controls(status_message)
        self.layout(is_exception)

        self.Fit()

    def info(self):
        # Allows all text fields in this dialog to be optional.
        #
        # If "title" isn't specified but message is, then title becomes
        # the first line of message.
        #
        # If message is blank and title is not, message becomes title.
        #
        # If both are blank, both become the status.
        #
        status = self.status.db_val

        if not self.is_exception:
            title = self.title.Value
            if not title or title.isspace():
                title = None

        message = self.message.Value
        if not message or message.isspace(): message = None

        if not self.is_exception:
            if title is None:
                title = message.split('\n')[0] if message is not None else status
        else:
            title = None

        if message is None:
            message = title if title is not None else _(status)

        s = Storage(message = message,
                    status = status,
                    format  = self.message.Format)

        if not self.is_exception:
            # while editing exceptions, there isn't a title.
            s.title = title
            s.exceptions = self.exceptions.Exceptions if self.diffcheck.IsChecked() else {}

        from pprint import pformat
        log.info(pformat(dict(s)))

        return s

    def show_exceptions(self, show = True):
        'Shows or hides the exceptions list at the bottom of the dialog.'

        with self.Frozen():
            if self.exceptionspanel.Show(show):
                self.Top.FitInScreen()

    def on_message_text(self, e):
        e.Skip()
        if not self.title_edited:
            # the ChangeValue function does not emit EVT_TEXT

            # skip leading whitespace
            msg = self.message.Value.lstrip()

            # find all text up to the first newline
            newline = msg.find('\n')
            if newline == -1: newline = len(msg)

            self.title.ChangeValue( msg[:newline] )

    def populate_controls(self, status_message = None):
        for key in ('title', 'message'):
            if hasattr(self, key):
                getattr(self, key).Value = getattr(status_message, key)

        # Online, Away, Out to Luncg, etc...
        self.status.SetStatus(status_message.status)


    def construct(self, is_exception, status_message = None):

        if not is_exception:
            self.title_label = wx.StaticText(self, -1, _('&Title:'))
            self.title = t   = wx.TextCtrl(self, -1, '', size=(340,-1), validator=LengthLimit(255))
            t.Bind(wx.EVT_TEXT, lambda e: setattr(self, 'title_edited',
                                                  bool(self.title.Value)))

        self.status_label = wx.StaticText(self, -1, _('&State:'))

        curstatus = self.status_message.status if self.status_message is not None else None
        choices = get_state_choices(curstatus, is_exception)

        self.status = StatusChoice(self, choices)
        self.status.SetStatus('Away')

        self.message_label = wx.StaticText(self, -1, _('&Status message:'))

        self.message_panel = OutlinePanel(self)

        self.message = FormattedInput(self.message_panel, multiFormat = False,
                                      autosize = False,
                                      format = getattr(status_message, 'format', None) or StyleFromPref('messaging.default_style'),
                                      skin = 'AppDefaults.FormattingBar',
                                      validator= LengthLimit(10240),
                                      )
        self.message_panel.AddControl(self.message, 1, wx.EXPAND)

        self.message.SetMinSize(status_message_size)

        if not is_exception:
            self.message.tc.Bind(wx.EVT_TEXT, self.on_message_text)

            msg = self.status_message

            self.exceptionspanel = StatusExceptionPanel(self)
            self.exceptions = StatusExceptionList(self.exceptionspanel, self, status_message.exceptions if status_message else {})
            self.exceptionspanel.SetExceptionList(self.exceptions)

            hasexcs = msg is not None and msg.use_exceptions
            self.exceptionspanel.Show(hasexcs)

            chk = self.diffcheck = wx.CheckBox(self, -1, _('&Use a different status for some accounts'))
            chk.Value = hasexcs
            chk.Bind(wx.EVT_CHECKBOX, lambda e: self.show_exceptions(not self.exceptionspanel.IsShown()))

        s = self.save = wx.Button(self, wx.ID_SAVE, _('&Set') if self.save_checkbox else _('&Save'))
        s.SetDefault()
        s.Bind(wx.EVT_BUTTON, self.on_save)

        c = self.cancel = wx.Button(self, wx.ID_CANCEL, _('&Cancel'))
        c.Bind(wx.EVT_BUTTON, self.on_cancel)

        # Save checkbox
        if self.save_checkbox:
            self.save_check = wx.CheckBox(self, -1, _('Save for &later'))

    def layout(self, is_exception):
        self.Sizer = sz = BoxSizer(wx.VERTICAL)

        # The upper two fields: title text field and state combo box
        inner = wx.FlexGridSizer(2, 2, 6, 6)

        if not is_exception:
            inner.AddMany([ (self.title_label, 0, wx.ALIGN_CENTER_VERTICAL),
                            (self.title) ])
        inner.AddMany([ (self.status_label, 0, wx.ALIGN_CENTER_VERTICAL),
                        (self.status) ])
        inner.AddGrowableCol(1, 1)
        sz.Add(inner, 0, wx.EXPAND | wx.ALL, 8)

        # The label for the message, and the big text area itself
        sz.Add(self.message_label, 0, EXPAND | ALL,            8)
        h = wx.BoxSizer(wx.HORIZONTAL)
        h.Add((1,status_message_size[1]))
        h.Add(self.message_panel,       1, EXPAND)
        sz.Add(h, 1, EXPAND | RIGHT | LEFT, 15)
        #sz.Add(self.message)

        sz.AddSpacer(3)

        # Save For Later
        if self.save_checkbox: sz.Add(self.save_check, 0, EXPAND | TOP | LEFT, 8)

        if not is_exception:
            # The checkbox to expand the dialog
            sz.Add(self.diffcheck,  0, EXPAND | ALL, 8)

            # Status exceptions
            sz.Add(self.exceptionspanel, 0, EXPAND | RIGHT | LEFT | BOTTOM, 8)

        # Save/Cancel
        sz.Add(build_button_sizer(save=self.save, cancel=self.cancel), 0, EXPAND | BOTTOM | RIGHT | LEFT, 4)

    def on_cancel(self,e):
        self.Parent.Cancel()

    def on_save(self, e):
        self.Parent.Save()

    @property
    def SaveForLater(self):
        return hasattr(self, 'save_check') and self.save_check.IsChecked()

class StatusDialog(wx.Dialog):

    minsize = (290, 290)

    @classmethod
    def new(cls, parent, is_exception = False, save_checkbox = False,
            save_callback = None, modal = False, init_status=None):
        if not modal and cls.raise_existing():
            return

        if not is_exception: title = _('New Status Message')
        else:                title = _('New Status for {name}').format(name=getattr(is_exception, 'name', is_exception))

        if parent:
            parent = parent.Top

        diag = StatusDialog(parent, status_message = init_status, title = title, is_exception = is_exception,
                            save_checkbox = save_checkbox)

        if is_exception and parent:
            diag.CenterOnParent()

        if not modal:
            diag.Prompt(save_callback)
        else:
            diag.ShowModal()
            return diag

    @classmethod
    def edit(cls, parent, status_message, is_exception = False,
             save_callback = None, modal = False):

        if not modal and cls.raise_existing():
            return

        if not is_exception:
            title = _('Edit Status Message')
        else:
            account_str = u'{0} ({1})'.format(is_exception.username, is_exception.protocol)
            title = _('Edit Status for {account}').format(account=account_str)

        diag = StatusDialog(parent, status_message, title = title, is_exception = is_exception)
        if not modal:
            diag.Prompt(save_callback)
        else:
            diag.ShowModal()
            return diag

    @classmethod
    def raise_existing(cls):
        for win in reversed(wx.GetTopLevelWindows()):
            if isinstance(win, StatusDialog):
                win.Show()
                win.Raise()
                return True


    def StatusMessageFromInfo(self):
        "Builds a StatusMessage object from this dialog's fields."
        return StatusMessage(**self.info())

    def __init__(self, parent, status_message = None, pos=(400,200),
                 title='Status Message', is_exception = False, save_checkbox = False):
        wx.Dialog.__init__(self, parent, title=title, pos=(400,200),
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)
        self.statuspanel = panel = StatusPanel(self, status_message, is_exception, save_checkbox)
        panel.message.SetFocus()
        s.Add(panel, 1, wx.EXPAND)

        self.Fit()
        self.SetMinSize(self.Size)

        self.Bind(wx.EVT_CLOSE,self.OnClose)

    def Save(self):
        self.SetReturnCode(wx.ID_SAVE)
        if hasattr(self, 'save_callback'):
            self.save_callback(self)
        self.Close()

    def Cancel(self):
        self.SetReturnCode(wx.ID_CANCEL)
        self.Close()


    def OnClose(self,event):
        if self.IsModal():
            self.EndModal(self.ReturnCode)
        else:
            self.Destroy()

    def Prompt(self, save_callback):
        if not hasattr(save_callback, '__call__'):
            raise TypeError('Prompt takes a callable which will be called when the dialog goes away.')

        self.save_callback = save_callback
        self.Show()

    def info(self):
        return self.statuspanel.info()

    @property
    def SaveForLater(self):
        return self.statuspanel.SaveForLater

# ----------------



class StatusRow(AnyRow):

    checkbox_border = 3
    image_offset = (6, 5)

    def __init__(self, parent, status_message):
        AnyRow.__init__(self, parent, status_message, use_checkbox = False)

    def PopulateControls(self, status):
        self.text = status.title

    @property
    def image(self):
        statusmsg = self.data
        return skin.get('statusicons.%s' % ('away' if statusmsg.away else 'available'))

    @property
    def popup(self):
        if hasattr(self, '_menu') and self._menu: self._menu.Destroy()
        menu = UMenu(self)

        menu.AddItem(_('&Edit'),   callback = lambda: self.on_edit())
        menu.AddItem(_('&Remove'), callback = lambda: self.on_delete())

        menu.AddSep()
        actions.menu(self, self.data, menu)

        self._menu = menu
        return menu

    def ConstructMore(self):

        # Extra component--the edit hyperlink
        edit = self.edit = wx.HyperlinkCtrl(self, -1, _('Edit'), '#')
        edit.Hide()
        edit.Bind(wx.EVT_HYPERLINK, lambda e: self.on_edit())

        remove = self.remove = wx.HyperlinkCtrl(self, -1, _('Delete'), '#')
        remove.Hide()
        remove.Bind(wx.EVT_HYPERLINK, lambda e: self.on_delete())

        edit.HoverColour = edit.VisitedColour = edit.ForegroundColour
        remove.HoverColour = remove.VisitedColour = remove.ForegroundColour

    def LayoutMore(self, sizer):
        sizer.AddStretchSpacer()
        sizer.Add(self.edit, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
        sizer.Add(self.remove, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)


class StatusList(AnyList):
    'Status messages list.'

    def __init__(self, parent, status_messages, edit_buttons = None):
        AnyList.__init__(self, parent, status_messages,
                         row_control = StatusRow, edit_buttons = edit_buttons)

        self.show_selected = False

        Bind = self.Bind
        Bind(wx.EVT_LISTBOX_DCLICK, self.on_doubleclick)
        Bind(wx.EVT_LIST_ITEM_FOCUSED,self.OnHoveredChanged)

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

    def on_doubleclick(self, e):
        self.on_edit(self.GetDataObject(e.Int))

    def OnDelete(self, msg):
        'Called when the minus button above this list is clicked.'

        if not msg: return

        # Display a confirmation dialog.
        message = _('Are you sure you want to delete status message "{title}"?').format(title=msg.title)
        caption = _('Delete Status Message')
        style   = wx.ICON_QUESTION | wx.YES_NO
        parent  = self

        # shift bypasses confirm dialog on dev.
        dev_and_shift = getattr(sys, 'DEV', False) and wx.GetKeyState(wx.WXK_SHIFT)

        if dev_and_shift or wx.MessageBox(message, caption, style, parent) == wx.YES:
            profile.remove_status_message(msg)
            self.Refresh()

    def on_edit(self, status_message):
        def onsave(diag):
            status_message.__setstate__(diag.info())
            status_message.notify()
            self.Refresh()

        print status_message
        StatusDialog.edit(self, status_message, save_callback = onsave)

    def OnNew(self, e = None):
        'Called when the plus button above this list is clicked.'

        self.add_status_message()

    def add_status_message(self):
        StatusDialog.new(self, save_callback = lambda diag: profile.add_status_message(**diag.info()))

if __name__ == '__main__':
    from tests.testapp import testapp
    from gui import skin
    app = testapp('../..')
    StatusDialog(None).ShowModal()
