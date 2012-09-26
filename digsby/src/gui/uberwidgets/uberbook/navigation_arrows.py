import wx
from gui.uberwidgets.UberButton import UberButton
from util.primitives.funcs import do
from common import pref
#from gui.windowfx import SmokeAndMirrorsBomb


CLOSEID=wx.NewId()
PREVID=wx.NewId()
NEXTID=wx.NewId()
UPID=wx.NewId()
DOWNID=wx.NewId()


class Navi(wx.Panel):
    """
    Container for in bar close button and navigation arrows
    """
    def __init__(self, parent):
        """
            standard fair
        """
        wx.Panel.__init__(self, parent, style=0)

        events=[
            (wx.EVT_PAINT,self.OnPaint),
            (wx.EVT_ERASE_BACKGROUND, lambda e:None),
            (wx.EVT_BUTTON, self.OnButton)
        ]
        do(self.Bind(event, method) for (event, method) in events)

        #make sizers
        self.Sizer=wx.BoxSizer(wx.HORIZONTAL)
        self.hsizer=wx.BoxSizer(wx.HORIZONTAL)
        self.vsizer=wx.BoxSizer(wx.VERTICAL)

        #make Buttons
        self.closebutton=UberButton(self, CLOSEID, skin=self.Parent.closebuttonskin, icon=self.Parent.closeicon)
        self.prevb=UberButton(self, PREVID, skin=self.Parent.scrollbuttonskin, icon=self.Parent.lefticon)
        self.nextb=UberButton(self, NEXTID, skin=self.Parent.scrollbuttonskin, icon=self.Parent.righticon)
        self.upb=UberButton(self, UPID, skin=self.Parent.scrollbuttonskin, icon=self.Parent.upicon)
        self.downb=UberButton(self, DOWNID, skin=self.Parent.scrollbuttonskin, icon=self.Parent.downicon)

        #add butons to sizers
        self.hsizer.Add(self.prevb, 0, wx.EXPAND)
        self.hsizer.Add(self.nextb, 0, wx.EXPAND)
        self.vsizer.Add(self.upb, 1, wx.EXPAND)
        self.vsizer.Add(self.downb, 1, wx.EXPAND)
        self.Sizer.Add(self.hsizer, 0, wx.EXPAND)
        self.Sizer.Add(self.closebutton, 0, wx.CENTER|wx.ALL, 5)

        #Hide all buttons
        self.prevb.Show(False)
        self.nextb.Show(False)
        self.upb.Show(False)
        self.downb.Show(False)
        self.closebutton.Show(pref('tabs.tabbar_x', False))

        self.type=None

#    def UpdateSkin(self):
#        p = self.Parent
#
#        self.closebutton.SetSkinKey(p.closeskin)
#
#        self.closebutton.SetIcon(p.closeicon)
#
#        scrollskin = p.scrollbuttonskin
#
#        self.prevb.SetSkinKey(scrollskin)
#        self.nextb.SetSkinKey(scrollskin)
#        self.upb.SetSkinKey(scrollskin)
#        self.downb.SetSkinKey(scrollskin)
#
#        self.prevb.SetIcon(p.lefticon)
#        self.nextb.SetIcon(p.righticon)
#        self.upb.SetIcon(p.upicon)
#        self.downb.SetIcon(p.downicon)

    def Enabler(self):
        """
            Enable/Disable each button based off of acceptable scrolling
        """
        self.prevb.Enable(self.Parent.tabindex>0)
        self.nextb.Enable(self.Parent.tabendex<self.Parent.GetTabCount()-1)
        self.upb.Enable(self.Parent.rowindex>0)
        self.downb.Enable(self.Parent.rowindex<len(self.Parent.rows)-pref('tabs.rows',2))#self.Parent.visible)

    def ShowNav(self, type=None):
        """
        tells the navi which set of nav aroows to show
        type 0 - No arrows
        type 1 - left and right next to close button
        type 3 - up and down below close button
        """

        #do nothing if no change
        if self.type==type:
            #self.Layout()
            return

        #hide everything in prep for change
        self.prevb.Show(False)
        self.nextb.Show(False)
        self.upb.Show(False)
        self.downb.Show(False)
        self.Sizer.Detach(self.vsizer)

        if not type:#No arrows
            self.Sizer.Detach(self.closebutton)
            self.Sizer.Add(self.closebutton, 0, wx.CENTER|wx.ALL, 5)
            self.prevb.Show(False)
            self.nextb.Show(False)
        elif type==1:#Horizantel Arrows
            self.Sizer.Detach(self.closebutton)
            self.Sizer.Add(self.closebutton, 0, wx.CENTER|wx.ALL, 5)
            self.Sizer.SetOrientation(wx.HORIZONTAL)
            self.prevb.Show(True)
            self.nextb.Show(True)
        elif type==3:#Vertical arrows
            self.Sizer.Detach(self.closebutton)
            self.Sizer.Add(self.closebutton, 0, wx.CENTER|wx.ALL, 5)
            self.Sizer.SetOrientation(wx.VERTICAL)
            self.Sizer.Add(self.vsizer, 1, wx.EXPAND)
            self.upb.Show(True)
            self.downb.Show(True)
        elif type==4:#sidebar mode, no arrows as they are part of TabBar
            self.prevb.Show(False)
            self.nextb.Show(False)
            self.Sizer.Detach(self.closebutton)
            self.Sizer.Add(self.closebutton, 0, wx.CENTER)

        self.type=type

        #self.Layout()



    def OnButton(self, event):
        """
            Handels all events for any button clciked in the navi
        """
        if event.GetId()==CLOSEID:
            self.Parent.Parent.pagecontainer.active.tab.Close()
        elif event.GetId()==PREVID:
            if self.Parent.tabindex>0:
                self.Parent.tabindex-=1
                self.Parent.Regenerate(True)
        elif event.GetId()==NEXTID:
            endex=self.Parent.tabendex
            if endex<self.Parent.GetTabCount()-1:
                while self.Parent.tabendex==endex:
                    self.Parent.tabindex+=1
                    self.Parent.Regenerate(True)
        elif event.GetId()==UPID:
            if self.Parent.rowindex>0:
                self.Parent.rowindex-=1
                self.Parent.Regenerate(True)
        elif event.GetId()==DOWNID:
            if self.Parent.rowindex<len(self.Parent.rows)-pref('tabs.rows',2):#self.Parent.visible:
                self.Parent.rowindex+=1
                self.Parent.Regenerate(True)
        self.Enabler()

#        SmokeAndMirrorsBomb(self,[self.prevb,self.nextb,self.upb,self.downb,self.closebutton])

        self.Parent.Refresh()

        self.Parent.UpdateNotify()

    def OnPaint(self,event):
        dc=wx.PaintDC(self)
        rect=wx.RectS(self.Size)

        dc.Brush=wx.WHITE_BRUSH
        dc.Pen=wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)
#        SmokeAndMirrorsBomb(self,[self.prevb,self.nextb,self.upb,self.downb,self.closebutton])
