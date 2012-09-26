from wx import Color
import wx
from time import clock

from random import randint

def randcolor():
    return Color(randint(0,255), randint(0,255), randint(0,255))

def paint(e):
    start = clock()
    f = e.EventObject
    dc = wx.PaintDC(f)

    i = 4

    dc.SetPen(wx.TRANSPARENT_PEN)
    dc.SetBrush(wx.WHITE_BRUSH)
    dc.DrawRectangleRect(f.ClientRect)

    for y in xrange(100):
        for x in xrange(100):
            dc.Brush = wx.Brush(randcolor())
            dc.DrawRectangle(x*i, y*i, x+i, y+i)

    print clock() - start

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None, style = wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)


    f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    f.Bind(wx.EVT_PAINT, paint)

    #from psyco import bind
    #bind(paint)

    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()