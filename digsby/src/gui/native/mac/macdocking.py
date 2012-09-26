import sys

from util.primitives.funcs import Delegate
from gui.native import notImplemented
from gui.toolbox import Monitor
from logging import getLogger; log = getLogger('dock')

import wx
from wx.lib.pubsub import Publisher

AUTOHIDE_TIMER_MS = 300
ANIMATE_DELTA = 6

DOCK_NONE = 0
DOCK_RIGHT = 1
DOCK_LEFT = 2

DOCK_MARGIN = 30
DRAG_THRESHOLD = 50

sign = lambda v: (1 if v > 0 else (-1 if v < 0 else 0))

class Docker(object):
    def __init__(self, win, autohide = False, enabled = True):
        self.Animate = True
        self.autohidden = False
        self.AutoHide = False
        self.docked = False
        self.docking = False
        self.LinkedWindows = []
        self.manualMove = False
        self.motiontrigger = False
        self.pixelsdragged = 0
        self.ShouldShowInTaskbar = lambda: True
        self.timer = wx.PyTimer(self.OnTimer)
        self.spookyGhostWindow = None

        self.win = win
        self.win.Bind(wx.EVT_ACTIVATE, self.OnActivateWin)
        self.win.Bind(wx.EVT_MOVE, self.OnMoving)
        
        self.lastrect = None
        
        self.SetAutoHide(autohide)
        
        self.OnDock = Delegate()
        self.OnHide = Delegate()
        
        publisher = Publisher()
        publisher.subscribe(self.OnActivateApp, 'app.activestate.changed')

    def OnActivateApp(self, message):
        if not self.AutoHide:
            return

        is_active = message.data

        if is_active:
            self.win.Show()

    def OnActivateWin(self, event):
        if not event.Active and self.AutoHide and self.docked:
            self.GoAway()
            
    def OnMouseEnterWindow(self, event):
        self.spookyGhostWindow.Destroy()
        self.bringBack()

    def bringBack(self):       
        if self.autohidden:
            self.ComeBack()

    def SetAutoHide(self, val):
        self.AutoHide = val

    def OnMoving(self, e):
        '''
        Bound to wx.EVT_MOVE. Detects when it is time to dock and undock.
        '''

        pos, margin = self.win.Rect, DOCK_MARGIN
        rect = monitor_rect()
        
        if not self.manualMove:
            e.Skip(True)
        else:
            return
        
        if not self.docked and not self.docking:
            if pos.Right > rect.Right - margin: # and pos.x < rect.Right:
                if not self.AutoHide or not onscreen(rect.Right+1, rect.Y):
                    self.Dock(DOCK_RIGHT)
            elif pos.x < rect.X + margin and pos.Right > rect.X:
                if not self.AutoHide or not onscreen(rect.X - 1, rect.Y):
                    self.Dock(DOCK_LEFT)
        elif self.docked:
            if self.side == DOCK_LEFT and pos.Left > rect.Left + margin:
                self.Undock()
            elif self.side == DOCK_RIGHT and pos.Right < rect.Right - margin:
                self.Undock()

    def SetEnabled(self, *a, **k):
        notImplemented()
        pass

    def SetRectSimple(self, rect):
        notImplemented()
        pass

    def OnTimer(self, e=None):
        'Called by self.timer for reliable mouse off detection.'
        if not (self.Enabled and self.AutoHide and self.docked):
            return

        w, p = self.win, wx.GetMousePosition()
        if w and not self.motiontrigger and not w.IsActive():
            if not any(r.Contains(p) for r in (w.ScreenRect for w in [w] + self.LinkedWindows)):
                self.GoAway()

    def GoAway(self):
        'Causes the window to autohide.'
        if not self.AutoHide:
            return

        log.debug('GoAway')
        w = self.win
        r = monitor_rect(w)
        margin = 3
        screen_y = self.win.Position.y

        # move it a little ways off screen so that shadows, etc. don't show at the very edge.
        if self.side == DOCK_LEFT:
            x, y = (-w.Rect.width - 10, screen_y)
        elif self.side == DOCK_RIGHT:
            x, y = (r.Right + 10, screen_y)
        else:
            assert False

        self.motiontrigger = True
        self.autohidden = True

        self.timer.Stop()
        self.OnHide()
        self.AnimateWindowTo(wx.Rect(x, y, *w.Size))
        ghost_x = x - 30
        if self.side == DOCK_LEFT:
            ghost_x = 1
        self.spookyGhostWindow = wx.Frame(None, -1, "Spooky Ghost Window", (ghost_x, y), (40, w.Size.height), style=0)
        panel = wx.Panel(self.spookyGhostWindow, -1)
        panel.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnterWindow)
        self.spookyGhostWindow.SetTransparent(0)
        self.spookyGhostWindow.Show()

    def ComeBack(self):
        rect = self.win.Rect
        mon_rect = monitor_rect()
        
        if self.side == DOCK_RIGHT:
            rect.x = mon_rect.Right - rect.width
        else:
            rect.x += mon_rect.Left + rect.width
            
        self.AnimateWindowTo(rect)
        self.autohidden = False

    def AnimateWindowTo(self, r):
        'Slides the window to position x, y.'

        x, y = r[:2]

        w = self.win
        rect = monitor_rect()
        if w.Position != (x, y):
            self.manualMove = True
            if self.Animate:
                end = w.Position.x + x
                steps = (x - w.Position.x) / ANIMATE_DELTA 
                s = 1
                if x < w.Position.x:
                    end = w.Position.x - x
                    steps = (w.Position.x - x) / ANIMATE_DELTA
                    s = -1

                delta = s * ANIMATE_DELTA
                for step in xrange(abs(steps)):
                    w.Move((w.Position.x + delta, y))

            else:
                w.SetRect(r)
            self.manualMove = False

    def UpdateTaskbar(self):
        pass

    def GetDockRect(self, side):
        screen_rect = monitor_rect(self.win)
        rect = self.win.Rect
        if side == DOCK_RIGHT:
            rect.x = screen_rect.width - rect.width
        else:
            rect.x = 0
        
        print >> sys.stderr, "old = %r, new = %r" % (self.win.Rect, rect)
        return rect
        
    def Dock(self, side = None, setStyle = True):
        print >> sys.stderr, "Docking window..." 
        log.debug("In Dock...")
        self.docking = True
        self.side = side
        
        rect = self.GetDockRect(side)
        self.AnimateWindowTo(rect)
        if self.AutoHide:
            self.timer.Start(AUTOHIDE_TIMER_MS)

        self.OnDock(True)
        self.docking = False
        self.docked = True
        return True

    def Undock(self, setFrameStyle = True):
        self.side = DOCK_NONE
        self.docked = self.docking = False
        self.OnDock(False)

    @property
    def Enabled(self):
        #notImplemented()
        return True

    def SetVelocity(self, vel):
        notImplemented()
        return False

    velocity = property(lambda self: notImplemented(), SetVelocity)

def monitor_rect(win = None):
    'returns a wxRect for the client area of the monitor the mouse pointer is over'

    return (Monitor.GetFromPoint(wx.GetMousePosition()) if win is None else Monitor.GetFromWindow(win)).ClientArea

def onscreen(x, y):
    'Returns True if the specified (x, y) point is on any screen.'

    return Monitor.GetFromPoint((x, y), find_near = False) is not None
