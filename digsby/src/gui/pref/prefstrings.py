'''

contains all visible strings in the preferences dialog for making searching fast

'''
import sys
from config import platformName

# maps pg_XXX.py (module names) to display names for each preference tab

tabnames = [

    # do not change the first column without searching the code for "prefsdialog.show('XXX')"
    ('accounts',           _('Accounts')),
    ('general_profile',    _('General & Profile')),
    ('appearance',         _('Skins')),
    ('contact_list',       _('Buddy List')),
    ('text_conversations', _('Conversations')),
    ('files',              _('File Transfers')),
    ('status',             _('Status')),
    ('privacy',            _('Privacy')),
    ('notifications',      _('Notifications')),
    ('widgets',            _('Widgets')),
#    ('supportdigsby',      _('Support Digsby')),
    ('research',           _('Research Module')),
    ('proxy',              _("Connection Settings")),
#   ('plugins',            _('Plugins')),
#   ('helpdigsby',         _('Help Digsby')),
#   ('advanced',           _('Advanced')),
]

if platformName != 'mac':
    tabnames.extend([
    ])

if getattr(sys, 'DEV', False):
    from path import path
    location = path(__file__)
    pg_dev_loc = location.parent / 'pg_dev.py'
    if pg_dev_loc.isfile():
        tabnames.extend([
            ('dev',  _('Developer'))
        ])
#    tabnames.insert(4, ('sandbox', _('Sandbox')),)

# for searching, keep a map of {module_name: set(translated strings)}
import gui.pref.prefsearchable as prefsearchable

all = dict()
for module, nice_name in tabnames:
    strs = getattr(prefsearchable, module, getattr(sys, 'DEV', False) and [])
    if strs is not None:
        all[module] = set(_(s) for s in strs)

