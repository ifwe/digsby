import wx
import gui.pref.prefcontrols as PC
from gui.uberwidgets.PrefPanel import PrefPanel, PrefCollection

import gui.supportdigsby as Support

import common

def panel(p, sizer, addgroup, exithooks):
    components = [o() for o in Support.supportoptions.get_enabled()]
    _supportpanel = Support.supportdialog.SupportPanel(components, p)
    outerpanel = PrefPanel(p, _supportpanel, _('Support Digsby'))
    exithooks += _supportpanel.OnClose 
    
    sizer.Add(outerpanel, 1, wx.EXPAND)
    return p