import wx
from wx import BufferedPaintDC,RectS
from gui.uberwidgets.uberwidget import UberWidget
from gui.uberwidgets.UberButton import UberButton
from util.primitives.funcs import Delegate

class SkinnedPanel(wx.Panel,UberWidget):
    '''
    Simple skinnable wxPanel
    Depricated - Replaced with SimplePanel from cgui
    '''
    def __init__(self, parent, key):
        wx.Panel.__init__(self, parent, style = wx.TAB_TRAVERSAL | wx.FULL_REPAINT_ON_RESIZE)

        self.SetSkinKey(key,True)

        Bind = self.Bind
        Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        Bind(wx.EVT_PAINT, self.OnPaint)

        self.ChildPaints = Delegate()

    def UpdateSkin(self):
        from gui import skin

        skinkey = self.skinkey

        native = self.native = not skinkey

        if not native:
            self.bg = skin.get(skinkey+".background")
            self.itemskin = skin.get(skinkey+".itemskin")

            for child in self.Children:
                if isinstance(child,UberButton):
                    child.SetSkinKey(self.itemskin)

        self.Refresh(False)


    def OnPaint(self, e):
        dc = BufferedPaintDC(self)

        if self.bg:
            self.bg.Draw(dc, RectS(self.ClientSize))
        self.ChildPaints(dc)
