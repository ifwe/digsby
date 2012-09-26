import gui.native

exec("from gui.native.%s.%ssysinfo import *" % (gui.native.getPlatformDir(), gui.native.getPlatformDir()))
