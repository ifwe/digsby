import wx
from gui.textutil import CopyFont, default_font
#from gui.toolbox import prnt

from wx import EXPAND,ALL,TOP,VERTICAL,ALIGN_CENTER_HORIZONTAL,ALIGN_CENTER_VERTICAL,LI_HORIZONTAL

ALIGN_CENTER = ALIGN_CENTER_HORIZONTAL|ALIGN_CENTER_VERTICAL
TOPLESS = ALL & ~TOP

bgcolors = [
    wx.Color(238, 238, 238),
    wx.Color(255, 255, 255),
]

hovbgcolor = wx.Color(220, 220, 220)

#def printlist(list):
#    prnt(list)

class VisualListEditorList(wx.VListBox):
    text_alignment = ALIGN_CENTER
    min_width = 150

    def __init__(self,
                 parent,
                 list2sort,
                 prettynames = None,
                 listcallback = None,
                 ischecked = None          # if given, a function of one argument that determines if an argument is checked
        ):

        wx.VListBox.__init__(self, parent)
        self.Font = default_font()
        self.item_height = self.Font.Height + 12

        self.oldlist = None
        self.prettynames = prettynames or {}
        self.listcallback = listcallback

        self.SetList(list2sort)
        self.setup_checkboxes(ischecked)
        self.BackgroundColour = wx.WHITE
        self._hovered = -1

        Bind = self.Bind
        Bind(wx.EVT_MOTION, self.OnMotion)
        Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        Bind(wx.EVT_PAINT,self.OnPaint)

    def CalcMinWidth(self):
        return self.min_width

    def SetList(self, seq):
        self.thelist = seq[:]
        self.SetItemCount(len(self.thelist))

        height = self.OnMeasureItem(0) * self.ItemCount
        self.SetMinSize(wx.Size(self.CalcMinWidth(), height))
        self.RefreshAll()

    def OnPaint(self,event):
        event.Skip()

        srect= wx.Rect(*self.Rect)
        srect.Inflate(1,1)
        pcdc = wx.ClientDC(self.Parent)
        pcdc.Brush = wx.TRANSPARENT_BRUSH

        pcdc.Pen   = wx.Pen(wx.Colour(213,213,213))

        pcdc.DrawRectangleRect(srect)

    def GetHovered(self):
        return self._hovered

    def GetItem(self, n):
        return self.thelist[n]

    def SetHovered(self,i):
        slist = self.thelist
        if i >= len(slist):
            return

        n = self._hovered
        self._hovered = i

        if n != -1:
            self.RefreshLine(n)

        if i != -1:
            self.RefreshLine(i)

    Hovered = property(GetHovered,SetHovered)

    def OnMeasureItem(self,n):
        return self.item_height

    def OnDrawBackground(self,dc,rect,n):
        dc.Brush = wx.Brush(hovbgcolor if self.Hovered == n else bgcolors[n % len(bgcolors)])
        dc.Pen = wx.TRANSPARENT_PEN

        dc.DrawRectangleRect(rect)

    def OnDrawItem(self,dc,rect,n):
        elem = self.thelist[n]
        
        self._draw_checkbox(dc, rect, n)

        if hasattr(self.prettynames, '__call__'):
            name = self.prettynames(elem)
        else:
            name = self.prettynames.get(self.thelist[n], _('(Unnamed Panel)'))

        dc.Font = self.Font
        dc.DrawLabel(name, rect, self.text_alignment)

    def OnMotion(self,event):
        rect = self.ClientRect
        wap = wx.FindWindowAtPointer()
        mp = event.Position
        hit = self.HitTest(mp)
        dragging = event.Dragging()
        selection = self.Selection
        thelist = self.thelist
        checked = self.checked

        if hit != -1:
            cursor = wx.CURSOR_ARROW if self._over_checkbox(mp, hit) else wx.CURSOR_HAND
            self.SetCursor(wx.StockCursor(cursor))

        if not dragging:
            if not rect.Contains(mp) or not wap == self:
                while self.HasCapture():
                    self.ReleaseMouse()

                self.Hovered = -1
                return

            elif not self.HasCapture():
                self.CaptureMouse()

        if dragging and -1 not in (selection, hit) and hit != selection:
            self.Selection = hit
            item =  thelist[selection]

            if checked is not None:
                item_checked = checked[selection]

            thelist.pop(selection)
            thelist.insert(hit, item)

            if checked is not None:
                checked.pop(selection)
                checked.insert(hit, item_checked)

            self.Refresh()

        self.Hovered = hit

    def OnLeftDown(self,event):
        mp = event.Position

        self.oldlist = list(self.thelist)
        hit = self.HitTest(mp)

        if hit != -1 and self._over_checkbox(mp, hit):
            self.checked[hit] = not self.checked[hit]
            self.listcallback(self.thelist, self.checked)
            self.Refresh()
        else:
            self.Selection = hit

    def OnLeftUp(self,event):
        if self.oldlist and self.oldlist != self.thelist and self.listcallback:
            if self.checked is not None:
                self.listcallback(self.thelist, self.checked)
            else:
                self.listcallback(self.thelist)

        self.Selection = -1
        self.oldlist = None

    #
    # checkbox support
    #
    
    def setup_checkboxes(self, ischecked):
        if ischecked is not None:
            self.checked = [ischecked(e) for e in self.thelist]
        else:
            self.checked = None

        self.checkbox_border = 5
        self.checkbox_size = 16
        self.checkbox_rect = wx.Rect(self.checkbox_border, (self.item_height - self.checkbox_size) / 2, self.checkbox_size, self.checkbox_size)
        
    def _draw_checkbox(self, dc, rect, n):
        if self.checked is None:
            return

        flag = wx.CONTROL_CHECKED if self.checked[n] else 0

        # draw a checkbox
        cbrect = wx.Rect(*self.checkbox_rect)
        cbrect.Offset((rect.x, rect.y))
        wx.RendererNative.Get().DrawCheckBox(self, dc, cbrect, flag)

        rect.x = rect.x + self.checkbox_size + self.checkbox_border * 2

    def _over_checkbox(self, mp, hit):
        if self.checked is None: return False
        hitmp = mp - (0, hit * self.item_height)
        return self.checkbox_rect.Contains(hitmp)

class VisualListEditorListWithLinks(VisualListEditorList):
    '''
    A "visual list editor" which draws clickable links on the right.

    Subclasses override LinksForRow(n), returning ("Link Text", link_func)
    where link_func is a callable taking one argument, the row's item.

    Subclasses should also call PaintLinks(dc, rect, n) in their EVT_PAINT
    handlers.
    '''
    link_padding = 5

    def LinksForRow(self, n):
        '''Overridden by subclasses'''
        return []

    def PaintLinks(self, dc, rect, n):
        '''Should be called by subclassess' EVT_PAINT handler.'''
        dc.Font = self.Font
        dc.TextForeground = wx.BLUE

        for (link_text, func), rect in self.LinkRectsForRow(n):
            rect.y += n * self.item_height
            dc.DrawLabel(link_text, rect, wx.ALIGN_CENTER_VERTICAL)

    def __init__(self, *a, **k):
        VisualListEditorList.__init__(self, *a, **k)
        self.Bind(wx.EVT_LEFT_DOWN, self.__leftdown)

    def __leftdown(self, e):
        mp = e.Position
        hit = self.HitTest(mp)
        link = self._link_hittest(mp, hit)
        if link:
            link_text, link_func = link
            return link_func(self.thelist[hit])
        
        e.Skip()

    def _link_hittest(self, mp, hit):
        if hit == -1: return
        mp = mp - (0, hit * self.item_height)

        for link, rect in self.LinkRectsForRow(hit):
            if rect.Contains(mp):
                return link

    def LinkRectsForRow(self, hit):
        links = self.LinksForRow(hit)
        dc = wx.ClientDC(self)
        dc.Font = self.Font

        # calculate link rects from the right.
        p = self.ClientRect.TopRight
        rects = []
        for link_text, func in reversed(links):
            w, h = dc.GetTextExtent(link_text)
            w += self.link_padding
            r = wx.Rect(p.x - w, p.y, w, self.item_height)
            rects.append(((link_text, func), r))
            p.x -= w

        rects.reverse() # restore left to right order.
        return rects

class VisualListEditor(wx.Dialog):
    dialog_style = wx.DEFAULT_DIALOG_STYLE | wx.FRAME_FLOAT_ON_PARENT

    def __init__(self, parent, list2sort, prettynames=None, listcallback=None,
                 title=_("Arrange Panels"),
                 listclass = VisualListEditorList,
                 ischecked = None):

        wx.Dialog.__init__(self, parent, -1, title, style = self.dialog_style)

        Bind = self.Bind
        Bind(wx.EVT_CLOSE, self.Done)

        # construct
        panel = wx.Panel(self)

        text = wx.StaticText(panel, -1, _('Drag and drop to reorder'), style = ALIGN_CENTER)
        text.Font = CopyFont(text.Font, weight=wx.BOLD)

        self.vle = vle = listclass(panel, list2sort, prettynames, listcallback, ischecked=ischecked)

        Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.vle.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        hline = wx.StaticLine(panel,style = LI_HORIZONTAL)

        done = wx.Button(panel,-1, _('Done'))
        done.Bind(wx.EVT_BUTTON,self.Done)

        # layout
        main_sizer = self.Sizer = wx.BoxSizer(VERTICAL)
        main_sizer.Add(panel, 1, EXPAND)
        s = panel.Sizer = wx.BoxSizer(VERTICAL)

        border_size = 6
        s.AddMany([(text,  0, EXPAND|ALL,     border_size),
                   (vle,   1, EXPAND|TOPLESS, border_size),
                   (hline, 0, EXPAND|TOPLESS, border_size),
                   (done,  0, EXPAND|TOPLESS, border_size)])
        self.Fit()

    def SetList(self, seq):
        return self.vle.SetList(seq)

    def Done(self, event):
        self.Hide()
        self.Destroy()

    def OnKeyDown(self, e):
        if e.KeyCode == wx.WXK_ESCAPE:
            self.Close()
        else:
            e.Skip()
