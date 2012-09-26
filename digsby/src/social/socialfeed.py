from gui.imwin.styles.adiummsgstyles import AdiumMessageStyle

class SocialFeedStyle(AdiumMessageStyle):
    pass

def main():
    from tests.testapp import testapp
    app = testapp()

    import wx.webview
    f = wx.Frame(None, -1, size=(300, 700))

    from gui.imwin.styles.msgstyles import get_theme
    style = SocialFeedStyle(get_theme('Smooth Operator').path)

    w = wx.webview.WebView(f)
    w.SetPageSource(style.initialContents('', None, False))
    f.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()

