'''

Patches wx.StandardPaths to include extra Windows specific methods.

'''

import wx
import os
import gui.native

_paths = [
    ('GetUserStartupDir', gui.native.notImplemented()),
    ('GetStartupDir',     gui.native.notImplemented()),
    # TODO: Get properly localized version! 
    ('GetUserDesktopDir', os.path.join(os.environ["HOME"], "Desktop")),
    ('GetDesktopDir',     os.path.join(os.environ["HOME"], "Desktop"))
]

for method_name, path in _paths:
    setattr(wx.StandardPaths, method_name, lambda p: path)
'''

Patches wx.StandardPaths to include extra Windows specific methods.

'''

import wx
import os
import gui.native

_paths = [
    ('GetUserStartupDir', gui.native.notImplemented()),
    ('GetStartupDir',     gui.native.notImplemented()),
    # TODO: Get properly localized version! 
    ('GetUserDesktopDir', os.path.join(os.environ["HOME"], "Desktop")),
    ('GetDesktopDir',     os.path.join(os.environ["HOME"], "Desktop"))
]

for method_name, path in _paths:
    setattr(wx.StandardPaths, method_name, lambda p: path)
