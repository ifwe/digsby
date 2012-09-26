from wx import Rect, DCClipper, Brush, RectS, BufferedPaintDC
import wx
from logging import getLogger; log = getLogger('skinvlist')
from traceback import print_exc


class SkinVListBox(wx.VListBox):
    def __init__(self, parent, id = -1, style = 0):
        wx.VListBox.__init__(self, parent, id = id, style = style)
        self.Bind(wx.EVT_PAINT, self.paint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        self.Bind(wx.EVT_KEY_DOWN, self.__keydown)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.bg = None
        self._refreshOnScroll = False

    def GetItemY(self, i):
        measure = self.OnMeasureItem
        first   = self.GetFirstVisibleLine()
        last    = self.GetLastVisibleLine()

        if i >= 0 and i >= first and i <= last:
            try:
                return sum(measure(x) for x in xrange(first, i))
            except TypeError:
                pass

        return -1

    def SetBackground(self, background_brush):
        self.bg = background_brush

        if not background_brush.ytile and not self._refreshOnScroll:
            self._refreshOnScroll = True
            self.Bind(wx.EVT_SCROLLWIN, self._onScroll)
        elif background_brush.ytile and self._refreshOnScroll:
            self._refreshOnScroll = False
            self.Unbind(wx.EVT_SCROLLWIN)

    def _onScroll(self, e):
        e.Skip()
        self.RefreshAll()


    def GetBackground(self):
        return self.bg

    Background = property(GetBackground, SetBackground)

    def PaintMoreBackground(self, dc, rect):
        pass

    def __keydown(self, e):
        e.Skip()

        scrollPos = self.GetScrollPos(wx.VERTICAL)
        def later():
            if scrollPos != self.GetScrollPos(wx.VERTICAL):
                self.RefreshAll()

        wx.CallAfter(later)

    # please ignore the excessive "local variables" idiom used in the arguments
    # in this function until I move make this class native and move it to CGUI
    def paint(self, e):
        #
        # translation from C++ version in VListBox::OnPaint
        #


        clientSize = self.ClientSize
        dc = BufferedPaintDC(self)

        # the update rectangle
        rectUpdate = self.GetUpdateClientRect()

        # fill background
        crect = self.ClientRect

        if self.bg is not None:
            self.bg.Draw(dc, crect)
        else:
            dc.Brush = Brush(self.BackgroundColour)
            dc.Pen   = wx.TRANSPARENT_PEN #@UndefinedVariable
            dc.DrawRectangleRect(RectS(self.Size))

        self.PaintMoreBackground(dc, crect)

        # the bounding rectangle of the current line
        rectLine = Rect(0, 0, clientSize.x, 0)

        # iterate over all visible lines
        lineMax = self.GetVisibleEnd()
        lineh    = self.OnMeasureItem
        drawbg   = self.OnDrawBackground
        drawsep  = self.OnDrawSeparator
        drawitem = self.OnDrawItem
        margins  = self.GetMargins()

        for line in xrange(self.GetFirstVisibleLine(), lineMax):
            try:
                hLine = lineh(line)
            except TypeError:
                log.critical('self.OnMeasureItem was None, returning')
                del dc
                return

            rectLine.height = hLine

            # and draw the ones which intersect the update rect
            if rectLine.Intersects(rectUpdate):
                # don't allow drawing outside of the lines rectangle
                clip = DCClipper(dc, rectLine)
                rect = Rect(*rectLine)

                try:
                    drawbg(dc,  Rect(*rect), line)
                except Exception:
                    print_exc()

                try:
                    drawsep(dc, Rect(*rect), line)
                except Exception:
                    print_exc()

                rect.Deflate(margins.x, margins.y)

                try:
                    drawitem(dc, rect, line)
                except Exception:
                    print_exc()
                del clip

            else: # no intersection
                if rectLine.Top > rectUpdate.Bottom:
                    # we are already below the update rect, no need to continue
                    # further
                    break
                else: #the next line may intersect the update rect
                    pass

            rectLine.y += hLine

        return dc

    def _emit_lbox_selection(self, i):
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_LISTBOX_SELECTED, self.Id)
        evt.SetInt(i)
        self.AddPendingEvent(evt)

if __name__ == '__main__':

    class MyList(SkinVListBox):
        def __init__(self, parent):
            SkinVListBox.__init__(self, parent)

        def OnGetLineHeight(self, i):
            return 20

        def OnDrawItem(self, dc, rect, n):
            dc.SetBrush(wx.RED_BRUSH) #@UndefinedVariable
            dc.DrawRectangleRect(rect)

        def OnDrawBackground(self, dc, rect, n):

            pass


    a = wx.PySimpleApp()
    f = wx.Frame(None)

    l = MyList(f)
    l.SetItemCount(10)

    f.Show()
    a.MainLoop()
