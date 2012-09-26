import wx
from time import time
from gui.toolbox import calllimit

class MyFrame(wx.Frame):

    @calllimit(1)
    def foo(self, e):
        self.Title = str(time())

def test_calllimit():
    f = MyFrame(None)
    b = wx.Button(f, -1, 'foo')
    b.Bind(wx.EVT_BUTTON, f.foo)
    f.Show()

def main():
    a = wx.PySimpleApp()
    test_calllimit()
    a.MainLoop()

if __name__ == '__main__':
    main()
