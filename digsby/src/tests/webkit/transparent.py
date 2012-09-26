import Digsby
import wx.webview
import os.path

thisdir = os.path.dirname(os.path.abspath(__file__))

def main():
    from tests.testapp import testapp
    app = testapp()

    from cgui import TransparentFrame

    class TransparentWebKit(TransparentFrame):
        def __init__(self, parent):
            TransparentFrame.__init__(self, parent)
            self.webview = wx.webview.WebView(self)

        def GetBitmap(self):
            s = self.ClientSize

            img = wx.EmptyImage(*s)
            bmp = wx.BitmapFromImage(img)
            bmp.UseAlpha()
            dc = wx.MemoryDC(bmp)
            dc.Clear()
            dc.DrawRectangleRect(self.ClientRect)
            self.webview.PaintOnDC(dc, False)
            dc.SelectObject(wx.NullBitmap)

            return bmp

    f = TransparentWebKit(None)
    w = f.webview

    w.SetTransparent(True)
    w.SetPageSource(open(os.path.join(thisdir, 'test.html')).read())
    #w.LoadURL('http://webkit.org/blog/138/css-animation/')

    f.Show()

    f.SetRect((200, 200, 400, 400))

    assert w.IsTransparent()
    app.MainLoop()

if __name__ == '__main__':
    main()
