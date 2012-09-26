import wx

from gui.textutil import GetTextWidth
from gui import skin
from gui.toolbox import prnt
from cgui import SimplePanel

from config import platformName

class Chevron(SimplePanel):

    def __init__(self,parent,label='',callapsedicon=None,expandedicon=None):
        SimplePanel.__init__(self,parent)

        self.callapsedicon = callapsedicon or skin.get('AppDefaults.icons.chevroncolapsed')
        self.expandedicon = expandedicon or skin.get('AppDefaults.icons.chevronexpanded')
        self.Label = label
        self._expanded = False

        self.CalcSize()

        self.isdown = False

        Bind = self.Bind
        Bind(wx.EVT_PAINT,self.OnPaint)
        Bind(wx.EVT_LEFT_DOWN,self.OnLeftDown)
        Bind(wx.EVT_LEFT_UP,self.OnLeftUp)
        Bind(wx.EVT_LEFT_DCLICK, self.OnDClick)
        Bind(wx.EVT_ENTER_WINDOW, self.OnMouseIn)
        Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOut)

    def OnMouseIn(self, e):
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

    def OnMouseOut(self, e):
        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def CalcSize(self):
        iwidth  = max([self.callapsedicon.Width,self.expandedicon.Width])
        iheight = max([self.callapsedicon.Height,self.expandedicon.Height])

        self.iconspace = wx.Size(iwidth,iheight)

        fwidth  = GetTextWidth(self.Label,self.Font)
        fheight = self.Font.Height

        self.MinSize = wx.Size(iwidth + fwidth + 12,
                               max([iheight, fheight]) + 6)


    def GetExpanded(self):
        return self._expanded

    def SetExpanded(self,expand):
        self._expanded = expand

        e = wx.CommandEvent(wx.wxEVT_COMMAND_CHECKBOX_CLICKED)
        e.EventObject = self
        e.SetInt(expand)
        self.AddPendingEvent(e)

    Expanded = property(GetExpanded,SetExpanded)

    def OnPaint(self,event):

        dc = wx.PaintDC(self)
        rect = wx.RectS(self.Size)

        if platformName != 'mac':
            dc.Brush = wx.Brush(self.BackgroundColour)
            dc.Pen = wx.TRANSPARENT_PEN
            dc.DrawRectangleRect(rect)

        dc.Font = self.Font

        iwidth, iheight = self.iconspace
        icon = self.expandedicon if self.Expanded else self.callapsedicon
        textrect = wx.Rect(iwidth + 9,0, rect.width - (iwidth+9) - 3,rect.height)
        dc.DrawBitmap(icon,(iwidth//2-icon.Width//2)+3,(iheight//2-icon.Height//2)+3,True)
        dc.DrawLabel(self.Label, textrect, wx.ALIGN_LEFT|wx.ALIGN_TOP)

    def OnDClick(self, event):
        self.OnLeftDown(event)
        self.OnLeftUp(event)

    def OnLeftDown(self,event):
        self.isdown = True

    def OnLeftUp(self,event):
        if self.isdown:
            self.Expanded = not self.Expanded
            self.isdown = False

        self.Refresh()

class ChevronPanel(SimplePanel):
    def __init__(self, parent, label = '', collapsedicon = None, expandedicon = None):
        SimplePanel.__init__(self, parent)

        self.construct(label, collapsedicon, expandedicon)
        self.layout()
        self.bind_events()
        self.ToggleContents()

        self.Label = "chevron panel"

    def construct(self, label, collapsedicon, expandedicon):
        self.chevron = Chevron(self, label, collapsedicon, expandedicon)
        self.contents = wx.Panel(self, -1)
        self.contents.Label = 'chevron contents panel'
        self.contents.Sizer = wx.BoxSizer(wx.VERTICAL)

    def layout(self):
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.chevron, 0, wx.EXPAND | wx.ALL)
        self.Sizer.Add(self.contents, 1, wx.EXPAND | wx.ALL)

    def bind_events(self):
        self.chevron.Bind(wx.EVT_COMMAND_CHECKBOX_CLICKED, self.ToggleContents)

    def ToggleContents(self, evt = None):
        if evt is not None:
            obj = evt.GetEventObject()
        else:
            obj = self.chevron

        self.contents.Show(obj.Expanded)
        self.Top.Fit()

class F(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None)

        S = self.Sizer = wx.BoxSizer(wx.VERTICAL)
        p = self.panel = wx.Panel(self)
        S.Add(p,1,wx.EXPAND)


        s = p.Sizer = wx.BoxSizer(wx.VERTICAL)

        chev = self.chev = Chevron(p,'Expand')
        chev.Bind(wx.EVT_CHECKBOX,lambda e: prnt('clixxd',e.IsChecked()))

        s.Add(chev,0,wx.ALL,10)

if __name__ == '__main__':
    from tests.testapp import testapp

    hit = wx.FindWindowAtPointer

    a = testapp('../../')

    f=F()
    f.Show(True)

    a.MainLoop()
