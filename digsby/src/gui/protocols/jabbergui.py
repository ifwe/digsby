'''

Controls and dialogs for Jabber.

'''

import wx
from wx import ALL, TOP, BOTTOM, ALIGN_CENTER, EXPAND, VERTICAL, HORIZONTAL, BoxSizer

from gui.toolbox import GetTextFromUser, wx_prop, build_button_sizer, persist_window_pos, snap_pref
from gui.validators import LengthLimit
from common import profile
from util.primitives.funcs import Delegate
from util.primitives.mapping import Storage as S
from logging import getLogger; log = getLogger('jabbergui')

def set_priority(jabber, set):
    val = GetTextFromUser(_('Enter a priority for %s:' % jabber.username),
                          caption = _('Set Jabber Priority'),
                          default_value = str(jabber.priority))

    if val is not None:
        try:
            set(int(val))
        except ValueError:
            pass


class JabberDeleteConfirmBox(wx.Dialog):
    def __init__(self, acct, msg, *a, **k):
        self.acct = acct
        wx.Dialog.__init__(self, *a, **k)

        self.init_components(msg)
        self.bind_events()
        self.layout_components()

        # TODO: we need
        self.del_check.Enable(self.acct.connection is not None)

        self.Layout()
        self.Sizer.Fit(self)


    def init_components(self, msg):
        self.help_bmp  = wx.StaticBitmap(self)
        self.help_bmp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_HELP, wx.ART_OTHER, (32, 32)))
        self.msg_label = wx.StaticText(self, label=msg)
        self.del_check = wx.CheckBox(self, label="Also delete from Jabber server")

        self.pw_text   = wx.TextCtrl(self, style=wx.TE_PASSWORD, validator=LengthLimit(1024))
        self.pw_label  = wx.StaticText(self, label="Password: ")
        self.yes_btn   = wx.Button(self, wx.ID_YES)
        self.yes_btn.SetDefault()
        self.no_btn    = wx.Button(self, wx.ID_NO)
        self.del_label = wx.StaticText(self, label='Deleting...')

        self.del_label.Show(False)
        self.del_label.Enable(False)

        self.info_sizer  = BoxSizer(HORIZONTAL)
        self.btn_sizer   = BoxSizer(HORIZONTAL)
        self.pw_sizer    = BoxSizer(HORIZONTAL)
        self.delpw_sizer = BoxSizer(VERTICAL)
        self.in_sizer    = BoxSizer(HORIZONTAL)

        self.main_sizer  = BoxSizer(VERTICAL)
        self.Sizer       = BoxSizer(HORIZONTAL)

    def bind_events(self):
        self.yes_btn.Bind(wx.EVT_BUTTON, self.yes_clicked)
        self.no_btn.Bind(wx.EVT_BUTTON, self.no_clicked)
        self.del_check.Bind(wx.EVT_CHECKBOX, self.on_check)

        self.on_check(None)

    def layout_components(self):
        self.pw_sizer.Add(int(self.del_check.Size.height*1.5), 0, wx.ALL, 3)
        self.pw_sizer.Add(self.pw_label, 0, ALL, 3)
        self.pw_sizer.Add(self.pw_text, 0, ALL, 3)

        self.btn_sizer.AddMany([(self.yes_btn, 0, ALL, 3),
                               (self.no_btn, 0, ALL, 3),
                               (self.del_label, 0, ALL, 3)])

        self.in_sizer.AddSpacer(self.help_bmp.Size.width)

        self.delpw_sizer.Add(self.del_check, 0, ALL)
        self.delpw_sizer.Add(self.pw_sizer, 0, ALL, 3)
        self.in_sizer.Add(self.delpw_sizer, 0, ALL, 3)

        self.info_sizer.Add(self.help_bmp, 0, TOP | BOTTOM | ALIGN_CENTER, 3)
        self.info_sizer.Add(self.msg_label, 0, ALL | ALIGN_CENTER, 3)

        self.main_sizer.AddMany([(self.info_sizer, 0, ALL, 3),
                                (self.in_sizer, 0, ALL, 3),
                                (self.btn_sizer, 0, ALIGN_CENTER | ALL, 3)])

        self.Sizer = self.main_sizer

    def yes_clicked(self, e):
        success = lambda: self.EndModal(wx.ID_YES)
        if self.delete:
            if self.acct.password != profile.crypt_pw(self.password):
                wx.MessageBox(_("Incorrect Password"), _("Incorrect Password"))
                return
            self.show_buttons(False)
            self.acct.delete_from_server(self.password,
                                          on_success=success,
                                          on_fail=lambda: (self.show_buttons(),
                                                          wx.MessageBox(message=_("Failed to delete account from the server."),
                                                                        caption=_("Delete Account - Failed"), style=wx.OK)))
        else:
            success()

    def show_buttons(self, val=True):
        self.yes_btn.Enabled = val
        self.no_btn.Enabled = val
        self.yes_btn.Show(val)
        self.no_btn.Show(val)
        self.del_label.Show(not val)

        self.Layout()

    def no_clicked(self, e):
        self.EndModal(wx.NO)

    def on_check(self, e):
        self.pw_text.Enabled = self.delete

    delete = wx_prop('del_check')
    password = wx_prop('pw_text')



class PasswordChangeDialog(wx.Dialog):
    def __init__(self, parent, acct, *a, **k):
        self.acct = acct
        wx.Dialog.__init__(self, parent, title = _('Change Password'), *a, **k)

        self.init_components()
        self.bind_events()
        self.layout_components()

        self.Layout()
        self.Sizer.Fit(self)


    def init_components(self):
        self.old_pw_label  = wx.StaticText(self, label = _("Old Password: "))
        self.old_pw_text   = wx.TextCtrl(self, style=wx.TE_PASSWORD, validator=LengthLimit(1024))
        self.new1_pw_label = wx.StaticText(self, label = _("New Password: "))
        self.new1_pw_text  = wx.TextCtrl(self, style=wx.TE_PASSWORD, validator=LengthLimit(1024))
        self.new2_pw_label = wx.StaticText(self, label = _("Confirm New Password: "))
        self.new2_pw_text  = wx.TextCtrl(self, style=wx.TE_PASSWORD, validator=LengthLimit(1024))

        self.ok_btn = wx.Button(self, wx.ID_OK)
        self.ok_btn.Enable(False)
        self.ok_btn.SetDefault()
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL)

        self.old_sizer  = BoxSizer(HORIZONTAL)
        self.new1_sizer = BoxSizer(HORIZONTAL)
        self.new2_sizer = BoxSizer(HORIZONTAL)

        self.btn_sizer  = build_button_sizer(self.ok_btn, self.cancel_btn, 2)

        self.main_sizer = BoxSizer(VERTICAL)

        self.Sizer      = BoxSizer(HORIZONTAL)

    def bind_events(self):
        self.old_pw_text.Bind(wx.EVT_TEXT, self.check_fields)
        self.new1_pw_text.Bind(wx.EVT_TEXT, self.check_fields)
        self.new2_pw_text.Bind(wx.EVT_TEXT, self.check_fields)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.cancel_clicked)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.ok_clicked)

    def check_fields(self, e):
        old, new1, new2 = self.old_password, self.new1_password, self.new2_password

        self.ok_btn.Enable(all([old, new1, new2]) and new1 == new2)

    def layout_components(self):
        border = (0, ALL, 2)

        self.old_sizer.Add(self.old_pw_label, *border)
        self.old_sizer.AddStretchSpacer()
        self.old_sizer.Add(self.old_pw_text, *border)

        self.new1_sizer.Add(self.new1_pw_label, *border)
        self.new1_sizer.AddStretchSpacer()
        self.new1_sizer.Add(self.new1_pw_text, *border)

        self.new2_sizer.Add(self.new2_pw_label, *border)
        self.new2_sizer.AddStretchSpacer()
        self.new2_sizer.Add(self.new2_pw_text, *border)

        self.main_sizer.AddMany([(self.old_sizer,  0, ALL | EXPAND, 2),
                                 (self.new1_sizer, 0, ALL | EXPAND, 2),
                                 (self.new2_sizer, 0, ALL | EXPAND, 2),
                                 (self.btn_sizer,  0, ALIGN_CENTER |  ALL, 2)])

        self.Sizer = self.main_sizer

    old_password  = wx_prop('old_pw_text')
    new1_password = wx_prop('new1_pw_text')
    new2_password = wx_prop('new2_pw_text')

    def cancel_clicked(self, e):
        self.EndModal(wx.ID_CANCEL)

    def ok_clicked(self, e):
        self.ok_btn.Disable()

        if self.acct.password != self.old_password:
            wx.MessageBox(_("Incorrect Old Password"), _("Incorrect Old Password"))
        elif self.new1_password != self.new2_password:
            wx.MessageBox(_("Passwords do not match"), _("Paswords do not match"))
        else:

            def success(st = None):
                print 'success!', st
                print 'setting password in', self.acct
                from common import profile
                self.acct.password = profile.crypt_pw(self.new1_password)

                for acct in profile.account_manager.accounts:
                    if acct.name == self.acct.username and acct.protocol == self.acct.protocol:
                        acct.update_info(password = profile.crypt_pw(self.new1_password))
                        break

                self.EndModal(wx.ID_OK)

            def error(self, e = None):
                print 'error', e
                self.EndModal(wx.ID_OK)

            self.acct.change_password(self.new1_password, success = success, error = error)

    def Prompt(self, callback):
        #self.callback = callback
        self.ShowModal()

def serialize_xmlnode(node):
    'Returns a unicode string for a libxml2 node.'

    return node.serialize(encoding = 'utf-8', format = True).decode('utf-8')

class XMLConsole(wx.Panel):
    '''
    A simple console for displaying incoming and outgoing Jabber XML.
    '''

    separator_text = '\n\n' # goes between stanzas

    def __init__(self, parent, jabber):
        wx.Panel.__init__(self, parent)

        self.enabled = True
        self.scroll_lock = False

        self.intercept = JabberXMLIntercept(jabber)
        self.intercept.on_incoming_node += lambda node: self.on_node(node, 'incoming')
        self.intercept.on_outgoing_node += lambda node: self.on_node(node, 'outgoing')

        self.construct()
        self.bind_events()
        self.layout()

    @property
    def Connection(self):
        return self.intercept.jabber

    def construct(self):
        'Construct controls.'

        self.console = wx.TextCtrl(self, -1, style = wx.TE_RICH2 | wx.TE_MULTILINE)

        self.enabled_cb = wx.CheckBox(self, -1, _('&Enabled'))
        self.enabled_cb.SetValue(self.enabled)

        self.scroll_lock_cb = wx.CheckBox(self, -1, _('&Scroll Lock'))
        self.scroll_lock_cb.SetValue(self.scroll_lock)

        # until I figure out how to make this work, disable it.
        self.scroll_lock_cb.Enable(False)

        self.buttons = S(clear_b = wx.Button(self, -1, _('C&lear')),
                         close = wx.Button(self, -1, _('&Close')))

        self.font_colors = dict(
            incoming = wx.BLUE,
            outgoing = wx.RED,
        )

    def bind_events(self):
        'Bind events to callbacks.'

        self.enabled_cb.Bind(wx.EVT_CHECKBOX, lambda e: setattr(self, 'enabled', e.IsChecked()))
        self.scroll_lock_cb.Bind(wx.EVT_CHECKBOX, lambda e: setattr(self, 'scroll_lock', e.IsChecked()))
        self.buttons.clear_b.Bind(wx.EVT_BUTTON, lambda e: self.console.Clear())
        self.buttons.close.Bind(wx.EVT_BUTTON, lambda e: self.Top.Destroy())

    def layout(self):
        'Layout controls.'

        self.Sizer = s = wx.BoxSizer(wx.VERTICAL)

        s.Add(self.console, 1, wx.EXPAND | wx.ALL, 7)

        # buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.enabled_cb, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 7)
        button_sizer.AddStretchSpacer(1)
        button_sizer.AddMany([(self.scroll_lock_cb, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 7),
                              (self.buttons.clear_b, 0, wx.RIGHT, 7),
                              (self.buttons.close, 0,   wx.RIGHT, 7)])

        s.Add(button_sizer, 0, wx.EXPAND | wx.BOTTOM, 7)

    def on_check(self, e):
        'Invoked when the "Enabled" checkbox is clicked.'

        self.enabled = e.Checked()

    def on_close(self, e):
        'Invoked when the XML console frame is closing.'

        self.intercept.close()
        self.Top.Destroy()

    def on_node(self, node, node_type):
        '''
        Invoked on the network thread with a libxml2 node and "incoming" or
        "outgoing" for node_type.
        '''

        if self.enabled:
            # no free-ing of the node necessary; it still belongs to the jabber
            # stream
            wx.CallAfter(self.on_node_gui, serialize_xmlnode(node), node_type)

    def on_node_gui(self, node_text, node_type):
        '''
        Invoked on the GUI thread with a serialized XML node and "incoming" or
        "outgoing" for node_type.
        '''
        console = self.console

        style   = console.GetDefaultStyle()
        style.SetTextColour(self.font_colors[node_type])

        start = end = console.GetLastPosition()

        console.SetStyle(start, end, style)

        if self.scroll_lock:
            vpos = console.GetScrollPos(wx.VERTICAL)

        console.AppendText(self.separator_text + node_text)

        if self.scroll_lock:
            console.SetScrollPos(wx.VERTICAL, vpos, True)

class XMLConsoleFrame(wx.Frame):
    'Frame holding the XMLConsole.'

    def __init__(self, connection):
        wx.Frame.__init__(self, None, -1, 'XML Console for %s' % connection.username, name = 'XML Console')

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.panel = XMLConsole(self, connection)
        self.Bind(wx.EVT_CLOSE, self.panel.on_close)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.panel, 1, wx.EXPAND | wx.ALL)

        persist_window_pos(self, nostack = True)
        snap_pref(self)

def show_xml_console(connection):
    '''
    Displays an XML console for connection.

    If an XML console for the connection is already showing, brings it to the
    front.
    '''

    for win in wx.GetTopLevelWindows():
        if isinstance(win, XMLConsoleFrame) and win.panel.Connection is connection:
            log.info('raising existing xml console: %r', win)
            win.Raise()
            return win

    frame = XMLConsoleFrame(connection)
    log.info('created new xml console: %r', frame)
    frame.Show()
    return frame

class JabberXMLIntercept(object):
    'Hooks callbacks up to a Jabber stream for incoming and outgoing stanzas.'

    def __init__(self, jabber):
        self.jabber = jabber

        self.on_incoming_node = Delegate()
        self.on_outgoing_node = Delegate()

        jabber.add_observer(self.state_changed, 'state')
        self.state_changed(jabber)

    def close(self):
        self.jabber.remove_observer(self.state_changed, 'state')

        stream  = self.jabber.stream
        if stream is not None:
            self.disconnect(stream)

        del self.on_incoming_node[:]
        del self.on_outgoing_node[:]

    def state_changed(self, jabber, *a):
        if jabber.state == jabber.Statuses.ONLINE:
            stream = jabber.stream
            if stream is None:
                log.warning('jabber is online but has no stream')
            else:
                self.connect(stream)
        else:
            self.disconnect(stream)

    def connect(self, stream):
        stream.on_incoming_node.add_unique(self.on_incoming_node)
        stream.on_outgoing_node.add_unique(self.on_outgoing_node)

    def disconnect(self, stream):
        stream.on_incoming_node.remove_maybe(self.on_incoming_node)
        stream.on_outgoing_node.remove_maybe(self.on_outgoing_node)
