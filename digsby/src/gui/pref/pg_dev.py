import wx
from gui.pref.prefcontrols import VSizer, Check, TOP, BOTTOM, EXPAND, ALL, pname,\
    Text, Label, HSizer
from gui.uberwidgets.PrefPanel import PrefPanel, PrefCollection
from gui.validators import NumericLimit
from common import setpref, pref

def panel(panel, sizer, addgroup, exithooks):
    top = HSizer()
    top_right = VSizer()

    debug = PrefPanel(panel,
            PrefCollection(Check('advanced_prefs',  _('Advanced Prefs')),
                           Check('console',         _('Enable Debug Console')),
                           Check('reenable_online', _('Allow Reconnect if --start-offline')),
                           layout = VSizer(),
                           itemoptions = (0, BOTTOM | TOP, 3)),
            _('Debug'),
            prefix = 'debug',
    )

    digsby = PrefPanel(panel,
            PrefCollection(Check('allow_add', _('Allow Adding\n Digsby Buddies')),
                           layout = VSizer(),
                           itemoptions = (0, BOTTOM | TOP, 3)),
            _('Digsby Protocol'),
            prefix = 'digsby',
    )

    top.Add(debug,          1, EXPAND | ALL, 3)
    top_right.Add(digsby,   1, EXPAND | ALL, 3)
    top.Add(top_right,      1, EXPAND | ALL, 0)

    email_value_text = Text(panel, 'email.signature.value',
                            style = wx.TE_MULTILINE | wx.TE_AUTO_SCROLL )#| wx.TE_PROCESS_ENTER)
    email_value_text.Enable(pref('email.signature.enabled', type = bool))
    email_value_text.SetMinSize((-1, 60))

    email = PrefPanel(panel,
                      PrefCollection(Check('email.signature.enabled', _('Append signature'),
                                           callback = email_value_text.Enable),
                                     (email_value_text, 1, wx.LEFT | wx.EXPAND, 18),
                                     layout = VSizer()),
                      _('Email'),
                      )

    bottom = VSizer()

    bottom.Add(email, -1, EXPAND | ALL, 3)
    #TODO: defaults for text fields.
    try:
        pref('research.percent')
    except KeyError:
        setpref('research.percent', 75)
    try:
        pref('research.revive_interval_seconds')
    except KeyError:
        setpref('research.revive_interval_seconds', 60*60)

    plura = PrefPanel(panel,
            PrefCollection(
                           PrefCollection(
                                          Check('local.research.enabled', _('Enabled'), default = True),
                                           Check('research.debug_output', _("Print debug output to console. (don't use pipes)"), default = False),
                                           Check('research.always_on',    _('Always On'), default = False),
                                           Check('research.battery_override', _('Run when on battery'), default = False),
                           layout = VSizer(),
                           itemoptions = (0, ALL, 3)),
                           PrefCollection(
                           Label('Percent:'),
                           lambda parent, prefix: Text(parent, pname(prefix, 'research.percent'),
                                                validator=NumericLimit(2, 100), _type=int),
                           Label('Revive in x seconds:'),
                           lambda parent, prefix: Text(parent, pname(prefix, 'research.revive_interval_seconds'), _type=int),
                           layout = VSizer(),
                           itemoptions = (0, ALL, 3)),
                           layout = HSizer(),
                           itemoptions = (0, BOTTOM | TOP, 3)),
            _('Plura'),
            prefix = '',
    )

    social = PrefPanel(panel,
                       PrefCollection(Check('social.use_global_status', _('Use Global Status Dialog (may require restart)'), default = False),
                                      Check('twitter.scan_urls', _('Scan tweets for URLs (for popup click action)'), default = False),
                                      layout = VSizer(),
                                      itemoptions = (0, BOTTOM | TOP, 3)
                                      ),
                       _('Social accounts'),
                       prefix = '',
                       )

    bottom.Add(top, 0, EXPAND | ALL, 0)
    bottom.Add(plura, 0, EXPAND | ALL, 3)
    bottom.Add(social, 0, EXPAND | ALL, 3)
    sizer.Add(bottom, 0, EXPAND | BOTTOM)

    return panel








