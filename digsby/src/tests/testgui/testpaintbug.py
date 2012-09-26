import wx

def main():
    a = wx.PySimpleApp()

    f = wx.Frame(None)


    class MyListBox(wx.VListBox):

        def OnDrawItem(self, dc, rect, n):
            dc = wx.PaintDC(f)
            dc.Brush = wx.WHITE_BRUSH
            dc.Pen = wx.TRANSPARENT_PEN


            dc.DrawRectangle(rect)
            dc.SetTextForeground(wx.BLACK)
            dc.DrawText('item %d' % n, rect.x + 5, rect.y + 3)

        def OnMeasureItem(self, n):
            return 20

    v = MyListBox(f)
    v.SetItemCount(50)

    f.Show()

    a.MainLoop()

if __name__ == '__main__':
    main()