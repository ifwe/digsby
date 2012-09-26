import wx, math
from random import randint

if 'wxMac' in wx.PlatformInfo:
    PDC = wx.PaintDC
else:
    PDC = wx.AutoBufferedPaintDC

class GFXList(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.FULL_REPAINT_ON_RESIZE)

        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_TIMER,self.OnAnimate)
        self.theta = 0
        self.scale = 1

        self.count=0
        self.FPS=0

        self.rr=33

        self.timer=wx.Timer()
        self.timer.SetOwner(self,0)
        self.timer.Start(self.rr)


        self.timer2=wx.Timer()
        self.timer2.SetOwner(self,1)
        self.timer2.Start(1000)
#        self.Bind(wx.EVT_IDLE, self.OnAnimate)
#
    def OnAnimate(self, e):
        if e.Id==0:
            self.theta += 0.1
            self.Refresh()
        elif e.Id==1:
            self.FPS= self.count
            self.count=0

    def OnPaint(self, e):

        self.count+=1

        dc = PDC(self)
        gc = wx.GraphicsContext.Create(dc)


        gc.Scale(*([self.scale]*2))
        path = gc.CreatePath()
        path.AddRectangle(0,0, *self.Rect[2:])

        path2 = gc.CreatePath()

        for i in xrange(30):
            path2.AddRectangle(randint(0,400),randint(0,400),50,50,)

        gc.SetPen(wx.Pen(wx.Colour(0,0,128), 3))
        gc.SetBrush(gc.CreateLinearGradientBrush(0,0,100,100,wx.GREEN,wx.BLUE))
        gc.DrawPath(path)

        gc.SetBrush(gc.CreateLinearGradientBrush(0,0,100,100,wx.RED,wx.BLUE))
        gc.DrawPath(path2)

        for fs in xrange(30, 100, 10):
              font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
              font.SetPointSize(fs)
              gc.SetFont(font, wx.Colour(randint(0,255),randint(0,255),randint(0,255)))
              gc.DrawRotatedText('hello digsby', 40,80, self.theta if fs%20==0 else -self.theta)

#        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
#        font.SetPointSize(72)
#        gc.SetFont(font, wx.WHITE)
#        gc.DrawRotatedText('hello digsby', 40,80, self.theta)#, wx.TRANSPARENT_BRUSH)
        font.SetPointSize(15)
        gc.SetFont(font, wx.WHITE)
        gc.DrawText("FPS: "+str(self.FPS)+"/"+str(1000.0/self.rr),0,0)
        gc.DrawText("Time: "+str(wx.GetLocalTime()),0,17)
        gc.DrawText("Process id: "+str(wx.GetProcessId()),0,34)
        gc.DrawText("OS: "+str(wx.GetOsDescription()),0,51)


def main():
    try: import psyco; psyco.full()
    except ImportError: pass

    app = wx.PySimpleApp()

    f = wx.Frame(None, -1, 'gfxlist test', size=(250,700))
    f.Sizer = sz = wx.BoxSizer(wx.VERTICAL)
    gfx = GFXList(f)
    sz.Add(gfx, 1, wx.EXPAND)

    s = wx.Slider(f, -1, 100, 100, 500)
    def onslide(e):
        gfx.scale = s.Value / 100.0

    s.Bind(wx.EVT_SLIDER, onslide)
    sz.Add(s, 0, wx.EXPAND)
    f.Show()


    app.MainLoop()


if __name__ == '__main__': main()
