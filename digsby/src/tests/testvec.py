from util import vector

if __name__ == '__main__':
    v = vector
    assert v(1,2) + v(2,3) == v(3,5)
    assert v(5,4) - v(3,2) == v(2,2)
    assert -v(3,3) == v(-3,-3)
    assert v(5,0).length == 5
    assert v(0,4).length == 4
    assert (v(3,0) - v(0,4)).length == 5
    assert v(4,0).to(v(0,3)) == 5
    assert v(3,4) * 2 == v(6,8)
    assert v(6,6).div(2) == v(3,3)
    assert v(0,5).normal == v(0,1)
    assert(v(1,1).angle == 45.0)

    vs = []

    import wx
    a = wx.PySimpleApp()
    f = wx.Frame(None)

    origin = v(400, 400)

    def paint(e):
        dc = wx.PaintDC(f)
        dc.Font = default_font()
        for v in vs:
            dc.DrawLine(*(tuple(origin) + tuple(v)))
            dc.DrawText('%s: %s' % ((v-origin), (v-origin).angle), *tuple(v))

    def click(e):
        p = v(e.Position)
        vs.append(p)
        f.Refresh()


    f.Bind(wx.EVT_PAINT, paint)
    f.Bind(wx.EVT_LEFT_DOWN, click)

    f.Show()
    a.MainLoop()



