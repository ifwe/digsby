import wx
from gui.uberwidgets import UberWidget
from gui import skin
from gui.skin.skinobjects import SkinColor,Margins
from cgui import SimplePanel

objget = object.__getattribute__

class PanelFrame(SimplePanel, UberWidget):
    '''
    Frame for panels in the buddylist
    '''

    def __init__(self, parent, panel, skinkey):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        self.SetSkinKey(skinkey, True)
        if not panel.Parent is self:
            panel.Reparent(self)

        self.panel = panel

        sizer = self.Sizer = wx.GridBagSizer()
        sizer.SetEmptyCellSize(wx.Size(0,0))
        sizer.Add(panel,(1,1),flag = wx.EXPAND)
        sizer.Add(wx.Size(self.framesize.left,  self.framesize.top),    (0,0))
        sizer.Add(wx.Size(self.framesize.right, self.framesize.bottom), (2,2))

        sizer.AddGrowableCol(1,1)
        sizer.AddGrowableRow(1,1)

        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def __repr__(self):
        return '<PanelFrame for %r>' % self.panel

    def __getattr__(self,attr):
        try:
            return objget(self, attr)
        except AttributeError:
            try:
                return getattr(objget(self, 'panel'), attr)
            except AttributeError,e:
                raise e

    def OnPaint(self,event):
        self.framebg.Draw(wx.AutoBufferedPaintDC(self), wx.RectS(self.ClientSize))

    def UpdateSkin(self):
        key = self.skinkey
        s = lambda k, default: skin.get('%s.%s' % (key, k), default)

        self.framebg   = s('frame',     SkinColor(wx.BLACK))
        self.framesize = s('framesize', Margins([0,0,0,0]))

        sz = self.Sizer
        if sz:
            sz.Detach(1)
            sz.Detach(1)
            sz.Add(wx.Size(self.framesize.left,  self.framesize.top),(0,0))
            sz.Add(wx.Size(self.framesize.right, self.framesize.bottom),(2,2))

        wx.CallAfter(self.Layout)
        wx.CallAfter(self.Refresh)
