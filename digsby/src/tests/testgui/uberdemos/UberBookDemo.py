import wx

from util.primitives.funcs import do
from gui import skin

from gui.uberwidgets.uberbook.UberBook import NoteBook
from gui.uberwidgets.uberbook.tabmanager import TabManager
from gui.uberwidgets.uberbook.dragtimer import WinDragTimer
from gui.uberwidgets.uberbook.OverlayImage import SimpleOverlayImage
from gui.uberwidgets.uberbook.SamplePanel import SamplePanel
from gui.windowfx import fadein

class F(wx.Frame):
    """
    Sample frame
    """
    def __init__(self,winman,tabman,pos=wx.DefaultPosition):
        wx.Frame.__init__(self, None, wx.NewId(), "UberBook Sampler", pos, (600, 150))

        events=[(wx.EVT_MOVE, self.OnMove),
                (wx.EVT_SIZE, self.OnSize)]

        do(self.Bind(event,method) for (event,method) in events)

        self.skin = 'Tabs'

        self.content = wx.BoxSizer(wx.VERTICAL)
        self.winman = winman
        self.tabman = tabman
        self.notebook = NoteBook(self, self, self.tabman, self.skin)
        self.content.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(self.content)

        self.focus = False

        self.mergstuff = None

    def OnMove(self,event):
        self.mergstuff = wx.CallLater(10,self.notebook.StartWindowDrag)

    def OnSize(self,event):
        if self.mergstuff:
            self.mergstuff.Stop()
            self.mergstuff = None
        event.Skip()


    def Close(self):
        self.tabman.books.remove(self.notebook)
        wx.Frame.Close(self)

    def AddTabs(self):
        colors = ['green', 'blue', 'red', 'yellow', 'MEDIUM FOREST GREEN','purple', 'grey', 'white']
        do(self.notebook.Add(SamplePanel(self.notebook.pagecontainer, color))
         for color in colors)

    def AddTabs2(self):
        colors = ['black', 'aquamarine', 'coral', 'orchid']
        do(self.notebook.Add(SamplePanel(self.notebook.pagecontainer, color)) for color in colors)



class WinManTmp(object):
    def __init__(self):
        self.wdt = WinDragTimer()
        self.tabman = TabManager()
        self.f = self.NewWindow(self.tabman, (50, 50))
        self.f.AddTabs()
        self.f2 = self.NewWindow(self.tabman, (200,200))
        self.f2.AddTabs2()



    def NewWindow(self,tabman=None,pos=wx.DefaultPosition):
        if pos[1]<0:pos[1]=0
        Fn=F(self,tabman,pos) if tabman else F(self,self.tabman,pos)
        Fn.Show(False)
        fadein(Fn,'quick')
        return Fn

if __name__ == '__main__':
    from tests.testapp import testapp

    a = testapp('../../../../')
    a.winman = WinManTmp()

    a.MainLoop()
