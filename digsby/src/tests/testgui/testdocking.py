import gettext; gettext.install('Digsby')
import gui.native.win.winhelpers
from gui.native.docking import Docker
import wx, sys

if __name__ == '__main__':

    from gui.toolbox import setuplogging
    from util import trace

    setuplogging()
    a = wx.PySimpleApp()

    f2 = wx.Frame(None, title = u'Docking Control',
                  pos = (400, 600), size = (150,130),
                  style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP)

    f = wx.Frame(f2, -1, u'Docking Test', size = (250, 500))


    b = wx.Button(f, -1, 'vars')



    f.Sizer = sz = wx.BoxSizer(wx.VERTICAL)
    sz.Add(b)

    f.docker = Docker(f)

    def printvars(e):
        from pprint import pprint
        pprint(vars(f.docker))
    b.Bind(wx.EVT_BUTTON, printvars)

    trace(Docker)
    f.Bind(wx.EVT_LEFT_DOWN, lambda e: sys.stdout.write('docked: %s\n' % f.docker.docked))
    f.docker.Enabled = False

    p = wx.Panel(f2)
    sz = p.Sizer = wx.BoxSizer(wx.VERTICAL)

    text = wx.StaticText(p, -1, 'Not Docked')
    f.docker.OnDock += lambda docked: text.SetLabel('Docked!' if docked else 'Not Docked')

    b = wx.CheckBox(p, -1, '&Docking')
    c = wx.CheckBox(p, -1, '&Auto Hiding')
    c.Enabled = False

    def on_dock(e): c.Enabled = f.docker.Enabled = e.IsChecked()
    def on_autohide(e): f.docker.AutoHide = e.IsChecked()

    b.Bind(wx.EVT_CHECKBOX, on_dock)
    c.Bind(wx.EVT_CHECKBOX, on_autohide)

    sz.Add(text, 0, wx.EXPAND | wx.ALL, 5)
    sz.Add(b, 0, wx.EXPAND | wx.ALL, 5)
    sz.Add(c, 0, wx.EXPAND | wx.ALL, 5)
    f2.Show()

    f.Show(True)
    a.MainLoop()