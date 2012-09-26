'''
Cross-platform wx API extensions go here.
'''

import new
import traceback

def SetMinHeight(self,h):
    self.minHeight = h
    if h != -1 and self.GetSize().height < h:
        self.SetSize((-1, h))

def GetMinHeight(self):
    return self.minHeight

import wx.lib.expando

wx.lib.expando.ExpandoTextCtrl.SetMinHeight = SetMinHeight
wx.lib.expando.ExpandoTextCtrl.GetMinHeight = GetMinHeight
wx.lib.expando.ExpandoTextCtrl.GetExtraHeight = lambda self: self.extraHeight

del SetMinHeight
del GetMinHeight

import cgui

if hasattr(cgui, 'TextCtrlAutoComplete'):
    wx.TextCtrl.AutoComplete = new.instancemethod(cgui.TextCtrlAutoComplete, None, wx.TextCtrl)

if not hasattr(wx, "IsMainThread"):
    import threading
    def isMainThread():
        return threading.currentThread().getName() == 'MainThread'
    wx.IsMainThread = isMainThread

wx.Rect.Clamp      = new.instancemethod(cgui.RectClamp, None, wx.Rect)
wx.Rect.ClampPoint = new.instancemethod(cgui.RectClampPoint, None, wx.Rect)

wx.ContextMenuEvent.IsKeyPress = lambda e: e.Position == (-1, -1)

# Easier to remember ways to start repeating and non-repeating timers
wx.Timer.StartRepeating = lambda self, ms: wx.Timer.Start(self, ms, False)
wx.Timer.StartOneShot   = lambda self, ms: wx.Timer.Start(self, ms, True)

def CreateTransparentBitmap(w, h):
    bitmap = wx.EmptyBitmap(w, h)
    bitmap.UseAlpha()
    return bitmap

wx.TransparentBitmap = CreateTransparentBitmap

try:
    from cgui import SetBold
except ImportError:
    import sys
    print >>sys.stderr, 'WARNING: using slow SetBold'
    def SetBold(win, bold = True):
        "Sets the window's font to bold or not bold."
        f = win.Font
        f.SetWeight(wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL)
        win.Font = f

if getattr(wx, 'WXPY', False):
    wx.WindowClass = wx._Window
else:
    wx.WindowClass = wx.Window

wx.WindowClass.SetBold = new.instancemethod(SetBold, None, wx.WindowClass)

def call_later_repr(self):
    from util import funcinfo
    fi = funcinfo(self.callable)
    if self.running:
        return '<CallLater (running) %s>' % fi
    else:
        return '<CallLater %s>' % fi

wx.CallLater.__repr__ = call_later_repr

def ReleaseAllCapture(ctrl):
    '''Releases all of this control's mouse capture.'''

    while ctrl.HasCapture():
        ctrl.ReleaseMouse()

wx.WindowClass.ReleaseAllCapture = ReleaseAllCapture

if not getattr(wx, 'WXPY', False):
    wx.Dialog.__enter__ = lambda self: self
    wx.Dialog.__exit__ = lambda self, type, value, traceback: self.Destroy()

    def IsDestroyed(win):
        return not bool(win)

    from cStringIO import StringIO
    def ImageFromString(s):
        return wx.ImageFromStream(StringIO(s))

    wx.ImageFromString = ImageFromString
    wx.AcceleratorTableFromSequence = wx.AcceleratorTable
    wx.IsDestroyed = IsDestroyed
    del IsDestroyed


if not hasattr(wx.RendererNative, 'DrawFocusRect'):
    # Patched wx on MSW has wxRenderer::DrawFocusRect
    wx.RendererNative.DrawFocusRect = lambda *a, **k: None

try:
    import webview
except ImportError:
    traceback.print_exc()
else:
    if not hasattr(webview.WebView, 'ResetTextSize'):
        webview.WebView.ResetTextSize = lambda *a, **k: None

    if not hasattr(webview.WebView, 'SetMouseWheelZooms'):
        webview.WebView.SetMouseWheelZooms = lambda *a, **k: None

if "wxGTK" in wx.PlatformInfo:
    orig_bmpeq = wx.Bitmap.__eq__
    def bmpeq(self, other):
        if isinstance(other, wx.Bitmap):
            return orig_bmpeq(self, other)
        return False
    wx.Bitmap.__eq__ = bmpeq


def RaiseExisting(cls):
    '''
    Raises the first existing window of the specified class.

    If one was found, the window is returned.
    '''

    for tlw in wx.GetTopLevelWindows():
        if type(tlw) is cls:
            tlw.Raise()
            return tlw

wx.TopLevelWindow.RaiseExisting = classmethod(RaiseExisting)

def MakeOrShow(cls, parent = None):
    win = cls.RaiseExisting()

    if win is None:
        win = cls(parent)
        wx.CallAfter(win.Show)

    return win

wx.TopLevelWindow.MakeOrShow = classmethod(MakeOrShow)

try:
    from cgui import LeftDown
except ImportError:
    def LeftDown():
        return wx.GetMouseState().LeftDown()

wx.LeftDown = LeftDown

if not hasattr(wx.PyTimer, 'SetCallback'):
    def SetCallback(self, cb):
        assert hasattr(self, '__call__')
        self.notify = cb

    wx.PyTimer.SetCallback = SetCallback

#sized_controls.py:474 "item.SetUserData({"HGrow":0, "VGrow":0})"
def SetUserData(self, data):
    self._userData = data

def GetUserData(self):
    return getattr(self, '_userData', None)

wx.SizerItem.SetUserData = SetUserData
wx.SizerItem.GetUserData = GetUserData
