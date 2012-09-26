from DemoApp import App
import wx
import gettext
gettext.install('Digsby', './locale', unicode=True)

from gui.capabilitiesbar import CapabilitiesBar

class Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,title='Simple Menu Test')
        self.panel=wx.Panel(self)

        self.Bind(wx.EVT_CLOSE, lambda e: wx.GetApp().ExitMainLoop())

        self.panel.Sizer=wx.BoxSizer(wx.VERTICAL)

        self.capbar=CapabilitiesBar(self.panel)

        self.panel.Sizer.Add(self.capbar,0,wx.EXPAND)

        b1=wx.Button(self.panel,-1,'Hide Capabilities')
        b2=wx.Button(self.panel,-1,'Hide To/From')
        b3=wx.Button(self.panel,-1,'Hide Compose')

        b1.Bind(wx.EVT_BUTTON,lambda e: self.capbar.ShowCapabilities(not self.capbar.cbar.IsShown()))
        b2.Bind(wx.EVT_BUTTON,lambda e: self.capbar.ShowToFrom(not self.capbar.tfbar.IsShown()))
        b3.Bind(wx.EVT_BUTTON, lambda e: self.capbar.ShowComposeButton(not self.capbar.bcompose.IsShown()))

        self.panel.Sizer.Add(b1)
        self.panel.Sizer.Add(b2)
        self.panel.Sizer.Add(b3)

        self.capbar.bsms.Bind(wx.EVT_BUTTON,self.OnButton)
        self.capbar.binfo.Bind(wx.EVT_BUTTON,lambda e: self.capbar.bsms.SendButtonEvent())

    def OnButton(self,event):
        print "button clicked"


def Go():
    f=Frame()
    f.Show(True)

if __name__=='__main__':
    a = App( Go )
    from util import profile
    profile(a.MainLoop)
