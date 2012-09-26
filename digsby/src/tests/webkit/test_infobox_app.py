import wx.webview
from tests.testapp import testapp
from path import path

def main():
    a = testapp()
    f = wx.Frame(None)
    w = wx.webview.WebView(f)

    def on_js_console_message(e):
        print u'JS {e.LineNumber:>4}: {message}'.format(
            e=e, message=e.Message.encode('ascii', 'replace'))

    w.Bind(wx.webview.EVT_WEBVIEW_CONSOLE_MESSAGE, on_js_console_message)

    js = path(__file__) / '../../../..' / 'res/html/infobox/infobox.js'
    url = js.abspath().url()

    html = '''\
<!doctype html>
<html>
    <head>
        <script src="%s" />
        <script>
            function loadme() {
                console.log('in load');
                updateContent('foo', 'bar');
                updateContent('baz', 'meep');
                swapToContent('foo');
            }
        </script>
        <style type="text/css" src="" id="appCSS"></style>
    </head>
    <body onload="loadme();">
        <a href="javascript:swapToContent('foo');">foo</a>
        <a href="javascript:swapToContent('baz');">baz</a>
        <p>
        <div id="digsby_app_content"></div>
    </body>
</html>''' % url

    w.SetPageSource(html, 'file://')
    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()
