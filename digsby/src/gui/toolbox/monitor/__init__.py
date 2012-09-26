import warnings
import wx

if 'wxMSW' in wx.PlatformInfo:
    from monitorwin import Monitor as MonitorWin
else:
    class MonitorDisplay(wx.Display):
        def __init__(self, displaynum):
            wx.Display.__init__(self, displaynum)

        @staticmethod
        def GetFromWindow(window):
            displaynum = wx.Display.GetFromWindow(window)
            if displaynum != wx.NOT_FOUND:
                return wx.Display(displaynum)

            return None

        @staticmethod
        def GetFromPoint(point, find_near = False):
            displaynum = wx.Display.GetFromPoint(point)
            if displaynum != wx.NOT_FOUND:
                return wx.Display(displaynum)
            if find_near:
                warnings.warn('Monitor.GetFromPoint with find_near = True is not implemented (and is returning display 0)')
                return wx.Display(0)
            return None

        @staticmethod
        def GetFromRect(rect):
            return Monitor.GetFromPoint(rect.GetPosition())

        @staticmethod
        def All():
            monitors = []
            for displaynum in range(0, wx.Display.GetCount()):
                monitors.append(wx.Display(displaynum))

            return monitors

Monitor = MonitorWin if 'wxMSW' in wx.PlatformInfo else MonitorDisplay
