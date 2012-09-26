import wx
import gui.native
import time
import os

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
    return 0

def createEmail(mailto):
    return gui.native.notImplemented()

wx.Window.ShowNoFocus = wx.Window.Show
wx.Window.ReallyRaise = wx.Window.Raise
wx.TopLevelWindow.Visible = wx.TopLevelWindow.Shown
