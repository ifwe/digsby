import wx
from gui.uberwidgets.UberBar import UberBar
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.simplemenu import SimpleMenuItem
from gui.skin import skininit

from util.primitives.funcs import do


class F4(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.NewId(), "UberBar Overflow sampler",(0,0),(600,150))

        content=wx.BoxSizer(wx.VERTICAL)

        self.skin = 'buttonbar'#None#

        self.ubar=UberBar(self,skinkey=self.skin,overflowmode=True,alignment=wx.ALIGN_LEFT)
        self.b1 = UberButton(self.ubar,-1,'Button 1')
        self.b2 = UberButton(self.ubar,-1,'Button 2')
        self.bi = UberButton(self.ubar,-1,'Button i')
        self.b3 = UberButton(self.ubar,-1,'Button 3')
        self.b4 = UberButton(self.ubar,-1,'Button 4')
        self.ubar.Add(self.b1)
        self.ubar.Add(self.b2)
        self.ubar.Add(self.bi)
        self.ubar.Add(self.b3)
        self.ubar.Add(self.b4)

#        self.b1.Show(self.b1,False)
        self.bi.Show(self.bi,False)

        self.ubar.AddMenuItem(SimpleMenuItem('Menu Item 1'))
        self.ubar.AddMenuItem(SimpleMenuItem('Menu Item 2'))
        self.ubar.AddMenuItem(SimpleMenuItem('Menu Item 3'))


        self.b4=UberButton(self.ubar, -1, icon = wx.Bitmap(resdir / 'skins/default/digsbybig.png',wx.BITMAP_TYPE_PNG))
        self.ubar.AddStatic(self.b4)

        content.Add(self.ubar,0,wx.EXPAND,0)
        self.SetSizer(content)

class F3(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.NewId(), "UberBar sampler",(0,0),(600,150))
        events=[
            #(wx.EVT_BUTTON,self.onButton)
        ]
        do(self.Bind(event, method) for (event,method) in events)
        content=wx.BoxSizer(wx.VERTICAL)

        self.skin = 'buttonbar'#None#

        self.ubar=UberBar(self,skinkey=self.skin,alignment=wx.ALIGN_LEFT)
        self.b1=UberButton(self.ubar,-1,'Button 1',icon=wx.Bitmap(resdir / 'skins/default/digsbybig.png',wx.BITMAP_TYPE_PNG))
        self.b2=UberButton(self.ubar,-1,'Button 2',style=wx.VERTICAL,icon=wx.Bitmap(resdir / 'skins/default/digsbybig.png',wx.BITMAP_TYPE_PNG))
        self.b3=UberButton(self.ubar,-1,'Button 3',icon=wx.Bitmap(resdir / 'skins/default/digsbybig.png',wx.BITMAP_TYPE_PNG))
        self.ubar.Add(self.b1)
        self.ubar.Add(self.b2)
        self.ubar.AddSpacer()
        self.ubar.Add(self.b3)

        content.Add(self.ubar,0,wx.EXPAND,0)
        self.SetSizer(content)

    def onButton(self,event):
        print 'clixxored!!!'
        self.ubar.SetAlignment(wx.ALIGN_LEFT if self.ubar.alignment!=wx.ALIGN_LEFT else wx.ALIGN_CENTER)

class F2(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.NewId(), "UberBar sampler 2",(0,0),(600,150))
        events=[
            #(wx.EVT_BUTTON,self.onButton)
        ]
        do(self.Bind(event, method) for (event,method) in events)
        content=wx.BoxSizer(wx.VERTICAL)

        self.skin = 'buttonbar'#None#

        self.ubar=UberBar(self,skinkey=self.skin,alignment=wx.ALIGN_CENTER)
        self.b1=UberButton(self.ubar,-1,'Button 1',icon=wx.Bitmap(resdir / 'skins/default/digsbybig.png',wx.BITMAP_TYPE_PNG))
        self.b2=UberButton(self.ubar,-1,'Button 2',style=wx.VERTICAL,icon=wx.Bitmap(resdir / 'skins/default/digsbybig.png',wx.BITMAP_TYPE_PNG))
        self.b3=UberButton(self.ubar,-1,'Button 3',icon=wx.Bitmap(resdir / 'skins/default/digsbybig.png',wx.BITMAP_TYPE_PNG))
        self.ubar.Add(self.b1)
        self.ubar.Add(self.b2)
        self.ubar.Add(self.b3)

        content.Add(self.ubar,0,wx.EXPAND,0)
        self.SetSizer(content)

    def onButton(self,event):
        print 'clixxored!!!'
        self.ubar.SetAlignment(wx.ALIGN_LEFT if self.ubar.alignment!=wx.ALIGN_LEFT else wx.ALIGN_CENTER)

if __name__ == '__main__':
    from tests.testapp import testapp
    a = testapp()

    from gui.skin import resourcedir
    global resdir
    resdir = resourcedir()

    hit = wx.FindWindowAtPointer
    def onKey(event):
        if hasattr(wx.GetActiveWindow(),'menubar'):
            menubar=wx.GetActiveWindow().menubar
            if menubar.focus != None:
                a.captured=True
                if menubar.DoNaviCode(event.GetKeyCode()):return
            elif event.GetKeyCode()==wx.WXK_ALT:
                if not menubar.navimode: menubar.ToggleNaviMode(True)
                return
        event.Skip()

    def onKeyUp(event):
        if not a.captured and hasattr(wx.GetActiveWindow(),'menubar') and event.GetKeyCode()==wx.WXK_ALT and wx.GetActiveWindow().menubar.focus == None:
                wx.GetActiveWindow().menubar.AltFocus()
                a.captured=False
                return
        a.captured=False
        event.Skip()

    a.Bind(wx.EVT_KEY_DOWN, onKey)
    a.Bind(wx.EVT_KEY_UP, onKeyUp)
    f2=F2()
    f2.Show(True)
    f3=F3()
    f3.Show(True)
    f4=F4()
    f4.Show(True)
    a.captured=False

    a.MainLoop()
