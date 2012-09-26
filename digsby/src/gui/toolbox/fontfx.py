import wx


__all__ = ['default_colors']

make_default_colors = lambda: [wx.BLACK, wx.Colour(190, 190, 190)]

class foo(list):
    def __getitem__(self, item):
        globals()['default_colors'] = make_default_colors()
        return globals()['default_colors'][item]

    def __getattr__(self, attr):
        globals()['default_colors'] = make_default_colors()
        return getattr(globals()['default_colors'], attr)

default_colors = foo()

def DrawTextFX(dc, text, x, y, colors = default_colors, spacing = 1):
    l = len(colors)
    p = wx.Point(x, y) + (spacing * l, spacing * l)
    offset = (spacing, spacing)

    for color in reversed(colors):
        dc.SetTextForeground(color)
        dc.DrawText(text, *p)
        p = p - offset

wx.DC.DrawTextFX = DrawTextFX

if __name__ == '__main__':
    a = default_colors
    ap = wx.App()
    bar = a[0]
    b = default_colors
    assert a is not b
    assert bar == wx.BLACK
