import wx
from cgui import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED




a = wx.PySimpleApp()

def MakeTextFrame(type = "Expando"):
    f = wx.Frame(None, -1, title=type)

    if type == "Expando":
        tc = ExpandoTextCtrl(f,-1)
    else:
        tc = wx.TextCtrl(f,-1,style = wx.TE_RICH2 | wx.TE_MULTILINE | wx.TE_NO_VSCROLL)

    tc.ShowScrollbar(wx.VERTICAL, False)
    def OnKey(event):
        event.Skip()
        line = tc.PositionToXY(tc.GetInsertionPoint())[2]
        scrollPos = tc.GetScrollPos(wx.VERTICAL)
        print line, scrollPos

    def OnLayoutneeded(event):
        event.Skip()
        f.Fit()

    def OnKeyDownStripNewlineModifiers(event):
        if event.KeyCode == wx.WXK_RETURN and event.Modifiers:

            e = wx.KeyEvent(wx.EVT_CHAR)
            e.m_keyCode = event.m_keyCode
            e.m_rawCode = event.m_rawCode
            e.m_rawFlags = event.m_rawFlags
            e.m_scanCode = event.m_scanCode
            e.m_controlDown = False
            e.m_altDown = False
            e.m_metaDown = False
            e.m_shiftDown = False

            tc.WriteText('\n')

            tc.ProcessEvent(e)
        else:
            event.Skip()

    tc.Bind(wx.EVT_KEY_DOWN, OnKeyDownStripNewlineModifiers)

    tc.Bind(wx.EVT_KEY_DOWN, OnKey)

    tc.Bind(EVT_ETC_LAYOUT_NEEDED, OnLayoutneeded)

    if type == "Expando":
        tc.SetMaxHeight(100)

    f.Show()
    f.Layout()

MakeTextFrame()
MakeTextFrame("wxTextCtrl")

a.MainLoop()