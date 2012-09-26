import wx
import gui.snap

def main():
    app = wx.PySimpleApp()
    f = wx.Frame(None)
    f.Snap = True
    f.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
