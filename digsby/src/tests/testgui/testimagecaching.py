from __future__ import division
import time
import wx
from tests.testapp import testapp
from gui.toolbox import draw_tiny_text

def main():
    a = testapp('../../..')
    f = wx.Frame(None, style = wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

    from gui.skin import get as skinget
    icons = skinget('serviceicons')

    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.DrawRectangleRect(f.ClientRect)

        dc.DrawBitmap(icons.gmail, 0, 0, True)
        dc.DrawBitmap(draw_tiny_text(icons.gmail, 'test').WXB, 0, 40, True)


    f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    f.Bind(wx.EVT_PAINT, paint)
    f.Show()

    a.MainLoop()

def main2():
    a = testapp('../../..')
    f = wx.Frame(None)

    from gui.skin import get as skinget
    icons = skinget('serviceicons')

    services = 'digsby aim icq jabber gtalk yahoo'.split()

    f.imgsize = 0

    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.DrawRectangleRect(f.ClientRect)

        drawbitmap = dc.DrawBitmap

        sizes = [(32, 32), (16, 16), (100, 100)]

        diff = f.imgsize

        y = 0
        for size in sizes:
            x = 0
            for srv in services:
                icon = icons[srv].Resized((size[0] + diff, size[1] + diff))
                drawbitmap(icon, x, y, True)
                x += size[0] + diff
            y += size[1] + diff

    f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    f.Bind(wx.EVT_PAINT, paint)

    sl = wx.Slider(f, minValue = -10, maxValue = 50, value = 0)

    def onslide(e):
        f.imgsize = sl.Value
        f.Refresh()
        f.SetTitle(str(sl.Value))


    sl.Bind(wx.EVT_SLIDER, onslide)

    f.Sizer = s = wx.BoxSizer(wx.VERTICAL)
    s.AddStretchSpacer(1)
    s.Add(sl, 0, wx.EXPAND)

    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()




if __name__ == '_dep_':
    @lru_cache(30)
    def reflected(bmp, heightPercent = None, maxalpha = None):
        sz = (bmp.Width, bmp.Height)
        flipped = ImageOps.flip(bmp.PIL)

        grad = Image.new('L', sz)
        draw = ImageDraw.Draw(grad)

        height = float(sz[1])

        alpha = flipped.split()[-1]

        if maxalpha is None:
            maxalpha = 100
        if heightPercent is None:
            heightPercent = 75

        hh = (heightPercent / 100.00) * height

        # draw the gradient
        for yy in xrange(0, hh):
            k = max(0, maxalpha - maxalpha * yy/hh)
            draw.line((0, yy, sz[0], yy), fill = k)

        flipped.putalpha(ImageMath.eval('convert(min(a,b), "L")', a=alpha, b=grad))

        return flipped.WXB


    def drawreflected(dc, bmp, x, y, alpha = True, heightPercent = None, maxalpha = None):
        gc = wx.GraphicsContext.Create(dc)
        sz = (bmp.Width, bmp.Height)

        gc.DrawBitmap(bmp, x, y, sz[0], sz[1])
        gc.DrawBitmap(reflected(bmp, heightPercent, maxalpha), x, y + sz[1], sz[0], sz[1])

    wx.DC.DrawReflectedBitmap = drawreflected

if __name__ == '__main__123':
    from time import clock
    N = 50000
    app = wx.PySimpleApp()

    def test(f):
        t = clock()
        for x in xrange(N):
            f(bmp, 16)
        diff = clock()-t
        print f, diff

    bmp = wx.Bitmap('c:\\digsbybig.png')

    test(wxbitmap_in_square)
    test(old_wxbitmap_in_square)


if __name__ == '__main__':
    from tests.testapp import testapp
    from gui.textutil import default_font
    from math import ceil, sqrt
    from path import path

    app = testapp('../../../')

    bitmaps = []



    for f in path('c:\\src\\digsby\\res\\skins\\default\\serviceicons').files('*.png'):
        bitmaps.append(wx.Bitmap(f))

    m = wx.Menu()
    item = wx.MenuItem(m)

    item.Bitmap = bitmaps[0]
    bitmaps.insert(0, item.Bitmap)
    bitmaps.insert(0, item.Bitmap)
    bitmaps.insert(0, item.Bitmap)
    bitmaps.insert(0, item.Bitmap)

#    from ctypes import cast, POINTER, c_long

#    def refdata(obj, n):
#        return cast(int(obj.this), POINTER(c_long))[n]

    from pprint import pprint
    pprint([(b.GetRefData(), id(b)) for b in bitmaps])

    f = wx.Frame(None, style = wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        gc = wx.GraphicsContext.Create(dc)
        r = f.ClientRect
        x1, y1 = r.TopLeft
        x2, y2 = r.BottomRight

        br = gc.CreateLinearGradientBrush(x1, y1, x2, y2, wx.BLACK, wx.WHITE)
        gc.SetBrush(br)
        gc.DrawRectangle(*r)
        dc.TextForeground = wx.WHITE
        dc.Font = default_font()

        j = int(ceil(sqrt(len(bitmaps))))

        i = 0
        for y in xrange(j):
            for x in xrange(j):
                w, h   = r.Width / j, r.Height / j
                xx, yy = w * x, h * y

                if len(bitmaps) > i:
                    dc.DrawBitmap(bitmaps[i].Resized(min((w, h))), xx, yy)


                    dc.DrawText(str(bitmaps[i].GetRefData()), xx, yy)

                i += 1


        #dc.DrawBitmap(b.Resized(min(r.Size)).Greyed, 0, 0, True)
        #dc.DrawBitmap(ResizeBitmapSquare(b, min(r.Size)), 0, 0, True)
        #dc.DrawBitmap(ResizeBitmap(b, *r.Size), 0, 0, True)
        #dc.DrawBitmap(b.Resized(r.Size), 0, 0, True)

    f.Bind(wx.EVT_PAINT, paint)
    f.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
    f.Show()
    app.MainLoop()
