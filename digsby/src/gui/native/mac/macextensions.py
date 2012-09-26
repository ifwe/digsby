'''
This file will contain all platform-specific extensions or method replacements
to functions in the Python stdlib or the WX API.
'''

import wx
import gui.native

# on mac, the %#I sequence to the system's strftime doesn't work--but
# a lowercase 'l' does almost the same thing 

import time
_strftime = time.strftime
def patched_strftime(fmt, t = None):
    return _strftime(fmt.replace('%#I', '%l'), t)

time.strftime = patched_strftime
del patched_strftime

wx._Window.ReallyRaise = lambda win: win.Raise()
