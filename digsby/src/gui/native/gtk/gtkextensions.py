'''
This file will contain all platform-specific extensions or method replacements
to functions in the Python stdlib or the WX API.
'''

import wx
import gui.native

# wxTLW.Show does not activate the window like it does
# on some other platforms--no special code is needed.
wx.TopLevelWindow.ShowNoActivate = wx.TopLevelWindow.Show

