'''
Shows a popup explaining popup features.
'''

from common import pref, setpref
from gui.toast.toast import popup
from gui import skin
import wx

SHOWN_HELP_PREF = 'notifications.popups.help_shown'

_didshow = False

def on_popup(options):
    global _didshow
    if _didshow:
        return
    if pref(SHOWN_HELP_PREF, default=False, type=bool):
        _didshow = True
        return

    _didshow = True # A backup in case setpref fails, so you only get one per session.
    setpref(SHOWN_HELP_PREF, True)

    popup(header = _('TIP: Popup Notifications'),
          major  = None,
          minor  = _("You can right click popups to close them right away instead of waiting for them to fade out."),
          sticky = True,
          icon   = skin.get('appdefaults.notificationicons.error'),
          always_show=True)

def enable_help():
    import hooks
    hooks.register('popup.pre', on_popup)


