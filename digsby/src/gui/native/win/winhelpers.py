from __future__ import with_statement
import ctypes, sys, os
from ctypes.wintypes import RECT
from ctypes import byref, c_int, c_long, WinError
from logging import getLogger; log = getLogger('winhelpers')
import traceback

user32         = ctypes.windll.user32
kernel32       = ctypes.windll.kernel32

SetWindowLong  = user32.SetWindowLongW
CallWindowProc = user32.CallWindowProcW
DefWindowProc  = user32.DefWindowProcW
WndProcType    = ctypes.PYFUNCTYPE(c_int, c_long, c_int, c_int, c_int)
GWL_WNDPROC    = -4

# some events.
WM_SIZING      = 0x214
WM_MOVING      = 0x216
WM_ENTERSIZEMOVE = 0x231
WM_EXITSIZEMOVE = 0x232
WM_NCHITTEST   = 0x084
WM_WINDOWPOSCHANGING = 0x046

GW_HWNDNEXT = 2

import wx

import win32events


wx.Window.ShowNoFocus = lambda win: win.Show(show = True, activate = False)

if getattr(wx, 'WXPY', False):
    import new
    meth = new.instancemethod
    wx._Window.BindWin32   = meth(win32events.bindwin32,   None, wx._Window)
    wx._Window.UnbindWin32 = meth(win32events.unbindwin32, None, wx._Window)
else:
    wx.Window.BindWin32 = win32events.bindwin32
    wx.Window.UnbindWin32 = win32events.unbindwin32


try:
    AttachThreadInput = user32.AttachThreadInput
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    GetCurrentThreadId = kernel32.GetCurrentThreadId
    GetForegroundWindow = user32.GetForegroundWindow
    GetDesktopWindow    = user32.GetDesktopWindow
    GetShellWindow      = user32.GetShellWindow
    SetForegroundWindow = user32.SetForegroundWindow
except:
    print >> sys.stderr, 'No ReallyRaise'
    wx.WindowClass.ReallyRaise = lambda win: win.Raise()
else:
    def ReallyRaise(win):
        '''
        Raises a window even when the active window doesn't belong to the
        current process.
        '''

        AttachThreadInput(GetWindowThreadProcessId(GetForegroundWindow(), 0), GetCurrentThreadId(), True)
        SetForegroundWindow(win.Handle)
        AttachThreadInput(GetWindowThreadProcessId(GetForegroundWindow(), 0), GetCurrentThreadId(), False)

    getattr(wx, '_Window', wx.Window).ReallyRaise = ReallyRaise

    def IsForegroundWindow(win):
        return win.GetHandle() == GetForegroundWindow()

    getattr(wx, '_Window', wx.Window).IsForegroundWindow = IsForegroundWindow

GetLastInputInfo = user32.GetLastInputInfo
GetTickCount     = kernel32.GetTickCount
GetLastError     = kernel32.GetLastError


try:
    from cgui import GetUserIdleTime
except ImportError:
    print >> sys.stderr, 'WARNING: using slow GetUserIdleTime'

    class LastInputInfo(ctypes.Structure):
        _fields_ = [('cbSize', ctypes.wintypes.UINT),
                    ('dwTime', ctypes.wintypes.DWORD)]


    # a global LastInputInfo object used by the GetUserIdleTime
    # function below
    input_info = LastInputInfo()
    input_info.cbSize = ctypes.sizeof(input_info)
    input_info_ref = ctypes.byref(input_info)

    def GetUserIdleTime():
        '''Returns the time since last user input, in milliseconds.'''

        if GetLastInputInfo(input_info_ref):
            return GetTickCount() - input_info.dwTime
        else:
            raise WinError()

GetTopWindow  = user32.GetTopWindow
GetWindow = user32.GetWindow
GetWindowRect = user32.GetWindowRect
IsWindowVisible = user32.IsWindowVisible
GetWindowLong = user32.GetWindowLongA
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x8

def win32ontop(hwnd):
    return bool(GetWindowLong(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST)



#
# the folowing logic checked for if the Taskbar was autohidden
# and didn't flash if so...
# but we decided that it should be configurable
#
#_TLW_RequestUserAttention = wx.TopLevelWindow.RequestUserAttention
#
#def RequestUserAttention(win):
#    # don't flash the taskbar entry red if the taskbar is set to autohide.
#    # flashing causes the taskbar to come back.
#    try:
#        from gui.docking.dock import taskbar_info
#        autohide = taskbar_info()['autohide']
#    except Exception:
#        print_exc()
#        autohide = False
#
#    if not autohide:
#        return _TLW_RequestUserAttention(win)
#
#wx.TopLevelWindow.RequestUserAttention = RequestUserAttention
from wx import FRAME_NO_TASKBAR

from gui.native.win.winconstants import SWP_NOMOVE, SWP_NOSIZE, SWP_NOZORDER, SWP_FRAMECHANGED, WS_EX_APPWINDOW, GWL_EXSTYLE
window_pos_flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED

from ctypes import windll; user32 = windll.user32

GA_ROOT = 2

def ctypes_import(src, **k):
    G = globals()
    for name, funcs in k.iteritems():
        dll = getattr(src, name)
        G.update((func, getattr(dll, func)) for func in funcs)


SetWindowLongA = user32.SetWindowLongA
GetWindowLongA = user32.GetWindowLongA
SetWindowPos   = user32.SetWindowPos
GetParent      = user32.GetParent
SetParent      = user32.SetParent
FindWindowA    = user32.FindWindowA
ShowWindow     = user32.ShowWindow
GetAncestor    = user32.GetAncestor

SetLastError   = kernel32.SetLastError
GetLastError   = kernel32.GetLastError

def SetOnTaskbar(f, val):
    hwnd = f.Handle

    needs_show  = f.IsShown()
    needs_focus = getattr(wx.Window.FindFocus(), 'Top', None) is f

    with f.Frozen():
        if needs_show: f.Hide()

        SetLastError(0)

        if val:
            #print '\nsetting TASKBAR ICON'
            f.WindowStyle = f.WindowStyle & ~FRAME_NO_TASKBAR
            res = SetWindowLongA(hwnd, GWL_EXSTYLE, (GetWindowLongA(hwnd, GWL_EXSTYLE) | WS_EX_APPWINDOW))
        else:
            #print '\nsetting NO TASKBAR'
            f.WindowStyle = f.WindowStyle | FRAME_NO_TASKBAR
            res = SetWindowLongA(hwnd, GWL_EXSTYLE, (GetWindowLongA(hwnd, GWL_EXSTYLE) & ~WS_EX_APPWINDOW))

        if needs_show:
            if not needs_focus:
                # try showing without activating
                try: return f.Show(True, False)
                except Exception: pass

            f.Show(True)

def GetOnTaskbar(f):
    return not FRAME_NO_TASKBAR & f.WindowStyle

wx.TopLevelWindow.OnTaskbar = property(GetOnTaskbar, SetOnTaskbar)

import cgui

wx.TopLevelWindow.Visible = property(cgui.WindowVisible)

FullscreenApp = cgui.FullscreenApp

def FullscreenAppLog():
    try:
        from gui.native.win import winfullscreen
    except ImportError:
        traceback.print_exc_once()
    else:
        if winfullscreen.enabled:
            try:
                return log.debug('fullscreen (notification state) is %s ', winfullscreen.last_state)
            except Exception:
                traceback.print_exc()
                winfullscreen.enabled = False
    log.info('fullscreen was computed')

def createEmail(mailto):
    return os.startfile(mailto)

def GetProcessDefaultLayout():
    from ctypes import windll, byref
    from ctypes.wintypes import DWORD

    layout = DWORD()
    windll.user32.GetProcessDefaultLayout(byref(layout))
    return layout.value

WS_EX_LAYOUTRTL = 0x400000

def mirror(win):
    """Flips a window's RTL setting."""

    hwnd = win.Handle
    new_style = GetWindowLong(hwnd, GWL_EXSTYLE) ^ WS_EX_LAYOUTRTL
    return SetWindowLong(hwnd, GWL_EXSTYLE, new_style)
