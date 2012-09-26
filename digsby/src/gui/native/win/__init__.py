import sys
if not sys.platform.startswith('win'):
    # Importing from gui.native.win on other platforms should never happen.
    assert 0

from peak.util.imports import lazyModule
dockconstants = lazyModule('gui.native.win.dockconstants')
winhelpers = lazyModule('gui.native.win.winhelpers')
process = lazyModule('gui.native.win.process')
toplevel = lazyModule('gui.native.win.toplevel')
winconstants = lazyModule('gui.native.win.winconstants')
winpaths = lazyModule('gui.native.win.winpaths')
winutil = lazyModule('gui.native.win.winutil')
appbar = lazyModule('gui.native.win.appbar')

