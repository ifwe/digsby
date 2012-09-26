from __future__ import division
import time
import wx
from tests.testapp import testapp

def main():
    a = testapp('../../..')
    f = wx.Frame(None)

    f.fontsize = 12

    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        dc.SetPen(wx.TRANSPARENT_PEN)
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.DrawRectangleRect(f.ClientRect)

        font = wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        font.SetPixelSize(wx.Size(0, -f.fontsize))
        font.SetFaceName('Times New Roman')
        dc.TextForeground = wx.WHITE
        dc.Font = font

        str = 'test hello world xyz'
        x, y = 40, 10
        dc.DrawText(str, x, y)
        w, h, desc, externalLeading = dc.GetFullTextExtent(str)
        print w, h, desc, externalLeading

        r = wx.Rect(x, y + desc, w, h - desc * 2)

        realHeight = (h-desc*2)
        f.SetTitle('%s / %s = %s' % (f.fontsize, realHeight, f.fontsize / realHeight))

        #dc.SetPen(wx.RED_PEN)
        #dc.SetBrush(wx.TRANSPARENT_BRUSH)
        #dc.DrawRectangleRect(r)

    f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    f.Bind(wx.EVT_PAINT, paint)

    sl = wx.Slider(f, minValue = -10, maxValue = 50, value = f.fontsize)

    def onslide(e):
        f.fontsize = sl.Value
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