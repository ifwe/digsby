import new
import gui.native

exec("from gui.native.%s.%seffects import *" % (gui.native.getPlatformDir(), gui.native.getPlatformDir()))

wx.WindowClass.Cut = new.instancemethod(ApplySmokeAndMirrors, None, wx.WindowClass)
