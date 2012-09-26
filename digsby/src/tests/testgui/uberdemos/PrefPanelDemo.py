import wx
from gui.uberwidgets.PrefPanel import PrefPanel
from gui.pref.noobcontactlayoutpanel import NoobContactLayoutPanel
class FakeContent(wx.Panel):
    def __init__(self, parent, color=wx.RED):
        wx.Panel.__init__(self, parent)

        self.brush = wx.Brush(color)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

    def OnPaint(self,event):
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)

        dc.Brush = self.brush
        dc.Pen = wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)

class Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,-1,"A simple test.",pos=wx.Point(50,50))

        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        pp = PrefPanel(self, FakeContent(self,wx.Colour(238,238,238)),' A test of silly proportions ',"A Button",self.AButtonCB)
        self.Sizer.Add(pp,1,wx.EXPAND|wx.ALL,5)

        self.SetBackgroundColour(wx.WHITE)

        self.Bind(wx.EVT_CLOSE,lambda e: wx.GetApp().ExitMainLoop())

    def AButtonCB(self,event):
        print "You clicked teh button, Tee-He!!!"

class Frame2(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,-1,"Hey! It's a combo title.",pos=wx.Point(300,300))

        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.pp = pp = PrefPanel(self,[(FakeContent(self,wx.Colour(238,238,238)),'grey'  ),
                                       (FakeContent(self,wx.Colour(238,238,255)),'blue'  ),
                                       (FakeContent(self,wx.Colour(255,238,238)),'red'   ),
                                       (FakeContent(self,wx.Colour(238,255,238)),'green' ),
                                       (FakeContent(self,wx.Colour(255,255,238)),'yellow'),
                                      ])
        self.Sizer.Add(pp,1,wx.EXPAND|wx.ALL,5)

        button = wx.Button(self,-1,'ZOMG Lazers')
        self.Sizer.Add(button,0,wx.EXPAND|wx.ALL,3)
        button.Bind(wx.EVT_BUTTON, self.OnLazers)

        self.SetBackgroundColour(wx.WHITE)

        self.Bind(wx.EVT_CLOSE,lambda e: wx.GetApp().ExitMainLoop())

    def OnLazers(self,event):
            self.pp.SetContents([(FakeContent(self,wx.Colour(255,255,238)),'yellow'),
                                 (FakeContent(self,wx.Colour(238,255,238)),'green' ),
                                 (FakeContent(self,wx.Colour(255,238,238)),'red'   ),
                                 (FakeContent(self,wx.Colour(238,238,255)),'blue'  ),
                                 (FakeContent(self,wx.Colour(238,238,238)),'grey'  ),
                                ],True)

class Frame3(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,-1,"A simple test.",pos=wx.Point(400,550),size=wx.Size(563, 294))

        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        pp = PrefPanel(self, NoobContactLayoutPanel(self),' A test of noobish proportions ')
        self.Sizer.Add(pp,1,wx.EXPAND|wx.ALL,5)

        self.SetBackgroundColour(wx.WHITE)

        self.Bind(wx.EVT_CLOSE,lambda e: wx.GetApp().ExitMainLoop())



if __name__ == '__main__':
    from tests.testapp import testapp

    hit = wx.FindWindowAtPointer

    a = testapp('../../../../')

    f = Frame()
    f.Show(True)

    f2 = Frame2()
    f2.Show(True)

    f3 = Frame3()
    f3.Show(True)

    a.MainLoop()