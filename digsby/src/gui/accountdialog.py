'''

Account editing dialog.

'''
from __future__ import with_statement

import wx
from wx import EXPAND, ALL, ALIGN_CENTER_VERTICAL, ALIGN_RIGHT, LEFT, BOTTOM, TOP

from util import Storage, try_this, import_function, traceguard
from util.primitives.funcs import get, Delegate, do
from gui.toolbox import build_button_sizer
from common.protocolmeta import protocols

from gui.controls import CheckBox, RadioPanel
from gui.clique import Clique
from wx import StaticText, TextCtrl, BoxSizer, RadioButton
from logging import getLogger; log = getLogger('accountdialog')
from gui.validators import LengthLimit, NumericLimit

from config import platformName
from gettext import ngettext
from common import profile

# imported for monkeypatches
import wx.lib.sized_controls

DEFAULT_JABBER_PRIORITY = 5
txtSize = (130, -1)

centerright = ALIGN_CENTER_VERTICAL | ALIGN_RIGHT

#TODO: validators

PortValidator = lambda: NumericLimit(65535)

MAIL_CLIENT_SYSDEFAULT = _('System Default')
MAIL_CLIENT_OTHER      = _('Other Mail Client...')
MAIL_CLIENT_URL        = _('Launch URL...')

def edit_account(parent, account):
    log.info('editing %r', account)

    parent = parent.Top

    diag = AccountPrefsDialog(parent, account = account)
    if platformName == 'mac':
        diag.Center()

    try:
        if diag.ShowModal() != wx.ID_SAVE:
            return # if cancelled
        else:
            account.update_info(**diag.info())
    finally:
        diag.Destroy()


GTALK_FILTERS = ('@gmail.com', '@googlemail.com')

def filter_acct_id(proto, name):
    if proto == 'gtalk' or proto == 'gmail':
        name = name.lower()
        for domain in GTALK_FILTERS:
            if name.endswith(domain):
                name = name[:-len(domain)]
                break
    if proto == 'yahoo':
        if '@yahoo.' in name:
            name = name.lower().split('@yahoo.')[0]
    if proto in ('oscar', 'aim', 'icq'):
        name = name.lower().replace(' ', '')
    return proto, name

def strip_acct_id(proto, name):
    if proto == 'gtalk' or proto == 'gmail':
        for domain in GTALK_FILTERS:
            if name.lower().endswith(domain):
                name = name[:-len(domain)]
                break
    if proto == 'yahoo':
        if '@yahoo.' in name:
            name = name.split('@yahoo.')[0]
    return proto, name

def acctid(proto, name):
    proto, name = filter_acct_id(proto, name)
    return proto + '%%~~%%' + name


class AccountPrefsDialog(wx.Dialog):
    'Small dialog window for editing and creating accounts.'

    # Use the following two methods to create and edit accounts.

    @classmethod
    def create_new(cls, parent, protocol_name):
        '''
        Make a dialog box that can create a new account.
        '''
        return cls(parent, protocol_name = protocol_name)

    @classmethod
    def edit_account(cls, parent, account):
        '''
        Make a dialog box that can edit an existing Account.
        '''
        return cls(parent, account = account)

    #

    def __init__(self, parent, account = None, protocol_name = None):
        "Please do not call directly. See classmethods create_new and edit_account."

        # Editing an existing account
        if account is not None:
            self.new = False
            assert protocol_name is None
            protocolinfo = account.protocol_info()
            self.protocol_name = account.protocol
            title = '%s - %s Settings' % (account.name, protocolinfo.name)

        # Creating a new account
        if account is None:
            self.new = True
            protocolinfo = protocols[protocol_name]
            self.protocol_name = protocol_name
            title = '%s Account' % protocolinfo.name

        # What to call the username (screenname, username, Jabber ID, etc.)
        self.screenname_name = protocolinfo.username_desc

        wx.Dialog.__init__(self, parent, title=title, size=(400,300))
        self.account = account if account is not None else emptystringer(getattr(protocolinfo, 'defaults', None))
        self.new = account is None
        self.protocolinfo = protocolinfo

        # Set the account type icon
        from gui import skin
        self.SetFrameIcon(skin.get('serviceicons.%s' % self.protocol_name))

        self.formtype  = getattr(protocolinfo, 'form', 'default')
        self.info_callbacks = Delegate()

        if self.new:
            self._allaccts = [acctid(a.protocol, a.name) for a in profile.account_manager]

        self.construct(account is None)
        self.layout()

        # enable or disable the save button as necessary.
        self.check_warnings()
        self.Fit()

        # focus the first enabled text control.
        for c in self.Children:
            if isinstance(c, TextCtrl) and c.IsEnabled() and c.IsEditable():
                if c is get(self, 'password', None):
                    c.SetSelection(-1, -1) # only makes sense to select all on a password field :)

                wx.CallAfter(c.SetFocus)
                break

    def info(self):
        'Returns a Storage containing the attributes edited by this dialog.'

        info = Storage(name = self.name.Value,
                       protocol = self.protocol_name)

        info.protocol, info.name = strip_acct_id(info.protocol, info.name)

        if hasattr(self, 'password'):
            info.password_len = len(self.password.Value)
            try:
                info.password = profile.crypt_pw(self.password.Value)
            except UnicodeEncodeError:
                # the database has corrupted the password.
                log.warning('corrupted password')
                info.password = ''
                self.password.Value = ''
                import hub
                hub.get_instance().on_error('This account\'s password has been corrupted somehow. Please report it immediately.')

        if hasattr(self, 'host'):
            info.server = (self.host.Value, int(self.port.Value) if self.port.Value else '')

        if hasattr(self, 'remote_alias'):
            info.remote_alias = self.remote_alias.Value

        if hasattr(self, 'autologin'):
            info.autologin = bool(self.autologin.Value)

        if hasattr(self, 'resource'):
            info.update(resource = self.resource.Value,
                        priority = try_this(lambda: int(self.priority.Value), DEFAULT_JABBER_PRIORITY))
#                        ,
#                        confserver = self.confserver.Value
        if hasattr(self, 'dataproxy'):
            info.update(dataproxy = self.dataproxy.Value)

        for d in getattr(self.protocolinfo, 'more_details', []):
            attr = d['store']
            ctrl = getattr(self, attr)
            info[attr] = ctrl.Value

        getattr(self, 'info_' + self.formtype, lambda *a: {})(info)

        for info_cb in self.info_callbacks:
            info_cb(info)

        defaults = self.protocolinfo.get('defaults', {})
        for k in defaults:
            if k not in info:
                info[k] = getattr(self.account, k, defaults.get(k))

        return info

    def info_email(self, info):
        info.update(Storage(updatefreq = int(self.updatefreq.Value)*60))

        if hasattr(self, 'mailclient'):
            assert isinstance(self.mailclient, basestring)
            info.update(dict(mailclient = self.mailclient,
                             custom_inbox_url = self.custom_inbox_url,
                             custom_compose_url = self.custom_compose_url))

        if hasattr(self, 'emailserver'):
            # email server information
            servertype = self.protocolinfo.needs_server.lower()
            info.update({servertype + 'server': self.emailserver.Value,
                         servertype + 'port' : int(self.emailport.Value) \
                             if self.emailport.Value else '',
                         'require_ssl': self.require_ssl.Value})

            if hasattr(self, 'smtp_server'):
                info.update(email_address     = self.email_address.Value,
                            smtp_server       = self.smtp_server.Value,
                            smtp_port         = int(self.smtp_port.Value) if self.smtp_port.Value else '',
                            smtp_require_ssl  = self.smtp_require_ssl.Value)

                if self.smtp_same.Value:
                    info.update(smtp_username = self.name.Value,
                                smtp_password = self.password.Value)
                else:
                    info.update(smtp_username = self.smtp_username.Value,
                                smtp_password = self.smtp_password.Value)

    def info_social(self, info):
        for d in ((self.new and getattr(self.protocolinfo, 'new_details', []) or []) +
                  getattr(self.protocolinfo, 'basic_details', [])):
            type_     = d['type']

            if type_ in ['bool']:
                attr     = d['store']
                ctrl = getattr(self, attr)
                info[attr] = ctrl.Value
            elif type_ == 'meta':
                key = d['store']
                val = d['value']
                info[key] = val
            elif type_ == 'label':
                pass
            else:
                raise AssertionError("This mechanism needs to be completed!")

        filters = {}
        for key in self.checks:
            filters[key] = []
            for chk in self.checks[key]:
                t, i = chk.Name.split('/')

                assert len(filters[key]) == int(i), (key, len(filters), int(i))
                filters[t].append(chk.Value)

        info['filters'] = filters

    def on_expand(self, e):
        isshown = self.expanded

        self.details.Show(not isshown)
        self.FitInScreen()
        self.expanded = not isshown

        wx.CallAfter(self.Refresh)

    def construct(self, is_new):
        self.construct_common(is_new)
        getattr(self, 'construct_' + self.formtype, getattr(self, 'construct_default'))()

        # after all textboxes have been constructed, bind to their KeyEvents so
        # that we can disable the Save button when necessary

        # Make sure textboxes have values.
        txts = [self.name]

        for textbox in self.get_required_textboxes(all = True):
            textbox.Bind(wx.EVT_TEXT, lambda e: self.check_warnings())

        if self.protocolinfo.get('needs_smtp', False):
            self.Bind(wx.EVT_RADIOBUTTON, lambda e: (e.Skip(), self.check_warnings()))

        # A small arrow for expanding the dialog to show advanced options.
        from gui.chevron import Chevron
        self.expand = Chevron(self, 'Advanced')
        self.expand.Bind(wx.EVT_CHECKBOX, self.on_expand)
        self.expanded = False

        self.AffirmativeId = wx.ID_SAVE
        self.save   = wx.Button(self, wx.ID_SAVE,   _('&Save'))
        self.save.Bind(wx.EVT_BUTTON, self.on_save)
        self.save.SetDefault()
        if is_new or try_this(lambda: self.password.Value, None) == '': self.save.Enable(False)

        self.cancel = wx.Button(self, wx.ID_CANCEL, _('&Cancel'))
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)

    def check_warnings(self):
        warnings = list(getattr(self.protocolinfo, 'warnings', ()))
        warnings.append(dict(checker = self.check_account_unique, critical = True,
                             text = _('That account already exists.')))
        warnings.append(dict(checker = self.filled_in, critical = True))

        warn_texts = []

        enable_save = True
        info = self.info()

        if self.protocolinfo.get('needs_password', True):
            info['plain_password'] = self.password.Value

        for warning in warnings:
            checker = warning.get('checker', None)
            check_passed = True
            if checker is not None:
                check_passed = checker(info)

            if not check_passed:
                text = warning.get('text', None)
                if text is not None:
                    warn_texts.append(text)

                if warning.get('critical', False):
                    enable_save = False

        self.set_warnings(warn_texts)
        self.save.Enable(enable_save)

    def construct_default(self):
        acct = self.account

        # Auto login checkbox: shown by default, turn off with show_autologin = False
        if getattr(self.protocolinfo, 'show_autologin', True):
            self.autologin = wx.CheckBox(self, -1, _('&Auto login'))
            self.autologin.SetToolTipString(_('If checked, this account will automatically sign in when Digsby starts.'))
            self.autologin.Value = bool(getattr(self.account, 'autologin', False))

        # Register new account checkbox: off by default. shows only on when this
        # is a new account dialog, and when needs_register = True
        if self.new and getattr(self.protocolinfo, 'needs_register', False):
            self.register = wx.CheckBox(self, -1, _('&Register New Account'))
            self.register.Bind(wx.EVT_CHECKBOX, self.on_register)

        if getattr(self.protocolinfo, 'needs_remotealias', False):
            self.remote_alias = TextCtrl(self, -1, value = getattr(acct, 'remote_alias', ''), validator = LengthLimit(120))

        if getattr(self.protocolinfo, 'needs_resourcepriority', False):
            # Length limit is according to rfc
            self.resource   = TextCtrl(self, value = getattr(acct, 'resource') or 'Digsby', validator = LengthLimit(1023))

            priority = getattr(acct, 'priority', DEFAULT_JABBER_PRIORITY)
            if priority == '':
                priority = DEFAULT_JABBER_PRIORITY
            self.priority   = TextCtrl(self, value = str(priority), validator = NumericLimit(-127,128))
            self.priority.MinSize = wx.Size(1, -1)

        if getattr(self.protocolinfo, 'needs_dataproxy', False):
            self.dataproxy  = TextCtrl(self, value = getattr(acct, 'dataproxy', ''), validator = LengthLimit(1024))

        if getattr(self.protocolinfo, 'hostport', True):
            server = getattr(self.account, 'server')
            if server: host, port = server
            else:      host, port = '', ''

            self.host = TextCtrl(self, size = (110, -1), value=host, validator = LengthLimit(1023))

            self.port = TextCtrl(self, value = str(port), validator = PortValidator())
            self.port.MinSize = wx.Size(1, -1)

    def on_register(self, event):
        checked = self.register.IsChecked()

        self.save.Label = _(u"&Register") if checked else _(u"&Save")

    def add_warning(self, text):
        lbl = self.label_warnings.Label
        if lbl:
            newlbl = lbl + u'\n' + text
        else:
            newlbl = text
        self.set_warning(newlbl)

    def set_warnings(self, texts):
        self.set_warning('\n'.join(texts))

    def set_warning(self, text):
        self.label_warnings.Label = text

        # FIXME: this throws the sizing on Mac all out of whack. Perhaps some native API gets
        # messed up when called on a hidden control?
        if not platformName == "mac":
            if not text:
                self.label_warnings.Show(False)
            else:
                self.label_warnings.Show(True)

        self.Layout()
        self.Fit()
        self.Refresh()

    def clear_warning(self):
        self.set_warning(u'')

    def construct_common(self, is_new):
        self.label_warnings = StaticText(self, -1, '', style = wx.ALIGN_CENTER)
        self.label_warnings.SetForegroundColour(wx.Colour(224, 0, 0))
        self.clear_warning()

        needs_password =  self.protocolinfo.get('needs_password', True)
        self.label_screenname = StaticText(self, -1, self.screenname_name + ':', style = ALIGN_RIGHT)

        if needs_password:
            self.label_password = StaticText(self, -1, 'Password:', style = ALIGN_RIGHT)


        if self.account.name == '' and hasattr(self.protocolinfo, 'newuser_url'):
            sn = self.url_screenname   = wx.HyperlinkCtrl(self, -1, 'New User?',
                                                     getattr(self.protocolinfo, 'newuser_url'))
            sn.HoverColour = sn.VisitedColour = sn.NormalColour

        if needs_password and hasattr(self.protocolinfo, 'password_url'):
            password = self.url_password     = wx.HyperlinkCtrl(self, -1, 'Forgot Password?',
                                                     getattr(self.protocolinfo, 'password_url'))

            password.HoverColour = password.VisitedColour = password.NormalColour

        if self.protocolinfo.get('needs_smtp', False):
            self.email_address = TextCtrl(self, -1, value = getattr(self.account, 'email_address', ''), size = txtSize, validator=LengthLimit(1024))

        self.name = TextCtrl(self, -1, value=self.account.name, size=txtSize, validator=LengthLimit(1024))

        # disable editing of username if this account is not new
        if not self.new:
            self.name.SetEditable(False)
            self.name.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_SCROLLBAR))
        # self.name.Enable(self.new)

        if needs_password:
            password = self.account._decryptedpw()

            f = lambda p: TextCtrl(self, -1, value = p,
                                          size = txtSize, style = wx.TE_PASSWORD,
                                          validator = LengthLimit(128))
            try:
                self.password = f(password)
            except UnicodeDecodeError:
                self.password = f('')


    def on_cancel(self, e):
        self.EndModal(self.EscapeId)

    def on_save(self, e):
        # Do some simple protocol dependent validation.

        c = get(self.account, 'connection', None)

        if c is not None:
            for updatee in get(c, 'needs_update', []):
                try:
                    attr, fname = updatee
                    f = getattr(c, fname)
                except:
                    attr = updatee
                    f = lambda _v: setattr(c, attr, _v)

                f(getattr(self, attr).Value)

        for attr, validator, message in getattr(self.protocolinfo, 'validators', []):
            if not validator(getattr(self, attr).Value):
                return wx.MessageBox(message, 'Account Information Error')

        if hasattr(self, 'register') and self.register.IsChecked():
            self.save.Enabled = False
            info = self.info()
            log.info_s('adding account: %r', info)
            profile.register_account(
                       on_success = lambda: wx.CallAfter(self.on_success_register),
                       on_fail    = lambda error: wx.CallAfter(self.on_fail_register, error),
                       **info)
        else:
            self.EndModal(wx.ID_SAVE)

    def on_success_register(self):
        self.EndModal(wx.ID_SAVE)

    def on_fail_register(self, error):
        textcode, text, kind, codenum = error
        wx.MessageBox("Error %(codenum)d: %(text)s" % locals(), textcode)
        self.EndModal(wx.ID_CANCEL)

    def EndModal(self, return_code):
        if self.formtype == 'social' and hasattr(self, '_origfilters') and return_code != self.AffirmativeId and self.account:
            if self.account.filters != self._origfilters:
                self.account.filters = self._origfilters
                self.account.notify('alerts')

        wx.Dialog.EndModal(self, return_code)

    def get_required_textboxes(self, all = False):
        tb = [self.name]
        pinfo = self.protocolinfo

        if pinfo.get('needs_password', True):
            tb += [self.password]

        if pinfo.get('needs_smtp', False):
            tb += [self.email_address,
                   self.emailserver, self.emailport,
                   self.smtp_port,   self.smtp_server]

            # when the "same" radio is not checked, the extra SMTP user/pass boxes
            # are required as well.
            if all or not self.smtp_same.Value:
                tb += [self.smtp_username, self.smtp_password]

        if pinfo.get('needs_remotealias', False) and all:
            tb += [self.remote_alias]

        return tb

    def check_account_unique(self, i):
        if self.new:
            return not (acctid(self.protocol_name, i.name) in self._allaccts) or self.protocol_name in ('imap', 'pop')
        else:
            return True

    def filled_in(self, _i):
        return all(tb.Value != '' for tb in self.get_required_textboxes())

    def SwapDefaultPorts(self, event, srv, ssl, portfield):
        stdport = unicode(self.protocolinfo.defaults[srv + 'port'])
        sslport = unicode(self.protocolinfo.defaults[srv + 'port_ssl'])

        rightport, wrongport = (sslport, stdport) if ssl else (stdport, sslport)

        if portfield.Value == wrongport:
            portfield.Value = rightport

        event.Skip()

    def construct_email(self):

        srv = self.protocolinfo.get('needs_server', None)
        if srv is not None:
            srv = srv.lower()
            self.emailserver = TextCtrl(self, -1, size = txtSize,
                                         value = unicode(getattr(self.account, srv + 'server')), validator=LengthLimit(1024))
            self.emailport   = TextCtrl(self, -1, size = (60, -1),
                                         value = unicode(getattr(self.account, srv + 'port')),
                                         validator = PortValidator())
            reqssl = self.require_ssl = CheckBox(self, '&This server requires SSL',
                                        value = bool(self.account.require_ssl))

            reqssl.Bind(wx.EVT_CHECKBOX, lambda e: self.SwapDefaultPorts(e, srv, reqssl.Value, self.emailport))

            smtp = self.protocolinfo.get('needs_smtp', False)
            if smtp: self.construct_smtp()

        updatetext = _('Check for new mail every {n} minutes').split(' {n} ')

        self.updatetext1 = StaticText(self, -1, updatetext[0])
        self.updatetext2 = StaticText(self, -1, updatetext[1])

        # email update frequency
        self.updatefreq = TextCtrl(self, -1, size=(30, -1), validator = NumericLimit(1, 999))

        def update_changed(e):
            e.Skip(True)
            import gettext
            newval = gettext.ngettext(u'minute', u'minutes', int(self.updatefreq.Value or 0))

            if newval != self.updatetext2.Label:
                self.updatetext2.Label = newval

        self.updatefreq.Bind(wx.EVT_TEXT, update_changed)

        minutes = str(self.account.updatefreq/60)

        self.updatefreq.Value = minutes

        if self.protocolinfo.get('needs_webclient', True):
            self.mailclient = self.account.mailclient or 'sysdefault'
            self.custom_inbox_url = self.account.custom_inbox_url
            self.custom_compose_url = self.account.custom_compose_url

            self.mailclienttext = StaticText(self, -1, _('Mail Client:'))
            self.mailclient_choice = wx.Choice(self)
            self.update_mailclient()
            self.mailclient_choice.Bind(wx.EVT_CHOICE, self.on_mailclient_choice)

    def construct_smtp(self):
        self.smtp_server = TextCtrl(self, -1, size = txtSize,
                                     value = unicode(getattr(self.account, 'smtp_server', '')),
                                     validator = LengthLimit(1024),
                                     )
        self.smtp_port   = TextCtrl(self, -1, size = (60, -1),
                                     value = unicode(getattr(self.account, 'smtp_port', '')),
                                     validator = PortValidator())
        reqssl = self.smtp_require_ssl = CheckBox(self, '&This server requires SSL',
                                    value = bool(getattr(self.account, 'smtp_require_ssl', False)))

        reqssl.Bind(wx.EVT_CHECKBOX, lambda e: self.SwapDefaultPorts(e, 'smtp_', reqssl.Value, self.smtp_port))

        servertype = self.protocolinfo.get('needs_server')
        self.smtp_same      = RadioButton(self, -1, _('SMTP username/password are the same as {servertype}').format(servertype=servertype), style = wx.RB_GROUP)
        self.smtp_different = RadioButton(self, -1, _('Log on using:'))

        u = self.smtp_username = TextCtrl(self, -1, size = (110, -1), validator=LengthLimit(1024))
        p = self.smtp_password = TextCtrl(self, -1, size = (110, -1), style = wx.TE_PASSWORD, validator=LengthLimit(1024))

        smtpuser, smtppass = getattr(self.account, 'smtp_username', ''), getattr(self.account, 'smtp_password', '')
        if (not smtpuser and not smtppass) or smtpuser == self.name.Value and smtppass == self.password.Value:
            self.smtp_same.SetValue(True)
            u.Enable(False)
            p.Enable(False)
        else:
            self.smtp_different.SetValue(True)
            u.Enable(True)
            p.Enable(True)

            u.Value = smtpuser
            p.Value = smtppass

        def on_radio(e = None, val = False):
            # when a radio is clicked
            enabled = val if e is None else e.EventObject is not self.smtp_same
            u.Enable(enabled)
            p.Enable(enabled)

        self.Bind(wx.EVT_RADIOBUTTON, on_radio)

    def construct_social(self):
        types = ('alerts','feed', 'indicators')
        self.checks = {}

        if self.account.filters:
            from copy import deepcopy as copy
            self._origfilters = copy(self.account.filters)


        def set_filter(e):
            _t,_i = e.EventObject.Name.split('/')
            keylist = get(self.account,'%s_keys' % _t)
            _k = get(keylist, int(_i))

            self.account.filters[_t][_k] = e.IsChecked()

            if _t == 'alerts':
                self.account.notify(_t)


        for typ in types:
            if getattr(self.protocolinfo, 'needs_%s' % typ, False):
                self.checks[typ] = []

                for i, nicename in enumerate(self.protocolinfo[typ]):
                    key = get(get(self.account,'%s_keys' % typ), i, None)

                    if key is not None:
                        val = self.account.filters[typ][key]
                    else:
                        val = True

                    chk = wx.CheckBox(self, label=nicename, name='%s/%s' % (typ,i))
                    chk.Value = val

                    if self.account:
                        chk.Bind(wx.EVT_CHECKBOX, set_filter)

                    self.checks[typ].append(chk)

    def layout_social(self, sizer, row):
        sizer, row = self.layout_top(sizer, row)

        self.layout_bottom(sizer,row)

    def layout_top(self, sizer, row):
        add = sizer.Add

        for d in ((self.new and getattr(self.protocolinfo, 'new_details', []) or []) +
                   getattr(self.protocolinfo, 'basic_details', [])):
            type_     = d['type']

            if type_ == 'bool':
                attr     = d['store']
                desc     = d['label']
                default  = d['default']
                ctrl = wx.CheckBox(self, -1, desc)

                setattr(self, attr, ctrl)

                s = wx.BoxSizer(wx.HORIZONTAL)
                ctrl.SetValue(getattr(self.account, attr, default) if self.account else default)
                s.Add(ctrl, 0, wx.EXPAND)

                # allow checkboxes to have [?] links next to them
                help_url = d.get('help', None)
                if help_url is not None:
                    from gui.toolbox import HelpLink
                    s.Add(HelpLink(self, help_url), 0, wx.EXPAND)

                add(s, (row,1), (1,3), flag = ALL, border = ctrl.GetDefaultBorder())

                row += 1
            elif type_ == 'label':
                desc = d['label']
                ctrl = wx.StaticText(self, -1, desc)
                add(ctrl, (row,1), (1,3), flag = ALL, border = ctrl.GetDefaultBorder())
                row += 1
            elif type_ == 'meta':
                pass
            else:
                raise AssertionError("This mechanism needs to be completed!")
        return sizer, row


    def build_details_social(self,sizer,row):
        types = ('alerts','feed', 'indicators')
        hsz = BoxSizer(wx.HORIZONTAL)


        d = self.details

        add = lambda c,s,*a: (d.add(c),s.Add(c,*a))

        for i, key in enumerate(types):
            checks = self.checks.get(key,())
            if not checks:
                continue

            sz = BoxSizer(wx.VERTICAL)
            tx = StaticText(self, -1, _('{show_topic}:').format(show_topic = self.protocolinfo['show_%s_label' % key]), style = wx.ALIGN_LEFT)
            from gui.textutil import CopyFont
            tx.Font = CopyFont(tx.Font, weight = wx.BOLD)

            add(tx, sz, 0, wx.BOTTOM, tx.GetDefaultBorder())
            for chk in checks:
                add(chk, sz, 0, ALL, chk.GetDefaultBorder())

            hsz.Add(sz,0)
#            if i != len(types)-1: hsz.AddSpacer(15)

        self.Sizer.Add(hsz,0,wx.BOTTOM | wx.LEFT,10)
        self.build_details_default(sizer, row)

    def update_mailclient(self, mc = None):
        if mc is None:
            mc = self.account.mailclient or ''

        ch = self.mailclient_choice
        with ch.Frozen():
            ch.Clear()

            choices = [MAIL_CLIENT_SYSDEFAULT]

            file_entry = 0
            if mc.startswith('file:'):
                import os.path
                if not os.path.exists(mc[5:]):
                    mc == 'sysdefault'
                else:
                    choices += [_('Custom ({mailclient_name})').format(mailclient_name=mc[5:])]
                    file_entry = len(choices) - 1

            choices += [MAIL_CLIENT_OTHER,
                        MAIL_CLIENT_URL]

            do(ch.Append(s) for s in choices)

            if mc == 'sysdefault':
                selection = 0
            elif mc == '__urls__':
                selection = ch.Count - 1
            else:
                selection = file_entry

            ch.SetSelection(selection)
            ch.Layout()

    def on_mailclient_choice(self, e):
        # TODO: don't use StringSelection, that's dumb.
        val = self.mailclient_choice.StringSelection

        if val.startswith(MAIL_CLIENT_SYSDEFAULT):
            self.mailclient = 'sysdefault'
        elif val == MAIL_CLIENT_OTHER:
            import os, sys
            defaultDir = os.environ.get('ProgramFiles', '')

            wildcard = '*.exe' if sys.platform == 'win32' else '*.*'
            filediag = wx.FileDialog(self, _('Please choose a mail client'),
                                     defaultDir = defaultDir,
                                     wildcard = wildcard,
                                     style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            if filediag.ShowModal() == wx.ID_OK:
                self.mailclient = 'file:' + filediag.Path
        elif val == MAIL_CLIENT_URL:
            diag = LaunchURLDialog(self, self.custom_inbox_url, self.custom_compose_url)
            try:
                if wx.ID_OK == diag.ShowModal():
                    self.mailclient = '__urls__'
                    self.custom_inbox_url = diag.InboxURL
                    self.custom_compose_url = diag.ComposeURL
            finally:
                diag.Destroy()
        else:
            self.mailclient = val

        self.update_mailclient(getattr(self, 'mailclient', 'sysdefault'))

    def build_details_email(self,sizer,row):
        v = BoxSizer(wx.VERTICAL)
        d = self.details

        add = lambda c,s,*a,**k: (d.add(c),s.Add(c,*a,**k))

        # text, update frequency textbox, text
        h = BoxSizer(wx.HORIZONTAL)
        add(self.updatetext1, h, 0, wx.ALIGN_CENTER_VERTICAL | ALL, self.updatetext1.GetDefaultBorder())
        add(self.updatefreq, h, 0, ALL, self.updatefreq.GetDefaultBorder())
        add(self.updatetext2, h, 0, wx.ALIGN_CENTER_VERTICAL | ALL, self.updatetext2.GetDefaultBorder())
        v.Add(h, 0, EXPAND)

        # text, mail client choice
        if hasattr(self, 'mailclient_choice'):
            h2 = BoxSizer(wx.HORIZONTAL)
            add(self.mailclienttext, h2, 0, ALIGN_CENTER_VERTICAL | ALL, self.mailclienttext.GetDefaultBorder())
            add(self.mailclient_choice, h2, 1, ALL, self.mailclient_choice.GetDefaultBorder())
#            h2.Add((30,0))
            v.Add(h2, 0, EXPAND | ALL, 3)
            add(wx.StaticLine(self),v,0,EXPAND|wx.TOP|wx.BOTTOM,3)

        if hasattr(self, 'smtp_same'):
            add(self.smtp_same, v, 0, EXPAND | ALL, self.GetDefaultBorder())
            add(self.smtp_different, v, 0, EXPAND | ALL, self.GetDefaultBorder())
#            v.AddSpacer(3)

            v2 = wx.GridBagSizer(8, 8); v2.SetEmptyCellSize((0,0))
            add(StaticText(self, -1, _('Username:')), v2, (0, 0), flag = ALIGN_CENTER_VERTICAL | ALIGN_RIGHT | ALL, border = self.GetDefaultBorder())
            add(self.smtp_username, v2, (0, 1), flag = ALL, border = self.smtp_username.GetDefaultBorder())
            add(StaticText(self, -1, _('Password:')), v2, (1, 0), flag = ALIGN_CENTER_VERTICAL | ALIGN_RIGHT | ALL, border = self.GetDefaultBorder())
            add(self.smtp_password, v2, (1, 1), flag = ALL, border = self.smtp_password.GetDefaultBorder())

            v.Add(v2, 0, EXPAND | wx.LEFT, 20)
#            v.AddSpacer(3)


        self.Sizer.Add(v,0,wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM,10)

    def layout(self):
        self.Sizer = s = BoxSizer(wx.VERTICAL)

        if hasattr(self, 'label_warnings'):
            warn_sz = BoxSizer(wx.HORIZONTAL)
            warn_sz.Add(self.label_warnings, 1, flag = wx.EXPAND | wx.ALIGN_CENTER)
            s.Add(warn_sz, flag = wx.EXPAND | wx.TOP, border = self.GetDefaultBorder())

        # Top Sizer: username, password, autologin[, register new]
        fx = wx.GridBagSizer(0,0)
        s.Add(fx, 1,  EXPAND|ALL, self.GetDialogBorder())

        # screenname: label, textfield, hyperlink
        row = 0

        fx.SetEmptyCellSize((0,0))

        if self.protocolinfo.get('needs_smtp', False):
            # email address
            label = StaticText(self, -1, _('Email Address'))
            fx.Add(label, (row, 0), flag = centerright | ALL, border = label.GetDefaultBorder())
            fx.Add(self.email_address, (row, 1), flag = ALL, border = self.email_address.GetDefaultBorder())
            row += 1

        # username
        fx.Add(self.label_screenname, (row,0), flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | ALL, border = self.label_screenname.GetDefaultBorder())
        fx.Add(self.name, (row,1), flag = ALL, border = self.name.GetDefaultBorder())
        if hasattr(self, 'url_screenname'):
            fx.Add(self.url_screenname, (row,2), (1,2), flag=ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | ALL, border = self.url_screenname.GetDefaultBorder())

        row += 1

        # password: label, textfield, hyperlink
        if self.protocolinfo.get('needs_password', True):
            fx.Add(self.label_password, (row,0), flag=ALIGN_CENTER_VERTICAL | ALIGN_RIGHT | ALL, border = self.label_password.GetDefaultBorder())
            fx.Add(self.password, (row,1), flag = ALL, border = self.password.GetDefaultBorder())
            if hasattr(self, 'url_password'):
                fx.Add(self.url_password, (row,2), (1,2), flag=ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | ALL, border = self.url_password.GetDefaultBorder())

        fx.AddGrowableCol(1,1)
        row += 1


        getattr(self, 'layout_' + self.formtype, getattr(self, 'layout_default'))(fx, row)
        row += 1

    def layout_default(self, sizer, row):
        add = sizer.Add

        if hasattr(self, 'remote_alias'):
            add(StaticText(self, -1, _('&Display Name:')), (row,0), flag = ALIGN_RIGHT|ALIGN_CENTER_VERTICAL|ALL, border=self.GetDefaultBorder())
            add(self.remote_alias, (row,1),flag = EXPAND | ALL, border = self.remote_alias.GetDefaultBorder())
            row += 1

        # autologin and register new account
        if hasattr(self, 'autologin') or hasattr(self, 'register'):
            checks = BoxSizer(wx.HORIZONTAL)

            if hasattr(self, 'autologin'):
                checks.Add(self.autologin, 0, EXPAND | ALL, self.autologin.GetDefaultBorder())

            if hasattr(self, 'register'):
                #checks.AddSpacer(10)
                checks.Add(self.register, 0, EXPAND | ALL, self.register.GetDefaultBorder())

            sizer.Add(checks, (row,1), (1,3))

            row += 1

        self.layout_bottom(sizer,row)

    def layout_bottom(self, sizer, row):
        s = self.Sizer

        sizer.Add(self.expand, (row, 0), (1,3))
        row+=1

        self.details = Clique()

        account_gui = getattr(self.protocolinfo, 'account_gui', None)
        if account_gui is not None:
            # Protocolmeta can specify a lazy import path to separate
            # GUI components.
            with traceguard:
                self.add_account_gui(account_gui)
        else:
            getattr(self, 'build_details_' + self.formtype,
                    getattr(self, 'build_details_default'))(sizer,row)

        self.expand.Show(bool(self.details))

        self.details.Show(False)
        s.Add(build_button_sizer(self.save, self.cancel, border=self.save.GetDefaultBorder()), 0, EXPAND | ALL, self.GetDefaultBorder())

    def add_account_gui(self, account_gui):
        '''
        Adds account specific GUI to the "extended" section.

        account_gui must be a dotted string import path to a function
        which returns a GUI component, and will be called with two
        arguments: this dialog, and the account we're editing/creating.
        '''

        log.info('loading account GUI from %r', account_gui)
        self.details_panel = import_function(account_gui)(self, self.account)
        self.details.add(self.details_panel)
        self.info_callbacks += lambda info: info.update(self.details_panel.info())

        self.Sizer.Add(self.details_panel, 0, EXPAND | ALL, self.GetDefaultBorder())

    def layout_email(self, gridbag, row):
        add = gridbag.Add

        # email Server, Port
        servertype = getattr(self.protocolinfo, 'needs_server', None)
        if servertype is not None:
            add(wx.StaticLine(self),(row,0),(1,4),flag = EXPAND)

            row +=1

            add(StaticText(self, -1, '&%s Server:' % _(servertype),
                              style = ALIGN_RIGHT), (row, 0), flag = centerright | ALL, border = self.GetDefaultBorder())
            add(self.emailserver, (row, 1), flag = ALL, border = self.emailserver.GetDefaultBorder())
            add(StaticText(self, -1, 'P&ort:', style = ALIGN_RIGHT), (row, 2), flag = centerright | ALL, border = self.GetDefaultBorder())
            add(self.emailport, (row, 3), flag = ALL, border = self.emailport.GetDefaultBorder())
            row += 1

            # This server requires SSL
            add(self.require_ssl, (row, 1), flag = ALL, border = self.require_ssl.GetDefaultBorder())
            row += 1

            if getattr(self.protocolinfo, 'needs_smtp', False):
                add(StaticText(self, -1, _('SMTP Server:'), style = ALIGN_RIGHT), (row, 0), flag = centerright | ALL, border = self.GetDefaultBorder())
                add(self.smtp_server, (row, 1), flag = ALL, border = self.smtp_server.GetDefaultBorder())
                add(StaticText(self, -1, _('Port:'), style = ALIGN_RIGHT), (row, 2), flag = centerright | ALL, border = self.GetDefaultBorder())
                add(self.smtp_port, (row, 3), flag = ALL, border = self.smtp_port.GetDefaultBorder())
                row += 1

                add(self.smtp_require_ssl, (row, 1), flag = ALL, border = self.smtp_require_ssl.GetDefaultBorder())
                row += 1

        self.layout_default(gridbag, row)

    def build_details_default(self,sizer,row):

        Txt = lambda s: StaticText(self, -1, _(s))

        details = self.details

        add = lambda i, *a, **k: (sizer.Add(i, *a, **k),details.add(i))

        #                              position  span
        if hasattr(self, 'host'):
            add(Txt(_('Host:')),     (row, 0), flag = ALIGN_RIGHT|ALIGN_CENTER_VERTICAL|ALL, border = self.GetDefaultBorder())
            add(      self.host,     (row, 1), flag = EXPAND|ALL, border = self.host.GetDefaultBorder())
            add(Txt(_('Port:')),     (row, 2), flag = ALIGN_RIGHT|ALIGN_CENTER_VERTICAL|ALL, border = self.GetDefaultBorder())
            add(      self.port,     (row, 3), flag = EXPAND|ALL, border = self.port.GetDefaultBorder())
            row += 1

        if hasattr(self, 'resource'):
            add(Txt(_('Resource:')),   (row, 0), flag = ALIGN_RIGHT|ALIGN_CENTER_VERTICAL|ALL, border = self.GetDefaultBorder())
            add(      self.resource,   (row, 1), flag = EXPAND|ALL, border = self.resource.GetDefaultBorder())
            add(Txt(_('Priority:')),   (row, 2), flag = ALIGN_RIGHT|ALIGN_CENTER_VERTICAL|ALL, border = self.GetDefaultBorder())
            add(      self.priority,   (row, 3), flag = EXPAND|ALL, border = self.priority.GetDefaultBorder())
            row += 1

        if hasattr(self, 'dataproxy'):
            add(Txt(_('Data Proxy:')), (row, 0), flag = ALIGN_RIGHT|ALIGN_CENTER_VERTICAL|ALL, border = self.GetDefaultBorder())
            add(       self.dataproxy, (row, 1), (1, 3), flag = EXPAND|ALL, border = self.dataproxy.GetDefaultBorder())
            row += 1

        sub2 = BoxSizer(wx.HORIZONTAL)
        col1 = BoxSizer(wx.VERTICAL)
        col2 = BoxSizer(wx.VERTICAL)

#        add = lambda c,r,f,p,s: (details.add(c),s.Add(c,r,f,p))

        for d in getattr(self.protocolinfo, 'more_details', []):
            type_ = d['type']
            name  = d['store']
            if type_ == 'bool':
                ctrl = wx.CheckBox(self, -1, d['label'])
                setattr(self, name, ctrl)

                ctrl.SetValue(bool(getattr(self.account, name)))
                details.add(ctrl)
                col2.Add(ctrl, 0, ALL, ctrl.GetDefaultBorder())
            elif type_ == 'enum':
                ctrl = RadioPanel(self, d['elements'], details)
                setattr(self, name, ctrl)

                ctrl.SetValue(getattr(self.account, name))
                col1.Add(ctrl, 0, ALL, self.GetDefaultBorder())

        sub2.Add(col1,0,wx.RIGHT)
        sub2.Add(col2,0,wx.LEFT)

        self.Sizer.Add(sub2, 0, wx.ALIGN_CENTER_HORIZONTAL)

def choicefor(parent, choices, callback, current_value = None):
    '''
    Returns a wxChoice for a set of choice tuples that calls "callback" when
    it changes.
    '''

    prefnames, displaynames = zip(*choices)
    prefnames = list(prefnames)

    def on_choice(e):
        callback(prefnames[e.GetInt()])

    c = wx.Choice(parent, choices = displaynames)
    c.Selection = prefnames.index(current_value) if current_value in prefnames else 0
    c.Bind(wx.EVT_CHOICE, on_choice)
    c.SetPref = lambda c: setattr(c, 'Selection', prefnames.index(c) if c in prefnames else 0)

    return c



class emptystringer(object):
    def __init__(self, defaults = None):
        self.defaults = {} if defaults is None else defaults

    def __getattr__(self, a):
        return self.defaults.get(a, '')

    def _decryptedpw(self):
        return ''

    def __nonzero__(self):
        return False

# centered, right and left
cr = lambda c: (c, 0, ALIGN_CENTER_VERTICAL | ALIGN_RIGHT)
cl = lambda c: (c, 0, ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)


from gui.toolbox import OKCancelDialog

class LaunchURLDialog(OKCancelDialog):
    '''
    email accounts let you specify custom URLs for inbox and compose actions.
    this dialog lets you enter those URLs.
    '''

    MINSIZE = (350, 1)

    inbox_tooltip   = _('Enter the URL that will be launched when you click "Inbox" for this email account.')
    compose_tooltip = _('Enter the URL that will be launched when you click "Compose" for this email account.')

    def __init__(self, parent, inbox_url = None, compose_url = None):
        OKCancelDialog.__init__(self, parent, title=_('Launch URL'))

        self.construct(inbox_url, compose_url)
        self.layout()

    @property
    def InboxURL(self): return self.inbox_text.Value

    @property
    def ComposeURL(self): return self.compose_text.Value

    def construct(self, inbox_url = None, compose_url = None):
        # construct GUI
        self.inbox_label = StaticText(self, -1, _('Enter a URL for the Inbox'))
        self.inbox_text = TextCtrl(self, -1, inbox_url or '')

        self.compose_label = StaticText(self, -1, _('Enter a URL for the Compose window'))
        self.compose_text = TextCtrl(self, -1, compose_url or '')

        # add tooltips
        self.inbox_label.SetToolTipString(self.inbox_tooltip)
        self.inbox_text.SetToolTipString(self.inbox_tooltip)
        self.compose_label.SetToolTipString(self.compose_tooltip)
        self.compose_text.SetToolTipString(self.compose_tooltip)

        # connect event handlers for disabling OK when there is missing
        # content.
        self.inbox_text.Bind(wx.EVT_TEXT, self.on_text)
        self.compose_text.Bind(wx.EVT_TEXT, self.on_text)
        self.on_text()

    def on_text(self, e = None):
        if e is not None:
            e.Skip()

        self.OKButton.Enable(bool(self.inbox_text.Value and self.compose_text.Value))

    def layout(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany([
            (self.inbox_label,    0, EXPAND | BOTTOM | TOP, 5),
            (self.inbox_text,     0, EXPAND | LEFT, 7),
            (self.compose_label,  0, EXPAND | BOTTOM | TOP, 5),
            (self.compose_text,   0, EXPAND | LEFT, 7),
            self.MINSIZE,
        ])

        self.set_component(sizer)

        self.Fit()

