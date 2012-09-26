'''
creates a virtual list big enough to induce bug #3107 (black buddylist.)
'''

import Digsby, wx
from cgui import SkinVList

def main():
    a = wx.PySimpleApp()
    f = wx.Frame(None)

    def draw(dc, rect, n):
        dc.DrawText(str(n), rect.x, rect.y)

    l = SkinVList(f)
    l.SetHeights([20,20,35,18] * 130)
    l.SetDrawCallback(draw)
    f.Show()
    a.MainLoop()

if __name__ == '__main__':
    main()