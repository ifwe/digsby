from common import pref
from gui.textutil import default_font
if __name__ == '__main__':
    import Digsby
    __builtins__._ = lambda s:s

from gui.uberwidgets.umenu import UMenu

import logging

import weakref
import os.path
import wx
import util
import util.net as net
import util.callbacks as callbacks
import common
import gui.anylists
import gui.accountslist
from cgui import InputBox
import gui.spellchecktextctrlmixin as SCTCM
import gui.toolbox

_BORDER = 3

log = logging.getLogger('gui.socialstatus')

_msg_color_thresholds = (
                         (129, (0x00, 0x00, 0x00)),
                         (140, (0xD8, 0x80, 0x00)),
                         (141, (0xFF, 0x00, 0x00)),
                         )

def acct_name_to_key(proto, name):
    return '%r // %r' % (proto, name)

class ParentHasControllerMixin(object):
    def get_controller(self):
        p = self
        c = getattr(self, 'controller', None)

        while p is not None and c is None:
            p = p.Parent
            c = getattr(p, 'controller', None)

        return c

PHCM = ParentHasControllerMixin

class PanelWithController(wx.Panel, PHCM):
    pass

def color_for_message(message, thresholds):
    mlen = len(message)

    low = -1
    for (high, color) in thresholds:
        if low < mlen <= high:
            return color
        low = high

    return color

ID_REDO = wx.NewId()
class SpellcheckedTextCtrl(InputBox, SCTCM.SpellCheckTextCtrlMixin):
    def __init__(self, parent,
                       id = wx.ID_ANY,
                       value = '',
                       pos = wx.DefaultPosition,
                       size = wx.DefaultSize,
                       style = 0,
                       validator = wx.DefaultValidator):

        InputBox.__init__(self, parent, id, value, pos, size, style, validator)
        SCTCM.SpellCheckTextCtrlMixin.__init__(self)

        self.SetStyle(0, self.LastPosition, wx.TextAttr(wx.BLACK, wx.WHITE, default_font())) #@UndefinedVariable

        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

        gui.toolbox.add_shortened_url_tooltips(self)

        import hooks
        hooks.notify('digsby.status_textctrl.created', self)

    def CanPaste(self):
        # with wx.TE_RICH2 on windows, CanPaste() only returns True (and therefore sends EVT_TEXT_PASTE)
        # when there's text in the clipboard, but we want to be able to paste images.
        return True

    def OnContextMenu(self, event):
        menu = UMenu(self)
        gui.toolbox.maybe_add_shorten_link(self, menu)
        self.AddSuggestionsToMenu(menu)
        gui.toolbox.std_textctrl_menu(self, menu)
        menu.PopupMenu()


class SetIMStatusEntry(object):
    protocol = 'im-status'
    #protocol = 'fake'
    username = name = 'im-status'
    display_name = _("Set IM Status")
    icon_key = 'icons.SetIMStatus'
    enabled = True

    def __init__(self, profile, editable = True, edit_toggle = True):
        self.profile = profile
        self.editable = editable
        self.edit_toggle = edit_toggle

    @property
    def serviceicon(self):
        return gui.skin.get(self.icon_key)

    @callbacks.callsback
    def SetStatusMessage(self, message, callback = None, **k):
        log.debug('Calling SetStatusMessage: message = %r, editable = %r, edit_toggle = %r', message, self.editable, self.edit_toggle)
        self.profile.SetStatusMessage(message, editable = self.editable, edit_toggle = self.edit_toggle)
        callback.success()

'''

    text_alignment = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL

    def get_icon(self, searchname):
        from gui import skin
        return skin.get('appdefaults.search.icons.' + searchname, None)

    def OnDrawItem(self, dc, rect, n):
        VisualListEditorList.OnDrawItem(self, dc, rect, n)
        icon = self.get_icon(self.GetItem(n).name)
        if icon is None:
            return

        # Draw search favicons on the right side of the list
        dc.DrawBitmap(icon, rect.Right - icon.Width - 32, rect.VCenter(icon), True)

'''

def make_counter_ctrl(parent):
    return wx.StaticText(parent, -1, str(0))

class TextFieldWithCounter(wx.Panel, PHCM):
    def __init__(self, parent, label = None, size = (300, 55), initial_text = '', select_text = False, text_id = None,
                 counter_ctrl=None):
        wx.Panel.__init__(self, parent)
        self._text_id = text_id
        self._select_text = select_text
        self._label_text = label or ''
        self._requested_size = size
        if counter_ctrl is False:
            self.ownscount = False
            self.use_counter = False
            self.charcount = None
        else:
            self.ownscount = counter_ctrl is None
            self.use_counter = True
            self.charcount = counter_ctrl

        self.construct(initial_text)
        self.bind_events()
        self.layout()

        if select_text:
            self.SelectText()

    def bind_events(self):
        self.input.Bind(wx.EVT_KEY_DOWN, self.on_key)

    def on_key(self, e):
        if e.KeyCode == wx.WXK_RETURN and e.GetModifiers() not in (wx.MOD_CONTROL, wx.MOD_SHIFT):
            self.Parent.ProcessEvent(e)
        else:
            e.Skip()

    def get_text_ctrl_class(self):
        wxMSW = 'wxMSW' in wx.PlatformInfo
        if wxMSW:
            return SpellcheckedTextCtrl
        else:
            return wx.TextCtrl

    @property
    def TextCtrl(self):
        return self.input

    def construct(self, initial_text=''):
        if self._label_text:
            self.text_label = wx.StaticText(self, -1, self._label_text)
            self.text_label.SetBold()

        if self.use_counter and self.ownscount:
            self.charcount = make_counter_ctrl(self)

        input = self.input = self.get_text_ctrl_class()(self, self._text_id or -1, initial_text,
                                                        style = wx.TE_MULTILINE
                                                              | wx.TE_AUTO_SCROLL
                                                              | wx.TE_PROCESS_ENTER)
        input.SetSizeHints(self._requested_size)
        input.Bind(wx.EVT_TEXT, self.updated_charcount)
        self.updated_charcount()

        if not self._select_text:
            @wx.CallAfter
            def unselect():
                input.InsertionPoint = input.LastPosition

    def updated_charcount(self, e=None):
        newlen = len(self.GetTextValue())

        if not self.use_counter:
            return

        self.charcount.SetLabel(str(newlen))

        color_tup = color_for_message(self.input.Value, _msg_color_thresholds)
        color = wx.Color(*color_tup)
        self.charcount.SetForegroundColour(color)

        if e is not None:
            e.Skip()
            self.Layout()

    def on_button(self, e):
        if self.url_input.IsShown():
            val = self.url_input.Value
            if not val:
                return self.end_url_input()
            if '://' not in val:
                val = 'http://' + val
            with self.Frozen():
                self.url_input.Enable(False)
                self.ok.Enable(False)
            self.tiny_url(val, success=lambda url:
                          wx.CallAfter(self.tiny_url_success, url), error=lambda *a, **k:
                          wx.CallAfter(self.tiny_url_error, *a, **k))
        else:
            self.on_close(self.info)

    def on_cancel(self, e):
        if e.Id == wx.ID_CANCEL:
            if e.EventObject is self.cancel and self.url_input.IsShown():
                self.end_url_input()
            else:
                self.on_close(None)
        else:
            e.Skip()

    @property
    def info(self):
        # replace vertical tabs that may have been inserted by shift+enter
        msg_txt = self.input.Value.replace("\x0b", "\n")

        return dict(message=msg_txt)

    def layout(self):
        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)

        if self._label_text or self.ownscount:
            h = wx.BoxSizer(wx.HORIZONTAL)
            if hasattr(self, 'text_label'):
                h.Add(self.text_label, 0)
            h.AddStretchSpacer()
            h.AddStretchSpacer()

            if self.use_counter and self.ownscount:
                h.Add(self.charcount, 0, wx.RIGHT, border = _BORDER)

            s.Add(h, 0, wx.EXPAND)

        s.Add(self.input, 1, wx.EXPAND | wx.TOP, _BORDER)

        s.Layout()

    def append_text(self, text):
        self.input.SetInsertionPointEnd()
        self.insert_text(text)

    def insert_text(self, text):

        textctrl = self.input
        ip = textctrl.InsertionPoint

        if ip != 0 and textctrl.Value[ip-1] and textctrl.Value[ip-1] != ' ':
            textctrl.WriteText(' ')

        textctrl.WriteText(text + ' ')
        self.focus_text()

    def focus_text(self):
        self.input.SetFocus()

    def GetTextValue(self):
        return self.input.Value

    def SetTextValue(self, txt):
        self.input.Value = txt

    def SelectText(self):
        self.input.SelectAll()

class SocialStatusRow(gui.accountslist.SocialRow, PHCM):
    def __init__(self, parent, *a, **k):
        gui.accountslist.SocialRow.__init__(self, parent, *a, **k)
        self.Bind(wx.EVT_CHECKBOX, self.on_account_checked)

    @property
    def image(self):
        img = getattr(self.data, 'serviceicon', None) or gui.skin.get("serviceicons." + self.data.protocol, None)
        return img.Resized(16) if img else None

    def get_account_enabled(self):
        return self.get_controller().get_account_enabled(self.account)

    def on_account_checked(self, e):
        checked = e.EventObject.Value
        self.get_controller().set_account_enabled(self.account, checked)

        e.Skip()

    def PopulateControls(self, account):
        self.account = account
        self.text = self.account.display_name
        self.RefreshRowValue()

    def RefreshRowValue(self):
        self.checkbox.Value = self.get_account_enabled()

class SocialListEditor(gui.anylists.AnyList, PHCM):
    SelectionEnabled = False
    ClickTogglesCheckbox = True

    def __init__(self, parent, data):
        gui.anylists.AnyList.__init__(self, parent, data, row_control = SocialStatusRow, draggable_items = False)

        self.Bind(wx.EVT_PAINT, self._on_paint)

    def GetSelectedAccounts(self):
        return [row.data for row in self.rows if row.checkbox.Value]

    def RefreshValues(self):
        for row in self.rows:
            row.RefreshRowValue()

        wx.CallAfter(self.ScrollToFirstSelectedRow)

    def ScrollToFirstSelectedRow(self):
        for row in self.rows:
            if row.checkbox.Value:
                break
        else:
            row = None

        if row is not None:
            self.ScrollChildIntoView(row)

    def on_data_changed(self, *a):
        self.data = self.get_controller().get_accounts()
        gui.anylists.AnyList.on_data_changed(self, *a)
        vheight = self.GetVirtualSize()[1]
        self.SetSizeHints(wx.Size(self.Size[0], max(32, vheight)))
        self.Top.FitInScreen()
        self.UpdateWindowUI()

    def _on_paint(self,event):
        event.Skip()
        _x = wx.PaintDC(self)

        srect = wx.Rect(*self.Rect)
        srect.Inflate(1,1)
        pcdc = wx.ClientDC(self.Parent)
        pcdc.Brush = wx.TRANSPARENT_BRUSH

        pcdc.Pen = wx.Pen(wx.Colour(213,213,213))

        pcdc.DrawRectangleRect(srect)

class AccountListPanel(wx.Panel, PHCM):
    TOP_LABEL = _("Choose Accounts:")
    TOP_LABEL_ID = wx.NewId()

    #VLE.VisualListEditorList

    def __init__(self, parent, *a, **k):
        wx.Panel.__init__(self, parent)
        self.construct()
        self.layout()
        self.bind_events()

    def bind_events(self):
        self.account_list.Bind(wx.EVT_CHECKBOX, self.on_checkbox)

        self.Top.Bind(wx.EVT_CLOSE, self.on_top_closed)

    def layout(self):
        pass

    def get_accounts(self):
        return self.get_controller().get_accounts()

    def construct(self):
        self.account_list = account_list = SocialListEditor(self, self.get_accounts())
        self.account_list.SetMinSize((200, 48)) # TODO: go away numbers

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        if not use_minimal_layout():
            top_label = wx.StaticText(self, self.TOP_LABEL_ID, self.TOP_LABEL, style = wx.BOLD)
            top_label.SetBold()
            self.Sizer.Add(top_label, 0, wx.EXPAND | wx.ALL, _BORDER)
        self.Sizer.Add(account_list, 1, wx.EXPAND | wx.ALL, _BORDER)
        self.Layout()

    def on_checkbox(self, e):
        e.Skip()

    def on_list_changed(self, enabled_items):
        log.info('list was changed: %r', enabled_items)

        for account in self.get_accounts():
            self.set_account_enabled(account, account in enabled_items)

    def on_top_closed(self, e):
        print 'calling "on_close" on %r' % self.account_list
        self.account_list.on_close()

    def GetSelectedAccounts(self):
        return self.account_list.GetSelectedAccounts()

    def RefreshAccountsList(self):
        self.account_list.on_data_changed()
        #self.account_list.RefreshValues()

    def ScrollAccountList(self):
        self.account_list.ScrollToFirstSelectedRow()

class InsertLinkPanel(wx.Panel, PHCM):
    label = _('Insert Link')
    icon_key = 'icons.insertlink'
    URL_TEXT_ID = wx.NewId()

    def __init__(self, parent, *a, **k):
        wx.Panel.__init__(self, parent, *a, **k)
        self.construct()

    def on_enter(self, e = None):
        self.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON, wx.ID_OK))

    def construct(self):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.stext = wx.StaticText(self, wx.NewId(), _('Website URL:'))
        self.stext.SetBold()

        self.url_text = wx.TextCtrl(self, wx.ID_OK, style = wx.TE_PROCESS_ENTER)

        self.Sizer.Add(self.stext, 0, wx.EXPAND | wx.ALL, _BORDER)
        self.Sizer.Add(self.url_text, 0, wx.EXPAND | wx.ALL, _BORDER)
        if not use_minimal_layout():
            self.Sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, _BORDER)

        self.ok_button = wx.Button(self, wx.ID_OK, _('Insert &Link'))
        self.ok_button.SetDefault()

        self.cancel_button = wx.Button(self, wx.ID_CANCEL)

        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.AddStretchSpacer()
        btnsizer.Add(self.ok_button, 0, wx.ALIGN_RIGHT | wx.ALL, _BORDER)
        btnsizer.Add(self.cancel_button, 0, wx.ALIGN_RIGHT | wx.ALL, _BORDER)

        self.Sizer.Add(btnsizer, 0, wx.EXPAND | wx.ALL)
        self.FitInScreen()
        self.Layout()

    @callbacks.callsback
    def GetInfo(self, callback = None):
        self.url_text.Enable(False)
        full_url = self.url_text.Value

        def _success(url):
            callback.success({'link':url})

        def _error(e):
            try:
                raise e
            except callbacks.CallbackStream.Cancel as c:
                callback.success({})
            except Exception as e:
                wx.CallAfter(self.url_text.Enable, True)
                callback.error(e)

        if not full_url:
            return _error(callbacks.CallbackStream.Cancel())

        util.threaded(net.get_short_url)(full_url,
                                         success = _success,
                                         error = _error)

    def clear(self):
        self.url_text.Enable(True)
        self.url_text.Value = u''

    def set_focus(self):
        self.url_text.SetFocus()

class InsertImagePanel(wx.Panel, PHCM):
    label = _('Share Image')
    icon_key = 'icons.insertimage'
    FILE_PICKER_ID = wx.NewId()
    def __init__(self, parent, *a, **k):
        wx.Panel.__init__(self, parent, *a, **k)
        self.current_transfer = None
        self.construct()
        self.bind_events()
        self.clear()

    def set_focus(self):
        pass

    def BeforeShow(self):
        filename = gui.toolbox.pick_image_file(self.Top)

        if filename is not None:
            wx.CallAfter(self.do_upload, filename)
            return True
        else:
            return False

    def do_upload(self, filename):
        self.enable_retry(False)
        self._filename = filename
        self.progress_bar.SetRange(os.path.getsize(filename))
        self.progress_bar.SetValue(0)

        file = open(filename, 'rb')
        cb = callbacks.CallbackStream(file, self.file_progress, self.file_finished)
        self.current_transfer = cb
#        import urllib2
#        util.threaded(urllib2.urlopen)("http://www.google.com", (('file', cb),),
#                                       success = self.on_upload_success,
#                                       error = self.on_upload_error)

        import imagehost.imgur as imgur
        api = imgur.ImgurApi()
        api.upload(cb,
                   success = self.on_upload_success,
                   error = self.on_upload_error)

    def file_progress(self, howmuch):
        if not wx.IsMainThread():
            return wx.CallAfter(self.file_progress, howmuch)

        self.progress_bar.SetValue(howmuch)

    def file_finished(self):
        if not wx.IsMainThread():
            return wx.CallAfter(self.file_finished)

        self.current_transfer = None

    def _emit_ok(self):
        e = wx.CommandEvent(wx.EVT_COMMAND_BUTTON_CLICKED, self.Id)
        e.SetEventObject(self)
        e.SetId(wx.ID_OK)
        self.GetEventHandler().ProcessEvent(e)

    def bind_events(self):
        self.Bind(wx.EVT_BUTTON, self.on_button)

    def on_button(self, e):
        if e.Id == wx.ID_CANCEL:
            if self.current_transfer is not None:
                self.current_transfer.cancel()
        elif e.Id == wx.ID_REDO:
            self.retry_clicked(e)

        if e.Id != wx.ID_REDO:
            e.Skip()

    def construct(self):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.sttext = wx.StaticText(self, label = _("Uploading Image..."))
        self.progress_bar = wx.Gauge(self, style = wx.GA_SMOOTH)
        self.Sizer.Add(self.sttext, 0, wx.EXPAND | wx.ALL, _BORDER)
        self.Sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.ALL, _BORDER)
        if not use_minimal_layout():
            self.Sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, _BORDER)

#        self.ok_button = wx.Button(self, wx.ID_OK, _('Insert &Image'))
#        self.ok_button.SetDefault()

        self.retry_button = wx.Button(self, wx.ID_REDO, label = _("Retry"))
        self.cancel_button = wx.Button(self, wx.ID_CANCEL)

        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.AddStretchSpacer()
        btnsizer.Add(self.retry_button, 0, wx.ALIGN_RIGHT | wx.ALL, _BORDER)
        btnsizer.Add(self.cancel_button, 0, wx.ALIGN_RIGHT | wx.ALL, _BORDER)


        self.Sizer.Add(btnsizer, 0, wx.EXPAND | wx.ALL)
        self.FitInScreen()
        self.Layout()

    @callbacks.callsback
    def GetInfo(self, callback = None):
        self._info_requested = True
        self._callback = callback
        if self._got_response or self._got_error:
            return self.emit_result(callback = callback)

    def emit_result(self, callback = None, response = None, exception = None):
        if self._got_response:
            cb, cb_args = self._emit_success(callback, response, exception)
        elif self._got_error:
            cb, cb_args = self._emit_error(callback, response, exception)

        cb(*cb_args)

    def _emit_success(self, callback, response, exception):
        cb = (self._callback or callback).success
        try:
            cb_args = self._prepare_success(self._response or response)
        except Exception, e:
            return self._emit_error(callback, response, e)

        return cb, cb_args

    def _emit_error(self, callback, response, exception):
        cb = (self._callback or callback).error
        cb_args = self._prepare_error(self._exception or exception, self._response or response)
        wx.CallAfter(self.enable_retry)

        return cb, cb_args

    def _prepare_success(self, resp):
        return ({'link' : resp['url']},)

    def _prepare_error(self, e, response):
        if response is not None:
            status = response.get('status', {})
            if status.get('result') == 'ERROR':
                return status.get('message', str(e)),

        return str(e),

    def on_upload_success(self, resp):
        self._got_response = True
        self._response = resp

        if self._info_requested:
            return self.emit_result(response = resp)
        self._emit_ok()

    def on_upload_error(self, e):
        self._got_error = True
        self._exception = e
        if self._info_requested:
            return self.emit_result(exception = e)
        self._emit_ok()

    def enable_retry(self, enable = True):
        self.retry_button.Enable(enable)

    def retry_clicked(self, e):
        self.do_upload(self._filename)

    def on_trim_error(self, e, err_cb):
        err_cb(e)

    def clear(self):
        self._got_response = self._info_requested = self._got_error = False
        self._response = self._callback = self._exception = None

class TransparentStaticBitmap(wx.StaticBitmap):
    def __init__(self, *a):
        wx.StaticBitmap.__init__(self, *a)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_PAINT, self._paint)

    def _paint(self, e):
        dc = wx.AutoBufferedPaintDC(self)
        sz  = self.ClientSize

        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.Brush(self.BackgroundColour))
        dc.DrawRectangleRect(wx.RectS(sz))

        bmp = self.GetBitmap()
        if bmp.HasAlpha():
            bmp.UseAlpha()

        dc.DrawBitmap(bmp, 0, 0, True)

        return dc

class StatusToolbar(wx.Panel, PHCM):
    def __init__(self, parent, **options):
        self._options = options
        wx.Panel.__init__(self, parent)
        self._tool_ids = {}

        self.construct()

    def construct(self):
        self.Sizer = wx.BoxSizer(wx.HORIZONTAL)

        if self._options.get('counter', False):
            self.charcount = make_counter_ctrl(self)
            self.Sizer.Add(self.charcount, 0, wx.EXPAND | wx.ALL, _BORDER)

        self.Sizer.AddStretchSpacer()

        # create hyperlinks without context menus
        hl_style = wx.HL_DEFAULT_STYLE & ~wx.HL_CONTEXTMENU

        for toolname, tool in self._options.get('tools', {}).items():
            id = self._tool_ids[toolname] = wx.NewId()
            lnk = wx.HyperlinkCtrl(self, id, tool.label, url = toolname,
                    style = hl_style)
            #lnk.Bind(wx.EVT_HYPERLINK, self.on_link_click)
            lnk.SetVisitedColour(lnk.GetNormalColour())

            icon = TransparentStaticBitmap(self, -1, gui.skin.get(tool.icon_key))
            self.Sizer.Add(icon, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border = _BORDER * 3)
            self.Sizer.AddSpacer(3)
            self.Sizer.Add(lnk, 0, wx.ALIGN_RIGHT |  wx.ALIGN_CENTER_VERTICAL)

        self.Layout()

class FauxNotebook(wx.Panel, PHCM):
    def __init__(self, parent):
        self.current_shown = None
        wx.Panel.__init__(self, parent)
        self.panels = {}
        self.panel_list = []
        self.Sizer = wx.BoxSizer(wx.VERTICAL)

    def AddPanel(self, name, panel):
        self.panels[name] = panel
        self.panel_list.append(panel)
        self.Sizer.Add(panel, 1, wx.EXPAND | wx.ALL, )# _BORDER)

        if len(self.panel_list) == 1:
            self.ShowPanel(name)
        else:
            panel.Hide()

    def ShowPanel(self, name, do_precheck = True):
        old_panel = self.GetPanel()
        new_panel = self.panels[name]

        self.current_shown = name

        if (not do_precheck) or getattr(new_panel, 'BeforeShow', lambda: True)():
            if old_panel is not None:
                getattr(old_panel, 'BeforeHide', Null)()
                old_panel.Show(False)
            new_panel.Show(True)
        else:
            e = wx.CommandEvent(wx.EVT_COMMAND_BUTTON_CLICKED, self.Id)
            e.SetEventObject(new_panel)
            e.SetId(wx.ID_CANCEL)
            self.GetEventHandler().ProcessEvent(e)

        new_panel.set_focus()
        self.Top.FitInScreen()

    def GetPanel(self, name = None):
        if name is None:
            name = self.current_shown

        return self.panels.get(name)

class ErrorPanel(wx.Panel):
    TITLE_TEXT = _("Errors Encountered:")
    def __init__(self, *a, **k):
        wx.Panel.__init__(self, *a, **k)

        self.construct()
        self.layout()

    def construct(self):
        self.title_text = wx.StaticText(self, -1)
        self.title_text.SetLabel(self.TITLE_TEXT)
        self.title_text.SetBold()
        self.title_text.SetForegroundColour(wx.Color(255,0,0))

        self.column1_text = wx.StaticText(self, -1)
        self.column1_text.SetBold()
        self.column1_text.SetForegroundColour(wx.Color(255,0,0))

        self.column2_text = wx.StaticText(self, -1)
        self.column2_text.SetForegroundColour(wx.Color(255,0,0))

    def layout(self):
        self.Sizer = wx.FlexGridSizer(2, 2)
        self.Sizer.Add(self.title_text, 0, wx.ALL, _BORDER)
        self.Sizer.AddStretchSpacer()
        self.Sizer.Add(self.column1_text, 0, wx.ALL, _BORDER)
        self.Sizer.Add(self.column2_text, 1, wx.ALL, _BORDER)

    def set_errors(self, texts):
        col1_buffer = []
        col2_buffer = []
        for col1, col2 in texts:
            col1_buffer.append(col1)
            col2_buffer.append(col2)

        self.column1_text.SetLabel('\n'.join(col1_buffer))
        self.column2_text.SetLabel('\n'.join(col2_buffer))

def use_minimal_layout():
    return common.pref('global_status_dialog.minimal', False)

class GlobalStatusDialog(wx.Dialog):
    TOOLS = util.odict([
                        ('link', InsertLinkPanel),
                        ('image', InsertImagePanel),
                        ],
                       )

    @classmethod
    def add_tool(cls, toolname, toolinfo):
        cls.TOOLS[toolname] = toolinfo

    def __init__(self, controller,
                 parent = None,
                 title = _('Set Global Status'),
                 frame_icon_key = 'icons.globalstatus',
                 on_close = None,
                 **options):

        self.controller = controller
        self._options = options

        style = (wx.DEFAULT_FRAME_STYLE) & ~(wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX)# | wx.RESIZE_BORDER)
        wx.Dialog.__init__(self, parent, title = title, style = style)

        self.tools = util.odict()

        self.SetFrameIcon(gui.skin.get(frame_icon_key))
        self.construct()
        self.layout()
        self.bind_events()
        gui.toolbox.persist_window_pos(self, close_method = on_close, position_only = True)


    def SetText(self, txt):
        self.text_panel.SetTextValue(txt)

    def SelectText(self):
        self.text_panel.SelectText()

    def RefreshAccountsList(self):
        self.accountslist_panel.RefreshAccountsList()

    def ScrollAccountsList(self):
        self.accountslist_panel.ScrollAccountList()

    def get_controller(self):
        return self.controller

    def construct(self):

        self.content = FauxNotebook(self)

        self.error_panel = ErrorPanel(self)
        self.error_panel.Show(False)
        self._text_id = wx.NewId()

        self.accounts_panel = PanelWithController(self.content)

        for toolname in self.TOOLS:
            self.tools[toolname] = self.TOOLS[toolname](self.content)

        minimal_layout = use_minimal_layout()

        toolbar_panel = StatusToolbar(self.accounts_panel, tools = self.tools, counter=minimal_layout)

        text_field_label = None if minimal_layout else (self._options.get('text_panel_label') or _('Your Status:'))
        self.text_panel = TextFieldWithCounter(self, text_id = self._text_id,
                                               label = text_field_label,
                                               initial_text = self._options.get('initial_text') or u'',
                                               select_text = self._options.get('select_text') or False,
                                               counter_ctrl = toolbar_panel.charcount if minimal_layout else None)

        # create these things next so they follow the text control in tab order.
        buttons_panel = PanelWithController(self.accounts_panel)
        self.ok_button = ok_button = wx.Button(buttons_panel, id = wx.ID_OK, label = _('&Update Status'))
        cancel_button = wx.Button(buttons_panel, id = wx.ID_CANCEL)

        self.accounts_panel.set_focus = self.text_panel.focus_text
        self.accountslist_panel = AccountListPanel(self.accounts_panel)
        ok_button.SetDefault()

        sz = self.accounts_panel.Sizer = wx.BoxSizer(wx.VERTICAL)
        sz.Add(toolbar_panel, 0, wx.EXPAND | (wx.ALL & ~wx.TOP), _BORDER)
        if not minimal_layout:
            sz.Add(wx.StaticLine(self.accounts_panel), 0, wx.EXPAND | wx.ALL, _BORDER)
        sz.Add(self.accountslist_panel, 1, wx.EXPAND | wx.ALL, _BORDER)
        if not minimal_layout:
            sz.Add(wx.StaticLine(self.accounts_panel), 0, wx.EXPAND | wx.ALL, _BORDER)

        bsz = buttons_panel.Sizer = wx.BoxSizer(wx.HORIZONTAL)
        bsz.AddStretchSpacer()
        bsz.Add(ok_button, 0, wx.ALIGN_RIGHT | (wx.ALL & ~wx.BOTTOM), border = _BORDER)
        bsz.Add(cancel_button, 0, wx.ALIGN_RIGHT | wx.ALL, border = _BORDER)
        sz.Add(buttons_panel, 0, wx.EXPAND | wx.ALL, border = _BORDER)

        self.content.AddPanel('default', self.accounts_panel)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.text_panel, 1, wx.EXPAND | (wx.ALL & ~wx.BOTTOM), _BORDER)
        self.Sizer.Add(hsizer, 0, wx.EXPAND | wx.ALL, _BORDER)
        self.Sizer.Add(self.error_panel, 0, wx.EXPAND | wx.ALL | wx.ALIGN_CENTER, _BORDER)
        self.Sizer.Add(self.content, 1, wx.EXPAND | wx.ALL, _BORDER)

        for toolname in self.TOOLS:
            p = self.tools[toolname]
#            p.Sizer = wx.BoxSizer(wx.HORIZONTAL)+
#            sttext = wx.StaticText(p, wx.NewId(), p.label)
#            p.Sizer.Add(sttext)
            self.content.AddPanel(toolname, p)


    def layout(self):
        minsize = wx.Size(320, 200)
        self.SetMinSize(minsize)
        #self.content.SetMinSize(wx.Size(205, 270))
        maxheight = gui.toolbox.Monitor.GetFromWindow(self).ClientArea.height * common.pref('social.status.ratio_to_screen', type = float, default = 0.75)
        maxsize = wx.Size(500, maxheight)
        self.SetMaxSize(maxsize)
        self.content.SetMaxSize(maxsize)

        self.text_panel.focus_text()

    def bind_events(self):
        self.Bind(wx.EVT_BUTTON, self.on_button)
        self.Bind(wx.EVT_CHECKBOX, self.check_enable_ok_button)
        self.Bind(wx.EVT_HYPERLINK, self.on_link)

        self.Bind(wx.EVT_TEXT, self.check_enable_ok_button)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_button)
        self.Bind(wx.EVT_TEXT_PASTE, self.on_text_paste)

        self.Bind(wx.EVT_UPDATE_UI, self.check_enable_ok_button)

    def check_enable_ok_button(self, e = None):
        # use this line if you want to disable when character count is 0

        self.ok_button.Enable(self.should_enable_ok())
        if e is not None:
            e.Skip()

    def should_enable_ok(self):
        return bool(self.GetSelectedAccounts())
#        return bool(self.GetMessage() and self.GetSelectedAccounts())

    def on_text_paste(self, e):
        import gui.clipboard as clipboard

        if e.EventObject is not self.text_panel.input:
            e.Skip()
            return

        text = clipboard.get_text()
        if text is not None and common.pref('social.status.shorten_pasted_urls', default = False, type = bool) and util.isurl(text):
            if not net.is_short_url(text):
                self.text_panel.insert_text(net.get_short_url(text))
                return

            if text.endswith('\r\n'):
                text = text[:-2]

            self.text_panel.insert_text(text)

        bitmap = clipboard.get_bitmap()
        if bitmap is not None:
#            if 'wxMSW' in wx.PlatformInfo and not bitmap.HasAlpha():
#                bitmap.UseAlpha()

            import stdpaths, time
            filename = stdpaths.temp / 'digsby.trim.clipboard.%s.png' % time.time()
            bitmap.SaveFile(filename, wx.BITMAP_TYPE_PNG)

            self.ChangePanel('image', False)
            self.content.GetPanel().do_upload(filename)
            return

    def check_image_data(self, e):
        print 'image data:',e
        #self.content.Bind(wx.EVT_SIZE, self.OnContentSized)

#    def OnContentSized(self, e):
#        self.Fit()
#        self.Layout()
#        e.Skip()

    def CloseWithReturnCode(self, code):
        self.SetReturnCode(code)
        self.Close()

    def on_button(self, e):
        panel_name = self.content.current_shown
        if panel_name == 'default':
            if e.Id == self._text_id:
                if self.should_enable_ok():
                    id = wx.ID_OK
                else:
                    id = wx.ID_CANCEL
            else:
                id = e.Id

            if not wx.GetKeyState(wx.WXK_SHIFT) and id in (wx.ID_CANCEL, wx.ID_OK):
                e.Skip()
                self.CloseWithReturnCode(id)
        else:
            self.PanelDone(panel_name, e.Id)

    def PanelDone(self, name, return_code):
        p = self.content.GetPanel()
        if return_code == wx.ID_OK:
            p.GetInfo(success = lambda info: wx.CallAfter(self.apply_info, name, info),
                      error = lambda *a: wx.CallAfter(self.info_error, p.label, *a))
        else:
            self.SwitchToDefaultView()

    def SwitchToDefaultView(self):
        self.ShowError(None)
        self.content.GetPanel().clear()
        self.content.ShowPanel('default')
        self.content.GetPanel().set_focus()
        self.text_panel.Enable(True)

    def on_link(self, e):
        self.ChangePanel(e.URL)

    def ChangePanel(self, name, do_precheck = True):
        self.ShowError(None)
        self.text_panel.Enable(False)
        self.content.ShowPanel(name, do_precheck = do_precheck)

    def info_error(self, name, e = None):
        print 'ohno, an error'
        #self.SwitchToDefaultView()
        self.ShowError([(name, e)])

    def ShowError(self, errors = None):
        if errors is None:
            errors = ()
            show = False
        else:
            show = True

        error_texts = [self.nice_message_for_error(*e) for e in errors]

        self.error_panel.set_errors(error_texts)
        self.error_panel.Show(show)
        self.Top.Layout()
        self.Top.FitInScreen()

    def nice_message_for_error(self, acct, e):
        import socket
        if isinstance(acct, basestring):
            acct_str = acct
        elif acct.protocol == 'im-status':
            acct_str = u"IM-Status: "
        else:
            acct_str = u"{acct.name!s} ({acct.protocol!s}): ".format(acct = acct)
        # TODO: work out more error messages
        log.info('Creating error message for account %r. error is %r', acct, e)

        import urllib2, socket

        try:
            raise e
        except socket.error:
            err_str = _(u"Network error (%r)" % e)
        except urllib2.URLError:
            err_str = _(u"Network error (%s)" % e)
        except IOError:
            err_str = _(u"Network error ({error!r} - {error!s})").format(error = str(e).replace('\r', '\\r').replace('\n','\\n'))
        except net.UrlShortenerException:
            err_str = _(u"%s") % e.message
        except Exception:
            if getattr(e, 'message', None) and isinstance(e.message, basestring):
                err_str = _(u"%s") % e.message
            elif str(e):
                err_str = _(u"Unknown error (%s)") % str(e)
            else:
                err_str = _(u"Unknown error")

        log.info('\terr_str = %r', err_str)
        return (acct_str, err_str)

    def apply_info(self, name, info):
        if name in ('link', 'image'):
            link = info.get('link')
            if link:
                self.text_panel.insert_text(link)

        self.SwitchToDefaultView()

    def GetSelectedAccounts(self):
        return self.accountslist_panel.GetSelectedAccounts()

    def GetMessage(self):
        msg = self.text_panel.GetTextValue()
        msg = msg.replace(u'\x0b', u'\n')
        return msg.rstrip()

class GlobalStatusController(object):
    _inst = None
    @classmethod
    def GetInstance(cls, profile, enabled_accounts = None, initial_text = u'', **options):
        if cls._inst is not None:
            inst = cls._inst()
        else:
            inst = None

        if inst is None:
            inst = cls(profile, enabled_accounts, initial_text, **options)
            cls._inst = weakref.ref(inst)
        else:
            inst.Populate(profile, enabled_accounts, initial_text, options)
        return inst

    def __init__(self, profile, enabled_accounts = None, initial_text = u'', **options):
        self._dialog = None
        self.Populate(profile, enabled_accounts, initial_text, options)

        self.observe_accounts()

    def observe_accounts(self):
        self.profile.account_manager.socialaccounts.add_list_observer(self.accounts_changed, self.accounts_changed)

    def unobserve_accounts(self):
        self.profile.account_manager.socialaccounts.remove_list_observer(self.accounts_changed, self.accounts_changed)

    def accounts_changed(self, *a):
        if not wx.IsMainThread():
            wx.CallAfter(self.accounts_changed)
            return

        if self._dialog is not None:
            self.GetDialog().RefreshAccountsList()


    def Populate(self, profile, enabled_accounts, initial_text, options):
        self.profile = profile
        self._options = options

        if enabled_accounts == 'ALL':
            enabled_accounts = [self.get_accounts()[0]] + self.profile.socialaccounts[:]

        self.enabled_accounts = enabled_accounts
        self.initial_text = initial_text

    def SetFocus(self):
        if self._dialog is None:
            return

        self._dialog.SetFocus()

    def ShowDialog(self, center = True):
        dlg = self.GetDialog()
        #dlg.CenterOnParent()
        dlg.SetText(self.initial_text)
        if self._options.get('select_text', False):
            dlg.SelectText()
        dlg.RefreshAccountsList()
        dlg.Show()
        dlg.ReallyRaise()

    def GetDialog(self):
        if self._dialog is None:
            self._dialog = self.CreateDialog()

        return self._dialog

    def CreateDialog(self):
        dlg = GlobalStatusDialog(self, initial_text = self.initial_text, select_text = self._options.get('select_text', False), on_close = self._on_dialog_close)
        return dlg

    def ShowError(self, etxt):
        self.GetDialog().ShowError(etxt)

    def _on_dialog_close(self, e):
        self.unobserve_accounts()

        dlg = self._dialog
        if dlg is None:
            return

        return_code = dlg.GetReturnCode()
        if return_code == wx.ID_OK:
            accounts = dlg.GetSelectedAccounts()
            message = dlg.GetMessage()
            self.apply_status_message(message, accounts)
            submit_callback = self._options.pop('submit_callback', None)
            if submit_callback is not None:
                submit_callback(message, accounts)

        dlg.Destroy()
        print 'dialog closed, return_code = %r' % return_code
        self._dialog = None

    def apply_status_message(self, message, accounts):
        if not accounts:
            return

        collector = SetStatusResults(self.profile, accounts, message, self._options)
        for account in accounts:
            options = self._options.get('account_options', {})
            proto_options = options.get(account.protocol, {}).copy()
            acct_options = options.get((account.protocol, account.name), {}).copy()
            proto_options.update(acct_options)
            try:
#                import random
#                if random.getrandbits(1):
#                    f = collector.error_handler(account)
#                    util.threaded(lambda e, func=f: func(e))(Exception("%r broke!" % account))
#                else:
                    if not hasattr(account, 'SetStatusMessage'):
                        continue
                    util.threaded(lambda a = account: a.SetStatusMessage
                                  (message,
                                   success = collector.success_handler(a),
                                   error   = collector.error_handler(a),
                                   **proto_options))()
            except Exception, e:
                log.error("error setting status on account %r: %r", account, e)

    def get_accounts(self):
        if getattr(self, '_im_status', None) is None:
            self._im_status = SetIMStatusEntry(self.profile,
                                               editable = self._options.get('editable', True),
                                               edit_toggle = self._options.get('edit_toggle', True))

        self.clear_unknown_accounts(self.profile.socialaccounts)

        return ([self._im_status] +
                [a for a in self.profile.socialaccounts
                 if a.enabled and (a.ONLINE or a.CHECKING)])

    def clear_unknown_accounts(self, accounts):
        active_keys = [acct_name_to_key('im-status', 'im-status')] + [acct_name_to_key(a.protocol, a.name) for a in accounts]

        acct_status_settings = self.profile.prefs.get('social.status.enabled_accts', {})
        for key in acct_status_settings.keys():
            if key not in active_keys:
                acct_status_settings.pop(key, None)

    def get_account_enabled(self, account):
        if self.enabled_accounts is not None:
            return account in self.enabled_accounts

        proto, name = account.protocol, account.name

        acct_status_settings = self.profile.prefs.get('social.status.enabled_accts', {})
        acctinfo = acct_status_settings.setdefault(acct_name_to_key(proto, name), {})

        return acctinfo.setdefault('enabled', True)

    def set_account_enabled(self, account, enabled):
        if self.enabled_accounts is not None:
            if enabled and account not in self.enabled_accounts:
                self.enabled_accounts.append(account)

            elif not enabled and account in self.enabled_accounts:
                self.enabled_accounts.remove(account)

            return
        proto, name = account.protocol, account.name

        acct_status_settings = self.profile.prefs.setdefault('social.status.enabled_accts', {})
        acctinfo = acct_status_settings.setdefault(acct_name_to_key(proto, name), {})

        acctinfo['enabled'] = enabled

class SetStatusResults(object):
    def __init__(self, profile, accounts, message, options):
        self.profile = profile
        self.options = options
        self.accounts = accounts
        self.results = dict.fromkeys(accounts, None)
        self.message = message
        self._got_result = False

    def success_handler(self, acct):
        def on_success(*a):
            self.results[acct] = 'success'
            self.check_results()

        return on_success

    def error_handler(self, acct):
        def on_error(e):
            import traceback; traceback.print_exc()
            self.results[acct] = e
            self.check_results()
        return on_error

    def check_results(self):
        if any(x is None for x in self.results.itervalues()) or self._got_result:
            print 'setstatus still waiting for some'
            return

        self._got_result = True

        # got response from every account
        for acct in self.results.keys():
            if self.results[acct] == 'success':
                self.results.pop(acct)

        if not self.results:
            # successfully set status
            log.info('Global status set successfully')
            return

        # Now all we have left are accounts with errors.
        log.info('Error(s) while setting global status: %r', self.results)
        wx.CallAfter(self.show_dialog_again)

    def error_messages(self):
        return [(account, self.results[account]) for account in self.results]

    def show_dialog_again(self):
        gsc = GlobalStatusController.GetInstance(self.profile,
                                                 [a for a in self.accounts if a in self.results],
                                                 self.message, **self.options)

        gsc.ShowError(self.error_messages())
        gsc.ShowDialog()

def main():
    from tests.testapp import testapp
    import stdpaths

    a = testapp(plugins = False)
    stdpaths.init()

    p = FakeProfile()
    c = GlobalStatusController(p,
                               p.socialaccounts,
                               initial_text = 'initial text',
                               )
    c.ShowDialog(center = True)
    d = c._dialog
    #d.Bind(wx.EVT_DESTROY, lambda e: (wx.GetApp().ExitMainLoop()))

    tp = util.threadpool.ThreadPool(5)

    a.MainLoop()

    tp.joinAll()
    print p.prefs

def main1():
    def progress(howmuch):
        print howmuch, 'was read'
    def finished():
        print 'finished'
    file = open('c:\\a.txt', 'rb')
    cb = callbacks.CallbackStream(file, progress, finished)

if __name__ == '__main__':
    class FakeSocialAccount(object):
        enabled = True
        ONLINE = True
        @property
        def display_name(self):
            return self.name

        @property
        def serviceicon(self):
            return gui.skin.get('serviceicons.%s' % self.protocol)

        def __init__(self, name, protocol):
            self.username = self.name = name
            self.protocol = protocol

        @callbacks.callsback
        def SetStatusMessage(self, message, callback = None, **kw):
            callback.success()
        def __repr__(self):
            return "FakeSocialAccount(%r, %r)" % (self.name, self.protocol)

    class FakeProfile(object):
        prefs = {}
        socialaccounts = [
                          FakeSocialAccount('mike', 'twitter'),
                          FakeSocialAccount('mike2', 'facebook'),
                          FakeSocialAccount('mike3', 'facebook'),
                          FakeSocialAccount('mike', 'myspace')
                          ]
        socialaccounts += [FakeSocialAccount('mike', 'myspace') for _ in range(30)]

        @callbacks.callsback
        def SetStatusMessage(self, message, callback = None, **kw):
            print 'omg setting status message! %r' % message
            callback.success()

        account_manager = Null

    main()

