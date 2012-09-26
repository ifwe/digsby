import wx

import gui.skin as skin
import gui.toolbox as toolbox
import gui.textutil as textutil

import digsby_service_editor.default_ui as default_ui

def construct_basic_subpanel_social(panel, SP, MSP, MSC):
    return True

def construct_advanced_subpanel_social(panel, SP, MSP, MSC):
    l_sz = wx.BoxSizer(wx.VERTICAL)
    newsfeed_lbl = wx.StaticText(panel, -1, _("Show Newsfeed:"), style = wx.ALIGN_LEFT)
    newsfeed_lbl.Font = textutil.CopyFont(newsfeed_lbl.Font, weight = wx.BOLD)

    labels = [
        _('Status Updates'),
        _('Friend Updates'),
        _('Blog/Forum Posts'),
        _('Group Updates'),
        _('Photos'),
        _('Music'),
        _('Videos'),
        _('Events'),
        _('Applications'),
    ]

    l_sz.Add(newsfeed_lbl, 0, wx.BOTTOM, newsfeed_lbl.GetDefaultBorder())

    newsfeed = panel.controls['newsfeed'] = []

    filters = getattr(SP, 'filters', {})
    values = filters.get('feed')
    if values is None:
        values = [True] * len(labels)

    for i, label in enumerate(labels):
        chk = wx.CheckBox(panel, label = label)
        chk.Value = values[i]
        newsfeed.append(chk)
        default_ui.ezadd(l_sz, chk, 0, wx.ALL)

    r_sz = wx.BoxSizer(wx.VERTICAL)
    alerts_lbl = wx.StaticText(panel, -1, _("Show Alerts:"), style = wx.ALIGN_LEFT)
    alerts_lbl.Font = textutil.CopyFont(alerts_lbl.Font, weight = wx.BOLD)

    labels = [
        _('Blog Comments'),
        _('Blog Subscriptions'),
        _('Picture Comments'),
        _('Event Invites'),
        _('Profile Comments'),
        _('Photo Tag Approvals'),
        _('Friend Requests'),
        _('Video Comments'),
        _('Group Notifications'),
        _('Recently Added Friends'),
        _('Birthdays'),
    ]

    r_sz.Add(alerts_lbl, 0, wx.BOTTOM, alerts_lbl.GetDefaultBorder())

    alerts = panel.controls['alerts'] = []

    values = filters.get('indicators')
    if values is None:
        values = [True] * len(labels)

    for i, label in enumerate(labels):
        chk = wx.CheckBox(panel, label = label)
        chk.Value = values[i]
        alerts.append(chk)
        default_ui.ezadd(r_sz, chk, 0, wx.ALL)

    h_sz = wx.BoxSizer(wx.HORIZONTAL)
    h_sz.Add(l_sz)
    h_sz.Add(r_sz)

    fx = panel.controls['advanced_sz']
    fx.Add(h_sz, (fx.row, 0), (11, 4))

    fx.row += 11
    return True

def extract_basic_subpanel_social(panel, info, SP, MSP, MSC):
    info['post_ach_all'] = False
    return True

def extract_advanced_subpanel_social(panel, info, SP, MSP, MSC):
    info['filters'] = filters = {}
    filters['feed'] = [x.Value for x in panel.controls['newsfeed']]
    filters['indicators'] = [x.Value for x in panel.controls['alerts']]
    info['informed_ach'] = True
    return True
