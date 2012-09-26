import wx

def main():
    from tests.testapp import testapp

    with testapp():
        f = wx.Frame(None)
        def paint(e):
            i = 1
            dc = wx.PaintDC(e.GetEventObject())
#            dc.DrawSplines(((0, 0), (100, 5), (350, 200)))
            for _x in xrange(100000):
#                i = i + i
                dc.DrawSplines(((0, 0), (100, 5), (350, 200)))
#                dc.DrawLine(0, 0, 50, 50)
            import gc
            gc.collect()

        f.Bind(wx.EVT_PAINT, paint)
        f.Show()


if __name__ == '__main__':
    main()

