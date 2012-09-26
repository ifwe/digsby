import wx
from gui import skin
from gui.uberwidgets import UberWidget
from util.primitives.funcs import do

class SizerBar(wx.Panel, UberWidget):
    """
    A nifty liddle bar that can be droped between two objects in a boxsizer
    and resize them.
    at least one of them must not be must be manualy sized in the relevent direction
    """
    def __init__(self, parent, item, sizer = None):
        """
        item - the object on the left or top
        """
        wx.Panel.__init__(self, parent, style=0)

        events=[(wx.EVT_PAINT, self.OnPaint),
                (wx.EVT_ERASE_BACKGROUND, lambda e:None),
                (wx.EVT_LEFT_DOWN, self.OnLDown),
                (wx.EVT_LEFT_UP,self.OnLUp),
                (wx.EVT_MOTION,self.OnDrag),
                (wx.EVT_SIZE,self.OnSize),
                (wx.EVT_IDLE,self.OnIdle),
                (wx.EVT_LEAVE_WINDOW,lambda e: self.Refresh()),
                (wx.EVT_ENTER_WINDOW,lambda e: self.Refresh())]

        do(self.Bind(event, method) for (event,method) in events)

        self.dpoint = 0
        self.delta  = None
        self.item   = item
        self.itemminsize = wx.Size(max(item.MinSize.width, 0), max(item.MinSize.height, 0))

        def NewSetMinSize(size):
            self.itemminsize=wx.Size(self.itemminsize.width if size[0]==-1 else size[0],self.itemminsize.height if size[1]==-1 else size[1])
            if self.item.OldMinSize<self.itemminsize: self.item.OldMinSize=self.itemminsize

        def NewGetMinSize():
            return self.itemminsize

        item.OldSetMinSize=item.SetMinSize
        item.OldGetMinSize=item.GetMinSize
        item.OldMinSize=item.MinSize

        item.SetMinSize=NewSetMinSize
        item.GetMinSize=NewGetMinSize
        item.__dict__['MinSize']=property(item.GetMinSize,item.SetMinSize)

        self.sizer = sizer or self.Parent.Sizer
        self.orientation = self.sizer.Orientation

        self.SetSkinKey('VerticalSizerBar'
                        if self.orientation == wx.VERTICAL else
                        'HorizontalSizerBar',
                        True)

        self.OnSize()
        self.sizer.Layout()

    def UpdateSkin(self):
        key = self.skinkey
        s = lambda k, default = sentinel: skin.get('%s.%s' % (key, k), default)

        self.thickness = s('Thickness', 4)
        self.icon      = s('Icon',      None)
        self.normalbg  = s('Backgrounds.Normal')
        self.hoverbg   = s('Backgrounds.Hover',  lambda: self.normalbg)
        self.activebg  = s('Backgrounds.Active', lambda: self.hoverbg)

    def OnSize(self, event=None):
        """
        when the size of the bar is changed, switches orientation if necissary
        """
        self.orientation = self.sizer.Orientation

        if self.orientation == wx.HORIZONTAL:
            self.Cursor  = wx.StockCursor(wx.CURSOR_SIZEWE)
            self.MinSize = (self.thickness,-1)
        else:
            self.Cursor  = wx.StockCursor(wx.CURSOR_SIZENS)
            self.MinSize = (-1,self.thickness)

        self.sizer.Layout()

        self.Refresh()

    def OnPaint(self,event):
        dc      = wx.AutoBufferedPaintDC(self)
        s, icon = self.Size, self.icon
        rect    = wx.RectS(s)

        if self.dpoint:
            self.activebg.Draw(dc, rect)
        elif wx.FindWindowAtPointer() is self:
            self.hoverbg.Draw(dc, rect)
        else:
            self.normalbg.Draw(dc, rect)

        if icon:
            dc.DrawBitmap(icon, (s.width - icon.Width)/2, (s.height - icon.Height)/2, True)

    def OnLDown(self,event):
        'Captures the mouse when clicked.'

        self.dpoint = event.Position
        self.CaptureMouse()
        self.Refresh()

    def OnLUp(self, event):
        'Release mouse stuff.'

        self.dpoint = 0
        if self.HasCapture():
            self.ReleaseMouse()
        self.Refresh()

    def OnDrag(self, event):
        'Notifies resizes the object(s) when the bar is dragged.'

        if event.Dragging() and event.LeftIsDown() and self.dpoint:
            cpoint=event.GetPosition()
            self.delta=None
            if self.orientation==wx.HORIZONTAL and self.dpoint.x!=cpoint.x:
                self.delta=wx.Point(cpoint.x-self.dpoint.x,0)
            elif self.orientation==wx.VERTICAL and self.dpoint.y!=cpoint.y:
                self.delta=wx.Point(0,cpoint.y-self.dpoint.y)

    def OnIdle(self,event):
        'Calls resize if necissary while the aplication is idle.'

        event.Skip()
        if self.delta: self.Resize()

    def Resize(self):
        'Resizes the object the bar was assigned.'

        item = self.item

        if item.IsShownOnScreen():
            if self.orientation==wx.HORIZONTAL:
                itemsize  = item.MinSize.width
                itemlimit = self.sizer.Size.width - self.sizer.MinSize.width+itemsize
                itemminsize = self.itemminsize.width
                maxsizesize = wx.Size(itemlimit,-1)
                minsizesize = wx.Size(itemminsize,-1)
                d=0
            else:
                itemsize = item.MinSize.height
                itemlimit = self.sizer.Size.height-self.sizer.MinSize.height+itemsize
                itemminsize = self.itemminsize.height
                maxsizesize = wx.Size(-1,itemlimit)
                minsizesize = wx.Size(-1,itemminsize)
                d=1

            if (self.orientation == wx.HORIZONTAL and self.Position.x < item.Position.x) or (self.orientation==wx.VERTICAL and self.Position.y < item.Position.y):
                self.delta = wx.Point(-self.delta.x, -self.delta.y)

            if item and self.delta.x != 0 or self.delta.y != 0:
                newsize = item.Size + self.delta.Get()
                item.Size = item.MinSize = minsizesize if newsize[d] < itemminsize else \
                    maxsizesize if newsize[d] > itemlimit else \
                    newsize

                self.sizer.Layout()

            #self.Parent.Refresh()
            self.delta = None
