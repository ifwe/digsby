import logging
log = logging.getLogger("service_editor.default_ui")
import wx
import gui.toolbox as toolbox
import gui.controls as controls

import common

## Some defaults and constants for building the dialogs:

txtSize = (130, -1)
halfTxtSize = (60, -1)  # Not actually half, but appropriate for the layout
qtrTxtSize = (30, -1)

center_right_all = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.ALL
center_left_all = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.ALL

def ezadd(sz, ctrl, *a, **k):
    '''
    Add a ctrl to a sz (sizer). Additional arguments will be passed to the sizer's Add function. Respects the control's DefaultBorder.
    '''
    do_border = k.pop('border', True)
    if do_border is True or do_border is False:
        border = getattr(ctrl, 'GetDefaultBorder', lambda:0)() * do_border
    else:
        border = do_border
    k['border'] = border
    sz.Add(ctrl, *a, **k)

def AddRowToGridBag(gb, stuff, spans=None):
    '''
    Adds a new row to a grid bag sizer containing "stuff", which is a mapping of strings to wx controls. The controls will span columns 
    specified by 'spans' (a mapping of strings to (int, int) tuples).

    Valid keys in 'stuff' and 'spans' are:
        check
        label
        choice
        url
        portlabel
        porttext

    Spans are not required, and defaults are given in the code below.
    '''
    if stuff is None:
        return
    if spans is None:
        spans = {}

    gb.row = getattr(gb, 'row', 0)

    if 'check' in stuff:
        ezadd(gb, stuff['check'], (gb.row, 1), spans.get('check', (1, 3)), flag = wx.EXPAND | wx.ALL)
    else:
        ezadd(gb, stuff['label'], (gb.row, 0), spans.get('label', (1, 1)), flag = center_right_all)
        if 'text' in stuff:
            ezadd(gb, stuff['text'], (gb.row, 1), spans.get('text', (1, 1)), flag = wx.ALL)
        elif 'choice' in stuff:
            ezadd(gb, stuff['choice'], (gb.row, 1), spans.get('choice', (1, 3)), flag = wx.ALL)

        if 'url' in stuff:
            ezadd(gb, stuff['url'], (gb.row, 2), spans.get('url', (1, 2)), flag = center_left_all)

        elif "portlabel" in stuff:
            ezadd(gb, stuff['portlabel'], (gb.row, 2), spans.get('portlabel', (1, 1)), flag = center_right_all)
            ezadd(gb, stuff['porttext'], (gb.row, 3), spans.get('porttext', (1, 1)), flag = wx.ALL)

    gb.row += 1

def AddLineToGridBag(gb, parent):
    '''
    Add a static line control to a grid bag sizer.
    '''
    gb.row = getattr(gb, 'row', 0)
    ezadd(gb, wx.StaticLine(parent), (gb.row, 0), (1, 4), flag = wx.EXPAND | wx.ALL, border = 5)
    gb.row += 1

def title_for_service(sp, sp_info):
    '''
    The title for the dialog.
    '''
    if sp is None:
        title = unicode(sp_info.name)
    else:
        title = _(u"{account_name:s} - {service_name:s} Settings").format(account_name=sp.name,
                                                                          service_name=sp_info.name)
    return title

def LabelText(parent, label, labelStyle = wx.ALIGN_RIGHT, textStyle = 0, textSize = txtSize):
    '''
    Create a label with a text control next to it.
    '''
    label = wx.StaticText(parent, -1, label, style = labelStyle)
    text = wx.TextCtrl(parent, -1, style = textStyle, size = textSize)

    return dict(label = label, text = text)

def LabelChoice(parent, label, labelStyle = wx.ALIGN_RIGHT):
    '''
    Create a label with a wx.Choice control next to it
    '''
    label = wx.StaticText(parent, -1, _('Mail Client:'), style = labelStyle)
    choice = wx.Choice(parent)

    return dict(label = label, choice = choice)

def HyperlinkControl(parent, label, url):
    '''
    Creates a hyperlink control with the given label and destination URL. Sets all display colors to be the same.
    '''
    hlc = wx.HyperlinkCtrl(parent, -1, label, url)
    hlc.HoverColour = hlc.VisitedColour = hlc.NormalColour

    return hlc

def LabelTextUrl(parent,  label, url_label, url,
                 labelStyle = wx.ALIGN_RIGHT,
                 textStyle = 0,
                 textSize = txtSize):
    '''
    Create a trio of label, text field, and URL controls.
    '''
    controls = LabelText(parent, label, labelStyle, textStyle, textSize)

    controls['url'] = HyperlinkControl(parent, url_label, url)
    controls['url'].MoveBeforeInTabOrder(parent.Children[0])

    return controls

def ServerPort(parent, server_label, port_label = _("Port:")):
    '''
    Creates two (label, text) pairs for use in entering a server address and port number.
    '''
    server = LabelText(parent, server_label)
    port = LabelText(parent, port_label, textSize = halfTxtSize)

    server['portlabel'] = port['label']
    server['porttext'] = port['text']
    return server

# Construct
## Basic
def construct_basic_panel(parent, SP, MSP):
    # TODO: bind and populate
    panel = getattr(parent, 'basic_panel', None)
    if panel is None:
        panel = wx.Panel(parent = parent)

    if getattr(panel, 'controls', None) is None:
        panel.controls = {}

    sz = panel.Sizer = wx.BoxSizer(wx.VERTICAL)

    # Warnings label
    warnings_lbl = panel.controls['warnings_lbl'] = wx.StaticText(panel, -1, '', style = wx.ALIGN_CENTER)
    warnings_lbl.SetForegroundColour(wx.Colour(224, 0, 0))
    warnings_lbl.Show(False)
    warn_sz = wx.BoxSizer(wx.HORIZONTAL)
    warn_sz.Add(warnings_lbl, 1, flag = wx.EXPAND | wx.ALIGN_CENTER | wx.ALL, border = warnings_lbl.GetDefaultBorder())
    sz.Add(warn_sz, flag = wx.EXPAND | wx.TOP, border = panel.GetDefaultBorder())

    fx = wx.GridBagSizer(0, 0)
    fx.SetEmptyCellSize((0, 0))
    fx.AddGrowableCol(1,1)
    fx.row = 0

    panel.controls['basic_sz'] = fx

    sz.Add(fx, 1, wx.EXPAND | wx.ALL, panel.Top.GetDialogBorder())

    return panel

def construct_basic_subpanel_provider(panel, SP, MSP, MSC):
    # TODO: bind and populate
    fx = panel.controls['basic_sz']

    emailaddress_stuff = username_stuff = password_stuff = None

    if MSP.info.provider_info.get('needs_smtp', False):
        emailaddress_stuff = LabelText(panel, _("Email Address:"))
        emailaddress_stuff['text'].Value = getattr(SP, 'email_address', u'')
        emailaddress_stuff['text'].SetFocus()

    if SP is None and MSP.info.provider_info.get('newuser_url', None) is not None:
        username_stuff = LabelTextUrl(panel,
                                            MSP.info.provider_info.get('username_desc', _("Username")) + ':',
                                            _("New User?"),
                                            MSP.info.provider_info.newuser_url)
    else:
        username_stuff = LabelText(panel,
                                   MSP.info.provider_info.get('username_desc', _("Username")) + ':')

    if SP is not None:
        username_stuff['text'].Value = getattr(SP, 'name', getattr(SP, 'label', u''))
        username_stuff['text'].Enabled = False
    elif emailaddress_stuff is None:
        username_stuff['text'].SetFocus()

    needs_password = MSP.info.provider_info.get('needs_password', True)

    if needs_password and MSP.info.provider_info.get('password_url', None) is not None:
        password_stuff = LabelTextUrl(panel,
                                            MSP.info.provider_info.get('password_desc', _("Password")) + ":",
                                            _("Forgot Password?"),
                                            MSP.info.provider_info.password_url,
                                            textStyle = wx.TE_PASSWORD,
                                            )
    elif needs_password:
        password_stuff = LabelText(panel,
                                   MSP.info.provider_info.get('password_desc', _("Password")) + ":",
                                   textStyle = wx.TE_PASSWORD,
                                   )

    if password_stuff is not None and SP is not None:
        try:
            password_stuff['text'].Value = SP._decryptedpw()
        except UnicodeError:
            log.error("Error decrypting password")
            password_stuff['text'].Value = u''

        if emailaddress_stuff is None:
            password_stuff['text'].SetFocus()
            password_stuff['text'].SetSelection(-1, -1)

    panel.controls.update(
        emailaddress = emailaddress_stuff,
        username = username_stuff,
        password = password_stuff,
    )

    AddRowToGridBag(fx, emailaddress_stuff)
    AddRowToGridBag(fx, username_stuff)
    AddRowToGridBag(fx, password_stuff)

    if password_stuff is not None and emailaddress_stuff is not None:
        AddLineToGridBag(fx, panel)

def construct_basic_subpanel_im(panel, SP, MSP, MSC):
    # TODO: bind and populate
    fx = panel.controls['basic_sz']

    remotealias_stuff = register_stuff = None
    if MSC.info.get('needs_remotealias', None) is not None:
        remotealias_stuff = LabelText(panel, _("Display Name:"))
        remotealias_stuff['text'].Value = getattr(SP, 'remote_alias', u'')

    if MSC.info.get('needs_register', False) and SP is None:
        register_stuff = dict(check = wx.CheckBox(panel, -1, _("&Register New Account")))

    panel.controls.update(
        remotealias = remotealias_stuff,
        register = register_stuff,
    )

    AddRowToGridBag(fx, remotealias_stuff)
    AddRowToGridBag(fx, register_stuff)

def construct_basic_subpanel_email(panel, SP, MSP, MSC):
    # TODO: bind and populate
    fx = panel.controls['basic_sz']

    emailserver_stuff = emailssl_stuff = smtpserver_stuff = smtpssl_stuff = None

    def ssl_port_swap_handler(checkbox, portfield, default_value, ssl_value):
        def handler(e = None):
            if e is not None:
                e.Skip()
            if checkbox.Value and portfield.Value == str(default_value):
                portfield.Value = str(ssl_value)
            elif (not checkbox.Value) and portfield.Value == str(ssl_value):
                portfield.Value = str(default_value)
        return handler

    needs_server = MSC.info.get('needs_server', None)
    if needs_server is not None:
        server_type = needs_server.lower()

        default_port = MSC.info.defaults.get('%sport' % server_type, u'')
        default_ssl_port = MSC.info.defaults.get('%sport_ssl' % server_type, u'')
        require_ssl = getattr(SP, 'require_ssl', MSC.info.defaults.get('require_ssl', False))

        port = getattr(SP, '%sport' % server_type, default_ssl_port if require_ssl else default_port)

        emailserver_stuff = ServerPort(panel, _('&{server_type} Server:').format(server_type = _(needs_server)))
        emailssl_stuff = dict(check = wx.CheckBox(panel, -1, _('&This server requires SSL')))
        emailserver_stuff['text'].Value = getattr(SP, '%sserver' % server_type, MSC.info.defaults.get('%sserver' % server_type, u''))
        emailserver_stuff['porttext'].Value = str(port)
        emailssl_stuff['check'].Value = bool(require_ssl)
        ssl_chk = emailssl_stuff['check']

        handler = ssl_port_swap_handler(ssl_chk, emailserver_stuff['porttext'], default_port, default_ssl_port)
        ssl_chk.Bind(wx.EVT_CHECKBOX, handler)
        handler()

    if MSP.info.provider_info.get('needs_smtp', False):
        default_port = MSC.info.defaults.get('smtp_port', u'')
        default_ssl_port = MSC.info.defaults.get('smtp_port_ssl', u'')
        require_ssl = getattr(SP, 'smtp_require_ssl', MSC.info.defaults.get('smtp_require_ssl', False))

        port = getattr(SP, 'smtp_port', default_ssl_port if require_ssl else default_port)

        smtpserver_stuff = ServerPort(panel, _('SMTP Server:'))
        smtpssl_stuff = dict(check = wx.CheckBox(panel, -1, _('This server requires SSL')))
        smtpserver_stuff['text'].Value = getattr(SP, 'smtp_server', MSC.info.defaults.get('smtp_server', u''))
        smtpserver_stuff['porttext'].Value = str(port)
        smtpssl_stuff['check'].Value = bool(require_ssl)
        ssl_chk = smtpssl_stuff['check']

        handler = ssl_port_swap_handler(ssl_chk, smtpserver_stuff['porttext'], default_port, default_ssl_port)
        ssl_chk.Bind(wx.EVT_CHECKBOX, handler)
        handler()

    panel.controls.update(
        emailserver = emailserver_stuff,
        emailssl = emailssl_stuff,
        smtpserver = smtpserver_stuff,
        smtpssl = smtpssl_stuff,
    )

    AddRowToGridBag(fx, emailserver_stuff)
    AddRowToGridBag(fx, emailssl_stuff)

    AddRowToGridBag(fx, smtpserver_stuff)
    AddRowToGridBag(fx, smtpssl_stuff)

def construct_basic_subpanel_social(panel, SP, MSP, MSC):
    # TODO: bind and populate
    pass

## Advanced
def construct_advanced_panel(parent, SP, MSP):

    panel = getattr(parent, 'advanced_panel', None)
    if panel is None:
        panel = wx.Panel(parent = parent)

    panel.Label = "advanced panel"

    if getattr(panel, 'controls', None) is None:
        panel.controls = {}

    sz = panel.Sizer = wx.BoxSizer(wx.VERTICAL)

    fx = wx.GridBagSizer(0, 0)
    fx.SetEmptyCellSize((0, 0))
    fx.AddGrowableCol(1,1)
    fx.row = 0

    panel.controls['advanced_sz'] = fx

    sz.Add(fx, 1, wx.EXPAND | wx.ALL, panel.Top.GetDialogBorder())

    return panel

def construct_advanced_subpanel_provider(panel, SP, MSP, MSC):
    return None

def construct_advanced_subpanel_im(panel, SP, MSP, MSC):
    fx = panel.controls['advanced_sz']

    imserver_stuff = dataproxy_stuff = httponly_stuff = resource_stuff = None

    imserver_stuff = ServerPort(panel, _("IM Server:"))

    host, port = getattr(SP, 'server', MSC.info.defaults.get('server'))
    imserver_stuff['text'].Value = host
    imserver_stuff['porttext'].Value = str(port)

    if MSC.info.get('needs_resourcepriority', False):
        resource_stuff = ServerPort(panel, _("Resource:"), _("Priority:"))
        resource_stuff['text'].Value = getattr(SP, 'resource', MSC.info.defaults.get('resource', u'Digsby'))
        resource_stuff['porttext'].Value = str(getattr(SP, 'priority', MSC.info.defaults.get('priority', 5)))

    if MSC.info.get('needs_dataproxy', False):
        dataproxy_stuff = LabelText(panel, _("Data Proxy:"))
        dataproxy_stuff['text'].Value = getattr(SP, 'dataproxy', MSC.info.defaults.get('dataproxy', u''))

    panel.controls.update(
        imserver = imserver_stuff,
        dataproxy = dataproxy_stuff,
        resource = resource_stuff,
    )

    if MSC.info.get('needs_httponly'):
        httponly_stuff = dict(check = wx.CheckBox(panel, -1, _("Always connect over HTTP")))
        httponly_stuff['check'].Value = getattr(SP, 'use_http_only', MSC.info.defaults.get('use_http_only'))
        panel.controls['httponly'] = httponly_stuff

    for detail in MSC.info.get('more_details', []):
        raise Exception("Implement a custom UI builder for this plugin: %r", MSP.provider_id)

    AddRowToGridBag(fx, imserver_stuff)
    AddRowToGridBag(fx, resource_stuff)
    AddRowToGridBag(fx, dataproxy_stuff, spans=dict(text=(1,3)))
    AddRowToGridBag(fx, httponly_stuff)

def construct_advanced_subpanel_email(panel, SP, MSP, MSC):
    fx = panel.controls['advanced_sz']

    textparts = _("Check for new mail every {minutes_input} minutes").split('{minutes_input}')


    updatefreq_stuff = dict(
        label1 = wx.StaticText(panel, -1, textparts[0].strip()),
        text   = wx.TextCtrl(panel, -1, size = qtrTxtSize),
        label2 = wx.StaticText(panel, -1, textparts[1].strip())
    )

    h = wx.BoxSizer(wx.HORIZONTAL)
    ezadd(h, updatefreq_stuff['label1'], 0, flag = center_right_all)
    ezadd(h, updatefreq_stuff['text'], 0, flag = wx.ALIGN_CENTER_VERTICAL | wx.ALL)
    ezadd(h, updatefreq_stuff['label2'], 0, flag = center_left_all)
    ezadd(fx, h, (getattr(fx, 'row', 0), 1), (1, 3), flag = wx.EXPAND)
    fx.row = getattr(fx, 'row', 0) + 1

    updatefreq_stuff['text'].Value = str(getattr(SP, 'updatefreq',
                                                 MSC.info.defaults.get
                                                 ('updatefreq', 300)) / 60)

    webclient_stuff = mailclient = None
    if MSC.info.get('needs_webclient', True):
        webclient_stuff = LabelChoice(panel, _("Mail Client:"))
        _setup_mailclient_choice(webclient_stuff['choice'], getattr(SP, 'mailclient', MSC.info.defaults.get('mailclient', 'sysdefault')) or 'sysdefault')
        webclient_stuff['choice'].custom_inbox_url = getattr(SP, 'custom_inbox_url', '')
        webclient_stuff['choice'].custom_compose_url = getattr(SP, 'custom_compose_url', '')
        webclient_stuff['choice'].Bind(wx.EVT_CHOICE, _mailclient_select_handler(webclient_stuff['choice']))

        AddRowToGridBag(fx, webclient_stuff)
        AddLineToGridBag(fx, panel)

    servertype = MSC.info.get('needs_server', None)
    smtppassword_stuff = smtpusername_stuff = None
    if servertype is not None:
        same = panel.controls['smtpsame_rdo'] = wx.RadioButton(panel, -1, _("SMTP username/password are the same as {servertype}").format(servertype=servertype), style = wx.RB_GROUP)
        diff = panel.controls['smtpdiff_rdo'] = wx.RadioButton(panel, -1, _("Log on using:"))

        ezadd(fx, panel.controls['smtpsame_rdo'], (fx.row, 0), (1, 4), flag = wx.EXPAND | wx.ALL)
        fx.row += 1

        ezadd(fx, panel.controls['smtpdiff_rdo'], (fx.row, 0), (1, 4), flag = wx.EXPAND | wx.ALL)
        fx.row += 1

        smtpusername_stuff = LabelText(panel, _("Username:"))
        smtppassword_stuff = LabelText(panel, _("Password:"), textStyle = wx.TE_PASSWORD)

        def set_textfields_enabled(e = None):
            enabled = diff.Value
            smtppassword_stuff['text'].Enabled = smtpusername_stuff['text'].Enabled = enabled
            if e is not None:
                e.Skip()

            if not enabled:
                smtppassword_stuff['text'].Value = smtpusername_stuff['text'].Value = u''

        same.Value = True
        diff.Value = False
        set_textfields_enabled()

        same.Bind(wx.EVT_RADIOBUTTON, set_textfields_enabled)
        diff.Bind(wx.EVT_RADIOBUTTON, set_textfields_enabled)

        AddRowToGridBag(fx, smtpusername_stuff)
        AddRowToGridBag(fx, smtppassword_stuff)

        if SP is None:
            smtpuser = smtppass = u''
        else:
            smtpuser, smtppass = getattr(SP, 'smtp_username', u''), SP._decrypted_smtppw()

        same = (not (smtpuser or smtppass)) or (smtpuser == getattr(SP, 'username', None) and smtppass == getattr(SP, 'password', None))
        panel.controls['smtpsame_rdo'].Value = same
        panel.controls['smtpdiff_rdo'].Value = not same
        if not same:
            smtpusername_stuff['text'].Value = smtpuser
            smtppassword_stuff['text'].Value = smtppass

        set_textfields_enabled()

    panel.controls.update(
        updatefreq = updatefreq_stuff,
        mailclient = webclient_stuff,
        smtpusername = smtpusername_stuff,
        smtppassword = smtppassword_stuff,
    )

def construct_advanced_subpanel_social(panel, SP, MSP, MSC):
    return None

def layout_polish(basic_panel, advanced_panel):

    if advanced_panel:
        labels = []
        label_align_w = -1
        for name, control_set in basic_panel.controls.items() + advanced_panel.controls.items():
            if not isinstance(control_set, dict):
                continue
            if 'port' not in name and control_set.get('label', None) is not None:
                labels.append(control_set['label'])
                label_align_w = max(label_align_w, control_set['label'].GetBestSize().x)

        for c in labels:
            c.SetMinSize((label_align_w, c.GetBestSize().y))

def extract_basic_panel(panel, info, SP, MSP):
    if SP is not None:
        # Start with the previous settings as the base. Changed options will get overridden in
        # the methods that follow. This also preserves account options not set by the dialog.
        info.update(SP.get_options('im'))
        info.update(SP.get_options('email'))
        info.update(SP.get_options('social'))

def extract_basic_subpanel_provider(panel, info, SP, MSP, MSC):
    emailaddress = panel.controls.get('emailaddress', None)
    if emailaddress is not None:
        info['email_address'] = emailaddress['text'].Value

    info['name'] = info['label'] = panel.controls['username']['text'].Value
    password = panel.controls.get('password', None)
    if password is not None:
        try:
            info['password'] = common.profile.crypt_pw(password['text'].Value)
            info['_real_password_'] = password['text'].Value
        except UnicodeError:
            log.error("Error encrypting password")
            info['password'] = ''

    return True

def extract_basic_subpanel_im(panel, info, SP, MSP, MSC):
    remotealias = panel.controls.get('remotealias', None)
    if remotealias is not None:
        info['remote_alias'] = remotealias['text'].Value

    register = panel.controls.get('register', None)
    if register is not None:
        info['register'] = register['check'].Value

    return True

def extract_basic_subpanel_email(panel, info, SP, MSP, MSC):
    emailserver = panel.controls.get('emailserver', None)
    if emailserver is not None:
        server_type = MSC.info.get('needs_server', '').lower()

        host = emailserver['text'].Value
        port = emailserver['porttext'].Value
        ssl = panel.controls['emailssl']['check'].Value

        info[server_type + 'server'] = host
        info[server_type + 'port'] = port
        info['require_ssl'] = ssl

    smtpserver = panel.controls.get('smtpserver', None)
    if smtpserver is not None:
        host = smtpserver['text'].Value
        port = smtpserver['porttext'].Value
        ssl = panel.controls['smtpssl']['check'].Value

        info['smtp_server'] = host
        info['smtp_port'] = port
        info['smtp_require_ssl'] = ssl

    return True

def extract_basic_subpanel_social(panel, info, SP, MSP, MSC):
    pass

def extract_advanced_panel(panel, info, SP, MSP):
    pass
def extract_advanced_subpanel_provider(panel, info, SP, MSP, MSC):
    pass
def extract_advanced_subpanel_im(panel, info, SP, MSP, MSC):
    host, port = panel.controls['imserver']['text'].Value, panel.controls['imserver']['porttext'].Value

    info['server'] = (host, port)

    httponly = panel.controls.get('httponly', None)
    if httponly is not None:
        info['use_http_only'] = httponly['check'].Value

    resource = panel.controls.get('resource', None)
    if resource is not None:
        info['resource'] = resource['text'].Value
        info['priority'] = resource['porttext'].Value

    dataproxy = panel.controls.get('dataproxy', None)
    if dataproxy is not None:
        info['dataproxy'] = dataproxy['text'].Value

    return True

def extract_advanced_subpanel_email(panel, info, SP, MSP, MSC):
    try:
        val = int(panel.controls['updatefreq']['text'].Value) * 60
    except ValueError:
        val = 300
    info['updatefreq'] = val

    mailclient = panel.controls.get('mailclient', None)
    if mailclient is not None:
        mailclient = _extract_mailclient_choice(mailclient['choice'])
        info.update(mailclient)

    smtpusername = panel.controls.get('smtpusername', None)
    if smtpusername is not None:
        unctrl = smtpusername['text']
        info['smtp_username'] = unctrl.Value if unctrl.Enabled else u''
        pwctrl = panel.controls['smtppassword']['text']
        info['_encrypted_pw'] = info.pop('password', '')
        info['_encrypted_smtppw'] = common.profile.crypt_pw(pwctrl.Value) if pwctrl.Enabled else u''
    elif MSP.info.get('protocol_info', {}).get('needs_smtp', False):
        info['smtp_username'] = info['username']
        info['_encrypted_smtppw'] = info['_encrypted_pw'] = info.pop('password')

    return True

def extract_advanced_subpanel_social(panel, info, SP, MSP, MSC):
    pass

MAIL_CLIENT_SYSDEFAULT = _('System Default')
MAIL_CLIENT_OTHER      = _('Other Mail Client...')
MAIL_CLIENT_URL        = _('Launch URL...')

def _setup_mailclient_choice(ch, mc):

    with ch.Frozen():
        ch.Clear()
        ch.mailclient = mc
        choices = [MAIL_CLIENT_SYSDEFAULT]

        file_entry = 0
        if mc.startswith('file:'):
            import os.path
            if not os.path.exists(mc[5:]):
                mc == 'sysdefault'
            else:
                choices += [_('Custom ({mailclient})').format(mailclient=mc[5:])]
                file_entry = len(choices) - 1

        choices += [MAIL_CLIENT_OTHER,
                    MAIL_CLIENT_URL]

        for s in choices:
            ch.Append(s)

        if mc == 'sysdefault':
            selection = 0
        elif mc == '__urls__':
            selection = ch.Count - 1
        else:
            selection = file_entry

        ch.SetSelection(selection)
        ch.Layout()

def _mailclient_select_handler(ch):
    def evt_handler(evt = None):
        val = ch.StringSelection
        if val.startswith(MAIL_CLIENT_SYSDEFAULT):
            ch._Value = dict(mailclient = 'sysdefault')
        elif val == MAIL_CLIENT_OTHER:
            import os, sys
            defaultDir = os.environ.get('ProgramFiles', '')

            wildcard = '*.exe' if sys.platform == 'win32' else '*.*'
            filediag = wx.FileDialog(ch.Top, _('Please choose a mail client'),
                                     defaultDir = defaultDir,
                                     wildcard = wildcard,
                                     style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
            if filediag.ShowModal() == wx.ID_OK:
                ch._Value = dict(mailclient = 'file:' + filediag.Path)
        elif val == MAIL_CLIENT_URL:
            diag = LaunchURLDialog(ch.Top, ch.custom_inbox_url, ch.custom_compose_url)
            try:
                if wx.ID_OK == diag.ShowModal():
                    mailclient = '__urls__'
                    ch.custom_inbox_url = diag.InboxURL
                    ch.custom_compose_url = diag.ComposeURL
                    ch._Value = dict(mailclient = '__urls__', custom_inbox_url = diag.InboxURL, custom_compose_url = diag.ComposeURL)

            finally:
                diag.Destroy()

    return evt_handler

def _extract_mailclient_choice(ch):
    val = getattr(ch, '_Value', None)
    if val is not None:
        return val

    return dict(mailclient = ch.mailclient, custom_inbox_url = ch.custom_inbox_url, custom_compose_url = ch.custom_compose_url)


class LaunchURLDialog(toolbox.OKCancelDialog):
    '''
    email accounts let you specify custom URLs for inbox and compose actions.
    this dialog lets you enter those URLs.
    '''

    MINSIZE = (350, 1)

    inbox_tooltip   = _('Enter the URL that will be launched when you click "Inbox" for this email account.')
    compose_tooltip = _('Enter the URL that will be launched when you click "Compose" for this email account.')

    def __init__(self, parent, inbox_url = None, compose_url = None):
        toolbox.OKCancelDialog.__init__(self, parent, title=_('Launch URL'))

        self.construct(inbox_url, compose_url)
        self.layout()

    @property
    def InboxURL(self): return self.inbox_text.Value

    @property
    def ComposeURL(self): return self.compose_text.Value

    def construct(self, inbox_url = None, compose_url = None):
        # construct GUI
        self.inbox_label = wx.StaticText(self, -1, _('Enter a URL for the Inbox'))
        self.inbox_text = wx.TextCtrl(self, -1, inbox_url or '')

        self.compose_label = wx.StaticText(self, -1, _('Enter a URL for the Compose window'))
        self.compose_text = wx.TextCtrl(self, -1, compose_url or '')

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
            (self.inbox_label,    0, wx.EXPAND | wx.BOTTOM | wx.TOP, 5),
            (self.inbox_text,     0, wx.EXPAND | wx.LEFT, 7),
            (self.compose_label,  0, wx.EXPAND | wx.BOTTOM | wx.TOP, 5),
            (self.compose_text,   0, wx.EXPAND | wx.LEFT, 7),
            self.MINSIZE,
        ])

        self.set_component(sizer)

        self.Fit()

