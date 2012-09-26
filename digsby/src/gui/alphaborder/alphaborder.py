import wx
from wx import Point, Size, TOP, BOTTOM, LEFT, RIGHT, Frame, RectPS, Rect
from gui.windowfx import resize_smoothly, move_smoothly, setalpha

from cgui import AlphaBorder, BorderedFrame, fadein, fadeout
from gui.toolbox import Monitor
from wx import FindWindowAtPointer
from operator import attrgetter
from gui import skin
from util.primitives.funcs import Delegate
from util.primitives.mapping import Storage as S

def main2():
    from tests.testapp import testapp
    a = testapp('../../..')

    frames = [wx.Frame(None, -1, 'test %d' % c) for c in xrange(5)]

    stack = PopupStack(1, BOTTOM | LEFT)
    stack.Add(frames[0])


def main():
    from tests.testapp import testapp
    a = testapp('../../..')
    from gui.skin.skinparse import makeImage

    b = makeImage('popupshadow.png 12 12 25 25')
    #slices = (12, 12, 25, 25)

    f = Popup(b)

    def onbutton(e):
        #f.Fit()
        f2 = Popup(b)
        f2.Size = (300, 100)
        f2.DesiredSize = Size(300, 100)
        stack.Add(f2)

    f.button.Bind(wx.EVT_BUTTON, onbutton)

    stack = PopupStack(1, BOTTOM | LEFT)
    f.DesiredSize = Size(300, 100)
    stack.Add(f)

    ctrl = wx.Frame(None)
    #slider = wx.Slider(ctrl, value = 255, minValue = 0, maxValue = 255)
    #def onslide(e):
    #    setalpha(f, slider.Value)
    #    f.border.Refresh()

        #f.SetTransparent(slider.Value)
    #slider.Bind(wx.EVT_SLIDER, onslide)
    ctrl.Show()

    a.MainLoop()

if __name__ == '__main__':
    main()
