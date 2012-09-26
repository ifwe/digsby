import wx
from gui.textutil import Wrap


class AutoHeightStaticText(wx.StaticText):
    '''
    Extension of wxStaticText that handels wrapping automatically figures out it's minheight from the contained text
    '''

    def __init__(self, parent, id, label, pos = wx.DefaultPosition, size = wx.DefaultSize, style = 0, name = 'staticText'):
        wx.StaticText.__init__(self, parent, id, label, pos, size, style, name)

        self.Bind(wx.EVT_SIZE, self.OnSize)

        self.CalcSize()

    def OnSize(self, event):
        event.Skip()
        self.CalcSize()

    def CalcSize(self):
        dc = wx.MemoryDC()
        wlabel = Wrap(self.Label, self.Size.width, self.Font, dc, 0)
        exts = dc.GetMultiLineTextExtent(wlabel, self.Font)[:2]
        self.SetMinSize((self.MinSize.width, exts[1]))
        self.Top.Layout()