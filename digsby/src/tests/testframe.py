import wx

from util import odict

class TestFrame(wx.Frame):
    def __init__(self,title = "Test - <Untitled>"):

        wx.Frame.__init__(self,None,-1,title)

        self.MenuBar = wx.MenuBar()

        self.menumap = {}

        menus = odict()
        menus['System'] = [('&About'  , self.OnAbout  , 'About this test'     ),
                           ('-'                                               ),
                           ('&Console', self.OnConsole, 'Digsby Shell'        ),
                           ('&Prefs'  , self.OnPrefs  , 'Advanced Preferences'),
                           ('-'                                               ),
                           ('E&xit'   , self.OnExit   , 'Terminate Test App'  )]



        self.AddMenu(menus)

        Bind = self.Bind
        Bind(wx.EVT_MENU,self.OnMenu)
        Bind(wx.EVT_CLOSE, self.OnClose)


    def AddMenu(self,menumeta):
        for menutitle in menumeta:
            wxmenu = wx.Menu()
            for item in menumeta[menutitle]:
                if item[0] == '-':
                    wxmenu.AppendSeparator()
                    continue;
                itemid = wx.NewId()
                self.menumap[itemid] = item[1]
                wxmenu.Append(itemid, item[0], item[2])
            self.MenuBar.Append(wxmenu, menutitle)

    def OnMenu(self,event):
        self.menumap[event.Id]()

    def OnAbout(self):
        print 'OnAbout'

    def OnConsole(self):
        print 'OnConsole'

    def OnPrefs(self):
        print 'OnPrefs'

    def OnExit(self):
        print 'OnExit'
        self.Close()

    def OnClose(self,event):
        wx.GetApp().Exit()







