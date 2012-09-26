import gui.native

exec("from gui.native.%s.%sextensions import *" % (gui.native.getPlatformDir(), gui.native.getPlatformDir()))
