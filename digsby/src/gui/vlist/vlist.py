from gui.skin.skinparse import makeBrush
import random
import wx
from wx import Rect, RectPS



class VList(wx.ScrolledWindow):
    'A smooth scrolling VListBox.'

    def __init__(self, parent, id = -1, style = wx.NO_BORDER | wx.FULL_REPAINT_ON_RESIZE,
                 multiple = False, # multiple selection
                 ):

        wx.ScrolledWindow.__init__(self, parent, style = style)

        if not isinstance(multiple, bool):
            raise TypeError('multiple argument must be a bool')

        self._selection = set()
        self.visible    = list()
        self.multiple   = multiple

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        Bind = self.Bind
        Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        Bind(wx.EVT_PAINT,            self.__paint)
        Bind(wx.EVT_MOUSEWHEEL,       self.__wheel)
        Bind(wx.EVT_KEY_DOWN,         self.__keydown)
        Bind(wx.EVT_LEFT_DOWN,        self.__leftdown)
        Bind(wx.EVT_LEFT_DCLICK,      self.__leftdclick)


    def SetBackground(self, background_brush):
        self.bg = background_brush


        s = background_brush.ytile
        self.EnableScrolling(s, s)

    def GetBackground(self):
        return self.bg

    Background = property(GetBackground, SetBackground)


    def RefreshLine(self, line):
        vis = dict((n, (y1, y2)) for y1, y2, n in self.visible)

        if line in vis:
            left, top, right, bottom = self.GetItemMargins()
            w = self.ClientSize.width
            y = self.ViewStart[1]

            y1, y2 = vis[line]

            r = wx.Rect(0, y1 - top - y, w, 0)
            r.SetHeight(y2-y1 + top + bottom)

            self.RefreshRect(r, False)


    def RefreshLines(self, lines):
        vis = dict((n, (y1, y2)) for y1, y2, n in self.visible)
        left, top, right, bottom = self.GetItemMargins()
        w = self.ClientSize.width
        y = self.ViewStart[1]

        for line in lines:
            if line in vis:
                y1, y2 = vis[line]

                r = wx.Rect(0, y1 - top - y, w, 0)
                r.SetHeight(y2-y1 + top + bottom)

                self.RefreshRect(r, False)

    def RefreshAll(self):
        return self.Refresh()

    def ScrollToLine(self, i):
        pass

    def UpdateScrollbars(self):
        margins     = self.GetItemMargins()
        totalHeight = sum(self.OnMeasureItem(n)
                          for n in xrange(self._itemcount))

        self.SetScrollbars(0, 1, 0,
                           (margins[1] + margins[3]) * self._itemcount +
                           totalHeight)

    def HitTest(self, (x, y)):
        '''
        Return the item at the specified (in physical coordinates) position or
        wxNOT_FOUND if none, i.e. if it is below the last item.
        '''

        p = wx.Point(x, y) + self.ViewStart

        for y1, y2, n in self.visible:
            if p.y >= y1 and p.y < y2:
                return n

        return wx.NOT_FOUND

    def GetSelection(self):
        if self.multiple:
            return self._selection
        else:
            try:
                return list(self._selection)[0]
            except IndexError:
                return -1


    def SetSelection(self, newsel):
        if self.multiple:
            assert False
        else:
            if not isinstance(newsel, int):
                raise TypeError('single selection lists take an integer argument to SetSelection')

            oldsel = self._selection
            self._selection = set([newsel])

            s = self._selection.union(oldsel)
            self.RefreshLines(min(s), max(s))

    Selection = property(GetSelection, SetSelection)

    def GetFirstVisibleLine(self):
        try:
            return self.visible[0][-1]
        except IndexError:
            return -1

    def GetLastVisibleLine(self):
        try:
            return self.visible[-1][-1]
        except IndexError:
            return -1

    def IsSelected(self, n):
        return n in self._selection

    def __wheel(self, e):
        self.Scroll(0, self.ViewStart[1] - e.WheelRotation)

    def __keydown(self, e):
        c   = e.KeyCode
        sel = self._selection

        if c == wx.WXK_DOWN:
            try: s = sel.pop()
            except KeyError: s = -1 # this is random and broken

            if s + 1 == len(self): s = -1
            self._selection = set([s + 1])
        elif c == wx.WXK_UP:
            try: s = sel.pop()
            except KeyError: s = -1 # this is random and broken

            if s == 0: s = -1
            self._selection = set([s - 1] if s != -1 else [len(self) - 1])
        else:
            return e.Skip()

        # update lines which were and are selected
        s = self._selection.union(sel)
        self.RefreshLines(min(s), max(s))

    def __paint(self, e):
        dc        = wx.AutoBufferedPaintDC(self, style = wx.BUFFER_VIRTUAL_AREA)
        size      = self.ClientSize
        viewstartx, viewstarty = self.ViewStart
        viewend   = viewstarty + size[1]
        #region    = self.GetUpdateRegion()
        #regioniter = wx.RegionIterator(region)
        #while regioniter:
        #    print regioniter.Next()

        self.bg.Draw(dc, RectPS((viewstartx, viewstarty), size))

        #wxRegionIterator upd(GetUpdateRegion()); // get the update rect list

        left, top, right, bottom = self.GetItemMargins()

        r = Rect(left, top, *size)
        r.SetSize((r.Width - right, 0))

        visible = self.visible
        visappend = visible.append
        del visible[:]
        selection = self._selection
        measureitem, drawitem, drawbg  = self.OnMeasureItem, self.OnDrawItem, self.OnDrawBackground
        offset    = r.Offset

        for n in xrange(self._itemcount):
            itemHeight = measureitem(n)

            if r.Y > viewend:
                break
            if r.Y + itemHeight >= viewstarty:# and region.IntersectRect(wx.Rect(r.X, r.Y + viewstarty, r.Width, r.Height)):
                r.Height = itemHeight
                visappend((r.Y - top, r.Y + r.Height + bottom, n))

                drawbg(dc, Rect(*r), n, n in selection)
                drawitem(dc, Rect(*r), n, n in selection)

            offset((0, itemHeight + top + bottom))

    def _ensure_visible(self, line):

        for top, bottom, n in self.visible:
            if n == line:
                return


    def __leftdown(self, e):
        i   = self.HitTest(e.Position)
        cmd = e.CmdDown()
        sel = self._selection

        if set([i]) != sel:
            try:
                old = self._selection.pop()
            except KeyError:
                self._selection.add(i)
                self.RefreshLine(i)
            else:
                self._selection.add(i)
                s = [old, i]
                self.RefreshLines(min(s), max(s))

    def __leftdclick(self, e):
        evt = wx.CommandEvent(wx.wxEVT_COMMAND_LISTBOX_DOUBLECLICKED, self.Id)
        evt.SetEventObject(self)
        evt.SetInt(self.HitTest(e.Position))

        self.ProcessEvent(evt)

    @property
    def NativeScrollbars(self):
        return True

    def GetItemMargins(self):
        return (0, 0, 0, 0)

    def SetItemCount(self, n):
        self._itemcount = n
        self.UpdateScrollbars()

    def GetItemCount(self):
        return self._itemcount

    __len__ = GetItemCount

    ItemCount = property(GetItemCount, SetItemCount)

    def OnDrawBackground(self, dc, rect, n, selected):
        if selected: dc.Brush = wx.BLUE_BRUSH
        else:        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)

class BList(VList):

    def __init__(self, parent):
        VList.__init__(self, parent)

        self.itembg = makeBrush('white 40% white 40%')
        self.selbg = makeBrush('white 90% white 90%')

    def OnMeasureItem(self, n):
        random.seed(n)
        return random.randint(15, 80)

    def OnDrawItem(self, dc, rect, n, selected):
        if not selected:
            self.itembg.Draw(dc, rect, n)
        else:
            self.selbg.Draw(dc, rect, n)


        dc.Font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        dc.DrawText('item %d' % n, rect.X, rect.Y)


    def GetItemMargins(self):
        return (3, 3, 3, 20)

if __name__ == '__main__':

    a = wx.PySimpleApp()
    f = wx.Frame(None, size = (240, 650))

    v = BList(f)

    v.SetItemCount(65)

    f.Show()
    a.MainLoop()

