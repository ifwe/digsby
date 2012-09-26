if __name__ == '__main__':
    __builtins__._ = lambda s: s

import wx.webview
import protocols
import gui.infobox.interfaces as gui_interfaces
from path import path
from util import Storage

class MockAccount(object):
    def get_dirty(self): return True
    def set_dirty(self, dirty): pass
    _dirty = property(get_dirty, set_dirty)

    protocol = 'mock'
    username = 'digsbee'

    def __init__(self):
        pass

returns_empty_str = lambda *a: path('')

mock_app_context = Storage(
        resource= lambda *a: Storage(url=returns_empty_str),
        get_res_dir = returns_empty_str)

content = '''

<div class="comment_button"></div>

function fb_comment_button_mousedown() {}

swapIn(function(){
    $(".comment_button").live("mousedown", fb_comment_button_mousedown);
});

swapOut(function(){
    $(".comment_button").die("mousedown", fb_comment_button_mousedown);
});

'''

import gui.infobox.providers as gui_providers
class MockProvider(gui_providers.InfoboxProviderBase):
    protocols.advise(
        asAdapterForTypes=[MockAccount],
        instancesProvide=[gui_interfaces.IInfoboxHTMLProvider])

    def __init__(self, account):
        self.acct = account

    def get_html(self, file, dir):
        print 'get_html', file
        if file == 'head.tenjin':
            return ''
        elif file == 'content.tenjin':
            return '<div>content!</div>' * 500

    def get_app_context(self, context):
        return mock_app_context

def on_console_message(e):
    print u'JS {e.LineNumber:>4}: {message}'.format(
        e=e, message=e.Message.encode('ascii', 'replace'))

def main():
    from tests.testapp import testapp
    app = testapp()
    f = wx.Frame(None)
    w = wx.webview.WebView(f)
    w.Bind(wx.webview.EVT_WEBVIEW_CONSOLE_MESSAGE, on_console_message)

    from gui.infobox.infoboxapp import init_host, set_hosted_content

    account = MockAccount()

    init_host(w)

    def do_set_content():
        for x in xrange(100):
            set_hosted_content(w, account)

    def on_load(e):
        if e.GetState() == wx.webview.WEBVIEW_LOAD_ONLOAD_HANDLED:
            pass
    w.Bind(wx.webview.EVT_WEBVIEW_LOAD, on_load)

    set_content_button = wx.Button(f, -1, 'set content')
    set_content_button.Bind(wx.EVT_BUTTON, lambda e: do_set_content())

    hsizer = wx.BoxSizer(wx.HORIZONTAL)
    hsizer.Add(set_content_button)

    f.Sizer = wx.BoxSizer(wx.VERTICAL)
    f.Sizer.AddMany([(hsizer, 0, wx.EXPAND), (w, 1, wx.EXPAND)])

    f.Show()

    app.MainLoop()

if __name__ == '__main__':
    main()
