import wx

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None, -1, 'test', style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_NO_TASKBAR)

    b = wx.ArtProvider.GetBitmap(wx.ART_QUESTION)
    i = wx.IconFromBitmap(b)
    f.SetIcon(i)
    f.Show()

    a.MainLoop()

if __name__ == '__main__':
    main()
