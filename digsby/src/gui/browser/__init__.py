import wx

#
# import browser classes lazily
#

if 'wxMSW' in wx.PlatformInfo:
    USE_WEBKIT_AS_BROWSER = True

    if USE_WEBKIT_AS_BROWSER:
        def Browser(*a, **k):
            from gui.browser.webkit.webkitwindow import WebKitWindow
            return WebKitWindow(*a, **k)
    else:
        def Browser(*a, **k):
            from gui.browser.iewindow import IEWindow
            return IEWindow(*a, **k)

elif 'wxMac' in wx.PlatformInfo:
    def Browser(*a, **k):
        from gui.browser.mac_webkit import WebKitWindow
        return WebKitWindow(*a, **k)

else:
    raise NotImplementedError('no Browser interface implemented for this platform')

class BrowserFrame(wx.Frame):
    def __init__(self, parent, title = '', size = wx.DefaultSize, pos = wx.DefaultPosition, url = '', style = wx.DEFAULT_FRAME_STYLE, name = '', external_links=True):
        wx.Frame.__init__(self, parent, title = title, size = size, pos = pos, style = style, name = name)

        self.browser = Browser(self, url = url, external_links=external_links)
        self.OnDoc = self.browser.OnDoc

def reload_plugins():
    import wx.webview
    if 'wxMSW' in wx.PlatformInfo and USE_WEBKIT_AS_BROWSER:
        wx.webview.WebView.ReloadPlugins()
        return True

    return False

