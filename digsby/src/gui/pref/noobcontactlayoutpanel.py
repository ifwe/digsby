import wx
from cgui import SimplePanel
from gui.pref.prefcontrols import mark_pref,get_pref

class NoobContactLayoutPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self,parent)
        self.links = parent.links
        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.grid = wx.FlexGridSizer(2,3)
        self.grid.AddGrowableRow(1,1)
        self.Sizer.Add(self.grid,0,wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER_HORIZONTAL)

        from gui import skin
        g=skin.get

        icons = g('AppDefaults.ez.icons')

        items = self.items =[
            LayoutItem(self, icons.one, dict(show_extra = True,
                                             extra_info = 'both',

                                             show_buddy_icon = True,
                                             buddy_icon_pos  = 'left',
                                             buddy_icon_size = 32,

                                             show_status_icon = True,
                                             status_icon_pos = 'bleft',

                                             show_service_icon = True,
                                             service_icon_pos = 'bright'
                                         )),

            LayoutItem(self, icons.two, dict(show_extra = True,
                                             extra_info = 'both',

                                             show_buddy_icon = True,
                                             buddy_icon_pos  = 'right',
                                             buddy_icon_size = 32,

                                             show_status_icon = True,
                                             status_icon_pos  = 'bleft',

                                             show_service_icon = True,
                                             service_icon_pos  = 'bright'
                                         )),

            LayoutItem(self, icons.three, dict(show_extra = True,
                                               extra_info = 'both',

                                               show_buddy_icon = True,
                                               buddy_icon_pos  = 'right',
                                               buddy_icon_size = 32,

                                               show_status_icon = True,
                                               status_icon_pos  = 'left',

                                               show_service_icon = True,
                                               service_icon_pos = 'bright'
                                         )),

            LayoutItem(self, icons.four, dict(show_extra = True,
                                              extra_info = 'idle',

                                              show_buddy_icon = False,

                                              show_status_icon = True,
                                              status_icon_pos  = 'right',

                                              show_service_icon = True,
                                              service_icon_pos = 'left'
                                         )),

            LayoutItem(self, icons.five, dict(show_extra = True,
                                              extra_info = 'idle',

                                              show_buddy_icon = False,

                                              show_status_icon = True,
                                              status_icon_pos  = 'left',

                                              show_service_icon = True,
                                              service_icon_pos  = 'right'
                                        )),

            LayoutItem(self, icons.six,  dict(show_extra = True,
                                              extra_info = 'idle',

                                              show_buddy_icon = False,

                                              show_status_icon = True,
                                              status_icon_pos = 'left',

                                              show_service_icon = False,
                                        ))
        ]

        self.grid.AddMany([(item, 0) for item in items])
        self.selection = None

        for item in items:
            for key in item.prefdict:
                if item.prefdict[key] != get_pref('buddylist.layout.%s'%key):
                    break
            else:
                self.SetSelection(item)
                break
#
#        lastselection = get_pref('buddylist.layout.ez_layout_selection',-1)
#        if lastselection != -1:
#            self.SetSelection(lastselection)

    def SetSelection(self,item):

#        if isinstance(item,int):
#            newselection = self.items[item]
#        else:
        newselection = item

        print newselection

        oldselection = self.selection
        if oldselection:
            oldselection.selected = False
            oldselection.Refresh()

        self.selection = newselection

        newselection.selected = True

        self.Refresh()

#        i = self.items.index(newselection)
#
#        mark_pref('buddylist.layout.ez_layout_selection',i)

        from peak.events import trellis
        @trellis.modifier
        def update():
            links = self.links
            for key in newselection.prefdict:
                if key in links:
                    links[key].value = newselection.prefdict[key]
                else:
                    value = newselection.prefdict[key]
                    mark_pref('buddylist.layout.%s'%key,value)
        update()

class LayoutItem(SimplePanel):
    def __init__(self,parent, bitmap, prefdict):
        SimplePanel.__init__(self,parent,wx.FULL_REPAINT_ON_RESIZE)

        self.prefdict=prefdict
        self.bitmap = bitmap
        self.MinSize = self.bitmap.Size + (16,16)

        self.selected = False

        self.Bind(wx.EVT_PAINT,self.OnPaint)
        self.Bind(wx.EVT_MOTION,lambda e: self.Refresh())
        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnMouseLeave)
        self.Bind(wx.EVT_LEFT_DOWN,self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP,self.OnLeftUp)

    def OnPaint(self,event):
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)

        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN
        dc.DrawRectangleRect(rect)

        if rect.Contains(self.ScreenToClient(wx.GetMousePosition())):
            dc.Brush = wx.Brush(wx.Color(238,239,255))
            dc.Pen   = wx.Pen(wx.Color(128,128,255))
            dc.DrawRoundedRectangleRect(rect,4)
            if wx.GetMouseState().LeftDown():
                rect2 = rect.Deflate(5,5)
                dc.Pen = wx.TRANSPARENT_PEN
                dc.Brush = wx.Brush(wx.Color(200,200,255))
                dc.DrawRectangleRect(rect2)

        if self.selected:
            rect2 = rect.Deflate(4,4)
            dc.Pen = wx.TRANSPARENT_PEN
            dc.Brush = wx.Brush(wx.Color(128,128,255))
            dc.DrawRectangleRect(rect2)

        dc.DrawBitmap(self.bitmap,8,8,True)

    def OnLeftUp(self,event):
        self.Parent.SetSelection(self)

    def OnLeftDown(self,event):

        self.Refresh()

    def OnMouseLeave(self,event):

        self.Refresh()
