import wx
import gui.native.helpers

from gui.native.win.dockconstants import *
from gui.native.docking import APPBARDATA
from gui.native.win.winhelpers import FullscreenApp

FULLSCREEN_CB_ID = WM_USER + 203

from ctypes import windll, byref
SHAppBarMessage = windll.shell32.SHAppBarMessage

def getabd(win, cb_id):
    abd  = APPBARDATA()
    abd.hWnd = win.Handle
    abd.uCallbackMessage = FULLSCREEN_CB_ID
    return abd

def AppBarCallback(hWnd, msg, wParam, lParam):
    cb_id = msg
    print locals()
    if cb_id == FULLSCREEN_CB_ID and wParam == ABN_FULLSCREENAPP:
        print 'FullscreenApp: %r' % FullscreenApp()
        print 'fullscreen is', bool(lParam)
#        print wParam, lParam

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None)
    f.Position = (1800, 400)
    f.Show()

    SHAppBarMessage(ABM_NEW, byref(getabd(f, FULLSCREEN_CB_ID)))
    f.BindWin32(FULLSCREEN_CB_ID, AppBarCallback)

#    print locals()
    a.MainLoop()

if __name__ == '__main__':
    main()
