from util.primitives.funcs import Delegate
from gui.native import notImplemented

class Docker(object):
    def __init__(self, win, autohide = False, enabled = True):
        self.docked = False
        self.LinkedWindows = []
        self.ShouldShowInTaskbar = lambda: True
        self.OnHide = Delegate()
        notImplemented()

    def SetAutoHide(self, *a, **k):
        notImplemented()
        pass

    def SetEnabled(self, *a, **k):
        notImplemented()
        pass

    def SetRectSimple(self, rect):
        notImplemented()
        pass

    def GoAway(self):
        notImplemented()
        pass

    def ComeBack(self):
        notImplemented()
        pass

    def AnimateWindowTo(self, r):
        notImplemented()
        pass

    def UpdateTaskbar(self):
        notImplemented()
        pass

    def Dock(self, side = None, setStyle = True):
        notImplemented()
        pass

    def Undock(self, setStyle = True):
        notImplemented()
        pass

    def GetDockRect(self, rect = None):
        notImplemented()
        pass

    @property
    def Enabled(self):
        notImplemented()
        return False

    def SetVelocity(self, vel):
        notImplemented()
        return False

    velocity = property(lambda self: notImplemented(), SetVelocity)
