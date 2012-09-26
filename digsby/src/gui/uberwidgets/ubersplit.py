import wx
from gui import skin
from gui.uberwidgets import UberWidget
from util import try_this

class UberSplitter(wx.SplitterWindow, UberWidget):
    def __init__(self, parent):
        wx.SplitterWindow.__init__(self, parent, style = wx.SP_NOBORDER | wx.SP_LIVE_UPDATE)

        b = self.Bind
        b(wx.EVT_LEFT_DCLICK,  lambda e: None)

        b(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        b(wx.EVT_PAINT,        self.__paint)


        b(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.__changed)

        b(wx.EVT_ENTER_WINDOW, self.__enter)
        b(wx.EVT_LEAVE_WINDOW, self.__leave)
        #b(wx.EVT_MOTION,       self.__motion)
        b(wx.EVT_LEFT_DOWN,    self.__ldown)

    def __ldown(self, e):
        e.Skip()
        self.Refresh()

    def __enter(self, e):
        e.Skip()
        #if not self.HasCapture(): self.CaptureMouse()
        self.Refresh()

    def __leave(self, e = None):
        if e: e.Skip()
        #while self.HasCapture(): self.ReleaseMouse()
        self.Refresh()

    def __motion(self, e):
        e.Skip()
        if self.HasCapture() and not self.SplitRect.Inside(e.Position):
            self.__leave()

    def __changed(self, e):
        wx.CallAfter(self.Refresh)

    def SplitHorizontally(self, w1, w2):
        self.SetSkinKey('HorizontalSizerBar',True)

        wx.SplitterWindow.SplitHorizontally(self, w1, w2)

    def SplitVertically(self, w1, w2):
        self.SetSkinKey('HorizontalSizerBar',True)

        wx.SplitterWindow.SplitVertically(self, w1, w2)

    def UpdateSkin(self):
        key = self.skinkey
        s = lambda k, default = sentinel: skin.get('%s.%s' % (key, k), default)

        self.SetSashSize(try_this(lambda: int(s('Thickness')), 4))

        self.icon      = s('Icon',      None)
        self.bg        = s('Backgrounds.Normal')
        self.bghover   = s('Backgrounds.Hover',  lambda: self.normalbg)
        self.bgactive  = s('Backgrounds.Active', lambda: self.hoverbg)

    def __paint(self, e):
        dc2 = wx.PaintDC(self)
        r  = self.SplitRect

        if r is None: return e.Skip()

        bg = 'bg'
        if wx.FindWindowAtPointer() is self:
            bg = 'bgactive' if wx.LeftDown() else 'bghover'

        wx.CallAfter(lambda: getattr(self, bg).Draw(wx.ClientDC(self), self.SplitRect))

    @property
    def SplitRect(self):
        w1, w2 = self.Window1, self.Window2
        if w1 is None or w2 is None:
            return None

        r1, r2 = w1.Rect, w2.Rect

        if self.SplitMode == wx.SPLIT_VERTICAL:
            return wx.Rect(r1.Right, 0, r2.X, self.Size.height)
        else:
            return wx.Rect(0, r1.Bottom, self.Size.width, r2.Y)


if __name__ == '__main__':
    from tests.testapp import testapp
    a = testapp('../../../')
    f = wx.Frame(None)

    split = wx.SplitterWindow(f)#UberSplitter(f)
    split.SetBackgroundColour(wx.RED)

    p1 = wx.Panel(split)
    p1.BackgroundColour = wx.WHITE

    p2 = wx.Panel(split)
    p2.BackgroundColour = wx.WHITE

    split.SplitHorizontally(p1, p2)

    #split.Unsplit()
    f.Show()
    a.MainLoop()