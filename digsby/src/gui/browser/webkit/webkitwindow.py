'''

Web browser control implemented on top of wx.webview.WebView, which is
based on WebKit.

'''
from __future__ import with_statement

import wx
from collections import defaultdict
from logging import getLogger; log = getLogger('webkitwindow')
from util import traceguard
from util.primitives.funcs import Delegate

try:
    import webview
    WebView = webview.WebView
except ImportError:
    from traceback import print_exc
    print_exc()

    class WebKitWindow(wx.Panel):
        pass
else:
    MinimumTextSizeMultiplier       = 0.5
    MaximumTextSizeMultiplier       = 3.0
    TextSizeMultiplierRatio         = 1.2

    class WebKitWindow(WebView):
        def __init__(self, parent, initialContents = '', contentPath = 'file:///c:/', url = None, simple_events = False, external_links=True, **opts):
            super(WebKitWindow, self).__init__(parent, size=wx.Size(200,200), **opts)

            self._jsqueue_enabled = True
            self.jsqueue = []
            self.js_to_stderr = False

            self.ExternalLinks = external_links

            self.OnNav = Delegate() # Called for NavigateComplete2 events
            self.OnDoc = Delegate() # Called for DocumentComplete events
            self.OnTitleChanged = Delegate()

            Bind = self.Bind
            Bind(wx.EVT_CONTEXT_MENU, self.__OnContextMenu)
            Bind(webview.EVT_WEBVIEW_LOAD,            self.OnStateChanged)
            Bind(webview.EVT_WEBVIEW_BEFORE_LOAD,     self.OnBeforeLoad)
            Bind(webview.EVT_WEBVIEW_RECEIVED_TITLE,  self.OnTitleChanged)
            from gui.browser.webkit import setup_webview_logging
            setup_webview_logging(self, 'webview')

            self.urltriggers = defaultdict(list)

            if initialContents and url is not None:
                raise ValueError("please specify initialContents or url, but not both")

            # some APIs call LoadUrl
            self.LoadUrl = self.LoadURL

            if url is not None:
                self.LoadURL(url)
            else:
                self.SetPageSource(initialContents, 'file:///')

            self.BlockWebKitMenu = True


        def set_jsqueue_enabled(self, enabled):
            self._jsqueue_enabled = enabled

        def set_window_open_redirects_to_browser(self, url_callback=None):
            '''Redirects window.open calls in this webview to the users's default browser.'''

            add_window_open_redirect(self, url_callback)

        def __OnContextMenu(self, e):
            # disable webkit's default context menus
            if not self.BlockWebKitMenu:
                e.Skip()

        def SetPageSource(self, source, baseUrl):
            if self._jsqueue_enabled:
                del self.jsqueue[:]
                self._js_paused = True
            WebView.SetPageSource(self, source, baseUrl)

        def SetPage(self, source, baseUrl=None):
            if baseUrl is None:
                baseUrl = 'file:///'
            return self.SetPageSource(source, baseUrl)

        def RunScript(self, s, cb = None, immediate=False):
            # ensure that the page loader isn't loading the current page--we have
            # to wait until after its done to execute javascript
            assert wx.IsMainThread()
            if self._jsqueue_enabled and self._js_paused:
                if immediate:
                    pass #log.debug('ignoring immediate javascript call: %r', s)
                else:
                    #log.debug('delaying execution of JS')
                    self.jsqueue.append((s, cb))
            else:
                val = self._runscript(s)
                if cb is None:
                    return val
                else:
                    cb(val)

    #    __call__ = webview.WebView.RunScript

        def AppendToPage(self, content):
            escaped = content.replace('\n', '\\\n').replace('"', '\\"')
            self.RunScript('appendMessage("%s");' % escaped)

        def ScrollToBottom(self):
            self.RunScript('window.scroll(0, 10000000);')

        def OnStateChanged(self, e):
            e.Skip()
            state = e.GetState()

            if state == webview.WEBVIEW_LOAD_NEGOTIATING:
                #log.debug('WEBVIEW_LOAD_NEGOTIATING')
                #log.debug('e.URL %r', e.URL)
                # pause javascript when loading a page
                self._pause_javascript()
            elif state == webview.WEBVIEW_LOAD_DOC_COMPLETED:
                #log.debug('WEBVIEW_LOAD_DOC_COMPLETED, calling _execute_delayed_javascript')
                #log.debug('e.URL %r', e.URL)
                # when the page is done loading, execute delayed javascript
                self._execute_delayed_javascript()
                self.OnDoc(e.URL)

            if state == webview.WEBVIEW_LOAD_DL_COMPLETED:
                self.OnNav(e.URL)

        def _pause_javascript(self):
            self._js_paused = True

        def _execute_delayed_javascript(self):
            self._js_paused = False

            #if self.jsqueue:
                #log.debug('done loading, executing %d JS calls', len(self.jsqueue))

            for n, (script, cb) in enumerate(self.jsqueue):
                val = self._runscript(script)
                if val != 'undefined':
                    log.debug('result %d: %r' % (n, val))
                if cb is not None:
                    cb(val)

            del self.jsqueue[:]

        def _runscript(self, s):
            return WebView.RunScript(self, s)

        def OnBeforeLoad(self, e):
            type = e.GetNavigationType()
            e.Skip()

            if e.IsCancelled():
                return

            url = e.GetURL()
            if type == webview.WEBVIEW_NAV_LINK_CLICKED:

                callback = self.urltriggers.get(url, None)
                if callback is not None:
                    with traceguard: callback()
                    e.Cancel()

                if self.ExternalLinks and not url.startswith('javascript'):
                    wx.LaunchDefaultBrowser(url)
                    e.Cancel()


        def OnURL(self, url, callback):
            if not hasattr(callback, '__call__'):
                raise TypeError('OnURL takes a callable')
            self.urltriggers[url].append(callback)

        def SetHTML(self, contents, baseUrl = 'file:///'):
            self.SetPageSource(contents, baseUrl)

        HTML  = property(webview.WebView.GetPageSource, SetHTML)
        Title = property(webview.WebView.GetPageTitle, webview.WebView.SetPageTitle)

        def EditSource(self):
            from gui.browser.webkit.webkiteditsource import EditSource
            return EditSource(self)

def add_window_open_redirect(self, url_callback=None, blank_opens_browser=False):
    # window.open calls in JavaScript fire EVT_WEBVIEW_NEW_WINDOW without an
    # event.URL argument. this is an invisible webview frame to work around
    # that fact for the times we want window.open to open links in a real
    # browser.

    if url_callback is None:
        url_callback = wx.LaunchDefaultBrowser

    class WindowOpenRedirector(wx.webview.WebView):
        def __init__(self):
            self.frame = wx.Frame(None)
            wx.webview.WebView.__init__(self, self.frame)
            self.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.__onbeforeload)
        def __onbeforeload(self, e):
            print '*** caught window.open(%r)' % e.URL
            url_callback(e.URL)
            e.Cancel()
            wx.CallAfter(self.Destroy)

    def _on_new_window(e):
        print '_on_new_window', e, e.URL
        if not e.URL:
            e.WebView = WindowOpenRedirector()
            e.Skip(False)
        else:
            if blank_opens_browser:
                url_callback(e.URL)
                e.Skip(False)
            else:
                e.Skip()

    self.Bind(wx.webview.EVT_WEBVIEW_NEW_WINDOW, _on_new_window)

