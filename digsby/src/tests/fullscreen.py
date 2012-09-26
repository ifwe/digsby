from gui.native.win.dockconstants import *
from gui.native.docking import APPBARDATA, RECT
from functools import wraps
from gui.toolbox import Monitor
from ctypes import sizeof
import wx
import util
import util.primitives.funcs as funcs

from logging import getLogger
log = getLogger('fullscreen')

FULLSCREEN_CB_ID = WM_USER + 203

from ctypes import windll, byref
SHAppBarMessage = windll.shell32.SHAppBarMessage

def AppBarFSCallback(func, cb_id):
    @wraps(func)
    def wrapper(hWnd, msg, wParam, lParam):
        if msg == cb_id and wParam == ABN_FULLSCREENAPP:
            func(bool(lParam))
    return wrapper

def BindFS(win, func, cb_id):
    abd  = APPBARDATA()
    abd.cbSize = sizeof(APPBARDATA)
    print sizeof(APPBARDATA)
    abd.hWnd = win.Handle
    abd.rc = RECT(win.Position.x, win.Position.y, 0, 0)
    abd.uCallbackMessage = cb_id
    SHAppBarMessage(ABM_NEW, byref(abd))

    win.BindWin32(cb_id, AppBarFSCallback(func, cb_id))

class FullscreenMonitor(object):
    def __init__(self):
        self.frames = {}
        self.values = {}
        self.check()
        self.timer = util.RepeatTimer(30, self.check)
        self.start = self.timer.start
        self.stop  = self.timer.stop

        self.on_fullscreen = funcs.Delegate()

    def __nonzero__(self):
        return sum(self.values.values())

    def check(self):
        '''
        get number of displays
        associate current windows with displays
        destroy other windows, clear state
        create new if necessary
        '''
        current = set((n, tuple(m.Geometry)) for n, m in enumerate(Monitor.All()))
        last_time = set(self.frames.keys())

        new = current - last_time
        dead = last_time - current
        check = last_time & current

        for n, geo in dead:
            f = self.frames.pop((n, geo))
            f.Destroy()
            self.values.pop((n, geo))

        for n, geo in new:
            self.frames[(n, geo)] = self.new_win(n, geo)
            self.values[(n, geo)] = False

        for n, geo in check:
            self.fix_win(n, geo)

    def set(self, (n, geo), state):
        self.values[(n, geo)] = state
        log.info('fullscreen %r, %r', (n, geo), state)
        log.info('fullscreen is %s', bool(self))
        log.info('fullscreen %r', self.values)
        # notify listeners with True for going fullscreen
        self.on_fullscreen(bool(self))

    def fix_win(self, n, geo):
        self.frames[(n, geo)].Position=geo[:2]

    def new_win(self, n, geo):
        f = wx.Frame(None, -1, pos=geo[:2], size=(300, 200), name="Fullscreen Detector #%s" % n)
        BindFS(f, (lambda state: self.set((n, geo), state)), FULLSCREEN_CB_ID+n)
        f.Show()
        return f

def main():
    a = wx.PySimpleApp()
    f = FullscreenMonitor()

    def on_fullscreen(val): print 'fullscreen!!!OMG', val
    f.on_fullscreen += on_fullscreen

    a.MainLoop()

if __name__ == '__main__':
    main()
