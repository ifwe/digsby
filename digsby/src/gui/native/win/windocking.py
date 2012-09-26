'''

Window docking and auto hiding.

>> w = wx.Frame(None)
>> docker = Docker(w)

Important properties:

>> docker.Enabled    # docking on or off
>> docker.AutoHide   # auto hiding on or off
>> docker.DockMargin # number of pixels away from edge to begin docking
>> docker.Animate    # whether to animate when autohiding

'''

from gui.native.win.dockconstants import WM_EXITSIZEMOVE, WM_WINDOWPOSCHANGING, WM_SIZING, WM_NCHITTEST, \
                                         WM_SYSCOMMAND, WM_USER, ABE_LEFT, ABE_RIGHT, ABM_REMOVE, SC_MAXIMIZE, \
                                         SC_MINIMIZE, HTBOTTOMLEFT, HTLEFT, HTTOPLEFT, HTBOTTOMRIGHT, HTRIGHT, \
                                         HTTOPRIGHT, SC_SIZE, ABM_SETPOS, WMSZ_LEFT, WMSZ_RIGHT, ABM_SETAUTOHIDEBAR, \
                                         sideStrings, ABM_NEW, SWP_NOACTIVATE, SWP_NOMOVE, SWP_NOSIZE, ABM_GETSTATE, \
                                         ABS_ALWAYSONTOP, HWND_BOTTOM, HWND_TOPMOST, ABE_TOP, ABE_BOTTOM, ABM_QUERYPOS, \
                                         ABN_STATECHANGE, ABN_FULLSCREENAPP, ABN_POSCHANGED, ABN_WINDOWARRANGE, \
                                         ABS_AUTOHIDE

import ctypes, wx
from wx import PyTimer
from ctypes import c_uint, Structure, byref, c_int, POINTER, cast
from logging import getLogger; log = getLogger('dock')
from gui.toolbox import Monitor
from util.primitives.funcs import Delegate
from util import default_timer

from gui.native.win.winextensions import wxRectToRECT

from ctypes.wintypes import DWORD, HANDLE, LPARAM, RECT
user32  = ctypes.windll.user32
SetWindowPos = user32.SetWindowPos
MoveWindow = user32.MoveWindow
shell32_SHAppBarMessage = ctypes.windll.shell32.SHAppBarMessage
CallWindowProc = ctypes.windll.user32.CallWindowProcW
DefWindowProc = ctypes.windll.user32.DefWindowProcW


def SHAppBarMessage(msg, abd):
    'Sends a message to the AppBar API for handling docking areas.'
    return shell32_SHAppBarMessage(msg, byref(abd))

ANIMATE_SECS = .1
AUTOHIDE_TIMER_MS = 130
ANIMATE_DELTA = 6

# WM_SYS_COMMAND's wParam throws this number on maximize, but it's not SC_MAXIMIZE
UNKNOWN_MAX_FLAG = 61490

sign = lambda v: (1 if v > 0 else (-1 if v < 0 else 0))


class Docker(object):
    'Causes a window to dock and optionally autohide.'

    def __init__(self, win, autohide = False, enabled = True):
        self.win = win
        self._side = None#ABE_LEFT
        self.DockMargin = 30
        self.ShouldShowInTaskbar = lambda: True  #must be set by window
        self.ShouldAlwaysStayOnTop = None
        self.RevealDurationMs = 300
        self.Animate = True
        self.autohidden = self.docking = self.docked = False
        self._enabled = enabled
        self._autohide = autohide

        self.bypassSizeEvents = False
        self.bypassMoveEvents = False
        self.reReserveTimer = None

        Bind = win.Bind
        BindWin32 = win.BindWin32

        Bind(wx.EVT_MOVING, self.OnMoving)
        Bind(wx.EVT_CLOSE, self.OnClose)
        Bind(wx.EVT_ACTIVATE, self.OnActivate)
        Bind(wx.EVT_DISPLAY_CHANGED, self.OnDisplayChanged)
        Bind(wx.EVT_SHOW, self.OnShow)


        BindWin32(WM_WINDOWPOSCHANGING, self.OnWindowPosChanging)

        BindWin32(WM_EXITSIZEMOVE, self.OnExitSizeMove)
        BindWin32(WM_SIZING, self.OnSizing)

        BindWin32(WM_NCHITTEST, self.OnNCHitTest)
        BindWin32(WM_SYSCOMMAND, self.OnSysCommand)

        self.appbar_cb_id = WM_USER + 100
        BindWin32(self.appbar_cb_id, self.AppBarCallback)

        self.firstShow = True
        self.wasDocked = False
        self.oldSize = None
        self.motiontrigger = False
        self.timer = PyTimer(self.OnTimer)

        self.OnDock = Delegate()
        self.OnHide = Delegate()
        self.LinkedWindows = []

    def __repr__(self):
        return '<Docker for %r>' % self.win

    def GetSide(self):
        if self._side == None:
            pos, margin = self.win.Rect, self.DockMargin
            screenRect = monitor_rect(self.win)

            if pos.x < screenRect.X + margin and pos.Right > screenRect.X:
                    self._side = ABE_LEFT
            if pos.Right > screenRect.Right - margin and pos.x < screenRect.Right:
                    self._side = ABE_RIGHT

        return self._side

    def SetSide(self, side):
        self._side = side

    side = property(GetSide, SetSide)


    def OnDisplayChanged(self, event):

        log.debug('OnDisplayChanged')

        if self.docked and not self.AutoHide:
            self.Undock(setFrameStyle=False)
            self.win.FitInScreen(Monitor.GetFromDeviceId(self.monId)) #@UndefinedVariable
            self.Dock(setFrameStyle=False)

            self.bypassMoveEvents = True
            self.win.SetRect(self.dockedRect)
            self.bypassMoveEvents = False

            self.docking = True
            self.docked = False

            self.OnExitSizeMove()

        elif self.docked and self.AutoHide:

            onRight = self.side == ABE_RIGHT

            mon = Monitor.GetFromDeviceId(self.monId) #@UndefinedVariable

            monRect = mon.ClientArea

            xPos = monRect.Right+1 if onRight else monRect.Left-1
            while onscreen(xPos, monRect.Y):
                mon = Monitor.GetFromPoint((xPos, monRect.Y)) #@UndefinedVariable
                monRect = mon.ClientArea
                xPos = monRect.Right+1 if onRight else monRect.Left-1

#            self.win.FitInScreen(mon)
            if onRight:
                self.dockedRect = wx.Rect(monRect.Right-self.win.Size.width + 1, monRect.Top, self.win.Size.width, monRect.Bottom - monRect.Top)
            else:
                self.dockedRect = wx.Rect(monRect.left-1,monRect.Top, self.win.Size.width, monRect.Bottom - monRect.Top)

            self.bypassMoveEvents = True
            self.win.SetRect(self.dockedRect)
            self.bypassMoveEvents = False

            self.GoAway(monRect)

        event.Skip()

    def OnShow(self,event):
        event.Skip()
        if not self.win.Shown:
            return

        onRight = self.side == ABE_RIGHT
        mon = Monitor.GetFromWindow(self.win) #@UndefinedVariable
        monRect = mon.ClientArea

        atEdge = not onscreen(monRect.Right+1 if onRight else monRect.Left-1, monRect.Y)
        shouldDock = self.wasDocked or (self.firstShow and (atEdge or not self.AutoHide))

        if self.Enabled and shouldDock and self.side is not None and not self.docked:

            self.Dock(setFrameStyle = self.firstShow)

            self.firstShow = False

            self.bypassMoveEvents = True
            self.win.SetRect(self.dockedRect)
            self.bypassMoveEvents = False

            self.docking = True
            self.docked  = False

            self.OnExitSizeMove()

        elif self.firstShow:
            self.firstShow = False

        self.wasDocked = False


    def SetEnabled(self, val):
        """
            Enable or disable docking, called by buddy list when the pref changes.
        """

        if not isinstance(val, bool):
            raise TypeError('Enabled must be a boolean')

        self._enabled = val

        #turn docking off docking
        if not val and self.docked:
            self.Undock()
            p = self.dockedRect[:2]
            self.docking = self.docked = self.autohidden = False
            wx.CallLater(50, self.SetRectSimple, wx.Rect(p[0],p[1], *wx.Size(*self.oldSize)))

            self.UpdateTaskbar()

        #turn docking on
        elif val and not self.docked and self.win.IsShownOnScreen():
            self.docking = False

            #emulate a motion event to initiate docking if the buddylist is in position
            if self.OnMoving():

                #emulate a finished moving event to finish docking procedure
                self.OnExitSizeMove()

                #if autohide preference is set, start timer to autohide the buddylist
                if self.AutoHide:
                    self.timer.Start(AUTOHIDE_TIMER_MS)
                    self.motiontrigger = False

                self.win.SetRect(self.dockedRect)

        elif self.wasDocked:
            SetToolStyle(self.win,val)
            self.bypassMoveEvents = True
            if val:
                self.win.Rect = self.dockedRect
            else:
                self.win.Rect = wx.RectPS(self.dockedRect.Position, self.oldSize)
            self.bypassMoveEvents = False

            self.UpdateTaskbar()


        if not val:
            self.oldSize = None

    Enabled = property(lambda self: self._enabled, SetEnabled, None,
                       'Set this boolean property to enable or disable docking')

    def SetAutoHide(self, val):
        """
            Called by buddylist when autohide pref change
        """

        log.debug('SetAutoHide')
        #if docking is enabled and the buddylist is currently docked,
        #undock and redock with the new settings
        if self.Enabled and self.docked:
            self.Undock(setFrameStyle = False)
            self._autohide = val
            self.Dock(setFrameStyle = False)

            # this swapping of these two bools happens a lot, possibly should be something else
            self.docking = True
            self.docked = False

            self.OnExitSizeMove()

            if not val:
                self.ComeBack()

            self.UpdateTaskbar()
        else:
            self._autohide = val


    AutoHide = property(lambda self: self._autohide, SetAutoHide, None,
                        'Set this boolean property to enable or disable autohiding.')

    def SetRectSimple(self, rect):
        'Sets the window rectangle without invoking special events.'

        self.bypassMoveEvents = True
        self.win.SetRect(rect)
        self.bypassMoveEvents = False

    def OnTimer(self, e=None):
        'Called by self.timer for reliable mouse off detection.'
        if not (self.Enabled and self.AutoHide and self.docked):
            return

        w  = self.win
        mp = wx.GetMousePosition()
        if w and not self.motiontrigger and not w.IsActive():
            if not any(r.Contains(mp) for r in (w.ScreenRect for w in [w] + self.LinkedWindows)):
                self.GoAway()

    def GoAway(self, rect = None):
        'Causes the window to autohide.'

        log.debug('GoAway')
        w = self.win
        r = rect if rect else monitor_rect(w)
        margin = 1

        if self.side == ABE_LEFT:
            x, y = (r.X - w.Rect.width + margin, r.Y)
        elif self.side == ABE_RIGHT:
            x, y = (r.Right - margin, r.Y)
        else:
            assert False

        self.motiontrigger = True
        self.autohidden = True

        self.timer.Stop()
        self.OnHide()
        self.AnimateWindowTo(wx.Rect(x, y, *w.Size))
        self.SetWinAlwaysOnTop(True)

    def ComeBack(self):
        """
            Causes the window to come back from its autohide position.

            Sets both self.autohidden and self.motiontrigger to False
        """

        log.debug('ComeBack')
        self.motiontrigger = False
        self.AnimateWindowTo(self.dockedRect)
        self.autohidden = False
        self.timer.Start(AUTOHIDE_TIMER_MS)

    def SetVelocity(self, v):
        self._velocity = v

    velocity = property(lambda self: self._velocity, SetVelocity)

    animateToTarget = None
    lasttick = None
    def AnimateWindowTo(self, r=None):
        'Slides the window to position x, y.'

        now = default_timer()
        if r is not None:
            self.animateToTarget = r
            self.lasttick = now

        targetx, y = self.animateToTarget[:2]
        win = self.win
        winx = win.Position.x

        direction = sign(targetx - win.Position.x)
        delta = int((now - self.lasttick)*self.velocity) * direction


        self.bypassMoveEvents = True
        if winx != targetx and self.Animate:
            if delta:
                newx = winx + delta

                if (targetx >= winx) != (targetx >= newx):
                    newx = targetx

                win.Move((newx, y))
                self.lasttick = now
            wx.CallLater(15, self.AnimateWindowTo)
        elif winx != targetx:
            win.SetRect(r)
        self.bypassMoveEvents = False

    def OnClose(self, e):
        'If the windows closing and docked, unregisters from the docking system.'

        log.info('OnClose: %r', e.EventObject)

        if self.Enabled and self.docked:
            if self.AutoHide:
                return self.GoAway()
            else:
                SHAppBarMessage(ABM_REMOVE, self.newAppBarData)

        e.Skip(True)

    def OnActivate(self, e):
        """
            Unhide the Window when it gets focus
        """

        if not self.Enabled or not self.AutoHide or not self.docked or not self.autohidden:
            return

        if e.GetActive():
            if not onscreen(*self.win.Position):
                self.ComeBack()
                self.win.Raise()
        else:
            self.timer.Start(AUTOHIDE_TIMER_MS)
        e.Skip()

    def OnSysCommand(self, hWnd, msg, wParam, lParam):
        '''
        Catches special WM_SYSCOMMAND messages to prevent minimizing and
        maximizing when docked.
        '''
        if self.Enabled and self.docked:
            if msg == WM_SYSCOMMAND and wParam in (UNKNOWN_MAX_FLAG, SC_MINIMIZE, SC_MAXIMIZE):
                return False

    def autohidden_mouseover(self):
        if self.Enabled and self.autohidden and self.motiontrigger and wx.FindWindowAtPointer() is self.win:

            self.ComeBack()

    def OnNCHitTest(self, hWnd, msg, wParam, lParam):
        'Win32 message event for "hit test" mouse events on a window.'

        if self.Enabled and self.motiontrigger:
            # The mouse has hit the one pixel window--bring the window back.


            ms = wx.GetMouseState()
            if ms.LeftDown():
                self.bypassSizeEvents = True
            elif self.bypassSizeEvents:
                self.bypassSizeEvents = False

            try:
                t = self.autohidden_timer
            except AttributeError:
                t = self.autohidden_timer = wx.PyTimer(self.autohidden_mouseover)

            if not t.IsRunning():
                t.StartOneShot(self.RevealDurationMs)

        elif self.Enabled and self.docked:
            # Don't allow the window's edge to be dragged if that edge is the
            # one at the edge of the screen.
            hit = DefWindowProc(hWnd, msg, wParam, lParam)
            if self.side == ABE_LEFT  and hit in (HTLEFT,  HTTOPLEFT,  HTBOTTOMLEFT) or \
               self.side == ABE_RIGHT and hit in (HTRIGHT, HTTOPRIGHT, HTBOTTOMRIGHT):
                return False

    def OnExitSizeMove(self, hWnd=0, msg=0, wParam=0, lParam=0):
        """
            When the window is _done_ moving, this method is called.

            Appears to cover the last steps of the (un)docking procedures
        """
        log.debug('SC_SIZE: %s', SC_SIZE)
        log.debug('OnExitSizeMove %s %s %s', msg, wParam, lParam)


        if not self.Enabled:
            return

        if self.docked and self.AutoHide:
            if self.bypassSizeEvents:
                ms = wx.GetMouseState()
                if not ms.LeftDown():
                    self.bypassSizeEvents = False

                return False

        #if in docking mode and not docked, dock
        if self.docking and not self.docked:
            self.docking = False
            self.docked = True
            self.AppBarQuerySetPos(set = True)

        if self.docked and not self.AutoHide:
            abd = self.GetNewAppBarData()
            abd.rc = wxRectToRECT(self.dockedRect)
            SHAppBarMessage(ABM_SETPOS, abd)

        #clear old size if not docked
        if not self.docked:
            self.oldSize = None


        self.UpdateTaskbar()

    def UpdateTaskbar(self):
        """
            Toggle Taskbar entry for the window

            If the window is on the taskbar and docked, remove it
            Else if it should show in taskbar, show it
        """

        log.debug('UpdateTaskbar')

        ontaskbar = self.win.OnTaskbar
        if ontaskbar and self.docked:
            log.debug('Hide Task')
            self.win.OnTaskbar = False
        else:
            should = self.ShouldShowInTaskbar()
            if should and not ontaskbar and not self.docked:
                log.debug('Show Task')
                self.win.OnTaskbar = True

    def OnSizing(self, hWnd, msg, wParam, lParam):
        """
            Intercepts moving events at the Win32 level

            For special case sizing rules while docked
        """

        #log.debug('OnSizing')

        # WM_SIZING callback
        if not (self.Enabled and self.docked):
            #log.debug('Not docked')
            return

        try:
            if self.__sizing: return
        except AttributeError: pass



        side = self.side
        if not self.bypassSizeEvents and ((side == ABE_LEFT  and wParam == WMSZ_RIGHT) or (side == ABE_RIGHT and wParam == WMSZ_LEFT)):
            # lParam is a pointer to a RECT
            log.debug('Docked sizing')
            r = wx.Rect.FromRECT(RECT.from_address(lParam)) #@UndefinedVariable

            # readjust the docking rectangle
            self.__sizing = True


            # this will cause the window to resize
            self.dockedRect = r

            # also save the width in our "oldSize" which is used when the window is finally undocked
            self.oldSize.width = r.width

            self.__sizing = False

        else:
            log.debug('Resize restricted')
            d = self.dockedRect

            # lParam holds the address of the RECT which will be the new
            # window size. setting it to our docked rectangle is like
            # "cancelling" the resize
            r = RECT.from_address(lParam) #@UndefinedVariable

            # set these explicitly so they go into memory at lParam.
            r.x = d.x
            r.y = d.y
            r.right = d.x + d.width
            r.bottom = d.y + d.height

            return False

    def OnWindowPosChanging(self, hWnd, msg, wParam, lParam):
        '''
            Intercepts moving events at the Win32 level so that the window's new
            position can be overridden.
        '''

        if not self.Enabled:
            return

        elif not self.bypassMoveEvents:
            mon = monitor_rect(self.win)
            margin = self.DockMargin
            pos = cast(lParam, POINTER(c_int))
            x, y, w, h = pos[2:6]

            #return if already docked or docking on that side
            if self.docked or self.docking:

                awayFromLeft  = self.side == ABE_LEFT  and   x > mon.X + margin     or x + w < mon.X
                awayFromRight = self.side == ABE_RIGHT and x+w < mon.Right - margin or     x > mon.Right
                notResized    =       y+h != self.dockedRect.Bottom+1

                if (awayFromLeft or awayFromRight) and notResized:
                    return

                for i, j in enumerate(xrange(2, 6)):
                    pos[j] = self.dockedRect[i]

            elif self.oldSize:
                pos[4] = self.oldSize.width
                pos[5] = self.oldSize.height


    def OnMoving(self, e=None):
        'Bound to wx.EVT_MOVE. Detects when it is time to dock and undock.'

        if e: e.Skip(True)
        if not self.Enabled:
            return

        #log.debug('OnMoving')
        pos, margin = self.win.Rect, self.DockMargin
        rect = monitor_rect(self.win)

        if not self.docked and not self.docking:
            if pos.Right > rect.Right - margin and pos.x < rect.Right:

                isOnScreen = isRectOnScreen(wx.Rect(rect.Right+1, rect.Top, 1, rect.Height))

                if not self.AutoHide or not isOnScreen:
                    return self.Dock(ABE_RIGHT)

            elif pos.x < rect.X + margin and pos.Right > rect.X:

                isOnScreen = isRectOnScreen(wx.Rect(rect.X-1, rect.Top, 1, rect.Height))

                if not self.AutoHide or not isOnScreen:
                    return self.Dock(ABE_LEFT)

        else:
            if self.side == ABE_LEFT and pos.x > rect.X + margin or pos.Right < rect.X:
                self.Undock()
            elif self.side == ABE_RIGHT and pos.Right < rect.Right - margin or pos.x > rect.Right:
                self.Undock()

    def Dock(self, side = None, setFrameStyle = True):
        """
            Dock to the side of the screen storing un-docked information for later use
            If self.AutoHide is True tries docking with autohide first,
            attempting to dock regularly if that fails or if self.autohide is False

            Sets the following:
                self.side
                self.oldSize
                self.autohidden - Only in autohide mode

            Calls self.OnDock in either docking style

            returns True if either docking style succeeds, None otherwise
        """

        log.debug('Dock')

        self.monId = Monitor.GetFromWindow(self.win).DeviceId #@UndefinedVariable


        if side is not None:
            self.side = side

        if self.AutoHide:
            if SHAppBarMessage(ABM_SETAUTOHIDEBAR, self.GetNewAppBarData(True)):
                log.info('registered autohide %s', sideStrings[self.side])
                if setFrameStyle: SetToolStyle(self.win, True)
                self.SetWinAlwaysOnTop(True)
                if self.oldSize is None:
                    self.oldSize = self.win.Size
                self.SetAutoHidePos()
                self.timer.Start(AUTOHIDE_TIMER_MS)
                self.autohidden = False
                self.OnDock(True)
                return True
            else:
                log.warning('obtaining autohide bar failed')

        # fall back to normal docking
        if SHAppBarMessage(ABM_NEW, self.newAppBarData):
            self.oldSize = self.oldSize or self.win.Size
            if setFrameStyle: SetToolStyle(self.win, True)
#            self.SetWinAlwaysOnTop(True)
            self.AppBarQuerySetPos(set = False)
            self.OnDock(True)
            return True

    def Undock(self, setFrameStyle = True):
        """
            Undock the window
        """

        log.debug('Undock')

        #TODO: Should we do this line? It never got hit before and it seemed to work fine

        if setFrameStyle: SetToolStyle(self.win, False)

        #TODO: should do both or just one SHAppBarMessage?
        if self.AutoHide:
            SHAppBarMessage(ABM_SETAUTOHIDEBAR, self.newAppBarData)
        SHAppBarMessage(ABM_REMOVE, self.newAppBarData)
        self.docking = self.docked = False
        self.OnDock(False)

        self.autohidden = False
        self.SetWinAlwaysOnTop()

    #===========================================================================
    # The following functions are invoked by the system when the AppBar needs
    # to be notified.
    #===========================================================================
    winPosArgs = (0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)

    def OnAppBarStateChange(self, wParam, lParam):
        log.info('OnAppBarStateChange')

        # Check to see if the taskbar's always-on-top state has
        # changed and, if it has, change the appbar's state
        # accordingly.
        state = SHAppBarMessage(ABM_GETSTATE, self.newAppBarData)
        SetWindowPos(self.Handle,HWND_TOPMOST if (ABS_ALWAYSONTOP & state) else HWND_BOTTOM, *self.winPosArgs)

    def OnAppBarFullscreenApp(self, wParam, lParam):
        log.info('OnAppBarFullscreenApp')

        state = SHAppBarMessage(ABM_GETSTATE, self.newAppBarData)

        if lParam:
            SetWindowPos(self.Handle, HWND_TOPMOST if (ABS_ALWAYSONTOP & state) else HWND_BOTTOM, *self.winPosArgs)

        elif state & ABS_ALWAYSONTOP:
            SetWindowPos(self.Handle, HWND_TOPMOST, *self.winPosArgs)

    def OnAppBarPosChanged(self, wParam, lParam):
#        log.warning('not implemented: OnAppBarPosChanged')
#        return

        log.info('OnAppBarPosChanged')

        rc, mon = RECT(), monitor_rect(self.win)
        rc.top    = mon.Top
        rc.left   = mon.Left
        rc.right  = mon.Right
        rc.bottom = mon.Bototm

        winrect = self.win.Rect
        iHeight = winrect.Bottom - winrect.Top
        iWidth  = winrect.Right  - winrect.Left

        if self.side == ABE_TOP:
            rc.bottom = rc.top + iHeight
        elif self.side == ABE_BOTTOM:
            rc.top = rc.bottom - iHeight
        elif self.side == ABE_LEFT:
            rc.right = rc.left + iWidth
        elif self.side == ABE_RIGHT:
            rc.left = rc.right - iWidth;

        #self.AppBarQuerySetPos(rc = rc)

    def GetDockRect(self, rect = None):
        """
            Calculates the new RECT for the window,
            returns a appBarData,
            also returns winWidth, the current width of the window
        """
        abd = self.newAppBarData
        mon = monitor_rect(self.win)

        if self.side in (ABE_LEFT, ABE_RIGHT):
            r = self.win.Rect if rect is None else rect
            winWidth = r.Width
            abd.rc.left  = mon.Left if self.side == ABE_LEFT else mon.Right - r.Width+1
            abd.rc.right = mon.Left + r.Width if self.side == ABE_LEFT else mon.Right+1

        abd.rc.top = mon.Top
        abd.rc.bottom = mon.Bottom+1
        return abd, winWidth

    def SetAutoHidePos(self):
        abd, unused_winWidth = self.GetDockRect()
        rc = abd.rc
        self.dockedRect = wx.Rect(rc.left, rc.top, rc.right  - rc.left, rc.bottom - rc.top)
        self.docking = True

    def AppBarQuerySetPos(self, set = True):
        """
            Query or set the size and position of the docked BuddyList
            Sets self.dockedRect
            self.Docking becomes True
        """
        side = self.side
        appBarData, winWidth = self.GetDockRect()

        if not set:
            SHAppBarMessage(ABM_QUERYPOS, appBarData)

        if side == ABE_LEFT:
            appBarData.rc.right = appBarData.rc.left + winWidth
        elif side == ABE_RIGHT:
            appBarData.rc.left = appBarData.rc.right - winWidth

        if set:
            SHAppBarMessage(ABM_SETPOS, appBarData)

        rc = appBarData.rc
        self.dockedRect = wx.Rect(rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top)
        self.docking = True

    def OnAppBarWindowArrange(self, wParam, lParam):
        log.info('OnAppBarWindowArrange')

    appBarCallbackMap = {ABN_STATECHANGE:   OnAppBarStateChange,
                         ABN_FULLSCREENAPP: OnAppBarFullscreenApp,
                         ABN_POSCHANGED:    OnAppBarPosChanged,
                         ABN_WINDOWARRANGE: OnAppBarWindowArrange}

    def AppBarCallback(self, *params):
        log.info('AppBarCallback %r', params)
        wParam, lParam = params[2:4]

        self.appBarCallbackMap[wParam](wParam, lParam)

    def GetNewAppBarData(self, lParam = False):
        """
            Create and return a new AppBarData Struct (see MSDN's "APPBARDATA structure")
            filling in the following with the current information:
                hWnd   - Window Handle
                uEdge  - side of screen
                rc     - Window Rectangle
                lParam - uses lParam Arg
        """

        abd  = APPBARDATA()
        abd.hWnd = self.Handle
        abd.uEdge = self.side
        abd.rc = self.win.RECT
        abd.lParam = lParam
        # abd.uCallbackMessage = self.appbar_cb_id
        return abd

    newAppBarData = property(GetNewAppBarData)

    @property
    def Handle(self):
        return self.win.Handle

    def SetWinAlwaysOnTop(self, val = None):
        if self.ShouldAlwaysStayOnTop:
            self.ShouldAlwaysStayOnTop(val)


def SetToolStyle(win, val):
    '''
    Sets a window to be "tool style," that is, no maximize/minimize buttons and
    with a smaller square border.
    '''
    if val: win.SetWindowStyle(wx.FRAME_TOOL_WINDOW  | win.GetWindowStyle())
    else:   win.SetWindowStyle(~wx.FRAME_TOOL_WINDOW & win.GetWindowStyle())


def monitor_rect(win):
    'returns a wxRect for the client area of the monitor the mouse pointer is over'

    return Monitor.GetFromWindow(win).ClientArea #@UndefinedVariable

def onscreen(x, y):
    'Returns True if the specified (x, y) point is on any screen.'

    return Monitor.GetFromPoint((x, y), find_near = False) is not None #@UndefinedVariable

def isRectOnScreen(rect):

    return Monitor.GetFromRect(rect, find_near = False) is not None #@UndefinedVariable

class APPBARDATA(Structure):
    'Used with the Win32 shell.dll SHAppBarMessage function.'

    _fields_ = [
        ("cbSize", DWORD),
        ("hWnd", HANDLE),
        ("uCallbackMessage", c_uint),
        ("uEdge", c_uint),
        ("rc", RECT),
        ("lParam", LPARAM),
    ]

taskbar_abd = APPBARDATA()
from ctypes import sizeof
taskbar_abd.cbSize = sizeof(APPBARDATA)

def taskbar_info():
    '''
    Returns a mapping with information about the state of the taskbar, with
    the following keys:

    always_on_top
    autohide
    '''
    uState = SHAppBarMessage(ABM_GETSTATE, taskbar_abd)
    return dict(always_on_top = uState & ABS_ALWAYSONTOP,
                autohide      = uState & ABS_AUTOHIDE)

try:
    import psyco #@UnresolvedImport
except Exception, e:
    pass
else:
    psyco.bind(Docker)
