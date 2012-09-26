import wx
import gui.proxydialog as proxydialog

from logging import getLogger; log = getLogger('pg_proxy')

def panel(p, sizer, addgroup, exithooks):
    pp = proxydialog.ProxyPanel(p)
    sizer.Add(pp, 0, wx.EXPAND | wx.ALL)
    p.on_close = pp.OnOK

    return p
