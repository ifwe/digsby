import wx
from gui.uberwidgets.UberProgressBar import UberProgressBar
from gui import skin as skincore



class F(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.NewId(), "Progress Bar sampler",(0,0),(600,250))

        self.Bind(wx.EVT_SLIDER, self.on_slide)
        self.content = wx.BoxSizer(wx.VERTICAL)
        self.g = UberProgressBar(self,wx.NewId(),100,'progressbar',showlabel=True,size=(300,20))
        self.s = wx.Slider(self, -1, 0, 0, 100, (0,0), (300, 50))

        self.content.Add(self.g,0,wx.ALIGN_CENTER_HORIZONTAL)
        self.content.Add(self.s,0,wx.ALIGN_CENTER_HORIZONTAL)
        self.SetSizer(self.content)

    def on_slide(self,e):
        self.g.SetValue(self.s.GetValue())
        print self.s.GetValue()



if __name__=='__main__':
    a = wx.PySimpleApp( 0 )
    skincore.skininit('../../../../res')
    f=F()
    f.Show(True)

    a.MainLoop()
