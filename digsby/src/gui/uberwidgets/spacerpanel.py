from gui.skin.skinobjects import SkinColor
import wx
from gui.prototypes.newskinmodule import NewSkinModule


SpacerPanelSkinDefaults = {
    'background' : lambda: SkinColor(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DFACE)),
    'size' : lambda: wx.Point(2,2)
}

class SpacerPanel(wx.Panel, NewSkinModule):
    '''
    Small spacer to visually separate UI components
    '''
    def __init__(self, parent, skinkey = None):
        wx.Panel.__init__(self, parent)


        self.SetSkinKey(skinkey, SpacerPanelSkinDefaults)


        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def DoUpdateSkin(self, skin):
        self.skinSP = skin

        self.SetMinSize(self.skinSP['size'])
        self.Parent.Layout()

    def GetSkinProxy(self):
        return self.skinSP if hasattr(self, 'skinSP') else None

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)

        self.skinSP['background'].Draw(dc, rect)



