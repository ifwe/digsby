import wx
wx.App()
from gui.windowfx import ApplySmokeAndMirrors

class MyWindow(wx.Window):
    def __init__(self, parent):
        wx.Window.__init__(self, parent)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnPaint(self, e):
        dc = wx.PaintDC(self)

        ApplySmokeAndMirrors(self, wx.Bitmap(r'c:\dev\digsby\res\digsbyclaus.png'))

        dc.SetBrush(wx.RED_BRUSH)
        dc.DrawRectangle(*self.ClientRect)

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None)
    c = MyWindow(f)
    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()