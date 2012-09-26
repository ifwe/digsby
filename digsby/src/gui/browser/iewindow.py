'''

embedded controllable ie

'''

from __future__ import with_statement
import wx
from random import randint
import wx.lib.iewin as iewin
from logging import getLogger; log = getLogger('iewindow')
from util.primitives.funcs import Delegate
from time import time
import stdpaths
import metrics

class IEWindow(iewin.IEHtmlWindow):
    def __init__(self, parent, initialContents = '', url = None):
        metrics.event('IE Window Created')

        iewin.IEHtmlWindow.__init__(self, parent, style = wx.NO_BORDER)

        self.OnNav = Delegate() # Called for NavigateComplete2 events
        self.OnBeforeNav = Delegate() # Called for Navigate2 events
        self.OnDoc = Delegate() # Called for DocumentComplete events

        # allow security popups to appear
        self._set_Silent(False)

        if url is not None:
            self.seturl = url
            assert isinstance(url, basestring)
            self.LoadUrl(url)
        else:
            s = initialContents or ''
            if s:
                self.SetPage(s)

    def LoadUrl(self, url):
        if isinstance(url, unicode):
            import warnings
            warnings.warn('LoadUrl called with a unicode: %r' % url)
            url = str(url)

        if not isinstance(url, str):
            raise TypeError('must pass a string to LoadUrl')

        return iewin.IEHtmlWindow.LoadUrl(self, url)

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
        # TODO: fix comtypes full IE support to not be SLOOOOOOOOOW
        #
        # At the moment, using LoadString requires comtypes to load the MSHTML
        # interface to IE, which is something like a 9mb generated Python file,
        # and memory usage spikes 40mb.
        #
        # To avoid this we write to a temporary file and use LoadUrl instead.

        tempname = 'digsby-%s-%s.html' % (time(), randint(1,9999)) # why doesn't TemporaryNamedFile work?

        p = stdpaths.temp / tempname
        p.write_bytes(content)
        return self.LoadUrl(p.url())

    # COM overloads (see DWebBrowserEvents2 interface at http://msdn.microsoft.com/en-us/library/aa768283.aspx)

    def BeforeNavigate2(self, this, pDisp, URL, *a):
        self.OnBeforeNav(URL[0])

    def NavigateComplete2(self, this, pDisp, URL, *a):
        self.OnNav(URL[0])

    def DocumentComplete(self, this, pDisp, URL, *a):
        self.OnDoc(URL[0])


if __name__ == '__main__':
    a = wx.PySimpleApp()
    _ = lambda s: s

    fbSize = (646, 436)
    url = 'http://www.google.com/'

    from util import trace
    trace(IEWindow)

    f = wx.Frame(None, size = fbSize, title = 'ie test')
    ie = IEWindow(f, url = url)

    def ondoc(e):
        print type(e)
        print e
        print e.URL

    ie.Bind(iewin.EVT_DocumentComplete,  ondoc)

    f.Show()
    a.MainLoop()
