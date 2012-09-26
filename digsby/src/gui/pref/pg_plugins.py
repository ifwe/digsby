import wx
from gui.pref.prefcontrols import *

def panel(panel, sizer, newgroup, exithooks):
    newgroup('Plugins',
        PluginList(panel)
    )
    return panel

class PluginList(wx.VListBox):
    pass