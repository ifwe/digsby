import util

import wx

import gui.skin as skin
import gui.toolbox as toolbox
import gui.textutil as textutil

import digsby_service_editor.default_ui as default_ui

import twitter_account_gui

def construct_basic_subpanel_social(panel, SP, MSP, MSC):
    fx = panel.controls['basic_sz']
    if SP is None:
        # new account
        follow_digsby = dict(check = wx.CheckBox(panel, -1, _("Follow Digsby on Twitter")))
        follow_digsby['check'].Value = True
        panel.controls['follow_digsby'] = follow_digsby
        default_ui.ezadd(fx, follow_digsby['check'], (fx.row, 1), (1, 2), flag = wx.EXPAND | wx.ALL)
        fx.row += 1

    return True

def construct_advanced_subpanel_social(panel, SP, MSP, MSC):
    freq_defaults = dict((k, MSC.info.defaults.get(k, 2)) for k in ['friends_timeline', 'replies', 'direct_messages', 'search_updatefreq'])
    freq_settings = dict((k, getattr(SP, k, freq_defaults[k])) for k in ['friends_timeline', 'replies', 'direct_messages', 'search_updatefreq'])
    fake_account = util.Storage(update_frequencies = freq_settings,
                                auto_throttle = getattr(SP, 'auto_throttle', MSC.info.defaults.get('auto_throttle', True)),
                                api_server = getattr(SP, 'api_server', MSC.info.defaults.get('api_server', u'')),
                                )

    twap = twitter_account_gui.TwitterAccountPanel(panel, fake_account)
    panel.controls.update(twitterpanel = twap)

    fx = panel.controls['advanced_sz']
    fx.Add(twap, (fx.row, 1), (1, 4), wx.EXPAND)

    return True

def extract_basic_subpanel_social(panel, info, SP, MSP, MSC):
    follow_digsby = panel.controls.get('follow_digsby', None)
    if follow_digsby is not None:
        info['do_follow_digsby'] = follow_digsby['check'].Value

    info['post_ach_all'] = False
    return True

def extract_advanced_subpanel_social(panel, info, SP, MSP, MSC):
    info.update(panel.controls['twitterpanel'].info())
    info['informed_ach'] = True
    return True
