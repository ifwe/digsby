import logging
logging.Logger.debug_s = logging.Logger.debug

import wx
from gui.browser.webkit import WebKitWindow



def test_webkit_unicode():
    f = wx.Frame(None)
    w = WebKitWindow(f, initialContents = 'test')

    #w.RunScript('document.write("test");')
    def foo():
        w.RunScript(u'document.write("<p>abcd\u1234</p>");')

    wx.CallLater(500, foo)

    f.Show()

def main():
    a = wx.PySimpleApp()
    test_webkit_unicode()
    a.MainLoop()

if __name__ == '__main__':
    main()