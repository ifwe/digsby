import wx
from tests.testapp import testapp

from gui.uberwidgets.UberBar import UberBar
from gui.uberwidgets.UberButton import UberButton

def main():
    a = testapp()
    f = wx.Frame(None)

    bar = UberBar(f, skinkey = 'ButtonBarSkin', overflowmode = True)


    for x in xrange(5):
        title = 'test %d' % x
        b = UberButton(bar, -1, title)
        bar.Add(b)



    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()