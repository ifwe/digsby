import wx

class ScrollWinBase(object):

    def BindScrollWin(self, obj):
        return
        obj.Bind(wx.EVT_SCROLLWIN, self._on_scrollwin)

    def _on_scrollwin(self, e):
        pass

class ScrollWinMixin(ScrollWinBase):

    def _on_scrollwin(self, e):
        scrollType = e.GetEventType()
        horiz = e.GetOrientation() == wx.HORIZONTAL
        if horiz:
            return e.Skip()

        if (scrollType == wx.EVT_SCROLLWIN_THUMBTRACK or scrollType == wx.EVT_SCROLLWIN_THUMBRELEASE):
            return e.Skip()
        elif (scrollType == wx.EVT_SCROLLWIN_LINEDOWN):
            self.ScrollLines(1)
        elif (scrollType == wx.EVT_SCROLLWIN_LINEUP):
            self.ScrollLines(-1)
        elif (scrollType == wx.EVT_SCROLLWIN_PAGEUP):
            self.ScrollPages(1)
        elif (scrollType == wx.EVT_SCROLLWIN_PAGEDOWN):
            self.ScrollPages(-1)
        else:
            return e.Skip();

class WheelBase(object):

    def get_wheel_lines(self, rotation, e):
        return int(round(rotation / float(e.GetWheelDelta()) * e.LinesPerAction))

    def rotation_for_lines(self, lines, e):
        return int(float(e.GetWheelDelta()) / e.LinesPerAction * lines)

    def BindWheel(self, obj):
        obj.Bind(wx.EVT_MOUSEWHEEL, self._on_mousewheel)

    def _on_mousewheel(self, e):
        pass

class WheelScrollMixin(WheelBase):
    def __init__(self, *a, **k):
        super(WheelScrollMixin, self).__init__(*a, **k)
        self.wheel_rotation_scroll = 0

    def _on_mousewheel(self, e):
        wheel_rotation_scroll = e.WheelRotation + self.wheel_rotation_scroll
        lines = self.get_wheel_lines(wheel_rotation_scroll, e)
        if lines:
            self._do_scroll(e, -lines)
            self.wheel_rotation_scroll = self.rotation_for_lines(-lines, e) + wheel_rotation_scroll
        else:
            self.wheel_rotation_scroll = wheel_rotation_scroll

    def _do_scroll(self, e, lines):
        self.ScrollLines(lines)

class FrozenLoopScrollMixin(object):
    def ScrollLines(self, lines):
        #HAX: webkit doesn't understand multiple lines at a time.
        abslines = int(abs(lines))
        with self.Frozen():
            for _i in xrange(abslines):
                super(FrozenLoopScrollMixin, self).ScrollLines(int(lines/abslines))

class WheelZoomMixin(WheelBase):
    def __init__(self, *a, **k):
        super(WheelZoomMixin, self).__init__(*a, **k)
        self.wheel_rotation_zoom = 0

    def _on_mousewheel(self, e):
        wheel_rotation_zoom = e.WheelRotation + self.wheel_rotation_zoom
        lines = self.get_wheel_lines(wheel_rotation_zoom, e)
        if lines > 0:
            self.IncreaseTextSize()
        elif lines < 0:
            self.DecreaseTextSize()
        else:
            self.wheel_rotation_zoom = wheel_rotation_zoom

class WheelCtrlZoomMixin(WheelZoomMixin):
    def _on_mousewheel(self, e):
        if e.CmdDown():
            WheelZoomMixin._on_mousewheel(self, e)
        else:
            super(WheelZoomMixin, self)._on_mousewheel(e)

class WheelScrollCtrlZoomMixin(WheelCtrlZoomMixin, WheelScrollMixin):
    pass

class WheelScrollFastMixin(WheelScrollMixin):
    def _do_scroll(self, e, lines):
        if self._fast_scroll_test(e):
            self.ScrollPages(lines)
        else:
            return super(WheelScrollFastMixin, self)._do_scroll(e, lines)

class WheelShiftScrollFastMixin(WheelScrollFastMixin):
    def _fast_scroll_test(self, e):
        if e.ShiftDown():
            return True
        else:
            try:
                return super(WheelShiftScrollFastMixin, self)._fast_scroll_test(e)
            except AttributeError:
                return False

class WheelCtrlScrollFastMixin(WheelScrollFastMixin):
    def _fast_scroll_test(self, e):
        if e.CmdDown():
            return True
        else:
            try:
                return super(WheelCtrlScrollFastMixin, self)._fast_scroll_test(e)
            except AttributeError:
                return False


