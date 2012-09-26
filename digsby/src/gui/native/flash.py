from config import platformName
import wx
from traceback import print_exc
from logging import getLogger
logger = getLogger('flash')

class StubFlashWindow(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        flash_url = 'http://www.adobe.com/go/EN_US-H-GET-FLASH'

        self.link = wx.HyperlinkCtrl(self, -1, 'Adobe Flash is required', url = flash_url)

    def LoadMovie(self, layer, url):
        log.warning('Flash is not initialized, cannot LoadMovie(%r)', url)

#
# TODO: Disabled until the cause of b14552 can be determined...
#
#if platformName == 'win':
#    try:
#        from wx.lib.flashwin import FlashWindow
#    except Exception:
#        print_exc()
#        FlashWindow = StubFlashWindow
#else:
#    raise NotImplementedError()