from DemoApp import App
import wx
from gui.uberwidgets.simplemenu import SimpleMenu,SimpleMenuItem
from gui.uberwidgets.UberButton import UberButton

class Frame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,title='Extended Simple Menu Test')
        self.panel=wx.Panel(self)

        self.panel.Sizer=wx.BoxSizer(wx.VERTICAL)


        menu=SimpleMenu(self, 'simplemenu',width=100)
        submenu=SimpleMenu(menu, 'simplemenu',width=100)
        submenu2=SimpleMenu(submenu, 'simplemenu',width=100)

        subitems=[
            SimpleMenuItem('Test5'),
            SimpleMenuItem(id=-1),
            SimpleMenuItem('Test6'),
            SimpleMenuItem('Test7',menu=submenu2),
            SimpleMenuItem('Test8')
        ]

        submenu.SetItems(subitems)

        items=[
            SimpleMenuItem('Test1'),
            SimpleMenuItem('Test2'),
            SimpleMenuItem("Test3 is a submenu m'kay",menu=submenu),
            SimpleMenuItem(id=-1),
            SimpleMenuItem('Test4'),
        ]

        items3=[
            SimpleMenuItem('Test9'),
            SimpleMenuItem('Test10'),
            SimpleMenuItem('Test11'),
            SimpleMenuItem('Test12'),
            SimpleMenuItem('Test13'),
            SimpleMenuItem('Test14'),
            SimpleMenuItem('Test15'),
            SimpleMenuItem('Test16'),
            SimpleMenuItem('Test17')
        ]

        submenu2.SetItems(items3)


        menu.SetItems(items)

        skin='button'
        size=None#(100,100)#
        type='menu'#None#'toggle'#
        #menu=None#self.menu#
        icon=wx.Bitmap('../../../res/skins/default/statusicons/mobile.png',wx.BITMAP_TYPE_PNG)#wx.Bitmap('../../res/skins/default/tinydigsby.png',wx.BITMAP_TYPE_PNG)

        self.smb1=UberButton(self.panel,wx.NewId(),"SMB",skin,icon=icon,style=wx.HORIZONTAL,size=size,type=type,menu=menu)

        self.panel.Sizer.Add(self.smb1)

        self.Bind(wx.EVT_MENU,self.OnMenu)

    def OnMenu(self,event):
        print "Hey, it works?!?"


def Go():
    f=Frame()
    f.Show(True)

if __name__=='__main__':
    a = App( Go )
    a.MainLoop()