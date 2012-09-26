import gui.native

exec("from gui.native.%s.%sdocking import *" % (gui.native.getPlatformDir(), gui.native.getPlatformDir()))
