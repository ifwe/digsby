import hooks
import wx
import digsby.blobs as blobs
import digsby.accounts as accounts
from digsby.DigsbyProtocol import DigsbyProtocol
from wx import WHITE, HORIZONTAL, VERTICAL, ALIGN_RIGHT, ALIGN_CENTER_VERTICAL, EXPAND, ALIGN_LEFT, ALL
from cgui import SimplePanel
from gui.uberwidgets.PrefPanel import PrefPanel
from gui.validators import NumericLimit
from config import platformName
import util.proxy_settings
import util.callbacks as callbacks

import logging
log = logging.getLogger('gui.profiledialog')

ID_NEWPROFILE = wx.NewId()
ID_IMPORTPROFILE = wx.NewId()

class ProfilePanel(SimplePanel):
    WRAP_WIDTH = 356

    def __init__(self, parent, validator = None):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)
        self.validator = validator

        if platformName != 'mac':
            self.BackgroundColour = WHITE

        sz = self.Sizer = wx.BoxSizer(VERTICAL)

        profile_type = wx.Panel(self)
        rs = profile_type.Sizer = wx.BoxSizer(VERTICAL)

        RADIO = wx.RadioButton
        overrads = self.overrads = dict(NEWPROFILE    = RADIO(profile_type, ID_NEWPROFILE,    _("&New Profile"), style = wx.RB_GROUP),
                                        IMPORTPROFILE = RADIO(profile_type, ID_IMPORTPROFILE, _("&Import an existing profile from the Digsby servers")))

        rs.Add(overrads["NEWPROFILE"], 0, ALL, 2)
        rs.Add(overrads["IMPORTPROFILE"], 0, ALL, 2)

#-------------------------------------------------------------------------------
        login_info = wx.Panel(self)

        ps = wx.FlexGridSizer(2, 2)

        TEXT = lambda s: wx.StaticText(login_info, -1, s)
        INPUT = lambda d, style = 0, v = wx.DefaultValidator: wx.TextCtrl(login_info, -1, d, style = style, validator = v)

        digsby_username = self.digsby_username = INPUT('')
        digsby_password = self.digsby_password = INPUT('', style = wx.TE_PASSWORD)

        ps.Add(TEXT(_("&Digsby Username:")), 0, ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)
        ps.Add(digsby_username, 0, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)

        ps.Add(TEXT(_("Digsby &Password:")), 0, ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)
        ps.Add(digsby_password, 0, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)

        ps.AddGrowableCol(1, 1)

        login_info.Sizer = wx.BoxSizer(wx.VERTICAL)
        login_info.Sizer.Add(ps, 1, wx.EXPAND)
        self.login_status_text = TEXT('')
        self.login_status_text.Hide()
        login_info.Sizer.Add(self.login_status_text, 0, wx.EXPAND | wx.ALL, 7)

#-------------------------------------------------------------------------------

        profile_info = wx.Panel(self)
        aus = profile_info.Sizer = wx.FlexGridSizer(2, 2)

        aus = wx.FlexGridSizer(2, 2)

        TEXT = lambda s: wx.StaticText(profile_info, -1, s)
        INPUT = lambda d, style = 0, id=-1: wx.TextCtrl(profile_info, id, d, style = style)

        profile_name = self.profile_name = INPUT('')
        profile_password = self.profile_password = INPUT('', wx.TE_PASSWORD)
        reenter_password = self.profile_password_2 = INPUT('', wx.TE_PASSWORD)

        aus.Add(TEXT(_("&Profile Name:")), 0, ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)
        aus.Add(profile_name, 0, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)

        aus.Add(TEXT(_("&Profile Password:")), 0, ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)

        s = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(profile_password, 1, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND)
        s.Add(TEXT(_('(optional)')), 0, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | wx.LEFT | wx.TOP, 5)
        aus.Add(s, 1, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)

        aus.Add(TEXT(_("&Re-Enter Password:")), 0, ALIGN_RIGHT | ALIGN_CENTER_VERTICAL | ALL, 2)

        s = wx.BoxSizer(wx.HORIZONTAL)
        s.Add(reenter_password, 1, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND)
        s.Add(TEXT(_('(optional)')), 0, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | wx.LEFT | wx.TOP, 5)
        aus.Add(s, 1, ALIGN_LEFT | ALIGN_CENTER_VERTICAL | EXPAND | ALL, 2)

        aus.AddGrowableCol(1, 1)

        password_note = TEXT(_('NOTE: For security, your password is not saved anywhere. If you forget it, there is no way to decrypt the account information for that profile. You\'ll need to remove the profile, create a new one, and add your accounts back.'))
        password_note.SetForegroundColour(wx.RED)
        password_note.Wrap(356)

        profile_info.Sizer = wx.BoxSizer(VERTICAL)
        profile_info.Sizer.Add(aus, 0, EXPAND | ALL)
        profile_info.Sizer.Add(password_note, 0, EXPAND | ALL, 7)

#-------------------------------------------------------------------------------

        self.profile_info_panel = PrefPanel(self, profile_info, _("Profile Info"))
        self.login_info_panel   = PrefPanel(self, login_info, _("Login Info"))
        self.login_info_panel.Show(False)

        sz.Add(PrefPanel(self, profile_type, _("Profile Type")), 0, EXPAND | ALL, 2)
        sz.Add(self.profile_info_panel, 0, EXPAND | ALL, 2)
        sz.Add(self.login_info_panel, 0, EXPAND | ALL, 2)

        Bind = self.Bind
        Bind(wx.EVT_RADIOBUTTON, self.OnRadio)
        Bind(wx.EVT_TEXT, self.validate_form)

        if platformName != 'mac':
            Bind(wx.EVT_PAINT, self.OnPaint)

        self.validate_form()

    def SetImportStatusText(self, text, red=False):
        '''Sets the text below the "import account" section.'''

        self.login_status_text.SetLabel(text)
        self.login_status_text.Wrap(356)
        self.login_status_text.Show(bool(text))
        self.login_status_text.SetForegroundColour(wx.RED if red else wx.BLACK)
        self.Layout()

    def validate_form(self, evt = None):
        valid = True

        if self.is_new_profile:
            if not self.profile_name.Value:
                valid = False
            if not self.profile_password.Value:
                valid = False
        else:
            if not self.digsby_username.Value:
                valid = False
            if not self.digsby_password.Value:
                valid = False

        if self.validator:
            self.validator(valid)

    def passwords_match(self):
        if self.is_new_profile:
            return self.profile_password.Value and self.profile_password.Value == self.profile_password_2.Value
        else:
            return True

    def OnRadio(self, event):
        new = self.is_new_profile
        self.profile_info_panel.Show(new)
        self.login_info_panel.Show(not new)
        self.Layout()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        rect = wx.RectS(self.ClientSize)
        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN
        dc.DrawRectangleRect(rect)

    @property
    def is_new_profile(self):
        return self.overrads['NEWPROFILE'].Value


class ProfileDialog(wx.Dialog):
    def __init__(self, parent = None):
        wx.Dialog.__init__(self, parent, title = _('Add Profile'))

        if not platformName == 'mac':
            self.SetBackgroundColour(wx.WHITE)

        bsz = wx.BoxSizer(wx.HORIZONTAL)
        self.ok_button = okb = wx.Button(self, wx.ID_OK, _("&OK"))
        okb.SetDefault()
        self.cancel_button = canb = wx.Button(self, wx.ID_CANCEL, _("&Cancel"))
        bsz.Add(okb, 0, ALL, 4)
        bsz.Add(canb, 0, ALL, 4)

        self.Sizer = wx.BoxSizer(VERTICAL)
        self.pp = ProfilePanel(self, self.on_validate)
        self.Sizer.Add(self.pp, 1, EXPAND | ALL, 5)

        self.Sizer.Add(bsz, 0, ALIGN_RIGHT)

        okb.Bind(wx.EVT_BUTTON, self.OnOK)
        canb.Bind(wx.EVT_BUTTON, lambda e: self.Close())

        self.Fit()
        self.Size = wx.Size(400, self.Size.height)

        self.Layout()
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.profile_importer = None

    def on_validate(self, valid):
        self.ok_button.Enabled = valid

    def GetUsername(self):
        if self.pp.is_new_profile:
            return self.pp.profile_name.Value
        else:
            return self.pp.digsby_username.Value

    def SetImportStatusText(self, text, red=False):
        return self.pp.SetImportStatusText(text, red)

    def GetPassword(self):
        if self.pp.is_new_profile:
            return self.pp.profile_password.Value
        else:
            return self.pp.digsby_password.Value

    def OnClose(self, event):
        self.Show(False)

    def OnOK(self, event):
        if hooks.first('digsby.identity.exists', self.GetUsername()):
            wx.MessageBox(_('A profile named "%s" already exists. Please choose a different name or remove the existing profile.') % self.GetUsername(),
                          _('Profile exists'))
            return

        if not self.pp.passwords_match():
            wx.MessageBox(_('Please ensure your passwords match.'),
                          _('Passwords do not match'))
        else:
            if self.pp.is_new_profile:
                self.CloseWithOK()
            else:
                self.SetImportStatusText(_("Importing..."))
                self.ok_button.Enabled = False
                self.profile_importer = import_profile(self.GetUsername(), self.GetPassword(),
                                                       success = self.import_profile_success,
                                                       error = self.import_profile_error,
                                                       progress = self.update_status_text)

    def update_status_text(self, pi):
        self.SetImportStatusText(pi.connection.state)

    @property
    def is_new_profile(self):
        return self.pp.is_new_profile

    def CloseWithOK(self):
        self.SetReturnCode(wx.ID_OK)
        self.Close()

    def import_profile_success(self):
        log.info("Got profile!")
        wx.CallAfter(self.CloseWithOK)

    def import_profile_error(self, err_text = None):
        if err_text is not None:
            self.SetImportStatusText(err_text, True)

        if self.profile_importer is None:
            return

        log.info("Error getting profile")
        pi, self.profile_importer = self.profile_importer, None

        if hooks.first('digsby.identity.exists', pi.identity.name):
            hooks.first('digsby.identity.delete', pi.identity.name, pi.identity.password)

        # Form validation will re-enable OK button
        self.pp.validate_form()

        if not err_text:
            self.SetImportStatusText(_("An error occurred."), red = True)


def import_profile(username, password, callback):
    profile_importer = DigsbyProfileImporter(username, password)
    profile_importer.import_profile(callback = callback)
    return profile_importer
import_profile = callbacks.callsback(import_profile, ('success', 'error', 'progress'))


class DigsbyProfileImporter(object):
    def __init__(self, username, password):
        self.callback = None
        self.identity = hooks.first('digsby.identity.create', username, password)
        self.connection = DigsbyProtocol(
            username, password,
            profile = Null,
            user = None,
            server = ("digsby.org", 5555),
            login_as='invisible',
            do_tls = False,
            sasl_md5 = False,
            digsby_login = True
        )

    def import_profile(self, callback = None):
        if self.callback is not None:
            raise Exception("Import already in progress")

        self.callback = callback
        self.connection.add_observer(self.on_conn_state_changed, 'state', 'offline_reason')
        self.connection.Connect(invisible = True, on_fail = self._on_conn_error)
    import_profile = callbacks.callsback(import_profile, ('success', 'error', 'progress'))

    def _on_conn_error(self, *a):
        self.error()

    def on_conn_state_changed(self, source, attr, old, new):
        if source is not self.connection:
            return

        if attr == 'offline_reason' and new == self.connection.Reasons.BAD_PASSWORD:
            return self.error(self.connection.offline_reason)

        if attr != 'state':
            return

        self.progress()

        if old == self.connection.Statuses.AUTHORIZED or new != self.connection.Statuses.AUTHORIZED:
            return

        log.info("Importer connection status: %r -> %r", old, new)

        blob_names = blobs.name_to_ns.keys()

        self.waiting_for = set(blob_names)

        for blob_name in blob_names:
            log.info("Requesting blob: %r", blob_name)
            self.connection.get_blob_raw(blob_name,
                                         success = self._blob_fetch_success,
                                         error = self._blob_fetch_error)

        self.waiting_for.add('accounts')
        self.connection.get_accounts(success = self._accounts_fetch_success,
                                     error = self._accounts_fetch_error)

    def got_item(self, name, data):
        log.info("Got blob: %r, saving.", name)
        self.identity.set(name, data)
        self.waiting_for.discard(name)
        log.info("\tNow waiting for: %r", self.waiting_for)

        if not len(self.waiting_for):
            self.success()

    def _blob_fetch_success(self, stanza):
        ns = stanza.get_query_ns()
        blob = blobs.ns_to_obj[ns](stanza.get_query())
        name = blobs.ns_to_name[ns]

        self.got_item(name, blob.data)

    def _blob_fetch_error(self, *_a):
        self.error()

    def _accounts_fetch_success(self, stanza):
        fetched_accounts = accounts.Accounts(stanza.get_query())
        self.got_item('accounts', fetched_accounts)

    def _accounts_fetch_error(self, *_a):
        self.error()

    def disconnect(self):
        conn, self.connection = self.connection, None
        if conn is not None:
            conn.remove_observer(self.on_conn_state_changed, 'state')
            conn.Disconnect()

    def progress(self):
        callback = getattr(self, 'callback', None)
        if callback is not None:
            getattr(callback, 'progress', lambda x: None)(self)

    def error(self, *a):
        self._cleanup('error', *a)

    def success(self):
        self._cleanup('success')

    def _cleanup(self, status, *a):
        util.threaded(self.disconnect)()
        callback, self.callback = self.callback, None

        if callback is not None:
            getattr(callback, status, lambda: None)(*a)


if __name__ == "__main__":
    from tests.testapp import testapp
    app = testapp()

    f = ProfileDialog()
    f.Show(True)

    app.MainLoop()
