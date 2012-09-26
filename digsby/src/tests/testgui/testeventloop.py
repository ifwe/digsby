if __name__ == '__main__':

    from wx import PyTimer
    import wx

    f = None

    a = wx.PySimpleApp()
    f2 = wx.Frame(None)
    f2.Show()
    b  = wx.Button(f2, -1, 'modal')
    b.Bind(wx.EVT_BUTTON, lambda e: wx.MessageBox('test'))

    def prnt(s):
        print s

    def foo():
        global f
        if f is None:
            f = wx.Frame(None)
            f.Bind(wx.EVT_WINDOW_DESTROY, lambda e: prnt('destroyed: %r' % f))
            f.Show()
        else:
            f.Destroy()
            f = None

    t = PyTimer(foo)
    t.Start(1000)

    a.MainLoop()