'''
This file will contain all platform-specific extensions or method replacements to wx API,
such as overriding wx.LaunchDefaultBrowser on Windows or adding wx.Window.Cut method.
'''

from peak.util.imports import lazyModule, whenImported
wx = lazyModule('wx')
os = lazyModule('os')
wintypes = lazyModule('ctypes.wintypes')

from threading import Thread
from logging import getLogger; log = getLogger('winextensions')
import traceback

def browse(url):
    'Opens "url" in the default web browser.'

    def go():
        try:
            os.startfile(url)
        except WindowsError:
            if hasattr(traceback, 'print_exc_once'):
                traceback.print_exc_once()
            else:
                traceback.print_exc()
            log.error('could not open browser for url: %r', url)
            _fire_browser_error_popup()

    # reenable once we have advanced prefs
    t = Thread(target=go)
    t.setDaemon(True)
    t.start()

wx.LaunchDefaultBrowser = browse

def _fire_browser_error_popup():
    from common import fire
    fire('error', title='Error Launching Default Browser',
                  msg="No default web browser set in Windows. Please check your web browser's preferences.",
                  details='')

def wxRectToRECT(rect):
    r = wintypes.RECT()
    r.left = rect.X
    r.top  = rect.Y
    r.right = rect.X + rect.Width
    r.bottom = rect.Y + rect.Height
    return r

def wxRectFromRECT(rect):
    return wx.Rect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)

def GetRECT(win):
    return wxRectToRECT(win.Rect)

def GetLRECT(win):
    return wxRectToRECT(wx.RectS(win.GetSize()))

def _monkeypatch(*a, **k):
    # Hack until patching methods works better in new bindings.
    WindowClass = wx._Window if wx.WXPY else wx.Window
    
    WindowClass.GetRECT = GetRECT
    WindowClass.RECT = property(GetRECT)
    WindowClass.GetLRECT = GetLRECT
    WindowClass.LRECT = property(GetLRECT)
    wx.Rect.FromRECT = staticmethod(wxRectFromRECT)
    wx.Rect.RECT = property(wxRectToRECT)

whenImported('wx', _monkeypatch)
