import wx
from gui.uberwidgets.UberCombo import UberCombo
from gui import skin as skincore
from gui.textutil import GetFonts
from gui.uberwidgets.simplemenu import SimpleMenuItem

from util.primitives.funcs import do

class F(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None,size=(500,55))

        events=[
            (wx.EVT_COMBOBOX,self.OnSelect),
#            (wx.EVT_TEXT,self.OnType),
#            (wx.EVT_TEXT_ENTER,self.OnPressEnter)
        ]
        do(self.Bind(event,method) for (event,method) in events)

        self.skin='combobox'
        self.uc=UberCombo(self, skinkey=self.skin,typeable=False,size=(100,20),maxmenuheight=3,minmenuwidth=400,)#selectioncallback=self.defaultmethodtest)
        items=[
            SimpleMenuItem([skincore.get("statusicons.typing"),'Test1']),
            SimpleMenuItem([skincore.get("statusicons.typing"),skincore.get("statusicons.typing"),'Test2']),
            SimpleMenuItem([skincore.get("statusicons.typing"),skincore.get("statusicons.typing"),skincore.get("statusicons.typing"),'Test3 followed by a long line of thext so I can see if truncating worked well or not, maybe?']),
            SimpleMenuItem(id=-1),
            SimpleMenuItem([skincore.get("statusicons.typing"),skincore.get("statusicons.typing"),skincore.get("statusicons.typing"),'Test4 cause I can'])
        ]
        self.uc.SetItems(items)

        self.ucf=UberCombo(self, skinkey=self.skin,typeable=False,size=(100,20),maxmenuheight=10,minmenuwidth=400)#font method
        self.ucf.SetItems(self.DoFonts())

        self.uct=UberCombo(self, value='test',skinkey=self.skin,typeable=True,valuecallback=self.ValueTest,size=(100,20))
        self.uct.AppendItem(SimpleMenuItem('Sample Item 1'))
        self.uct.AppendItem(SimpleMenuItem('Sample Item 2'))
        self.uct.AppendItem(SimpleMenuItem(id=-1))
        self.uct.AppendItem(SimpleMenuItem('Sample Item 3'))


        sizer=wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(sizer)
        sizer.Add(self.uc,1,wx.EXPAND | wx.ALL, 3)
        sizer.Add(self.ucf,1,wx.EXPAND | wx.ALL, 3)
        sizer.Add(self.uct,1,wx.EXPAND | wx.ALL, 3)

        self.Fit()

    def DoFonts(self):
        fontlist = GetFonts()
        fontitems = []
        for font in fontlist:
            wxfont = wx.Font(self.Font.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                             wx.FONTWEIGHT_NORMAL, False, font)
            if font[0] != '@':
                fontitems.append(SimpleMenuItem([font], font=wxfont))

        return fontitems

    def defaultmethodtest(self,item):
        print item.id
        for i in item.content:
                if isinstance(i,basestring):
                    print i
                    break

    def DifferentMethodTest(self,item):
        print 'workage!!'

    def CycleTest(self,button):
        print 'yey!'
        button.Parent.display.TypeField()
        button.Parent.display.txtfld.SetSelection(-1,-1)

    def OnSelect(self,event):
        print 'OnSelect:', event.GetInt()

    def OnType(self,event):
        print 'OnType'

    def OnPressEnter(self,event):
        print 'OnPressEnter'

    def ValueTest(self,value):
        print 'valuecallback',value

if __name__ == '__main__':
    from tests.testapp import testapp
    hit = wx.FindWindowAtPointer
    a = testapp('../../../../')
    f=F()
    f.Show(True)
    del f
    a.MainLoop()
