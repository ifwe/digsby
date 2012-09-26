import wx

def print_display_info():
    count = wx.Display.GetCount()

    print count, 'displays:'

    for i in xrange(count):
        display = wx.Display(i)
        print ' %d: %r' % (i, display.Geometry)


def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None)

    b = wx.Button(f, -1, 'Get Displays')
    b.Bind(wx.EVT_BUTTON, lambda e: print_display_info())

    f.Sizer = s = wx.BoxSizer(wx.VERTICAL)
    s.Add(b)

    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()