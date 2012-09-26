import wx
from wx import RectPS, ClientDC, PaintDC, BoxSizer, HORIZONTAL

from gui.textutil import default_font,Wrap

default_alignment = wx.ALIGN_LEFT | wx.ALIGN_TOP

class ClearText(wx.BoxSizer):
    '''
    A hack to display text on a parent with custom background with wrapping support
    Draws the text directly on it's parent
    If the parent has a ChildPaints delegate it hooks into that otherwise hooks into the paint of a 1x1px child
    '''
    def __init__(self, parent, label = '', alignment = default_alignment):
        BoxSizer.__init__(self, HORIZONTAL)

        self.parent    = parent
        self.label     = self.flabel = label
        self.fontcolor = wx.BLACK
        self.font      = default_font()
        self.alignment = alignment

        #Child used to hook into drawing events
        self.anchor = wx.Window(parent, -1 ,size=(1, 1),
                                style = wx.BORDER_NONE | wx.TRANSPARENT_WINDOW)
        self.anchor.Bind(wx.EVT_ERASE_BACKGROUND, Null)

        if hasattr(parent, 'ChildPaints'):
            parent.ChildPaints += self.PaintSlave
        else:
            self.anchor.Bind(wx.EVT_PAINT,self.OnPaint)

        self.CalcSize()

    def Show(self,s = True):
        wx.BoxSizer.Show(self, 0, s)
        wx.BoxSizer.Show(self, 1, s)
        self.Layout()

    def Hide(self):
        self.Show(False)

    def UpdateSkin(self):
        self.CalcSize()

    def CalcSize(self):
        dc = wx.MemoryDC()
        exts = dc.GetMultiLineTextExtent(self.flabel, self.font)[:2]
        self.SetMinSize(exts)

        self.Clear()
        self.Add(self.anchor)
        self.AddSpacer((max(1,exts[0]-1), # to account for self.anchor's size
                       exts[1]))

    def SetFontColor(self,color):
        assert isinstance(color,wx.Color), (type(color), color)
        self.fontcolor = color

    def GetFontColor(self):
        return self.fontcolor


    ForegroundColour = FontColor = property(GetFontColor,SetFontColor)

    def SetFont(self,font):
        assert isinstance(font,wx.Font), (type(font), font)
        self.font = font

        self.CalcSize()

    def GetFont(self):
        return self.font

    Font = property(GetFont,SetFont)

    def SetLabel(self,label):
        self.label = self.flabel = label

        self.CalcSize()
        self.parent.Refresh(False)

    def GetLabel(self):
        return self.label

    Label = property(GetLabel, SetLabel)

    @property
    def Position(self):
        return self.anchor.Position

    def PaintSlave(self,dc):
        self.OnPaint(None, dc)

    def OnPaint(self, event, pdc = None):
        #If this is in reponse to a paint event, wx requires a PaintDC for the anchor
        if event: dc2 = PaintDC(self.anchor)
        dc = pdc or ClientDC(self.parent)

        dc.Font = self.font
        dc.TextForeground=self.fontcolor

        dc.DrawLabel(self.flabel, RectPS(self.anchor.Position, self.Size), alignment = self.alignment)

    def Wrap(self, width, maxlines=0):
        self.flabel = Wrap(self.label, width, self.font, None, maxlines)
        self.CalcSize()
