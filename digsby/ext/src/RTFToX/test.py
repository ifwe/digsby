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

from cgui import ExpandoTextCtrl

from gui.uberwidgets.formattedinput2.fontutil import FontFromFacename
from cgui import EVT_ETC_LAYOUT_NEEDED

def _(text):
    return text
__builtins__._ = _

from gui.uberwidgets.formattedinput2.formattedinput import FormattedInput





def NewInput():


    f = wx.Frame(None)

    f.Sizer = wx.BoxSizer(wx.VERTICAL)

    font = wx.Font(22, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, True, "Comic Sans MS");
    textattr = wx.TextAttr(wx.Color(255,0,255), wx.Color(0,255,255), font);

    #font = FontFromFacename('Arial')
    #font.SetPointSize(10)
    #textattr = wx.TextAttr(wx.Color(255,0,255), wx.WHITE, font) #@UndefinedVariable

    output = wx.TextCtrl(f, -1, style = wx.TE_READONLY | wx.TE_MULTILINE)
    output.SetMinSize(wx.Size(200, 200))
    f.Sizer.Add(output, 1, wx.EXPAND)


#    fo = {'default': False,
#          'italic': True}

    input = ExpandoTextCtrl(f, wx.ID_ANY)
    input.SetStyle(0,0,textattr)

    #input = FormattedExpandoTextCtrl(f, multiFormat = True, format = textattr)
    #input = FormattedInput(f, multiFormat = True, format = textattr)#, formatOptions = fo)

    def OnExpandEvent(event):
        try:
            height = (input.fbar.Size.height if input.FormattingBarIsShown() else 0) + input.tc.MinSize.height
        except:
            height = input.MinSize.height

        input.MinSize = wx.Size(-1, height)
        f.Fit()

    def OnEnterKey(event):

        if event.KeyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and event.Modifiers == wx.MOD_SHIFT:
            try:
                output.Value = input.tc.GetRTF()
            except:
                output.Value = input.GetRTF()
            input.Clear()

            return

        event.Skip()


    input.Bind(EVT_ETC_LAYOUT_NEEDED, OnExpandEvent)
    try:
        input.tc.Bind(wx.EVT_KEY_DOWN, OnEnterKey)
    except:
        input.Bind(wx.EVT_KEY_DOWN, OnEnterKey)

    f.Sizer.Add(input, 0, wx.EXPAND)
    f.MinSize = f.BestSize

    f.Show()
    f.Fit()

    input.SetFocus()

if __name__ == '__main__':
    app = testapp(plugins = False)

    NewInput()

    app.MainLoop()

