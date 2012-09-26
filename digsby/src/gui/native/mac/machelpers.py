import wx
import gui.native
import time
import os

import Carbon.CarbonEvt

def FullscreenApp():
    gui.native.notImplemented()
    return False

def FullscreenAppLog():
    gui.native.notImplemented()

def SetOnTaskbar(f, val):
    # TODO: Do we need to implement this for the Window menu?
    gui.native.notImplemented()

def GetOnTaskbar(f):
    return True

def GetUserIdleTime():
    # Carbon functions are in seconds, not milliseconds, so multiply after getting the proper time
    lastEventTime = Carbon.CarbonEvt.GetCurrentEventTime() - Carbon.CarbonEvt.GetLastUserEventTime()
    return lastEventTime * 1000

def createEmail(mailto):
    return os.system("open " + mailto)

wx.Window.ShowNoFocus = wx.Window.Show
wx.Window.ReallyRaise = wx.Window.Raise
# wx.TopLevelWindow.Visible = wx.TopLevelWindow.Shown

from AppKit import *
from Foundation import *

class nspool(object):
    def __init__(self):
        self.pool = None
    
    def __enter__(self):
        self.pool = NSAutoreleasePool.alloc().init()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # the pool calls release in its destructor, if we call it ourselves
        # we'll get asserts about doing a double-free.
        self.pool = None
