import wx
from gui.uberwidgets.UberButton import UberButton
#from gui.uberwidgets.umenu import UMenu



class F(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.NewId(), "Button sampler",(400,100),(400,600),wx.DEFAULT_FRAME_STYLE)
        self.panel=P(self)

class P(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent,-1)#,style = wx.CLIP_CHILDREN|wx.CLIP_SIBLINGS

        self.Bind(wx.EVT_BUTTON,self.onButton),
        self.Bind(wx.EVT_LEFT_UP,self.OnMouse),
        self.Bind(wx.EVT_LEFT_DOWN,self.OnMouse)

        self.skin = 'button'
#        print self.skin
#        self.menu=UMenu(self)
#        self.menu.Append(wx.NewId(),'item 1')
#        self.menu.Append(wx.NewId(),'item 2')
#        self.menu.Append(wx.NewId(),'item 3')

        content=wx.BoxSizer(wx.VERTICAL)

        size=None#(200,50)#
        type=None#'menu'#'toggle'#'toggle'#
        menu=None#self.menu#
        icon=wx.Bitmap('../../../../res/skins/default/statusicons/mobile.png',wx.BITMAP_TYPE_PNG)#wx.Bitmap('../../res/skins/default/tinydigsby.png',wx.BITMAP_TYPE_PNG)
        #label= "button"#"Super wide Button Name of Impending doooooooooooom!!!"#"button"#
        skin=self.skin#None#

        self.b1=UberButton(self,wx.NewId(),'&One',skin,icon=icon,style=wx.HORIZONTAL,size=size,type=type,menu=menu)
#        self.b1.SetStaticWidth(60)
        self.b2=UberButton(self,wx.NewId(),'&Two',icon=icon,style=wx.HORIZONTAL,size=size,type=type,menu=menu)
        self.b3=UberButton(self,wx.NewId(),'T&hree',skin,icon=icon,style=wx.VERTICAL,size=size,type=type,menu=menu)
        self.b4=UberButton(self,wx.NewId(),'&Four',icon=icon,style=wx.VERTICAL,size=size,type=type,menu=menu)
        self.b5=UberButton(self,wx.NewId(),"",skin,icon=icon,size=size,type=type,menu=menu)
        self.b6=UberButton(self,wx.NewId(),"",icon=icon,size=size,type=type,menu=menu)
        self.b7=UberButton(self,wx.NewId(),'Fi&ve',skin,size=size,type=type,menu=menu)
        self.b8=UberButton(self,wx.NewId(),'&Six',size=size,type=type,menu=menu)
        self.b9=UberButton(self,wx.NewId(),"",skin,size=size,type=type,menu=menu)
        self.b10=UberButton(self,wx.NewId(),"",size=size,type=type,menu=menu)
        self.b11 = wx.Button(self, wx.NewId(), 'Native')
        self.b12= wx.Button(self, wx.NewId(), ' ')
        self.b12.Bind(wx.EVT_BUTTON,self.ToggleAlignment)

        self.b13 = UberButton(self, wx.NewId(), 'active?', self.skin)
        self.b13.Bind(wx.EVT_BUTTON,self.ToggleSkin)

        wexp = 0#wx.EXPAND#wx.ALL|
        hrat = 0#1#
        pad = 0

        content.Add(self.b1,hrat,wexp,pad)
        content.Add(self.b2,hrat,wexp,pad)
        content.Add(self.b3,hrat,wexp,pad)
        content.Add(self.b4,hrat,wexp,pad)
        content.Add(self.b5,hrat,wexp,pad)
        content.Add(self.b6,hrat,wexp,pad)
        content.Add(self.b7,hrat,wexp,pad)
        content.Add(self.b8,hrat,wexp,pad)
        content.Add(self.b9,hrat,wexp,pad)
        content.Add(self.b10,hrat,wexp,pad)
        content.Add(self.b11,hrat,wexp,pad)
        content.Add(self.b12,hrat,wexp,pad)
        content.Add(self.b13, hrat, wexp, pad)


        self.SetSizer(content)

    def onButton(self,event):
        print event.GetEventObject().Label
#        print "..."
#        if type(event.EventObject)==wx.Button:
#            print event.EventObject.Label
#        else:
#            print event.EventObject.label
#        switch= not self.b1.IsEnabled()
#        self.b1.Enable(switch)
#        self.b2.Enable(switch)
#        self.b3.Enable(switch)
#        self.b4.Enable(switch)
#        self.b5.Enable(switch)
#        self.b6.Enable(switch)
#        self.b7.Enable(switch)
#        self.b8.Enable(switch)
#        self.b9.Enable(switch)
#        self.b10.Enable(switch)
#        self.b11.Enable(switch)

    def ToggleSkin(self,event = None):
        key = None if self.b1.skinkey else 'button'

        print 'toggleskin to',key
        self.b1.SetSkinKey(key,1)
        self.b3.SetSkinKey(key,1)
        self.b5.SetSkinKey(key,1)
        self.b7.SetSkinKey(key,1)
        self.b9.SetSkinKey(key,1)

    def ToggleAlignment(self,event = None):
        print "ToggleAlignment DISABLED!!! It can not be!!!"
#        align = wx.VERTICAL if self.b1.Alignment == wx.HORIZONTAL else wx.HORIZONTAL
#        self.b1.Alignment = align
#        self.b3.Alignment = align
#        self.b5.Alignment = align
#        self.b7.Alignment = align
#        self.b9.Alignment = align
#        self.Layout()


    def OnMouse(self,event):
        print "window caught mouse"


if __name__ == '__main__':
    from tests.testapp import testapp

    hit = wx.FindWindowAtPointer

    a = testapp()

    f=F()
    f.Show(True)

    a.MainLoop()
