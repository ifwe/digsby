import wx
import gui.native
import ctypes

def ApplySmokeAndMirrors(win, shape = None):
    pass
    
def _setalpha_wxMac(window, alpha):
    tlw = wx.GetTopLevelParent(window)
    tlw.SetTransparent(alpha)
    
def _getalpha_wxMac(window):
    tlw = wx.GetTopLevelParent(window)
    return tlw.GetTransparent()

setalpha = _setalpha_wxMac
getalpha = _getalpha_wxMac

def DrawSubMenuArrow(dc, arect):
    gui.native.notImplemented()

controls = {}
states = {}
