import wx
from gui.skin.skinparse import makeImage
from gui import skin
from gui.skin.skinparse import makeImage, makeFont, makeBrush

def test_splitimage():
    f = wx.Frame(None, style = wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

    s = makeImage(skin.resourcedir() / 'digsbybig.png')#si4(S(source = 'c:\\digsbybig.png', center = {'extend': 'up down'},
        #      x1 = 30, x2 = -30, y1 = 30, y2 = -30))

    def paint(e):
        dc=  wx.AutoBufferedPaintDC(f)
        dc.Brush = wx.BLACK_BRUSH
        dc.DrawRectangleRect(f.ClientRect)
        s.Draw(dc, f.ClientRect)

    f.Bind(wx.EVT_PAINT, paint)
    f.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
    return f


def test_skinparsing():
    cols = 'AQUAMARINE, BLACK, BLUE, BLUE VIOLET, BROWN, CADET BLUE, CORAL, CORNFLOWER BLUE, CYAN, DARK GREY, DARK GREEN, DARK OLIVE GREEN, DARK ORCHID, DARK SLATE BLUE, DARK SLATE GREY DARK TURQUOISE, DIM GREY, FIREBRICK, FOREST GREEN, GOLD, GOLDENROD, GREY, GREEN, GREEN YELLOW, INDIAN RED, KHAKI, LIGHT BLUE, LIGHT GREY, LIGHT STEEL BLUE, LIME GREEN, MAGENTA, MAROON, MEDIUM AQUAMARINE, MEDIUM BLUE, MEDIUM FOREST GREEN, MEDIUM GOLDENROD, MEDIUM ORCHID, MEDIUM SEA GREEN, MEDIUM SLATE BLUE, MEDIUM SPRING GREEN, MEDIUM TURQUOISE, MEDIUM VIOLET RED, MIDNIGHT BLUE, NAVY, ORANGE, ORANGE RED, ORCHID, PALE GREEN, PINK, PLUM, PURPLE, RED, SALMON, SEA GREEN, SIENNA, SKY BLUE, SLATE BLUE, SPRING GREEN, STEEL BLUE, TAN, THISTLE, TURQUOISE, VIOLET, VIOLET RED, WHEAT, WHITE, YELLOW, YELLOW GREEN'
    cols = filter(lambda s: s.find(' ') == -1, cols.split(', '))

    import random
    random.shuffle(cols)

    f = wx.Frame(None, style = wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE)

    font  = makeFont("comic sans ms 35 bold italic underlined")
    popupshadow = 'popup.png 14 14 -18 -18'
    #bb = ['white border black', popupshadow, 'actions/bulb.png', 'actions/email.png']
    #bb = popupshadow
    bb = 'white border black'
    brush = makeBrush(bb)#'vertical red black 40% border dashed 5px')
    g     = [makeBrush('%s %s' % tuple(cols[c:c+2])) for c in xrange(0, len(cols)-2, 2)]
    #g = [makeBrush(c) for c in cols]

    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        dc.Pen = wx.TRANSPARENT_PEN
        dc.Brush = wx.Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DFACE))

        dc.DrawRectangleRect(f.ClientRect)
        dc.Font = font
        dc.SetTextForeground(wx.WHITE)

        r = f.ClientRect
        r.Deflate(17, 17)
        brush.Draw(dc, r)

        dc.DrawText('Digskin', 0, 0)

    f.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
    f.Bind(wx.EVT_PAINT, paint)


    f.Sizer = wx.BoxSizer(wx.HORIZONTAL)
    f.Sizer.AddStretchSpacer(1)
    return f

def main():
    from tests.testapp import testapp
    a = testapp()
    test_skinparsing().Show()
    a.MainLoop()

if __name__ == '__main__':
    main()
