import wx
from wx import HORIZONTAL, VERTICAL, Point, Rect

lineSize = Point(10, 10)

class ScrollWindow(wx.Window):
    def __init__(self, parent, id = -1,
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = wx.HSCROLL | wx.VSCROLL | wx.FULL_REPAINT_ON_RESIZE,
                 name = 'ScrollWindow'):

        wx.Window.__init__(self, parent, id, pos, size, style, name)

        evts = ('top bottom lineup linedown pageup pagedown '
                'thumbtrack thumbrelease').split()

        for e in evts:
            self.Bind(getattr(wx, 'EVT_SCROLLWIN_' + e.upper()),
                      lambda evt, e=e: self._scroll(evt, e))

        self.Bind(wx.EVT_SIZE, self._size)

    def SetVirtualSize(self, size):
        wx.Window.SetVirtualSize(self, size)
        print size
        self.AdjustScrollbars()
        self.Refresh()

    def _scroll(self, e, name):
        e.Skip()

        clientRect = self.ClientRect
        virtual    = self.VirtualSize

        scrollType  = e.EventType
        orientation = e.Orientation
        o_idx       = 0 if orientation == HORIZONTAL else 1

        x, y = self.GetScrollPos(HORIZONTAL), self.GetScrollPos(VERTICAL)
        newPos = Point(x, y)
        setScrollbars = True

        # THUMBTRACK: dragging the scroll thumb
        if scrollType == wx.wxEVT_SCROLLWIN_THUMBTRACK:
            newPos[o_idx] = e.Position
            #setScrollbars = False

        # THUMBRELEASE: mouse up on the thumb
        elif scrollType == wx.wxEVT_SCROLLWIN_THUMBRELEASE:
            newPos[o_idx] = e.Position

        # LINEDOWN: clicking the down arrow
        elif scrollType == wx.wxEVT_SCROLLWIN_LINEDOWN:
            newPos[o_idx] = newPos[o_idx] + lineSize[o_idx]

        # LINEUP: clicking the up arrow
        elif scrollType == wx.wxEVT_SCROLLWIN_LINEUP:
            newPos[o_idx] = newPos[o_idx] - lineSize[o_idx]

        # PAGEDOWN: clicking below the scroll thumb
        elif scrollType == wx.wxEVT_SCROLLWIN_PAGEDOWN:
            newPos[o_idx] = newPos[o_idx] + clientRect[2 + o_idx]

        # PAGEUP: clicking above the scroll thumb
        elif scrollType == wx.wxEVT_SCROLLWIN_PAGEUP:
            newPos[o_idx] = newPos[o_idx] - clientRect[2 + o_idx]

        # keep scroll position within bounds
        newPos[0] = max(min(newPos[0], virtual.width  - clientRect.width), 0)
        newPos[1] = max(min(newPos[1], virtual.height - clientRect.height), 0)

        self.ScrollWindow(-(newPos.x - x), -(newPos.y - y))

        if setScrollbars:
            self.AdjustScrollbars(*newPos)

    def _size(self, e):
        self.AdjustScrollbars()

    def AdjustScrollbars(self, x = -1, y = -1):
        r = self.Rect
        virtual = self.VirtualSize

        if x == -1: x = self.GetScrollPos(HORIZONTAL)
        if y == -1: y = self.GetScrollPos(VERTICAL)

        self.SetScrollbar(HORIZONTAL, x, r.Width,  virtual.width)
        self.SetScrollbar(VERTICAL,   y, r.Height, virtual.height)

    def PrepareDC(self, dc):
        pt   = dc.GetDeviceOrigin()
        x, y = self.GetScrollPos(HORIZONTAL), self.GetScrollPos(VERTICAL)
        dc.SetDeviceOrigin(pt.x - x, pt.y - y)


if __name__ == '__main__':

    def bindPaint(w, paint = None):
        w.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        if paint is not None: w.Bind(wx.EVT_PAINT, paint)


    a = wx.PySimpleApp()
    f = wx.Frame(None, title = 'scroll area'); bindPaint(f)
    f.Bind(wx.EVT_CLOSE, lambda e: a.ExitMainLoop())

    f2 = wx.Frame(None, pos = f.Position + tuple(f.Size), size = f.ClientSize, title = 'virtual area',
                  style = wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)
    f2.Bind(wx.EVT_SIZE, lambda e: s.SetVirtualSize(f2.Size))


    s = ScrollWindow(f)

    def paint(ctrl, e):
        dc = wx.AutoBufferedPaintDC(ctrl)

        try: ctrl.PrepareDC(dc)
        except AttributeError: pass

        dc.Brush = wx.WHITE_BRUSH
        dc.Clear()
        p = wx.BLACK_DASHED_PEN
        p.SetWidth(10)
        dc.Pen = p

        gc = wx.GraphicsContext.Create(dc)
        r = Rect(0, 0, *f2.Size)
        b = gc.CreateLinearGradientBrush(r.x, r.y, r.width, r.height,
                                         wx.WHITE, wx.BLACK)
        gc.SetBrush(b)
        gc.DrawRectangle(*r)


    bindPaint(s, lambda e: paint(s, e))
    bindPaint(f2, lambda e: paint(f2, e))

    f.Show()
    f2.Show()
    a.MainLoop()