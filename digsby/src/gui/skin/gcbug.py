import wx



if __name__ == '__main__':

    a = wx.PySimpleApp()
    f = wx.Frame(None)
    fix = False

    def drawrect(dc, x, y, round = False):
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.TRANSPARENT_PEN)

        w, h = 30, 30

        if round:
            dc.DrawRoundedRectangle(x, y, w, h, 5)
        else:
            dc.DrawRectangle(x, y, w, h)


    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        gc = wx.GraphicsContext.Create(dc)
        if fix: gc.Translate(-.5,-.5)

        dc.Brush = wx.BLACK_BRUSH
        dc.Pen   = wx.TRANSPARENT_PEN
        dc.DrawRectangleRect(wx.RectS(f.ClientSize))

        drawrect(dc, 10, 35)
        drawrect(gc, 40, 35)
        drawrect(dc, 70, 35, True)
        drawrect(gc, 100, 35, True)




    def button(e):
        global fix
        fix = not fix
        f.Refresh()


    f.Bind(wx.EVT_PAINT, paint)
    f.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)

    f.Sizer = wx.BoxSizer(wx.VERTICAL)
    b = wx.Button(f, -1, 'toggle fix')
    f.Sizer.Add(b)
    b.Bind(wx.EVT_BUTTON, button)






    f.Show()
    a.MainLoop()
