import Digsby
import sys
import wx.webview
from tests.testapp import testapp

wxMSW = sys.platform.startswith("win")
if wxMSW:
    from cgui import ApplyAlpha

html = '''
<html>
<head>
<style type="text/css">
body {
    background: rgba(0,0,255,0);
}
</style>
</head>
<body>
hello world
</body>
</html>
'''

def main():
    app = testapp()
    style = wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR | wx.FRAME_TOOL_WINDOW

    f = wx.Frame(None, style=style, pos = (400, 300), size = (300, 300))
    p = wx.Panel(f, -1)
    p.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

    s = wx.BoxSizer(wx.VERTICAL)
    w = wx.webview.WebView(p)

    def paint(e):
        '''
        i = wx.ImageFromBitmap(w.Bitmap)
        b = wx.BitmapFromImage(i)
        b.UseAlpha()
        '''
        print "Hello..."
        bitmap = wx.EmptyBitmap(*w.Size)
        dc = wx.MemoryDC(bitmap)
        dc.Clear()
        #w.PaintOnDC(dc, False)

        dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0, 0)))
        dc.DrawRectangle(0, 0, 400, 400)
        #dc.SetBrush(wx.RED_BRUSH)
        #dc.DrawRectangle(50, 50, 300, 200)
        
        if wxMSW:
            ApplyAlpha(f, bitmap)

        dc = wx.PaintDC(e.GetEventObject())
        dc.DrawBitmap(bitmap, 0, 0, True)
        #wx.ScreenDC().DrawBitmap(bitmap, 0, 0, True)

    if not wxMSW:
        p.Bind(wx.EVT_PAINT, paint)
        f.Bind(wx.EVT_PAINT, paint)

    s.Add(w, 1, wx.EXPAND)
    p.SetSizer(s)
    w.SetPageSource(html)
    f.SetTransparent(125)

    w.SetTransparent(True)

    #wx.CallLater(2000, lambda: ApplyAlpha(f, w.Bitmap))

    f.Show()

    f.SetSize((500, 500))
    if wxMSW:
        paint(None)
    app.MainLoop()

if __name__ == '__main__':
    main()
