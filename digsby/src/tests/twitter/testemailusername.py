html = '''
<!doctype html>
<html>
    <head>
        <script type="text/javascript" src="jquery-1.3.2.js"></script>
        <script type="text/javascript">
            $.load(function() {
                console.log('on load!');
            });
        </script>
        
    </head>
    <body>
    </body>
</html>
    

'''

def main():
    from tests.testapp import testapp
    app = testapp()
    
    from path import path
    import os
    os.chdir(path(__file__).parent)
    
    import wx.webview
    
    
    f = wx.Frame(None)
    w = wx.webview.WebView(f)

    from gui.browser.webkit import setup_webview_logging
    setup_webview_logging(w, 'webview')

    w.SetPageSource(html)
    
    app.MainLoop()

if __name__ == '__main__':
    main()