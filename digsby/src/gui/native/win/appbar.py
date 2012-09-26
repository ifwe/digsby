from gui.native.win.winutil import WinStruct, win_id
from gui.native.win.winconstants import ABM_NEW
from ctypes.wintypes import UINT, HWND, DWORD, c_uint, RECT, HANDLE, LPARAM
from ctypes import windll
import winhelpers

SHAppBarMessage = windll.shell32.SHAppBarMessage

def notify_fullscreen(win, on_fullscreen, off_fullscreen):
    '''
    Registers for fullscreen notification. "on_fullscreen" is called when an
    application goes into fullscreen mode, and "off_fullscreen" is called when
    it comes back from fullscreen mode.
    '''

    win.BindWin32(EVT_WIN32_FULLSCREEN, _fullscreen_callback)
    abd = APPBARDATA(hWnd = win.Handle, uCallbackMessage = EVT_WIN32_FULLSCREEN)
    SHAppBarMessage(ABM_NEW, abd.ptr)

def _fullscreen_callback(hWnd, msg, wParam, lParam):
    print 'in _fullscreen_callback'
    print locals()

EVT_WIN32_FULLSCREEN = win_id()

class APPBARDATA(WinStruct):
    'Used with the Win32 shell.dll SHAppBarMessage function.'

    _fields_ = [('cbSize', DWORD),
                ('hWnd', HANDLE),
                ('uCallbackMessage', c_uint),
                ('uEdge', c_uint),
                ('rc', RECT),
                ('lParam', LPARAM)]

def main():
    import wx
    a = wx.PySimpleApp()
    f = wx.Frame(None)

    notify_fullscreen(f, lambda: None, lambda: None)

    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()