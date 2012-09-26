'''
test AutoBufferedPaintDC
'''
import wx

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None, -1, 'AutoBufferedPaintDC test')
    f.BackgroundStyle = wx.BG_STYLE_CUSTOM

    def paint(e):
        #dc = wx.PaintDC(f)                # 1) this one works
        #dc = wx.AutoBufferedPaintDC(f)        # 2) this one works also
        dc = wx.AutoBufferedPaintDC(f)     # 3) this one results in a traceback

        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.RED_BRUSH)
        dc.DrawRectangle(20, 20, 30, 30)

        gc = wx.GraphicsContext.Create(dc) # XXX the traceback occurs here
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.BLUE_BRUSH)
        gc.DrawRectangle(40, 40, 30, 30)

    f.Bind(wx.EVT_PAINT, paint)

    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()