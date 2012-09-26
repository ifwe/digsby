'''
Status tab in the preferences dialog.
'''

import wx
from gui.pref.prefcontrols import *
from common import profile
from gui.status import StatusList

from gui.uberwidgets.PrefPanel import PrefPanel, PrefCollection

import config

def panel(p, sizer, addgroup, exithooks):

    #idle_panel = wx.Panel(p)

    # Idle message checkbox, minutes box, and status box
    addgroup(_('Status Options'),
             Check('digsby.status.promote_tag.enabled',
                   _('Promote Digsby in my IM status messages'), default = True,
                   help = 'http://wiki.digsby.com/doku.php?id=faq#q34'),
#             Check('plugins.nowplaying.show_link',
#                   _('Help Digsby by linking album when sharing "Listening to..." as status')),
             Check('messaging.become_idle',
                   _('Let others know that I am idle after '
                     '%2(messaging.idle_after)d minutes of inactivity')),
    )

    bottom = HSizer()

    when_away = PrefPanel(p,
                    PrefCollection(Check('autorespond',   _('Autorespond with status message')),
                                   Check('disable_sound', _('Disable sounds')),
                                   Check('disable_popup', _('Disable pop-up notifications')),
                                   layout = VSizer(),
                                   itemoptions = (0, BOTTOM | TOP,3)),
                    _('When away...'),
                    prefix = 'messaging.when_away',
    )
    bottom.Add(when_away,  1, EXPAND | ALL, 3)

    if config.platformName != 'mac':
        fullscreen = PrefPanel(p,
                        PrefCollection(Check('hide_convos',    _('&Hide new conversation windows')),
                                       Check('disable_sounds', _('&Disable sounds')),
                                       Check('disable_popups', _('Disable &pop-up notifications')),
                                       layout = VSizer(),
                                       itemoptions = (0, BOTTOM | TOP, 3)),
                        _('When running full screen applications...'),
                        prefix = 'fullscreen',
    #        Check('disable_alerts', _('Disable &alerts')),
        )
        bottom.Add(fullscreen, 1, EXPAND | ALL, 3)

    sizer.Add(bottom, 0, EXPAND | BOTTOM)


    statuses = StatusList(p, profile.statuses)
    msgs = PrefPanel(p, statuses, _('Status Messages'), buttonlabel=_('New Status Message'), buttoncb=lambda b: statuses.add_status_message())

    sizer.Add(msgs, 1, wx.EXPAND)
    return p
