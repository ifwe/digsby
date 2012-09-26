import wx

from gui import skin
import gui.toolbox as toolbox
import gui.textutil as textutil

import digsby_service_editor.default_ui as default_ui

class FacebookAchievementsDialog(toolbox.UpgradeDialog):
    faq_link_label = _('Learn More')
    faq_link_url   = 'http://wiki.digsby.com/doku.php?id=faq#q32'

    def __init__(self, parent, title, message):
        icon = skin.get('serviceicons.facebook', None)
        super(FacebookAchievementsDialog, self).__init__(parent, title,
                                     message=message,
                                     icon=icon,
                                     ok_caption = _('Post Achievements'),
                                     cancel_caption = _('No Thanks'),
                                     link=(self.faq_link_label, self.faq_link_url))


def construct_basic_subpanel_social(panel, SP, MSP, MSC):
    return True

def construct_advanced_subpanel_social(panel, SP, MSP, MSC):
    sz = wx.BoxSizer(wx.VERTICAL)
    alerts_lbl = wx.StaticText(panel, -1, _("Show Alerts:"), style = wx.ALIGN_LEFT)
    alerts_lbl.Font = textutil.CopyFont(alerts_lbl.Font, weight = wx.BOLD)

    labels = [_('Messages'),
              _('Pokes'),
              _('Shares'),
              _('Friend Requests'),
              _('Group Invitations'),
              _('Event Invitations'),
              _('Notifications')]

    sz.Add(alerts_lbl, 0, wx.BOTTOM, alerts_lbl.GetDefaultBorder())

    alerts = panel.controls['alerts'] = []

    values = getattr(SP, 'filters', {}).get('alerts', None)
    if values is None:
        values = [True] * len(labels)

    for i, label in enumerate(labels):
        chk = wx.CheckBox(panel, label = label)
        chk.Value = values[i]
        alerts.append(chk)
        default_ui.ezadd(sz, chk, 0, wx.ALL)

    fx = panel.controls['advanced_sz']
    fx.Add(sz, (fx.row, 1), (6, 4))
    fx.row += 6
    return True

def extract_basic_subpanel_social(panel, info, SP, MSP, MSC):
    info['post_ach_all'] = False

    return True

def extract_advanced_subpanel_social(panel, info, SP, MSP, MSC):
    info['filters'] = {'alerts' : [x.Value for x in panel.controls['alerts']]}
    info['informed_ach'] = True
    return True
