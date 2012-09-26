import wx
import gui.toolbox as toolbox
import gui.skin as skin

import digsby_service_editor.default_ui as default_ui

class LinkedInAchievementsDialog(toolbox.UpgradeDialog):
    faq_link_label = _('Learn More')
    faq_link_url   = 'http://wiki.digsby.com/doku.php?id=faq#q32'

    def __init__(self, parent, title, message):
        icon = skin.get('serviceicons.linkedin', None)
        super(LinkedInAchievementsDialog, self).__init__(parent, title,
                                                         message = message,
                                                         icon = icon,
                                                         ok_caption = _('Post Achievements'),
                                                         cancel_caption = _('No Thanks'),
                                                         link = (self.faq_link_label, self.faq_link_url))


def construct_advanced_panel(*a, **k):
    return False

def construct_basic_social_panel(panel, SP, MSP, MSC):
    if getattr(panel, 'controls', None) is None:
        panel.controls = {}

    if panel.Sizer is None:
        panel.Sizer = wx.BoxSizer(wx.VERTICAL)

    sz = panel.Sizer

    fx = panel.controls.get('basic_sz', None)
    if fx is None:
        fx = panel.controls['basic_sz'] = wx.GridBagSizer(0, 0)
        fx.SetEmptyCellSize((0, 0))
        fx.row = 0

        sz.Add(fx, 1, wx.EXPAND | wx.ALL, panel.Top.GetDialogBorder())

    row = fx.row

    fx.row = row

    return True

def extract_basic_provider_panel(panel, info, SP, MSP, MSC):
    info['username'] = panel.controls['username']['text'].Value
    return True

def extract_basic_social_panel(panel, info, SP, MSP, MSC):
    info['post_ach_all'] = False
    info['informed_ach'] = True
    return True


