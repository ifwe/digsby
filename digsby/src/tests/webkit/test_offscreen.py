import wx.webview
from tests.testapp import testapp
import cgui

def main():
    app = testapp()

    f = wx.Frame(None)
    n = wx.Notebook(f)

    f.Sizer = wx.BoxSizer(wx.HORIZONTAL)
    f.Sizer.Add(n, 1, wx.EXPAND)

    taskbar = cgui.TabNotebook(f)

    def page_index(win):
        for x in xrange(n.GetPageCount()):
            nwin = n.GetPage(x)
            if win is nwin:
                return x

        return -1

    class Preview(cgui.TabController):
        def OnTabClosed(self, tab):
            i = page_index(tab.Window)
            if i != -1:
                n.DeletePage(i)

        def GetLivePreview(self, tab, rect):
            print 'yay', rect
            return self.get_preview(tab, rect)

        def GetIconicBitmap(self, tab, width, height):
            return self.get_preview(tab, wx.Rect(0, 0, width, height))

        def get_preview(self, tab, r):
            bitmap = wx.EmptyBitmap(r.width, r.height, False)
            memdc = wx.MemoryDC(bitmap)
            memdc.SetBrush(wx.WHITE_BRUSH)
            memdc.SetPen(wx.TRANSPARENT_PEN)
            memdc.DrawRectangle(0, 0, *r.Size)

            #memdc.Brush = wx.RED_BRUSH
            #memdc.DrawRectangle(50, 50, 100, 100)

            tab.Window.PaintOnDC(memdc, r, r.Size)
            memdc.SelectObject(wx.NullBitmap)

            return bitmap

    pages = []
    def addpage(url):
        w = wx.webview.WebView(f)
        pages.append(w)
        w.LoadURL(url)
        n.AddPage(w, url)
        taskbar.CreateTab(w, Preview())

    addpage('http://google.com')
    addpage('http://digsby.com')

    f.Show()

    if False:
        f2 = wx.Frame(None)
        f2.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        t = wx.PyTimer(f2.Refresh)
        t.StartRepeating(1000)

        def paint(e):
            dc = wx.PaintDC(f2)

            r = f2.ClientRect

            bitmap = wx.EmptyBitmap(r.width, r.height, False)
            memdc = wx.MemoryDC(bitmap)
            memdc.SetBrush(wx.WHITE_BRUSH)
            memdc.SetPen(wx.TRANSPARENT_PEN)
            memdc.DrawRectangle(0, 0, *r.Size)

            #memdc.Brush = wx.RED_BRUSH
            #memdc.DrawRectangle(50, 50, 100, 100)

            pages[1].PaintOnDC(memdc, f2.ClientRect, f2.ClientSize)
            memdc.SelectObject(wx.NullBitmap)

            #cgui.Unpremultiply(bitmap)
            dc.DrawBitmap(bitmap, 0, 0, False)

        f2.Bind(wx.EVT_PAINT, paint)
        f2.Show()


    def close(e):
        app.ExitMainLoop()
    for _f in (f,  ):
        _f.Bind(wx.EVT_CLOSE, close)

    app.MainLoop()

if __name__ == '__main__':
    main()
