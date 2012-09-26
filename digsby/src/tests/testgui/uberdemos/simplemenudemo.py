from DemoApp import App
import wx
#from gui import skin as skincore
from gui.uberwidgets.simplemenu import SimpleMenu,SimpleMenuItem
from gui.uberwidgets.UberButton import UberButton

class Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,title='Simple Menu Test')
        self.panel=wx.Panel(self)

        self.panel.Sizer=wx.BoxSizer(wx.VERTICAL)


        menu=SimpleMenu(self, skinkey='simplemenu',maxheight=10,width=100)


        items=[
            SimpleMenuItem('Test1'),#,self.DifferentMethodTest),
            SimpleMenuItem('Test2'),
            SimpleMenuItem('Test3'),
            SimpleMenuItem(id=-1),
            SimpleMenuItem('Test4')
        ]

        menu.SetItems(items)

        skin='button'
        size=None#(100,100)#
        type='menu'#None#'toggle'#
        #menu=None#self.menu#
        icon=None#wx.Bitmap('../../../res/skins/default/statusicons/mobile.png',wx.BITMAP_TYPE_PNG)#wx.Bitmap('../../res/skins/default/tinydigsby.png',wx.BITMAP_TYPE_PNG)

        self.smb1=UberButton(self.panel,wx.NewId(),"SMB",skin,icon=icon,style=wx.HORIZONTAL,size=size,type=type,menu=menu)

        self.panel.Sizer.Add(self.smb1)


def Go():
    f=Frame()
    f.Show(True)

if __name__=='__main__':
    a = App( Go )
    a.MainLoop()