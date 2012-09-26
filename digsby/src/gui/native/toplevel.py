import gui.native

exec("from gui.native.%s.toplevel import *" % gui.native.getPlatformDir())
