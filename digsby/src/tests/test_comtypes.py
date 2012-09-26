import wx
from wx.lib import iewin
import ctypes

class IETest(iewin.IEHtmlWindow):
    def DocumentComplete(self, this, pDisp, URL):
        print self, this, pDisp, URL
        print dir(URL)
        print dir(URL.value)
        print str(URL)
        print URL[0]


def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None)
    ie = IETest(f)
    f.Show()

    ie.LoadUrl('http://www.google.com')

    a.MainLoop()

if __name__ == '__main__':
    main()
