from __future__ import with_statement
from gui.toolbox import Monitor

import wx, sys
import math
import traceback
from wx import Bitmap, Rect, RectS, RectPS, GetMousePosition,  \
    MenuEvent, Point, VERTICAL, HORIZONTAL, Pen, Brush, \
    Size

from gui.skin.skinobjects import SkinColor,Margins
from gui.windowfx import fadein
from gui import skin
from util.primitives.funcs import do, Delegate
from common import pref
from gui.uberwidgets import UberWidget
from gui.textutil import GetTextWidth,default_font
from gui.windowfx import DrawSubMenuArrow, ApplySmokeAndMirrors

from logging import getLogger; log = getLogger('simplemenu')

class SMDTimer(wx.Timer):

    def __init__(self,menu):
        self.menu = menu
        wx.Timer.__init__(self)

    def Start(self,hitrect,*args,**kwargs):
        self.hitrect = hitrect
        self.args   = args
        self.kwargs = kwargs
        wx.Timer.Start(self, 500, True)

    def Notify(self):
        if not self.menu.Shown and self.hitrect.Contains(wx.GetMousePosition()):
            self.menu.Display(*self.args,**self.kwargs)

class RecapTimer(wx.Timer):
    "This timer tells the curent lowest level menu to recapture the mouse, along with it's parent tree "
    def __init__(self,target):
        wx.Timer.__init__(self)
        self.target=target
        self.Start(10)

    def Notify(self):

        target = self.target
        mp = target.Parent.ScreenToClient(wx.GetMousePosition())

        if (not target.Rect.Contains(mp) or target.ClientRect.Contains(mp)) and not wx.GetMouseState().LeftDown():
            self.Stop(target)

    def Stop(self,target):
        wx.Timer.Stop(self)
        target.Parent.CascadeCapture()
        del target.recaptimer

class SimpleMenuSpine(wx.VListBox, UberWidget):
    'This is the list handler for the menu.'

    def __init__(self, parent, skin):
        'Generic constructor'

        wx.VListBox.__init__(self,parent)
        UberWidget.__init__(self,'LISTBOX')

        self.MinSize = wx.Size(1, 1) #fix for small menus

        events = [
            (wx.EVT_PAINT,       self.OnPaint),
            (wx.EVT_MOUSEWHEEL,  self.OnMouseWheel),
            (wx.EVT_MOTION,      self.OnMouseMove),
            (wx.EVT_LEFT_UP,     self.OnLUp),
            (wx.EVT_LEFT_DOWN,   self.OnLDown),
            (wx.EVT_RIGHT_DOWN,  self.OnLDown),
            (wx.EVT_MIDDLE_DOWN, self.OnLDown),
            (wx.EVT_LEFT_DCLICK, lambda e:None),
            (wx.EVT_SCROLLWIN,   self.OnScroll),
            (wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)
        ]
        do(self.Bind(event, method) for (event, method) in events)

        #TODO: soft code this
        self.itemheight = 20

        self.items = []
        self.ItemCount = len(self.items)

        self.SetSkinKey(skin,True)

    def OnMouseCaptureLost(self, e):
        self.Parent.CloseRoot()

    def UpdateSkin(self):
        key = self.skinkey

        self.native = native = not key
        if native:
            self.OpenNativeTheme()

            self.padding = wx.Point(2,2)

            self.framesize  = Margins([1,1,1,1])#[0,0,0,0] if uxthemed else

            sz = self.Parent.Sizer
            if sz:
                sz.Detach(1)
                sz.Detach(1)
                sz.Add(wx.Size(self.framesize.left,self.framesize.top),(0,0))
                sz.Add(wx.Size(self.framesize.right,self.framesize.bottom),(2,2))

            self.framebg = None
            self.menubg  = None
            self.itembg  = None
            self.selbg   = None

            self.Font    = default_font()

            self.normalfc = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            self.selfc    = wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)

            self.MakeNativeSubmenuIcons()

            self.separator   = None

        else:

            self.CloseNativeTheme()

            s = lambda k, default: skin.get('%s.%s' % (key,k), default)

            self.padding = s('padding', wx.Point(2,2))

            self.framesize  = s('framesize',Margins([0,0,0,0]))

            sz = self.Parent.Sizer
            if sz:
                sz.Detach(1)
                sz.Detach(1)
                sz.Add(wx.Size(self.framesize.left,self.framesize.top),(0,0))
                sz.Add(wx.Size(self.framesize.right,self.framesize.bottom),(2,2))

            self.framebg = s('frame', lambda: SkinColor(wx.BLACK))
            self.menubg  = s('backgrounds.menu',  None)
            self.itembg  = s('backgrounds.item',  None)
            self.selbg   = s('backgrounds.selection', None)

            self.Font    = s('font', default_font())

            self.normalfc = s('fontcolors.normal',    lambda: wx.BLACK)
            self.selfc    = s('fontcolors.selection', lambda: wx.BLACK)


            #TODO: Default?
            submenuicon = self.submenuicon = s('submenuicon', None)
            if submenuicon is None:
                self.MakeNativeSubmenuIcons()
            else:
                self.submenuiconhot = s('submenuiconhover', submenuicon)

            #TODO: Default?
            self.separator   = s('separatorimage',None)

        for item in self.items:
            if item.menu:
                item.menu.spine.SetSkinKey(key)


    def MakeNativeSubmenuIcons(self):
        arrowmask = wx.EmptyBitmap(10,10)
        mdc = wx.MemoryDC()
        mdc.SelectObject(arrowmask)

        from gui.windowfx import controls
        arect = wx.Rect(0,0,10,10)
        DrawSubMenuArrow(mdc,arect)
        mdc.SelectObject(wx.NullBitmap)

        mdc2 = wx.MemoryDC()
        for s in xrange(2):
            acolor = self.selfc if s else self.normalfc
            arrow = wx.EmptyBitmap(10,10)
            arrow.SetMask(wx.Mask(arrowmask,wx.WHITE))
            mdc2.SelectObject(arrow)
            mdc2.Brush = wx.Brush(acolor)
            mdc2.FloodFill(0,0,wx.BLACK)
            mdc2.SelectObject(wx.NullBitmap)
            if s:
                self.submenuiconhot = arrow
            else:
                self.submenuicon = arrow#wx.Mask(arrowmask,wx.WHITE)#

    def DrawNativeBackgroundFallback(self,dc,part,state,unusedrect):

        rect = wx.RectS(self.Size)

        dc.Brush = Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
        dc.Pen   = wx.TRANSPARENT_PEN#wx.Pen(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWFRAME))
        dc.DrawRectangleRect(rect)

    def OnPaint(self,event):
        'Standard paint handling.'

        dc   = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.ClientSize)

        if self.menubg:
            self.menubg.Draw(dc, rect)
        else:
            dc.SetClippingRect(rect)
            nrect = wx.Rect(*rect)
            nrect.Inflate(1, 1)#wx.RectPS((-self.Rect.x,-self.Rect.y),self.Size)
            self.DrawNativeLike(dc,0,0,nrect,self.DrawNativeBackgroundFallback)
            dc.DestroyClippingRegion()

#            dc.Brush = wx.RED_BRUSH
#            dc.Pen = wx.TRANSPARENT_PEN
#            dc.DrawRectangleRect(rect)

        rect.Height = self.itemheight

        i, j = self.FirstVisibleLine, self.LastVisibleLine
        if j >= 0 and j != sys.maxint*2+1:
            bg, draw, measure = self.OnDrawBackground, self.OnDrawItem, self.OnMeasureItem
            for n in xrange(i, j + 1):
                bg(dc, rect, n)
                draw(dc, rect, n)
                rect.SetY(rect.GetY() + measure(n))

#    def DrawThemelessItemBG(self,dc,part,state,rect):
#
#        if state == 2:
#            dc.Brush = wx.Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
#            dc.Pen = wx.TRANSPARENT_PEN
#            dc.DrawRectangleRect(rect)

    def OnDrawBackground(self,dc,rect,n):
        'Draws the background for each item.'

        if self.native:
            if self.GetSelection() == n:
                dc.Brush = wx.Brush(wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
                dc.Pen = wx.TRANSPARENT_PEN
                dc.DrawRectangleRect(rect)
#            s = 3 if self.GetSelection() == n else 1
#                self.DrawNativeLike(dc,5,1,rect,self.DrawThemelessItemBG)
        else:
            if self.GetSelection() == n and self.selbg:
                self.selbg.Draw(dc, rect)
            elif self.itembg:
                self.itembg.Draw(dc, rect)

    def OnDrawItem(self,dc,rect,n):
        'Draws the foreground of each item.'

        curser  = Point(rect.x, rect.y) + (self.padding.x, 0)

        if self.items[n].id==-1:
            return self.DrawSeparator(dc, rect, n)

        if self.items[n].font:
            font = self.items[n].font
        else:
            font = self.Font

        dc.Font=font
        dc.TextForeground=(self.selfc if self.Selection==n else self.normalfc)

        if self.items[n].menu:
            dc.Brush=wx.BLACK_BRUSH
            dc.Pen=wx.TRANSPARENT_PEN
            smi=self.submenuiconhot if self.Selection==n else self.submenuicon

#            if isinstance(smi,wx.Mask):
#                acolor = self.selfc if self.Selection==n else self.normalfc
#                arrow = wx.EmptyBitmap(10,10)
#                arrow.SetMask(smi)
#                mdc2 = wx.MemoryDC()
#                mdc2.SelectObject(arrow)
#                mdc2.Brush = wx.Brush(acolor)
#                mdc2.FloodFill(0,0,wx.BLACK)
#                mdc2.SelectObject(wx.NullBitmap)
#                dc.DrawBitmap(arrow,rect.Width-self.padding.x-arrow.Width,rect.Y+(rect.Height/2)-arrow.Height/2,True)
#                endcap=arrow.Width+self.padding.x
#            else:
            dc.DrawBitmap(smi,rect.Width-self.padding.x-smi.Width,rect.Y+(rect.Height/2)-smi.Height/2,True)
            endcap=smi.Width+self.padding.x
        else:
            endcap=0

        padx   = self.padding.x
        txtext = dc.Font.Height
        txtext_pad = Point(txtext + padx, 0)

        for i in self.items[n].content:
            if type(i) is Bitmap:
                curser.y = rect.Y + (rect.height / 2 - i.Height / 2)
                imgpad = (self.bitmapwidth - i.Width)//2 if self.bitmapwidth else 0
                try:
                    dc.DrawBitmapPoint(i, (curser.x + imgpad, curser.y), True)
                except Exception:
                    traceback.print_exc_once()
                    try:
                        log.error("Failed drawing bitmap: %r", getattr(i, 'path', None))
                    except Exception:
                        pass
                curser += Point(max(self.bitmapwidth, i.Width) + padx, 0)
            elif isinstance(i, basestring):
                curser.y = rect.Y + (rect.height / 2 - txtext / 2)
                text_rect = RectPS(curser, Size(rect.width - curser.x - padx - endcap, txtext))
                dc.DrawTruncatedText(i, text_rect, alignment = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
                curser += txtext_pad

    def DrawSeparator(self, dc, rect, n):
        sepwidth  = rect.width - self.padding.x * 2

        if self.separator:
            sepheight = self.separator.Size.height
            seppos    = (self.padding.x, rect.y + rect.height // 2 - sepheight // 2)
            self.separator.Draw(dc, RectPS(seppos, (sepwidth, sepheight)))
        else:
            dc.Pen = Pen(self.normalfc, 1)
            seppos   = Point(self.padding.x, rect.y + rect.height // 2)
            endpos   = seppos + Point(sepwidth, 0)
            dc.DrawLinePoint(seppos, endpos)

    def OnMouseWheel(self, e):
        self.ScrollLines(-math.copysign(1, e.WheelRotation))

    def OnMouseMove(self,event):
        'Mouse over event handling.'

        mp    = self.ScreenToClient(GetMousePosition())
        items = self.items

        if self.ClientRect.Contains(mp):
            n = self.HitTest(mp)
            if self.Selection != n:
                do(item.menu.Show(False) for item in self.items if item.menu and item.menu.IsShown())
                if items[n].id != -1:
                    self.SetSelection(n)
                    if items[n].menu:
                        items[n].menu.DelayedDisplay(self.GetItemRect(n), self)
                else:
                    self.SetSelection(-1)
        elif self.Rect.Contains(mp):
            self.Parent.CascadeRelease()
            self.recaptimer = RecapTimer(self)
        else:
            self.SetSelection(-1)
            gp = self.GrandParent
            if isinstance(gp, SimpleMenu) and gp.CheckParentalContact(GetMousePosition()):
                gp.spine.AddPendingEvent(event)

    def OnLUp(self,event):
        """
        Release left mouse button handling
        """
        if self.GetClientRect().Contains(event.Position):
            n = self.HitTest(event.Position)
            if self.items[n].id != -1:
                item = self.items[n]
                if not item.menu:
                    self.TriggerItem(item)

    def TriggerItem(self,item):
        'Steps to take when a item is clicked.'

        if item.method is not None:
            wx.CallAfter(item.method, item)
        elif self.Parent.callback:
            wx.CallAfter(self.Parent.callback, item)
        else:
            menuevent = MenuEvent(wx.wxEVT_COMMAND_MENU_SELECTED, item.id)
            self.Parent.AddPendingEvent(menuevent)
        self.Parent.CloseRoot()

    def OnLDown(self,event):
        """
        Mouse down handling
        """
        if not self.Rect.Contains(event.Position) and not self.Parent.CheckParentalContact(wx.GetMousePosition(),True):
            self.Parent.CloseRoot()

    def OnScroll(self,event):
        'What to do when the window is scrolled.'

        self.Refresh()
        event.Skip()

    def CalcSize(self):
        'Calculates the size of the menu.'

        self.CalcItemHeight()
        if self.Parent.staticwidth:
            width = self.Parent.width
        else:
            self.CalcItemWidth()
            width = self.calcedwidth

        if not self.Parent.maxheight or self.ItemCount<self.Parent.maxheight:
            height = self.itemheight * self.ItemCount
        else:
            height = self.itemheight * self.Parent.maxheight

        maxwidth = self.Parent.maxwidth
        if maxwidth and width > maxwidth:
            width = maxwidth

        minwidth = self.Parent.minwidth
        if minwidth and width < minwidth:
            width = minwidth


        p = self.Parent.ScreenRect[:2]
#        self.MinSize = wx.Size(self.menuwidth-self.framesize.x, height)
        self.Parent.Rect = RectPS(p, wx.Size(width, height+self.framesize.y))
        #self.Parent.Size = (self.menuwidth+self.framesize.x, height+self.framesize.y)

    def CalcItemHeight(self):
        'Calculates tallest item.'
#        print 'SimpleMenu CalcItemHeight being ran too much, this is a reminder to create a simpler version for individual changes'

        hset = list(item.font.Height for item in self.items if item.font)
        hset.append(self.Font.Height)


        if max(hset)-min(hset)>10:

            hset = sorted(hset)
            lhset = len(hset)

            def Median(set):
                lset = len(set)
                if lset % 2:
                    m1=lset//2
                    m2=m1+1
                    return set[m1] + ((set[m2] - set[m1])//2)
                else:
                    return set[lset//2+1]

            q1      = Median(hset[:lhset//2])
            q3      = Median(hset[(lhset//2)+1:])
            iqr     = q3 - q1
            hi      = q3 + 1.5*iqr

            hset = set(h for h in hset if h < hi)

        self.bitmapwidth = bitmapwidth = 0
        for item in self.items:
            if item.id == -1:
                pass
            elif item.content and isinstance(item.content[0], Bitmap):
                bitmapwidth = max(bitmapwidth, item.content[0].Width)

            for object in item.content:
                if type(object) is Bitmap:
                    hset.append(object.Height)

        # keep track of the biggest bitmap on the left to align plain text
        # items
        if bitmapwidth:
            empty_bitmap = wx.EmptyBitmap(bitmapwidth, 1)
            for item in self.items:
                if item.id == -1:
                    pass
                elif item.content and isinstance(item.content[0], basestring):
                    item.content.insert(0, empty_bitmap)
            self.bitmapwidth = bitmapwidth

        h=max(hset)

#HACK: The following section of code is a hax to remove all fonts with extreme sizes
#-------------------------------------------------------------------------------
        for item in self.items:
            if item.font and item.font.Height>h:
                self.items.remove(item)
        self.ItemCount = len(self.items)
#-------------------------------------------------------------------------------

        self.itemheight = h+2*self.padding.y

    def CalcItemWidth(self):
        if not self.items:
            self.calcedwidth=0
        else:
            wset = set(item.GetContentWidth(self.Parent) for item in self.items)#set(GetTextWidth(item.GetContentAsString(),item.font or self.Font)+len(item.content)*self.padding.x for item in self.items)
            w = max(wset)
            w += self.framesize.x

            self.calcedwidth = w

    def OnMeasureItem( self, n ):
        'Returns item height.'

        return self.itemheight


    def GetSelectionRect(self):
        return self.GetItemRect(self.Selection)

    def GetItemRect(self,n):
        pos = self.ScreenRect.Position

        x = pos.x
        width= self.Size.x
        y = pos.y + sum(self.OnMeasureItem(i) for i in xrange(n))

        height=self.OnMeasureItem(n)

        return Rect(x,y,width,height)

class SimpleMenu(wx.PopupTransientWindow, UberWidget):
    '''
    This is the class for most menus throughout the codebase
    The use of this class should be deprecated and replaced by new menus based off the menu code located in gui.prototypes
    '''

    def __init__(self, parent, skinkey = 'simplemenu', maxheight = None, width = 0, minwidth = 0, maxwidth=0, callback = None):
        """
        items - Initial items - cut - was never used
        """

        wx.PopupTransientWindow.__init__(self, parent)

        self.BeforeDisplay = Delegate()
        Bind = self.Bind
        Bind(wx.EVT_PAINT,  self.OnPaint)
        Bind(wx.EVT_SIZE,   self.OnSize)
        Bind(wx.EVT_SHOW,   self.OnClose)
        Bind(wx.EVT_MENU,   self.PassEvent)

        self.maxheight = maxheight

        self.staticwidth = bool(width)
        self.width  = width

        self.maxwidth = maxwidth
        self.minwidth = minwidth

        self.spine = SimpleMenuSpine(self,skinkey)
        self.displaytimer=SMDTimer(self)

        s = self.Sizer = wx.GridBagSizer()
        s.SetEmptyCellSize(wx.Size(0, 0))
        s.Add(self.spine,(1, 1), flag = wx.EXPAND)
        s.Add(wx.Size(self.spine.framesize.left,self.spine.framesize.top),(0,0))
        s.Add(wx.Size(self.spine.framesize.right,self.spine.framesize.bottom),(2,2))
        s.AddGrowableCol(1, 1)
        s.AddGrowableRow(1, 1)

        self.callback = callback

        self.connected=None

    def SetSkinKey(self, key):
        """shortcut to spine.updateskin"""
        self.spine.SetSkinKey(key)

    def SetWidth(self,width):
        """Set the width of the menu in pixels"""

        self.staticwidth = True

        w=width

        if self.minwidth:
            w = max(w,self.minwidth)

        if self.maxwidth:
            w = min(w,self.maxwidth)

        self.width = w
        self.Size  = wx.Size(w,-1)

    def OnSize(self, event):
        event.Skip()

#        if hasattr(self.spine,'framebg'):
        background= self.spine.framebg
        from cgui import SplitImage4
        if isinstance(background,SplitImage4):
            ApplySmokeAndMirrors(self, background.GetBitmap(self.Size))
        else:
            ApplySmokeAndMirrors(self)

        self.Layout()

    def OnPaint(self,event):
        """Draws the background of the menu"""
        dc   = wx.PaintDC(self)
        rect = wx.RectS(self.Size)

        bg = self.spine.framebg
        if bg:
            bg.Draw(dc, rect)
        elif self.spine.native:
            dc.Brush = wx.TRANSPARENT_BRUSH
            dc.Pen = wx.Pen(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWFRAME))
            dc.DrawRectangleRect(rect)

            #self.DrawNativeLike(dc,0,0,rect)

    def GetIndex(self, item):
        try:
            return self.spine.items.index(item)
        except ValueError:
            return -1

    def Insert(self, index, *args, **kwargs):
        'Insert a new item into the menu.'

        self.InsertItem(index, SimpleMenuItem(*args, **kwargs))

    def Append(self, *args, **kwargs):
        'Appends a new item to the end of the menu.'

        self.AppendItem(SimpleMenuItem(*args, **kwargs))

    def InsertItem(self, index, item):
        'Insert an item to an index.'

        self.spine.items.insert(index,item)
        self.spine.ItemCount=len(self.spine.items)

    def AppendItem(self, item):
        'Adds an item to the end of the menu.'

        self.spine.items.append(item)
        self.spine.ItemCount = len(self.spine.items)

    def RemoveItem(self, item):
        'Remove the item provided from the menu.'

        sp = self.spine

        if isinstance(item, int):
            item = sp.items[item]

        sp.Selection=-1
        sp.items.remove(item)
        sp.ItemCount = len(self.spine.items)

    def RemoveAll(self):
        """
        removes all items from the menu
        """
        self.spine.items=[]
        self.spine.ItemCount=len(self.spine.items)

    def GetCount(self):
        'Returns the number of items in the menu.'

        return len(self.spine.items)

    Count = property(GetCount)

    __len__ = GetCount

    def SetSelection(self, selection): self.spine.Selection = selection
    def GetSelection(self): return self.spine.Selection

    Selection = property(GetSelection, SetSelection)

    def SetItems(self, items):
        'Set the menu to a list of items.'

        if wx.IsDestroyed(self):
            print >> sys.stderr, "WARNING: %r is destroyed" % self
            return

        with self.Frozen():

            sp = self.spine

            sp.items = items
            sp.ItemCount = len(items)

            if sp.IsShownOnScreen():
                sp.RefreshAll()

    def GetItem(self, index):
        return self.spine.items[index]

    def GetItems(self):
        return self.spine.items

    def GetItemIndex(self, item):
        return self.spine.items.index(item)

    def FindItemById(self, id):
        '''Returns a SimpleMenuItem with a matching id, or None.'''
        for item in self.spine.items:
            if item.id == id:
                return item

    def PassEvent(self,event):
        """
        A shortcut to self.Parent.AddPendingEvent(event) (Why?)
        """
        self.Parent.AddPendingEvent(event)

    def DelayedDisplay(self, rect, *args, **kwargs):
        if not self.displaytimer.IsRunning():
            self.displaytimer.Start(rect, *args, **kwargs)

    def Display(self, caller = None, funnle = True,funnlefullscreen=False):
        """
        Display the menu
        """

        self.BeforeDisplay()

        if not self.IsShown() and len(self):

            self.spine.CalcSize()

            if caller and isinstance(caller, SimpleMenuSpine):

                self.caller = None
                rect = caller.GetSelectionRect()

                position = Point(rect.x+rect.width,rect.y - self.spine.framesize.top)
                newrect  = RectPS(position, self.ScreenRect.Size)
                screenrect = Monitor.GetFromRect(newrect).Geometry

                if newrect.bottom > screenrect.bottom:
                    position.y=rect.y+rect.height-self.Size.height
                if newrect.right > screenrect.right:
                    position.x=rect.x-self.Size.width

            elif caller:
                self.caller = caller
                caller_rect = caller.ScreenRect
                position    = caller_rect.BottomLeft
                newrect     = RectPS(position, self.ScreenRect.Size)
                screenrect  = Monitor.GetFromWindow(caller).Geometry

                if newrect.bottom > screenrect.bottom:
                    position.y -= caller_rect.Height + self.spine.Size.height
                if newrect.right > screenrect.right:
                    position.x += caller_rect.Width - self.spine.Size.width

            else:
                self.caller = None
                position    = wx.GetMousePosition()
                newrect     = RectPS(position, self.ScreenRect.Size)
                screenrect  = Monitor.GetFromPoint(position).Geometry

                if newrect.bottom > screenrect.bottom:
                    position.y -= self.spine.Size.height
                if newrect.right > screenrect.right and pref('menus.shift_mode', False):
                    position.x -= self.spine.Size.width

            newrect = wx.RectPS(position,self.Size)
            screenrect = Monitor.GetFromRect(newrect).Geometry
            pos = screenrect.Clamp(newrect).Position if funnle else position
            self.SetRect(RectPS(pos, self.Size))

            self.spine.SetSelection(-1)

            fadein(self, 'xfast')
            self.spine.RefreshAll()

            if not self.spine.HasCapture():
                self.spine.CaptureMouse()

            wx.CallLater(10, self.Refresh)

            if not isinstance(caller, SimpleMenuSpine):
                self.TopConnect()

    def TopConnect(self):
        # Find the first TopLevelWindow owner of this menu
        # (popup menus are not isinstance(popup, wx.TopLevelWindow)
        t = self.Top
        while not isinstance(t, wx.TopLevelWindow):
            t = t.Parent.Top

        id = t.Id
        t.Connect(id, id, wx.wxEVT_ACTIVATE, self.OnActiveChange)
        self.connected=(t,id)

    def OnActiveChange(self,event):
        self.CloseRoot()

    def OnClose(self,event):
        """
        Handels hiding of submenus and deactivating caller if aplicable
        when the menu is closed
        """

        if not self.IsShown():
            do(item.menu.Show(False) for item in self.spine.items if item.menu and item.menu.IsShown())
            while self.spine.HasCapture():self.spine.ReleaseMouse()

            if self.caller:# and hasattr(self.caller,'Active'):
                event=wx.MenuEvent(wx.wxEVT_MENU_CLOSE,self.Id)
                self.caller.AddPendingEvent(event)
                self.caller = None

            if self.connected:
                window, id = self.connected
                window.Disconnect(id, id, wx.wxEVT_ACTIVATE)
                self.connected = None

    def CloseRoot(self):
        """
        Closes the root menu, that then handles closing of it's children
        """
        if isinstance(self.Parent,SimpleMenu):
            self.Parent.CloseRoot()
        else:
            self.Show(False)

    def __repr__(self):
        return '<SimpleMenu %r>' % self.spine.items

    def CheckParentalContact(self,pos,ignoresubmenu=False):
        """
        Checks if the mouse is inside one of the parent menus of this menu
        """
        rect = RectS(self.spine.Size)
        mp=self.spine.ScreenToClient(pos)
        if rect.Contains(mp) and (ignoresubmenu or not self.spine.items[self.spine.HitTest(mp)].menu or not self.spine.items[self.spine.HitTest(mp)].menu.IsShown()):
            return True
        if isinstance(self.Parent, SimpleMenu):
            return self.Parent.CheckParentalContact(pos, ignoresubmenu)
        return False

    def CascadeRelease(self):
        """
        All menus in hierarchy release the mouse
        """
        while self.spine.HasCapture():
            self.spine.ReleaseMouse()
        if isinstance(self.Parent,SimpleMenu):
            self.Parent.CascadeRelease()

    def CascadeCapture(self):
        """
        All menus in hierarchy capture the mouse
        """
        if isinstance(self.Parent,SimpleMenu):
            self.Parent.CascadeCapture()
        if not self.spine.HasCapture():
            self.spine.CaptureMouse()


class SimpleMenuItem(object):
    "Menu Item for the combo box"

    def __init__(self, content = '', method = None,
                 font = None, id = None, menu = None):
        """
        content - string or list of bitmaps and strings that are displayed as item lable
        method - methode exicuted when the item is slected
        id - unique ID number for the item, if left none is not generated, so
            if you need an id set it
        """

        assert isinstance(content,(basestring,list,)), 'content of type %s is not a string or list' % type(content)

        if content is not None:
            if isinstance(content, basestring):    # For strings, wrap in a list
                self.content = [content]
            elif isinstance(content,list):
                self.content = content
            else:
                raise TypeError
        else: self.content = []
        self.method = method
        self.menu   = menu
        self.font   = font

        self.id=id

    def __repr__(self):
        return '<SMItem %s>' % self.GetContentAsString()

    def __str__(self):
        return self.GetContentAsString()

    def __eq__(self, o):
        return isinstance(o, self.__class__) and self.content == o.content

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(id(self))

    def GetContentAsString(self):
        "Returns first string in this menu item's content, or an empty string."

        for thing in self.content:
            if isinstance(thing, basestring):
                return thing

        return ''

    def GetContentWidth(self,menu):
        if not menu:
            return None

        pad = menu.spine.padding
        font = self.font or menu.spine.Font
        cont = self.content

        count = len(cont)

        w = sum(GetTextWidth(s,font) for s in cont if isinstance(s,basestring))
        w += sum(b.Width for b in cont if type(b) is Bitmap)

        w += (count+1)*pad.x+1

        return w

    def SetLabel(self, label):
        '''Changes the first string item in self.content to the given label.'''

        for i, item in enumerate(self.content):
            if isinstance(item, basestring):
                self.content[i] = label
                return

