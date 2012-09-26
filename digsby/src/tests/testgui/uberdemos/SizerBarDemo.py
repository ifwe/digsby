import wx
from gui.uberwidgets.SizerBar import SizerBar
from gui.uberwidgets.uberbook.SamplePanel import SamplePanel
from DemoApp import App

class P(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)

        self.Sizer=wx.BoxSizer(wx.HORIZONTAL)

        red=SamplePanel(self,'red')
        blue=SamplePanel(self,'blue')
        blue.MinSize=(10,10)
        green=SamplePanel(self,'green')
        self.sizer2=wx.BoxSizer(wx.VERTICAL)

        sb=SizerBar(self,blue,self.sizer2)
        self.sizer2.Add(red,1,wx.EXPAND)
        self.sizer2.Add(sb,0,wx.EXPAND)
        self.sizer2.Add(blue,0,wx.EXPAND)

        self.Sizer.Add(self.sizer2,1,wx.EXPAND)
        self.Sizer.Add(green,1,wx.EXPAND)

class F(wx.Frame):
    def __init__(self,parent=None):
        wx.Frame.__init__(self,parent)
        self.p=P(self)


def Go():
    f=F()
    f.Show(True)

if __name__=='__main__':
    a = App( Go )
    a.MainLoop()
