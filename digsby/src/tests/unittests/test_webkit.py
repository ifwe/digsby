from tests import TestCase, test_main
from path import path
import wx.webview

if False:
    class TestWebKit(TestCase):
        def test_unicode_paths(self):
            '''
            ensure that webkit can load unicode paths from the harddrive
            '''
            unicode_name = u'\u0439\u0446\u0443\u043a\u0435\u043d' 
            html = u'''\
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body>
        <img id="unicodeImage" src="data/%s/%s.png" />
    </body>
    </html>
    ''' % (unicode_name, unicode_name)

            f = wx.Frame(None)
            try:
                w = wx.webview.WebView(f)
                thisdir = path(__file__).dirname()
                htmlfile = thisdir / 'unicode_test.html'
                htmlfile.write_bytes(html.encode('utf-8'))

                w.LoadURL(htmlfile.url())
                
                self._did_onload = False

                def onload(e):
                    e.Skip()
                    if e.GetState() == wx.webview.WEBVIEW_LOAD_ONLOAD_HANDLED:
                        self._did_onload = True

                w.Bind(wx.webview.EVT_WEBVIEW_LOAD, onload)
                f.Show()

                # <--- hypothetical "block until loaded" here
                
                assert '149' == w.RunScript('document.getElementById("unicodeImage").clientWidth')
            finally:
                f.Destroy()
                try:htmlfile.remove()
                except Exception: pass
        
if __name__ == '__main__':
    test_main()
