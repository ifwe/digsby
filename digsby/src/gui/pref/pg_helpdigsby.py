'''
help digsby page
'''
import wx

from gui.pref.prefcontrols import Check, VSizer
from gui.uberwidgets.PrefPanel import PrefPanel, PrefCollection

def panel(panel, sizer, addgroup, exithooks):
    collection = PrefCollection(
        Check(None, _('&Allow Digsby to conduct research during idle itme')),
        layout = VSizer(),
        itemoptions = (0, wx.BOTTOM, 6))

    help_group = PrefPanel(panel, collection, _('Help Digsby'))
    sizer.Add(help_group)
    return panel

