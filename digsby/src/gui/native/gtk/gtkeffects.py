import gui.native

def _setalpha_wxGTK(window, alpha):
    window._transparency = alpha
    window.SetTransparent(alpha)
def _getalpha_wxGTK(window):
    return getattr(window, '_transparency', 255)
def _donealpha_wxGTK(window):
    return _setalpha_wxGTK(window, 255)

setalpha = _setalpha_wxGTK
getalpha = _getalpha_wxGTK
drawnative = lambda *a,**kw: None
controls = {}
states = {}

def DrawSubMenuArrow(dc, arect):
    gui.native.notImplemented()

import wx
import gui.native
import ctypes

def ApplySmokeAndMirrors(win, shape = None):
    pass#gui.native.notImplemented()
