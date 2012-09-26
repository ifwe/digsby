from logging import getLogger; log = getLogger('tagged.gui')
import wx

import gui.skin as skin
import gui.toolbox as toolbox
import gui.textutil as textutil

import digsby_service_editor.default_ui as default_ui

def construct_advanced_subpanel_social(panel, SP, MSP, MSC):
    l_sz = wx.BoxSizer(wx.VERTICAL)
    leftPanel_lbl = wx.StaticText(panel, -1, _("Show Alerts:"), style = wx.ALIGN_LEFT)
    leftPanel_lbl.Font = textutil.CopyFont(leftPanel_lbl.Font, weight = wx.BOLD)

    left_labels = [
                   _('Actions'),
                   _('Birthdays'),
                   _('Cafe'),
                   _('Comments'),
                   _('Elections'),
                   _('Farm'),
                   _('Friends'),
                   _('Gifts'),
                   _('Gold'),
                   _('Groups'),
                   _('Luv'),
                   _('Meetme'),
                   _('Mob'),
    ]

    l_sz.Add(leftPanel_lbl, 0, wx.BOTTOM, leftPanel_lbl.GetDefaultBorder())

    leftPanel = panel.controls['leftPanel'] = []
    filters = getattr(SP, 'filters', [])
    values = filters[:len(left_labels)] if filters else None

    if values is None:
        values = [True] * len(left_labels)
        
    for i, label in enumerate(left_labels):
        chk = wx.CheckBox(panel, label = label)
        chk.Value = values[i]
        leftPanel.append(chk)
        default_ui.ezadd(l_sz, chk, 0, wx.ALL)
    r_sz = wx.BoxSizer(wx.VERTICAL)
    rightPanel_lbl = wx.StaticText(panel, -1, '', style = wx.ALIGN_LEFT)
    rightPanel_lbl.Font = textutil.CopyFont(rightPanel_lbl.Font, weight = wx.BOLD)
    right_labels = [
                _('Mobile Updates'),
                _('Pets'),
                _('Photo Violations'),
                _('Poker'),
                _('Profile'),
                _('Questions'),
                _('Sorority Life'),
                _('Tags'),
                _('Topics'),
                _('Unread Messages'),
                _('Videos'),
                _('Winks'),
                _('Zoosk'),
    ]

    r_sz.Add(rightPanel_lbl, 0, wx.BOTTOM, rightPanel_lbl.GetDefaultBorder())

    rightPanel = panel.controls['rightPanel'] = []

    values = filters[len(left_labels):len(left_labels)+len(right_labels)] if filters else None
    if values is None:
        values = [True] * len(right_labels)

    for i, label in enumerate(right_labels):
        chk = wx.CheckBox(panel, label = label)
        chk.Value = values[i]
        rightPanel.append(chk)
        default_ui.ezadd(r_sz, chk, 0, wx.ALL)

    h_sz = wx.BoxSizer(wx.HORIZONTAL)
    h_sz.Add(l_sz)
    h_sz.Add(r_sz)

    fx = panel.controls['advanced_sz']
    fx.Add(h_sz, (fx.row, 0), (11, 4))

    fx.row += 11
    return True

def extract_advanced_subpanel_social(panel, info, SP, MSP, MSC):
    alerts = [x.Value for x in panel.controls['leftPanel']]
    alerts.extend([x.Value for x in panel.controls['rightPanel']])
    info['filters'] = alerts
    return True