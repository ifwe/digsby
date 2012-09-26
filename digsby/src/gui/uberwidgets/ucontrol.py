from gui.skin.skinobjects import Margins
from gui.textutil import default_font
from gui.skin import get as skinget

import wx
from gui.uberwidgets.keycatcher import KeyCatcher


class UControl(wx.PyControl):
    def __init__(self, parent, skinkey, id = -1, label = '',
                 pos = wx.DefaultPosition,
                 size = wx.DefaultSize,
                 style = wx.NO_BORDER):

        self.Padding = wx.Size()

        wx.PyControl.__init__(self, parent, id = id, style = style)

        self.skinkey = skinkey
        self.margins = Margins((0, 0, 0, 0))
        self._native    = False


        self.Font = default_font()

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_PAINT, self.__paint)

        self.SetLabel(label)
        self.SetInitialSize(size)
        self.InheritAttributes()

    @property
    def KeyCatcher(self):
        try:
            return self.Top._keycatcher
        except AttributeError:
            k = self.Top._keycatcher = KeyCatcher(self.Top)
            return k

    def UpdateSkin(self):
        self.skin = skinget(self.skinkey)

        self.Padding = wx.Size(*skinget(self.skinkey + '.Padding', (0, 0)))
        self.SetMargins(skinget(self.skinkey + '.Margins', lambda: Margins((0, 0, 0, 0))))
        #self.Font = skinget(self.skin)


    def BindHover(self, callback = None):
        self.Hover = False
        self.hover_callback = callback
        self.Bind(wx.EVT_ENTER_WINDOW, self.__enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.__leave)

    def BindFocus(self, callback = None):
        self.Focus = False
        self.focus_callback = callback
        self.Bind(wx.EVT_SET_FOCUS, self.__setfocus)
        self.Bind(wx.EVT_KILL_FOCUS, self.__killfocus)

    def __setfocus(self, e):
        e.Skip()
        self.Focus = True
        if self.focus_callback is not None: self.focus_callback(True)

    def __killfocus(self, e):
        e.Skip()
        self.Focus = False
        if self.focus_callback is not None: self.focus_callback(False)

    def __enter(self, e):
        e.Skip()
        self.Hover = True
        if self.hover_callback is not None:
            self.hover_callback(True)

    def __leave(self, e):
        e.Skip()
        self.Hover = False
        if self.hover_callback is not None:
            self.hover_callback(False)

    def DrawBackground(self, dc, rect):
        self.BackgroundRegion.Draw(dc, rect)

    def GetMargins(self):
        return self.margins

    def SetMargins(self, margins):
        self.margins = margins
        self.InvalidateBestSize()

    Margins = property(GetMargins, SetMargins)

    def __paint(self, e):
        if self._native: return wx.PaintDC(self)

        dc   = wx.AutoBufferedPaintDC(self)
        rect = self.ClientRect

        if rect.width and rect.height:
            self.DrawBackground(dc, rect)

            # offset by margins before passing rect to Draw
            m = self.margins
            rect.Offset(m[:2])
            rect.SetSize((rect.Width   - m.left - m.right,
                         rect.Height - m.top - m.bottom))

            self.Draw(dc, rect)

    def DrawFocusRect(self, dc, rect):
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.Pen(wx.BLACK, style=wx.DOT))
        dc.DrawRectangleRect(rect)


    def DoGetBestSize(self):
        m, s = self.margins, self.GetContentSize()
        s.IncBy(m.left, m.top)
        s.IncBy(m.right, m.bottom)
        self.CacheBestSize(s)
        return s

    def ShouldInheritColours(self):
        return False
