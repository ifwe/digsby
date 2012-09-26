from __future__ import with_statement
import wx

from gui.uberwidgets.UberEmotiBox import EmotiHandler,UberEmotiBox

from gui.skin import skininit

from util.primitives.funcs import do

class F(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,size=(75,100))

        events=[
            (wx.EVT_BUTTON,self.OnButton)
        ]
        do(self.Bind(event,method) for (event,method) in events)
        emotihandler=EmotiHandler()
        self.cp=UberEmotiBox(self,emotihandler)

        self.b1=wx.Button(self,label='^_^')

    def OnButton(self,event):
        #print 'open faces'
        self.cp.Display(self.b1.ScreenRect)

class A(wx.App):
    def OnInit(self):
        skininit('../../../../res')
        f=F()
        f.Show(True)
        return True

if __name__=='__main__':
    a=A(0)
    a.MainLoop()
