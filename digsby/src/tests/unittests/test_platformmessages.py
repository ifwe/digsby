from tests import TestCase, test_main
import wx
import sip
import weakref
from cgui import PlatformMessageBinder, WindowSnapper
import gc

class TestPlatformMessages(TestCase):
    def test_ownership(self):
        f = wx.Frame(None)
        p = PlatformMessageBinder.ForWindow(f)
        assert not sip.ispyowned(p)
        f.Destroy(); del f; wx.GetApp().ProcessIdle(); gc.collect()

    def test_forwindow_returns_same(self):
        f = wx.Frame(None)
        p1 = PlatformMessageBinder.ForWindow(f)
        p2 = PlatformMessageBinder.ForWindow(f)
        assert p1 is p2
        f.Destroy(); del f; wx.GetApp().ProcessIdle(); gc.collect()

    def test_cycle(self):
        f = wx.Frame(None)
        f._binder = PlatformMessageBinder.ForWindow(f)
        ref = weakref.ref(f._binder)
        f.Destroy(); del f; wx.GetApp().ProcessIdle(); gc.collect()
        assert ref() is None

    def test_snap(self):
        f = wx.Frame(None)
        f._snapper = WindowSnapper(f)
        snapper = weakref.ref(f._snapper)
        f.Destroy(); del f; wx.GetApp().ProcessIdle(); gc.collect()
        assert snapper() is None


if __name__ == '__main__':
    test_main()

