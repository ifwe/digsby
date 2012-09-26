import wx, wx.html

from wx.lib.expando import ExpandoTextCtrl
#from gui.uberwidgets.formattedinput import FormattedInput
#from gui.uberwidgets.SizerBar import SizerBar
import gettext
gettext.install('Digsby', unicode=True)
from gui.skin import skininit
from gui.uberwidgets.formattedinput import FormattedInput

class P(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent,-1)

        self.Sizer=wx.BoxSizer(wx.VERTICAL)

        from util import trace
        trace(ExpandoTextCtrl)

        #profile = ExpandoTextCtrl(self,style= wx.TE_MULTILINE|wx.TE_CHARWRAP|wx.TE_PROCESS_ENTER|wx.NO_BORDER|wx.WANTS_CHARS|wx.TE_NOHIDESEL|wx.TE_RICH)
        profile=FormattedInput(self)
        self.Sizer.Add(profile,0)
        self.Layout()



class F(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None,-1,"Profile Box Test")

        self.Sizer =wx.BoxSizer(wx.VERTICAL)
        p=P(self)
        self.Sizer.Add(p,1,wx.EXPAND)


class A(wx.App):
    def OnInit(self):

#        self.Bind(wx.EVT_KEY_DOWN,self.OnKeyDown)

        skininit('../../../res')
        f=F()
        f.Bind(wx.EVT_CLOSE, lambda e: self.ExitMainLoop())

        wx.CallAfter(f.Show)
#        pref=PreF()
#        pref.Show(True)
        return True



if __name__=='__main__':

    #a = A( 0 )
    #from util import profile
    #profile(a.MainLoop)

    from tests.testapp import testapp
    a = testapp('../../../../')
    f = F()

#    inp = FormattedInput(f)
#    s.Add(inp, 0, wx.EXPAND)


#    def doit(e):
#        inp.Fit()

    #inp.bemote.Bind(wx.EVT_BUTTON, doit)

    f.Show()
    a.MainLoop()

