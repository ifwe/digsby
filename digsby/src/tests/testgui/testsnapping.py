import wx, gui.snap

def main():
    app = wx.PySimpleApp()
    frame = wx.Frame(None, -1, 'Snap Test')
    frame.Snap = True

    f = wx.Frame(frame, -1, 'Other Frame', size=(300,400), pos=(700,300))
    f.Show()

    panel = wx.Panel(frame)
    panel.Sizer = wx.BoxSizer(wx.VERTICAL)
    b = wx.Button(panel, -1, "Don't Snap")

    def push(e):
        if frame.Snap:
            frame.Snap = False
            b.Label = 'Snap'
        else:
            frame.Snap = True
            b.Label = "Don't Snap"

    b.Bind(wx.EVT_BUTTON, push)

    panel.Sizer.Add(b, 0, wx.ALL, 20)
    frame.Show()
    app.MainLoop()


if __name__ == '__main__':
    main()
