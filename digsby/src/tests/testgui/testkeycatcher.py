import wx
from gui.uberwidgets.keycatcher import KeyCatcher

if __name__ == '__main__':
    a = wx.PySimpleApp()
    f = wx.Dialog(None)

    keycatcher = KeyCatcher(f)

    s = f.Sizer = wx.BoxSizer(wx.HORIZONTAL)

    b  = wx.Button(f, -1, '&test')
    b2 = wx.Button(f, -1, 't&est')
    s.AddMany([b, b2])

    def msg(a): print a

    b.Bind(wx.EVT_BUTTON,      lambda e: msg('test button'))
    keycatcher.OnDown('cmd+k', lambda e: msg('ctrl K!!! from accelerator'))
    keycatcher.OnDown('cmd+alt+return', lambda e: msg('ctrl alt enter from accelerator'))

    f.Show()
    a.MainLoop()