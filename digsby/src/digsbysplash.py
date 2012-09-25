'''
Digsby splash screen.

Logs in to the Digsby server.
'''

from __future__ import with_statement

import wx
import cgui
from cgui import IsMainThread
#from cgui import LoginWindow
from LoginWindow import LoginWindow
from traceback import print_exc

import hooks
DEFAULT_SPLASH_POS = (300, 300)

from cPickle import dump, load
import os.path
import sys
import path
import syck
import re

import datastore.v0 as datastore

import logging
log = logging.getLogger('loginwindow')

try:
    _
except:
    _ = lambda s: s

SIGN_IN = _("&Sign In")
RESDIR = 'res'
USE_NEW_STORAGE = True or sys.DEV

import datetime

if datetime.date.today().timetuple()[1:3] == (3, 17):
    digsby_logo_filename = 'digsby_stpatricks.png'
else:
    digsby_logo_filename = 'digsbybig.png'

connection_errors = dict(
    auth     = _('Authentication Error'),
    connlost = _('Connection Lost'),
    server   = _('We are upgrading Digsby. Please try connecting again in a few minutes.'),
    client   = _('Could not contact remote server. Check your network configuration.'),
)


class DataProblems(object):
    BAD_USERNAME = _('Invalid Digsby Username')


def GetUserTempDir():
    import stdpaths

    if getattr(sys, 'is_portable', False):
        base_temp = stdpaths.temp / 'digsby'
    else:
        base_temp = stdpaths.userlocaldata

    pth = path.path(base_temp) / 'temp'
    if not pth.isdir():
        os.makedirs(pth)
    return pth


def res(*a):
    return os.path.join(RESDIR, *a)


def digsby_icon_filename():
    return res('digsby.ico')

_icon_bundle = None


def icon_bundle():
    global _icon_bundle
    if _icon_bundle is None:
        _icon_bundle = wx.IconBundleFromFile(digsby_icon_filename(), wx.BITMAP_TYPE_ANY)
    return _icon_bundle

def identity(username):
    return (i for i in hooks.first('digsby.identity.all')
            if i.name == username).next()

def identities():
    return [i for i in hooks.first('digsby.identity.all')]

def last_identity():
    return hooks.first('digsby.identity.last')

class LoginController(object):
    '''
    Shows and interacts with the login window (see LoginWindow.cpp)
    '''

    have_shown_updated = False

    def __init__(self, on_success=lambda *a, **k: None, autologin_override = None):
        # Signing off respawns Digsby with "--noautologin" so that we don't
        # quickly log back in.
        self.allow_autologin = sys.opts.autologin
        self.cancelling = False
        self.on_success = on_success

        self._datastore = datastore.LoginInfo()
        self._profile = sentinel

        profiles, profile = identities(), None
        if profiles:
            profile = last_identity() or profiles[0]
            username = profile.name
            position = profile.get('pos', DEFAULT_SPLASH_POS)
        else:
            username = ''
            position = DEFAULT_SPLASH_POS

        bitmaps = cgui.LoginWindowBitmaps()
        bitmaps.logo = wx.Bitmap(res('digsbybig.png'))
        bitmaps.help = wx.Bitmap(res('skins/default/help.png'))
        bitmaps.settings = wx.Bitmap(res('AppDefaults', 'gear.png'))
        bitmaps.language = wx.Bitmap(res('skins/default/serviceicons/widget_trans.png'))

        revision_string  = ' '.join(str(x) for x in (getattr(sys, 'REVISION', ''),
                                                     getattr(sys, 'TAG', ''),
                                                     getattr(sys, 'BRAND', '')))

        show_languages = False
        self.window = LoginWindow(None, position, bitmaps, str(revision_string), show_languages, profiles)
        self.bind_events()

        try:
            self._set_frame_icon()
        except Exception:
            print_exc()

        cgui.FitInMonitors(self.window)

        status_message = ''

        if not status_message:
            if not self.have_shown_updated and sys.opts.updated:
                status_message = _('Update Successful')
                LoginController.have_shown_updated = True

        self.set_status(status_message)

        if profile:
            self.apply_info(profile)

        # don't allow autologin if the password is empty
        if not profile or not profile.get('password', ''):
            autologin_override = False

        self._init_state(autologin_override)

        @wx.CallAfter
        def doselection():
            un_textbox = self.window.FindWindowById(LoginWindow.USERNAME)
            un_textbox.SetFocus()

        self.setup_languages()

    def setup_languages(self):
        choice = self.window.LanguageChoice
        if choice is None:
            return

        languages = [p.name for p in wx.GetApp().plugins if p.__class__.__name__ == 'LangPluginLoader']

        with choice.Frozen():
            choice.Clear()
            for lang in languages:
                choice.Append(lang)
            if languages:
                choice.SetSelection(0)

    def _set_frame_icon(self):
        wx.Log.SetActiveTarget(wx.LogStderr())
        wx.Log.EnableLogging(False)
        self.window.SetIcons(icon_bundle())
        wx.Log.EnableLogging(True)

    def ShowWindow(self):
        self.window.Show()
        self.window.Raise()

    def DestroyWindow(self):
        import digsbyprofile
        try:
            if digsbyprofile.profile and getattr(digsbyprofile.profile, 'connection', None) is not None:
                digsbyprofile.profile.connection.remove_observer(self.OnStatusChange, 'state')
            self.window.Hide()
        finally:
            self.window.Destroy()

    def bind_events(self):
        bind = self.window.Bind
        bind(wx.EVT_CHECKBOX, self.OnCheck)
        #bind(wx.EVT_TEXT,  self.OnText)
        bind(wx.EVT_CHOICE, self.OnChoice)
        bind(wx.EVT_BUTTON, self.OnButton,          id=wx.ID_OK)
        bind(wx.EVT_BUTTON, self.OnHelpButton,      id=LoginWindow.HELPBUTTON)
        bind(wx.EVT_BUTTON, self.OnCreateProfile,   id=LoginWindow.CREATEPROFILE)
        bind(wx.EVT_HYPERLINK, self.OnPWLink,       id=LoginWindow.FORGOTPASSWORD)
        bind(wx.EVT_HYPERLINK, show_conn_settings,  id=LoginWindow.CONNSETTINGS)
        bind(wx.EVT_CLOSE, self.OnClose)
        bind(wx.EVT_CHOICE, self.OnLanguage,        id=LoginWindow.LANGUAGE)

    def OnLanguage(self, e):
        import main
        main.set_language(['', 'en_LT'][e.Int])
        self.window.UpdateUIStrings()

    def _init_state(self, autologin_override):
        # Call some events to get the initial state set properly
        self.OnCheck(None)
        self.OnText(None)

        # Click the login button if we're auto logging in
        if self._should_autologin(autologin_override):

            # make sure the window has had a chance to paint itself before autologin
            def paint():
                self.window.Refresh()
                self.window.Update()
            wx.CallAfter(paint)

            wx.CallAfter(self.signin)

    def _should_autologin(self, autologin_override):
        # autologin_override is None (ignore), True or False

        if not self.allow_autologin:
            return False

        if autologin_override is not None and not autologin_override:
            return False

        if not self.window.GetAutoLogin() or (autologin_override is not None and not autologin_override):
            return False

        return True

    def disconnect_prof(self):
        import digsbyprofile as d
        if d.profile:
            from AsyncoreThread import call_later
            call_later(d.profile.disconnect)
            if d.profile is self._profile:
                self.unwatch_profile(d.profile)

    def OnClose(self, evt):
        sys.util_allowed = True
        self.window.Hide()
        self.cleanup()
        wx.CallAfter(self.exit)

    def cleanup(self):
        try:
            self.disconnect_prof()
            self.save_info()
        except Exception:
            print_exc()

    def exit(self):
        try:
            self.DestroyWindow()
        except:
            print_exc()

        wx.GetApp().DigsbyCleanupAndQuit()

    def watch_profile(self, p):
        if self._profile is not sentinel:
            self.unwatch_profile(self._profile)
        self._profile = p

    def unwatch_profile(self, p=None):
        if p is None:
            p = self._profile

        if p is self._profile:
            self._profile = sentinel

    def OnButton(self, evt):
        self.signin()

    def signin(self):
        # Set the label early if we're about to import the rest of Digsby,
        # because it may take awhile with a cold cache.
        my_id = identity(self._get_window_username())
        my_id.password = self.window.GetPassword()
        hooks.first('digsby.identity.activate', my_id, raise_hook_exceptions = True)

        if not 'digsbyprofile' in sys.modules:
            sys.util_allowed = True
            self.set_status(_('Loading...'))
            self.window.EnableControls(False, SIGN_IN, False)
            self.window.Update()
            from M2Crypto import m2 #yeah, we're actually Loading...
            m2.rand_bytes(16)       #just in case this chunk of dll isn't in memory, preload
        import digsbyprofile
        if (digsbyprofile.profile and digsbyprofile.profile.is_connected):
            self.window.EnableControls(True, SIGN_IN, True)
            self.disconnect_prof()
            self.cancelling = True
        else:
            self.login()

    def login(self):
        good_data, reason = validate_data(self.get_info().values()[0])
        if not good_data:
            self.set_status(_(reason))
            self.window.EnableControls(True, SIGN_IN, True)
            self.window.Update()
            return

        self.set_status(_('Connecting...'))
        self.window.EnableControls(False, SIGN_IN)
        self.window.Update()

        #self.save_info()

        #info = self.allinfo[self._get_window_username()]
        info = self.get_info()[self._get_window_username()]

        def myfunc():
            import digsby

            try:
                self.cancelling = False
                self.on_success(info)
                import digsbyprofile
                self.watch_profile(digsbyprofile.profile)
            except digsby.DigsbyLoginError:
                # this will NEVER happen. need to switch to using callbacks?!
                self.set_status(_('Login error!'))
                self.window.EnableControls(True, SIGN_IN, True)
                return
            else:
                import digsbyprofile
                if digsbyprofile.profile and getattr(digsbyprofile.profile, 'connection', None) is not None:
                    conn, cb = digsbyprofile.profile.connection, self.OnStatusChange
                    conn.add_observer(cb, 'state')

        wx.CallAfter(myfunc)

    def OnChoice(self, evt):
        evt.Skip()

        last_choice = getattr(self, '_last_choice', 0)

        i = evt.Int
        length = len(evt.EventObject.Items)

        print 'LAST WUT', evt.EventObject.GetCurrentSelection()

        if i == length - 3:
            # the ----- line. do nothing
            self.window.FindWindowById(LoginWindow.USERNAME).SetSelection(last_choice)
        elif i == length - 2:
            # Add Profile
            evt.Skip(False)
            if not self.OnCreateProfile():
                self.window.FindWindowById(LoginWindow.USERNAME).SetSelection(last_choice)

        elif i == length - 1:
            username = self.window.FindWindowById(LoginWindow.USERNAME).GetItems()[last_choice]
            identity_obj = identity(username)
            if identity_obj is None:
                return

            identity_obj.password = self.window.GetPassword()

            if wx.OK == wx.MessageBox(
                _('Are you sure you want to delete profile "%s"?' % username),
                _('Remove Profile'), wx.OK | wx.CANCEL):

                import digsby.digsbylocal as digsbylocal
                try:
                    hooks.first('digsby.identity.delete', username,
                                raise_hook_exceptions=True)
                except digsbylocal.InvalidPassword:
                    wx.MessageBox(_('Please enter the correct password to delete "%s".' % username),
                                  _('Remove Profile'))
                    self.window.FindWindowById(LoginWindow.USERNAME).SetSelection(last_choice)
                else:
                    self.window.set_profiles(identities())
                    self._last_choice = 0
                    self.window.FindWindowById(LoginWindow.PASSWORD).SetValue('')
                    self.window.panel.Layout()
                    self.window.Layout()

            else:
                self.window.FindWindowById(LoginWindow.USERNAME).SetSelection(last_choice)

        else:
            self._last_choice = i
            print 'LAST CHOICE', i
            self.window.FindWindowById(LoginWindow.PASSWORD).SetValue('')

    def OnText(self, evt):
        self._ontextcount = getattr(self, '_ontextcount', 0) + 1
        if getattr(self, "_in_on_text", False):
            return evt.Skip()
        else:
            self._in_on_text = True

        try:
            if evt is not None:
                evt.Skip()

            window = self.window

            if not hasattr(self, 'allinfo'):
                return

            if evt and evt.Id == LoginWindow.USERNAME:
                if self.allinfo.get(self._get_window_username(), None) is not None:
                    self.apply_info(self.allinfo[self._get_window_username()], set_username = False)
                else:
                    window.SetPassword('')

            enabled = bool(self._get_window_username() and window.GetPassword())

            window.FindWindowById(wx.ID_OK).Enable(enabled)
        finally:
            self._in_on_text = False

    def OnCheck(self, evt):
        if not self.window.GetSaveInfo():
            self.window.SetAutoLogin(False)

        if evt and evt.GetId() == LoginWindow.SAVEPASSWORD and evt.GetInt() and getattr(sys, 'is_portable', False):
            if not self.do_portable_security_warning():
                self.window.SetAutoLogin(False)
                self.window.FindWindowById(LoginWindow.SAVEPASSWORD).Value = False
                self.save_info()
                return

        if evt and evt.GetId() in (LoginWindow.SAVEPASSWORD, LoginWindow.AUTOLOGIN):
            self.save_info()

    def do_portable_security_warning(self):
        security_warning_hdr = _("Your password will be saved on your portable device.")
        security_warning_q = _("Anyone with access to this device will be able to log into your Digsby account. "
                               "Are you sure you want to save your password?")

        security_msg = u'%s\n\n%s' % (security_warning_hdr, security_warning_q)

        dlg = wx.MessageDialog(self.window, security_msg, _("Security Information"), wx.ICON_EXCLAMATION | wx.YES_NO)

        response = dlg.ShowModal()

        return response == wx.ID_YES

    def OnPWLink(self, evt):
        dlg = wx.MessageDialog(
            None,
            _("For security, your password is not saved anywhere. "
              "If you forget it, there is no way to decrypt the "
              "account information for that profile. You'll need "
              "to remove the profile, create a new one, and add "
              "your accounts back."),
            _('Forgotten password'),
            wx.OK)

        dlg.ShowModal()

    def OnHelpButton(self, evt = None):
        wx.LaunchDefaultBrowser('http://wiki.digsby.com')

    def OnCreateProfile(self, evt=None):
        from gui.profiledialog import ProfileDialog

        # show a profile dialog
        dialog = ProfileDialog(self.window)
        self.profile_dialog = dialog
        dialog.CenterOnParent()

        res = dialog.ShowModal()

        if res != wx.ID_OK: return

        # create the identity
        username, password = dialog.GetUsername(), dialog.GetPassword()
        assert username and password

        if dialog.is_new_profile:
            hooks.first('digsby.identity.create', username, password)
        else:
            hooks.first('digsby.identity.get', username, password)

        self.window.set_profiles(identities(), username, password)
        self._last_choice = self.window.FindWindowById(LoginWindow.USERNAME).GetSelection()
        self.window.panel.Layout()
        self.window.Layout()

        return True

    def OnStatusChange(self, src, attr, old, new):
        assert attr == 'state'
        wx.CallAfter(self.OnStatusChanged, src, attr, old, new)

    def OnStatusChanged(self, src, attr, old, new):

        if wx.IsDestroyed(self.window):
            log.warning("Warning: splash screen is Destroyed but still getting notified.")
            return

        if self.cancelling and new != src.Statuses.OFFLINE:
            src.disconnect()

        if new in (src.Statuses.CONNECTING, src.Statuses.AUTHENTICATING, src.Statuses.SYNC_PREFS, src.Statuses.AUTHORIZED):
            self.window.EnableControls(False, SIGN_IN, False)

        def f():
            if self.cancelling or new == src.Statuses.OFFLINE:

                if self.cancelling:
                    self.set_status('')
                else:
                    self.set_status(_(src.offline_reason))
                self.window.EnableControls(True, SIGN_IN, True)
            else:
                self.window.EnableControls(False, SIGN_IN)
                self.set_status(_(new))

        wx.CallAfter(f)

    def set_status(self, label, window_title = None, do_conn_error=False):
        '''
        Changes the main label and the window title.

        If not window title is given, it is set to be the same as the label.
        '''
        assert IsMainThread()

        conn_fail_message = _('Failed to Connect')

        self.window.SetStatus(label, window_title or '')

        if label == _('Authentication Error') and not getattr(self, 'auth_error_fired', False):
            self.auth_error_fired = True
            line1 = _('Please make sure you have entered your Digsby username and password correctly.')
            line2 = _('If you need an account or forgot your password, use the links on the login screen.')
            wx.MessageBox(u'%s\n%s' % (line1, line2), _('Authentication Error'))
        if do_conn_error:
            #TODO: fix protocol states.
            if label == conn_fail_message and not getattr(self, 'connect_error_fired', False):
                self.connect_error_fired = True
                wx.MessageBox(_('Please check your Internet connection and make sure a firewall isn\'t blocking Digsby.\n'
                                'If you connect to the Internet through a proxy server,\n'
                                'click the "Connection Settings" link to set up the proxy.\n'
                                'If you are still unable to connect, email bugs@digsby.com for technical support.'),
                              _('Failed to Connect'))

    def _get_window_username(self):
        return self.window.GetUsername().strip()

    def get_info(self):
        assert IsMainThread()
        find = self.window.FindWindowById

        window = self.window
        username = self._get_window_username()

        info_dict = dict(
            username=username,
            password=window.GetPassword(),
            save=window.GetSaveInfo(),
            autologin=window.GetAutoLogin()
        )

        return {username: info_dict}

    def apply_info(self, info, set_username=True):
        w = self.window
        if set_username:
            w.SetUsername(info.name)
        w.SetPassword(info.password or '')
        w.SetSaveInfo(info.get('save', False))
        w.SetAutoLogin(info.get('autologin', False))

    def set_username(self, username):
        self.window.SetUsername(username)

    def set_password(self, password):
        self.window.SetPassword(password)

    def save_info(self):
        username = self._get_window_username()
        if not username or username == u'------------------------------':
            return

        userinfo = self.get_info()
        profile = identity(username)

        for k in ('save', 'autologin'):
            profile.set(k, userinfo[username][k])

        if userinfo[username].get('save'):
            profile.set('saved_password', userinfo[username]['password'])
        else:
            profile.set('saved_password', '')

    def proto_error(self, exc):
        import digsby

        msgbox = None

        if exc is None:
            message = _('Failed to Connect')
        else:
            try:
                raise exc
            except digsby.DigsbyLoginError:
                if exc.reason == 'auth':
                    message = _('Authentication Error')
                elif exc.reason == 'connlost':
                    message = _('Connection Lost')
                else:
                    message = _('Failed to Connect')

                if exc.reason == 'server':
                    msgbox = _("We are upgrading Digsby. Please try connecting again in a few minutes.")
                elif exc.reason == 'client':
                    msgbox = _('Could not contact remote server. Check your network configuration.')

            except Exception:
                print_exc()
                message = _("Failed to Connect")

        self.set_status(message, do_conn_error=True)
        self.window.EnableControls(True, SIGN_IN, True)
        self.disconnect_prof()

        if msgbox is not None:
            wx.MessageBox(msgbox, message)

def show_conn_settings(evt):
    sys.util_allowed = True
    from gui.proxydialog import ProxyDialog
    import util

    parent = None
    for tlw in wx.GetTopLevelWindows():
        if isinstance(tlw, LoginWindow):
            parent = tlw

    p = ProxyDialog(parent)
    p.CenterOnParent()

    def later():
        try:
            p.ShowModal()
        except Exception:
            print_exc()
        else:
            hooks.notify('proxy.info_changed', util.GetProxyInfo())
        finally:
            p.Destroy()

    wx.CallAfter(later)


def validate_data(info):
    # copypasta'd from util/net.py since we can't import util yet
    email_regex_string = r'^(?:([a-zA-Z0-9_][a-zA-Z0-9_\-\.]*)(\+[a-zA-Z0-9_\-\.]+)?@((?:[a-zA-Z0-9\-_]+\.?)*[a-zA-Z]{1,4}))$'

    if not re.match(email_regex_string, info['username'] + '@digsby.org'):
        log.error('Bad username: %r', info['username'])
        return False, DataProblems.BAD_USERNAME

    return True, None
