import ctypes
from ctypes import byref, WinError, wstring_at
from ctypes.wintypes import POINT, RECT, DWORD, WCHAR
from gui.native.win.winextensions import wxRectFromRECT, wxRectToRECT
import wx
from wx import Rect, GetMousePosition
import cgui

# Windows user32 functions
user32 = ctypes.windll.user32
MonitorFromPoint     = user32.MonitorFromPoint
MonitorFromWindow    = user32.MonitorFromWindow
MonitorFromRect      = user32.MonitorFromRect
GetMonitorInfo       = user32.GetMonitorInfoW

# constants
MONITOR_DEFAULTTONULL    = 0
MONITOR_DEFAULTTOPRIMARY = 1
MONITOR_DEFAULTTONEAREST = 2

CCHDEVICENAME = 32

class MONITORINFOEX(ctypes.Structure):
    _fields_ = [('cbSize', DWORD),
                ('rcMonitor', RECT),
                ('rcWork', RECT),
                ('dwFlags', DWORD),
                ('szDevice', WCHAR * CCHDEVICENAME)]

MONITORINFOEX_size = ctypes.sizeof(MONITORINFOEX)

# seq -> POINT
def makePOINT(point):
    pt = POINT()
    pt.x, pt.y = point
    return pt

def Monitor_FromPoint(point, find_near = False):
    hmonitor = MonitorFromPoint(makePOINT(point), MONITOR_DEFAULTTONEAREST if find_near else MONITOR_DEFAULTTONULL)
    if hmonitor:
        return Monitor(hmonitor)

def Monitor_FromWindow(window):
    return Monitor_FromHandle(window.Handle)

def Monitor_FromHandle(handle):
    return Monitor(MonitorFromWindow(handle, MONITOR_DEFAULTTONEAREST))

def Monitor_FromRect(rect, find_near = True):
    hmonitor = MonitorFromRect(byref(wxRectToRECT(rect)), MONITOR_DEFAULTTONEAREST if find_near else MONITOR_DEFAULTTONULL)
    if hmonitor:
        return Monitor(hmonitor)

def Monitor_FromDeviceId(deviceId, orPrimary = True):
    mons = Monitor.All()
    for mon in mons:
        if mon.DeviceId == deviceId:
            return mon

    if orPrimary:
        for mon in mons:
            if mon.Primary:
                return mon

    return None

class Monitor(object):
    def __init__(self, hmonitor):
        self.hmonitor = hmonitor

    def GetClientArea(self):
        try: return self._clientarea
        except AttributeError:
            self._getinfo()
            return self._clientarea

    ClientArea = property(GetClientArea)

    def GetGeometry(self):
        try: return self._geometry
        except AttributeError:
            self._getinfo()
            return self._geometry

    Geometry = property(GetGeometry)

    def GetDeviceId(self):
        try: return self._deviceid
        except AttributeError:
            self._getinfo()
            return self._deviceid

    DeviceId = property(GetDeviceId)

    GetFromPoint    = staticmethod(Monitor_FromPoint)
    GetFromPointer  = staticmethod(lambda: Monitor_FromPoint(GetMousePosition(), find_near = True))
    GetFromWindow   = staticmethod(Monitor_FromWindow)
    GetFromRect     = staticmethod(Monitor_FromRect)
    GetFromHandle   = staticmethod(Monitor_FromHandle)
    GetFromDeviceId = staticmethod(Monitor_FromDeviceId)

    @staticmethod
    def GetCount():
        return len(get_hmonitors())

    @staticmethod
    def All():
        return [Monitor(hmonitor) for hmonitor in get_hmonitors()]

    if hasattr(cgui, 'GetMonitorInfo'):
        def _getinfo(self):
            work, mon, self._deviceid = cgui.GetMonitorInfo(self.hmonitor)

            self._clientarea  = RECTtuple_to_rect(work)
            self._geometry    = RECTtuple_to_rect(mon)
    else:
        def _getinfo(self):
            info = MONITORINFOEX()
            info.cbSize = MONITORINFOEX_size
            if not GetMonitorInfo(self.hmonitor, byref(info)):
                raise WinError()

            self._clientarea = wxRectFromRECT(info.rcWork)
            self._geometry   = wxRectFromRECT(info.rcMonitor)
            self._deviceid   = wstring_at(info.szDevice)

    def IsPrimary(self):
        pos = self.Geometry.Position

        # Primary monitor is always at (0, 0)
        if pos.x == pos.y == 0:
            return True
        return False

    Primary = property(IsPrimary)

try:
    from cgui import GetHMONITORs as get_hmonitors #@UnusedImport
except ImportError:
    EnumDisplayMonitors  = user32.EnumDisplayMonitors
    _hmonitors = []

    def MultimonEnumProc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        _hmonitors.append(hMonitor)
        return True

    def get_hmonitors():
        global _hmonitors
        del _hmonitors[:]
        EnumDisplayMonitors(None, None, MultimonEnumProc, None)
        return _hmonitors

def RECTtuple_to_rect(r):
    return Rect(r[0], r[1], r[2]-r[0], r[3]-r[1])

wx.Window.Monitor = Monitor_FromWindow

def main():
    print [m.ClientArea for m in Monitor.All()]

if __name__ == '__main__':
    main()
