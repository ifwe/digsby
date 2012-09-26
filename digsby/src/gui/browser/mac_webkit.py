'''

embedded controllable ie

'''

from __future__ import with_statement
import wx
import wx.webkit as webkit
from logging import getLogger; log = getLogger('iewindow')
from util.primitives.funcs import Delegate

class WebKitWindow(webkit.WebKitCtrl):
    def __init__(self, parent, initialContents = '', url = None):
        webkit.WebKitCtrl.__init__(self, parent, style = wx.NO_BORDER)

        self.OnNav = Delegate() # Called for NavigateComplete2 events
        self.OnDoc = Delegate() # Called for DocumentComplete events

        # allow security popups to appear
        #self._set_Silent(False)

        if url is not None:
            self.seturl = url
            assert isinstance(url, basestring)
            self.LoadUrl(url)
        else:
            s = initialContents or ''
            if s:
                self.SetPage(s)

        self.Bind(webkit.EVT_WEBKIT_BEFORE_LOAD, self.BeforeLoad)
        self.Bind(webkit.EVT_WEBKIT_STATE_CHANGED, self.StateChanged)

    def LoadUrl(self, url):
        if isinstance(url, unicode):
            import warnings
            warnings.warn('LoadUrl called with a unicode: %r' % url)
            url = str(url)

        if not isinstance(url, str):
            raise TypeError('must pass a string to LoadUrl')

        return self.LoadURL(url)

    def OnURL(self, url, callback):
        if not callable(callback):
            raise TypeError('callback must be callable')

        self.urltriggers[url] += [callback]

    @property
    def FileURL(self):
        try:
            return 'file:///' + self.file.name.replace('\\', '/')
        except AttributeError:
            return self.seturl

    #SetPage = iewin.IEHtmlWindow.LoadString

    def SetPage(self, content):
        return self.SetPageSource(content)

    def BeforeLoad(self, event):
        self.OnNav(event.GetURL())

    def StateChanged(self, event):
        if event.GetState() == webkit.WEBKIT_STATE_STOP:
            self.OnDoc(event.GetURL())

if __name__ == '__main__':
    a = wx.PySimpleApp()
    _ = lambda s: s

    fbSize = (646, 436)
    url = 'http://www.google.com/'

    from util import trace
    trace(WebKitWindow)

    f = wx.Frame(None, size = fbSize, title = 'ie test')
    wk = WebKitWindow(f, url = url)

    f.Show()
    a.MainLoop()
