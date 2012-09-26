import sys;
sys.path.append('C:\\Users\\Aaron\\workspace\\DigsbyTrunk\\digsby');

#import os
#os.chdir('C:\\Users\\Aaron\\workspace\\DigsbyTrunk\\digsby')

from ctypes import windll
windll.comctl32.InitCommonControls()

import wx
from tests.testapp import testapp
from win32events import bindwin32
from gui.uberwidgets.formattedinput2.FormattedExpandoTextCtrl import FormattedExpandoTextCtrl
FormattedExpandoTextCtrl.BindWin32 = bindwin32

#wx.Window.BindWin32 = bindwin32
#import gui.native.win.winhelpers

from gui.uberwidgets.formattedinput2.fontutil import FontFromFacename
from cgui import EVT_ETC_LAYOUT_NEEDED

def _(text):
    return text
__builtins__._ = _

from gui.uberwidgets.formattedinput2.formattedinput import FormattedInput


def NewInput():
    f = wx.Frame(None)

    f.Sizer = wx.BoxSizer(wx.VERTICAL)

    font = FontFromFacename('Arial')
    font.SetPointSize(10)
#    fo = {'default': False,
#          'italic': True}
    textattr = wx.TextAttr(wx.BLACK, wx.WHITE, font) #@UndefinedVariable

    i = FormattedInput(f, multiFormat = True)#, formatOptions = fo)

    def OnExpandEvent(event):
        height = (i.fbar.Size.height if i.FormattingBarIsShown() else 0) + i.tc.MinSize.height

        i.MinSize = wx.Size(-1, height)
        f.Fit()

    i.Bind(EVT_ETC_LAYOUT_NEEDED, OnExpandEvent)

    f.Sizer.Add(i, 0, wx.EXPAND)

    f.Show()
    f.Fit()

if __name__ == '__main__':
    app = testapp(plugins = False)

    NewInput()

    app.MainLoop()

