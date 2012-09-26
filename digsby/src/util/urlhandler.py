import wx
from logging import getLogger; log = getLogger('urlhandler'); info = log.info
if 'wxMSW' in wx.PlatformInfo:


    def register_protocol(protocol):

        key = _winreg.OpenKeyEx(_winreg.HKEY_CURRENT_USER, #@UndefinedVariable
                                "HKEY_CLASSES_ROOT\\%s" % protocol,0,
                                _winreg.KEY_ALL_ACCESS) #@UndefinedVariable

        # an example of how to do this...
        '''
[HKEY_CLASSES_ROOT\news]
@="URL:news Protocol"
"URL Protocol"=""
"EditFlags"=hex:02,00,00,00

[HKEY_CLASSES_ROOT\news\DefaultIcon]
@="\"C:\\Xnews\\Xnews.exe\""

[HKEY_CLASSES_ROOT\news\shell]

[HKEY_CLASSES_ROOT\news\shell\open]

[HKEY_CLASSES_ROOT\news\shell\open\command]
@="\"C:\\Xnews\\Xnews.exe\" /url=\"%1\""
'''


else:
    log.warning('No URL handling implementation for this platform.')