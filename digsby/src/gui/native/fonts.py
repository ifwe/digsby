from gui.native import getPlatformDir
platdir = getPlatformDir()

exec("from gui.native.%s.%sfonts import *" % (platdir, platdir))

#__import__('gui.native.%s.%sfonts' % (platdir, platdir),
#           globals(), locals(), fromlist = '*')
