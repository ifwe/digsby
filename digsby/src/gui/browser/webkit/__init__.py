from .webkitwindow import WebKitWindow

import logging
import wx.webview

webview_to_logging_levels = {
    wx.webview.TipMessageLevel: logging.DEBUG,
    wx.webview.LogMessageLevel: logging.INFO,
    wx.webview.WarningMessageLevel: logging.WARNING,
    wx.webview.ErrorMessageLevel: logging.ERROR
}

def setup_webview_logging(webview, log, logfilter=None, logbasedir=None):
    log = logging.getLogger(log) if isinstance(log, basestring) else log

    if logbasedir is not None:
        assert logfilter is None

        def logfilter(i):
            filename = i['fn']
            if filename.startswith('file:///'):
                filename = filename[len('file:///'):]
            relpath = logbasedir.relpathto(filename)
            if len(relpath) < len(filename):
                i['fn'] = unicode(relpath)
            return True

    if logfilter is None:
        logfilter = lambda info: True

    def on_js_console_message(e):
        info = dict(
             level = webview_to_logging_levels.get(e.Level, logging.INFO),
             fn = e.GetSourceID(),
             lno = e.LineNumber,
             msg = e.Message)

        if logfilter(info):
            msg = '%(fn)s:%(lno)s | %(msg)s' % info
            record = log.makeRecord(log.name, info['level'], info['fn'], info['lno'], msg, (), None, "(unknown function)", None)
            log.handle(record)

    webview.Bind(wx.webview.EVT_WEBVIEW_CONSOLE_MESSAGE, on_js_console_message)

class WebKitDisplay(wx.webview.WebView):
    def __init__(self, parent):
        wx.webview.WebView.__init__(self, parent)
        self.Bind(wx.EVT_CONTEXT_MENU, lambda e: e.Skip(False))
        self.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.on_before_load)

    def on_before_load(self, e):
        e.Cancel()
        wx.LaunchDefaultBrowser(e.URL)
        
_origin_whitelist = {}
def get_origin_whitelist():
    return dict(_origin_whitelist)


def update_origin_whitelist(originURL, destProtocol, destDomain, allowSubdomains):
    'Makes an exception for XSS to destProtocol://destDomain from originURL.'
    # keep a map of exceptions we've already added, since webkit's API
    # for SecurityOrigin exceptions doesn't allow us to check if we already
    # have
    key = (originURL, destProtocol, destDomain, allowSubdomains)

    already_added = key in _origin_whitelist
    if already_added:
        return

    _origin_whitelist[key] = True
    assert len(_origin_whitelist) < 100 # ensure we're not leaking--this map should stay small

    wx.webview.WebView.AddOriginAccessWhitelistEntry(
        originURL, destProtocol, destDomain, allowSubdomains)

