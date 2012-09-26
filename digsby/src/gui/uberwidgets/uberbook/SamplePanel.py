import wx
from gui.toolbox import get_wxColor
from util.primitives.funcs import do
class SamplePanel(wx.Panel):
    """
    This is a panel that is provided a color, used as a sample place holder
    stores one variable, name which is the color provided, and is filled with
    that color
    """
    def __init__(self, parent, color="red"):
        wx.Panel.__init__(self, parent, style=0)
        self.name=color

        events=[
            (wx.EVT_PAINT, self.OnPaint),
            (wx.EVT_ERASE_BACKGROUND, lambda e:None)
        ]
        do(self.Bind(event, method) for (event, method) in events)

    def OnPaint(self, event):
        dc=wx.AutoBufferedPaintDC(self)
        rect=wx.RectS(self.GetSize())

        dc.SetBrush(wx.Brush(get_wxColor(self.name)))
        dc.DrawRectangleRect(rect)
