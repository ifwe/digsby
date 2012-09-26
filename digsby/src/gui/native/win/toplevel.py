import wx, sys, ctypes
from util import ffi
from ctypes import sizeof, byref
from ctypes.wintypes import UINT, HWND, DWORD
from gui.native.win.winutil import WinStruct

ffi.cimport(user32 = ['FlashWindowEx', 'FlashWindow'])

FLASHW_STOP      = 0
FLASHW_CAPTION   = 0x00000001
FLASHW_TRAY      = 0x00000002
FLASHW_ALL       = FLASHW_CAPTION | FLASHW_TRAY
FLASHW_TIMER     = 0x00000004 # Flash continuously, until the FLASHW_STOP flag is set.
FLASHW_TIMERNOFG = 0x0000000C # Flash continuously until the window comes to the foreground.


class FLASHWINFO(WinStruct):
    _fields_ = [('cbSize',    UINT),
                ('hwnd',      HWND),
                ('dwFlags',   DWORD),
                ('uCount',    UINT),
                ('dwTimeout', DWORD)]

# failed import?
if not FlashWindowEx: #@UndefinedVariable
    wx.TopLevelWindow.StopFlashing = lambda win: None
else:
    FLASHWINFOsize = sum(sizeof(zz) for zz in (UINT, HWND, DWORD, UINT, DWORD))
    assert FLASHWINFOsize == len(FLASHWINFO())

    tlw = wx.TopLevelWindow
    def StopFlashing(win):
        f = FLASHWINFO(cbSize  = FLASHWINFOsize,
                       hwnd    = win.Handle,
                       dwFlags = FLASHW_STOP)

        FlashWindowEx(f.ptr) #@UndefinedVariable
        def doint():
            if not wx.IsDestroyed(win): tlw.SetTitle(win, tlw.GetTitle(win))
        wx.CallLater(1000, doint)
        wx.CallLater(3000, doint)
        doint()

    wx.TopLevelWindow.StopFlashing = StopFlashing

def Flash(win, titlebar = True, taskbar = True, timeout = 0, count = 1, until = 'foreground'):
    '''
    Requests the user's attention.

    until can be
        'foreground'   stop flashing when the window comes to the foreground
        'stop'         don't stop flashing until FlashWindowEx is called with FLASHW_STOP
    '''

    flags  = 0#FLASHW_TIMER if until == 'stop' else FLASHW_TIMERNOFG
    flags |= FLASHW_CAPTION if titlebar else 0
    flags |= FLASHW_TRAY if taskbar else 0

    flashinfo = FLASHWINFO(hwnd    = win.Handle,
                           dwFlags = flags,
                           uCount  = count,
                           dwTimeout = timeout)


    flashinfo.cbSize = sizeof(FLASHWINFO)
    #print flashinfo

    #print
    FlashWindowEx(flashinfo.ptr) #@UndefinedVariable

def FlashOnce(win):
    return FlashWindow(win.Handle, 1) #@UndefinedVariable

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None, title = 'test')
    f.Title = 'test %s' % f.Handle
    f.Show()

    f2 = wx.Frame(None, title = 'control')
    r = f.Rect
    f2.Rect = wx.Rect(r.Right, r.Top, r.Width, r.Height)

    def b(t, c):
        button = wx.Button(f2, -1, t)
        button.Bind(wx.EVT_BUTTON, lambda e: c())
        return button

    #flash    = b('FlashWindow', lambda: Flash2(f))
    flashex  = b('FlashWindowEx', lambda: Flash(f))
    request  = b('RequestUserAttention', f.RequestUserAttention)
    settitle = b('Set Title', lambda: (f.SetTitle(f.GetTitle() + ' Yay'), Flash(f)))
    stop     = b('Stop Flashing', lambda: StopFlashing(f))

    s = f2.Sizer = wx.BoxSizer(wx.VERTICAL)
    s.AddMany([flashex, request, settitle, stop])
    s.Layout()

    f2.Show()


    a.MainLoop()

if __name__ == '__main__':
    main()
