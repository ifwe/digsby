import wx, sys
from util.primitives.funcs import do, Delegate
from util.introspect import debug_property
from common import pref, profile, prefprop
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.UberEvents import TabNotifiedEvent
from gui.textutil import default_font
from gui.windowfx import ApplySmokeAndMirrors
from gui import skin
from gui.skin.skinobjects import Margins

from logging import getLogger; log = getLogger('tab')

from wx import EmptyBitmap, Size, ImageFromBitmap, \
    WHITE_BRUSH, TRANSPARENT_PEN, BitmapFromImage, BLACK, NullBitmap, \
    RectS, ClientDC, MemoryDC, Rect, PaintDC, BufferedPaintDC, \
    GetMousePosition, ALIGN_LEFT, ALIGN_CENTER_VERTICAL, GetTopLevelParent, Mask, Point


class MultiTab(object):
    """
        Used for generating a preview of multiple tabs, such as when a window
        is about to be merged with another window
    """
    def __init__(self, tabs):

        self.tabwidth  = max(tab.Size.width for tab in tabs)
        self.tabheight = tabs[0].Size.height
        self.Size      = Size(self.tabwidth + 14*len(tabs), self.tabheight + 14*len(tabs))

        self.tabs=tabs

    def OnPaint(self, otherdc, otherwindow):
        """
            Paints all tabs into the passed DC and a copy of the backgrounds
            into a Bitmap to geneate the SmokeAndMirrors for other window
        """
        size   = self.Size
        bitmap = EmptyBitmap(*size)
        mdc    = MemoryDC()
        tab    = self.tabs[0].states[self.tabs[0].mode][0].GetBitmap(Size(self.tabwidth,self.tabheight))#.Draw(mdc,rect)
        tab    = ImageFromBitmap(tab)
        tab.ConvertAlphaToMask()
        tab    = BitmapFromImage(tab)
        mdc.SelectObject(tab)
        mdc.Brush = WHITE_BRUSH
        mdc.Pen   = TRANSPARENT_PEN
        mdc.DrawRectangle(0, 0, self.tabwidth, self.tabheight)
        mdc.SelectObject(bitmap)

        for i, tabobj in enumerate(self.tabs):
            s = 14 * i
            rect = Rect(s, s, self.tabwidth, self.tabheight)
            mdc.DrawBitmap(tab, s, s, True)
            tabobj.OnPaint(forcedrect = rect, otherdc = otherdc)

        mdc.SelectObject(NullBitmap)
#        otherdc.DrawBitmap(bitmap,0,0,True)
        bitmap.SetMask(Mask(bitmap, BLACK))
        ApplySmokeAndMirrors(otherwindow, bitmap)


class NotifiedTimer(wx.Timer):
    """
        When a tab is in the notified state this handles blinking back and forth
        between the notified look and normal look
    """
    def __init__(self,tab):
        wx.Timer.__init__(self)
        self.drawnotified = False
        self.tab = tab
        self.click = 0

    def Start(self):
        self.click = 0

        if not self.IsRunning():
            wx.Timer.Start(self, pref('tabs.notify_duration', 1000))

    def Notify(self):
        """
            When triggered notifies so many times, then sets it permanently
            to notified
        """
        self.drawnotified = not self.drawnotified
        self.RefreshTab()
        self.click += 1

        if self.click >= pref('tabs.notify_count',10):
            self.drawnotified = True
            wx.Timer.Stop(self)

    def Stop(self):
        """Stops the timer."""

        self.drawnotified = False
        self.RefreshTab()
        wx.Timer.Stop(self)

    def RefreshTab(self):
        if not wx.IsDestroyed(self.tab):
            self.tab.Refresh()

from gui.uberwidgets import UberWidget
class Tab(wx.Window, UberWidget):
    """
    Tabs!!!
    """

    # tab states
    NORMAL = 0
    ACTIVE = 1
    HOVER  = 2
    ACTIVE_HOVER = 3
    NOTIFIED = 4

    def __init__(self, parent, page, _id = -1, skinkey = ''):
        wx.Window.__init__(self, parent, id=_id)
        self.Show(False)
        """
            icon - icon to place in corner of tab
        """
        self.events=[
            (wx.EVT_PAINT, self.OnPaint),
            (wx.EVT_ERASE_BACKGROUND, lambda e:None),
            (wx.EVT_ENTER_WINDOW, self.OnMouseEnter),
            (wx.EVT_LEAVE_WINDOW, self.OnMouseLeave),
            (wx.EVT_RIGHT_DOWN, self.OnRightDown),
            (wx.EVT_LEFT_DOWN, self.OnLeftDown),
            (wx.EVT_MIDDLE_UP, self.OnMidUp),
            (wx.EVT_LEFT_UP, self.OnLeftUp),
            (wx.EVT_BUTTON, self.OnButton),
            (wx.EVT_MOTION,self.OnMotion),
            (wx.EVT_CLOSE, self.OnClose),
            (wx.EVT_SIZE, self.OnSize)
        ]
        do(self.Bind(event, method) for (event, method) in self.events)


        if sys.DEV and not isinstance(page.name, unicode):
            msg = 'please only use unicode for labels: %r', page.name

            if pref('errors.nonunicode_buddy_names', type=bool, default=False):
                raise TypeError(msg)
            else:
                log.warning(msg)


        self.page=page
        self.page.tab=self

        if sys.DEV and not isinstance(page.title, unicode):
            msg = 'please only use unicode for labels: %r', page.title

            if pref('errors.nonunicode_buddy_names', type=bool, default=False):
                raise TypeError(msg)
            else:
                log.warning(msg)

        self.label1 = self.page.title

        self.row=None



        self.notified = page.notified
        self.drawnotified = NotifiedTimer(self)
        self.focus = False
        self.alignment = wx.ALIGN_LEFT

        #TODO: Check parent if should be active or as a pass in argument
        self._active=False
        self.clickage=False

        self.OnActive = Delegate()


        self.fontcolors = ([None]*5, [None]*5)
        self.states = ([None]*5, [None]*5)
        self.state  = 0
        self.mode   = pref('tabs.side_tabs',False)

        self.SetSkinKey(skinkey,True)

        self.mark=None

        # Keeps a copy of what itself looks like.
        self.bufferbitmap = None

        # When dragging, the overlay image preview of tabs
        self.previewtabs = None
        if self.notified: self.drawnotified.Start()

        #link prefs
        profile.prefs.link('tabs.style',     self.OnPrefChange, False)
        profile.prefs.link('tabs.flip',      self.OnPrefChange, False)
        profile.prefs.link('tabs.max_width', self.OnPrefChange, False)

    def OnPrefChange(self,val):
        self.Calcumalate()

    def UpdateSkin(self):
        key = self.skinkey
        s = lambda k, default = sentinel,mode=0: skin.get('%s%s.%s' % ('side'*mode,key, k), default)

        self.mode = pref('tabs.side_tabs',False)

        self.maxtabwidth = s('maxwidth',pref('tabs.max_width',100))#TODO: Completly remove pref?

        padd = s('padding', lambda: Point(0, 0))
        marg = s('margins', lambda: Margins([0,0,0,0]))
        icsz = s('iconsize', 16)
        font = s('font', lambda: default_font())
        spad = s('padding', padd, 1)
        smar = s('margins', marg, 1)
        sico = s('iconsize', icsz, 1)
        sfnt = s('font', font, 1)

        self.padding = (padd,spad)
        self.margins = (marg,smar)
        self.iconsize = (icsz,sico)
        self.font = (font,sfnt)

        states = self.states
        states[0][0] = s('backgrounds.normal')
        states[0][1] = s('backgrounds.active')
        states[0][2] = s('backgrounds.hover',       states[0][0])
        states[0][3] = s('backgrounds.activehover', states[0][2])
        states[0][4] = s('backgrounds.notify',      states[0][0])

        states[1][0] = s('backgrounds.normal',      states[0][0],1)
        states[1][1] = s('backgrounds.active',      states[0][1],1)
        states[1][2] = s('backgrounds.hover',       states[0][2],1)
        states[1][3] = s('backgrounds.activehover', states[0][3],1)
        states[1][4] = s('backgrounds.notify',      states[0][4],1)

        fc = self.fontcolors
        fc[0][0] = s('fontcolors.normal',      BLACK)
        fc[0][1] = s('fontcolors.active',      BLACK)
        fc[0][2] = s('fontcolors.hover',       fc[0][0])
        fc[0][3] = s('fontcolors.activehover', fc[0][2])
        fc[0][4] = s('fontcolors.notify',      fc[0][0])

        fc[1][0] = s('fontcolors.normal',      fc[0][0],1)
        fc[1][1] = s('fontcolors.active',      fc[0][1],1)
        fc[1][2] = s('fontcolors.hover',       fc[1][0],1)
        fc[1][3] = s('fontcolors.activehover', fc[1][2],1)
        fc[1][4] = s('fontcolors.notify',      fc[1][0],1)

        if pref('tabs.style', 2) and not hasattr(self, 'closebutton'):
            self.GenCloseButton()

        if hasattr(self, 'closebutton'):
            self.closebutton.SetSkinKey(self.Parent.closebuttonskin)
            self.closebutton.SetIcon(self.Parent.closeicon)

        self.Calcumalate()
        self.Refresh(False)

    def UpdateMode(self):
        self.mode = pref('tabs.side_tabs',False)
        self.closebutton.SetSkinKey(self.Parent.closebuttonskin,True)
        self.closebutton.SetIcon(self.Parent.closeicon)

        self.Calcumalate()
        self.Refresh(False)

    def OnSize(self,event):
        self.Refresh(False)

    def __repr__(self):
        return '<Tab %r>' % self.label1

    def GenCloseButton(self):
        """
            Creates a close button from the skin
        """
        self.closebutton = UberButton(self,
                                      skin = self.Parent.closebuttonskin,
                                      icon = self.Parent.closeicon,
                                      size = (self.iconsize[self.mode],
                                              self.iconsize[self.mode]))
        if pref('tabs.style',2)==2: self.closebutton.Show(False)

    @debug_property
    def Icon(self):
        return self.page.Icon.Resized(self.iconsize[self.mode]).WXB

    def Calcumalate(self):
        'Tab layout calculations, sets cursor positions for the label, the icon, and the button.'

        #Create a DC for use as calculation reference
        dc = ClientDC(self)
        dc.Font=self.font[self.mode]

        #curent Horizantal placement position
        xpad     = self.padding[self.mode].x
        xcurser  = xpad + self.margins[self.mode].left
        ypad     = self.padding[self.mode].y
        flip     = pref('tabs.flip', False)
        style    = pref('tabs.style', 2)
        icon     = self.Icon
        iconsize = self.iconsize[self.mode]

        #determine tab height

        label1 = self.label1
        if isinstance(label1, str):
            label1 = label1.decode('fuzzy utf8')

        txtwh = dc.GetTextExtent(label1)[0]
        ycurser = self.txtht = dc.Font.Height#sum([txtexts[1],txtexts[2],txtexts[3]])
        if (icon or style) and ycurser < iconsize:
            ycurser=iconsize
        ycurser += 2 * ypad + self.margins[self.mode].y


        #Icon and button placement if on the left
        if not flip: self.iconcurser=Point(xcurser, (ycurser-self.margins[self.mode].y)/2+self.margins[self.mode].top-iconsize/2)
        #icon and
        #else: self.iconcurser = 0
        if (style == 2 and not flip) or (style==1 and flip):
            self.closebutton.Size = Size(iconsize,iconsize)
            self.buttoncurser=self.iconcurser or Point(xcurser, (ycurser-self.margins[self.mode].y)/2+self.margins[self.mode].top-iconsize/2)

        if (icon and not flip) or (style==2 and not flip) or (style==1 and flip):
            xcurser +=iconsize + xpad

        #Label placement
        self.label1curser=Point(xcurser, (ycurser-self.margins[self.mode].y)/2+self.margins[self.mode].top-self.txtht/2)
        xcurser += txtwh + xpad

        #adding space for right hand elements to be placed during painting
        if (icon and flip) or (style==1 and not flip) or (style==2 and flip): xcurser+=iconsize + xpad
        xcurser+=self.margins[self.mode].right
        #setting tabs to just fit contents

        maxwidth = self.maxtabwidth
        if maxwidth and maxwidth < xcurser: xcurser=maxwidth
        self.gensize = (xcurser, ycurser)
        self.SetMinSize(self.gensize)
        #self.Parent.Generate()

        #print 'hey look, the close button is shown is a',(style==1),'statement'
        self.closebutton.Show(style==1 or (style==2 and self.Rect.Contains(self.Parent.ScreenToClient(GetMousePosition()))))

        #print "calced tab size for",repr(self.label1),'at',self.gensize,' / ',self.Size


    def OnPaint(self, event=None, forcedrect=None, otherdc=None, otherwindow=None):
        """
        Painty goodness!
        """
        size = forcedrect.Size if forcedrect else self.Size
        rect = forcedrect or RectS(size)
        iconsize = self.iconsize[self.mode]

        # Prep for clipping calculations
        cliptangle = self.Rect
        sx, sy = self.Rect.Position
        sw, sh = size
        ph = self.Parent.Size.height - 16

        sidetabs, style, flip = pref('tabs.side_tabs', False), pref('tabs.style', 2), pref('tabs.flip', False)

        # calculates the clipping rectangle when in sidetabs mode and the tab
        # goes over the bottom of the bar also manualy buffers in this situation
        if sidetabs and event and sy + sh > ph :
                cliptangle = Rect(sx, sy, sw, ph - sy)
                cdc        = PaintDC(self)
                cdc.SetClippingRegion(0, 0, cliptangle.width, cliptangle.height)
                buffer     = EmptyBitmap(*self.Size)
                dc         = MemoryDC()

                dc.SelectObject(buffer)
        else:
            cdc = None
            dc = otherdc or BufferedPaintDC(self)

        # figure out the correct current state
        state = Tab.NOTIFIED if not self.active and self.notified and self.drawnotified.drawnotified else self.state
        bg = self.states[self.mode][state if event else 0]

        bg.Draw(dc,rect)
        if (event or otherwindow):
            ApplySmokeAndMirrors(otherwindow or self, bg.GetBitmap(rect.Size))

        # calc icon and button placement if on the right
        icon = self.Icon
        iconoffsetx = (iconsize - icon.Size.width) // 2
        iconoffsety = (iconsize - icon.Size.height) // 2

        xpad = self.padding[self.mode].x

        # Place icon
        if icon and flip:
            self.iconcurser = Point(size.width - (iconsize + xpad + self.margins[self.mode].right),
                                     (size.height - self.margins[self.mode].y) / 2 + self.margins[self.mode].top - iconsize // 2)
        if (style == 1 and not flip) or (style == 2 and flip):
            self.buttoncurser = Point(size.width - (iconsize + xpad + self.margins[self.mode].right),
                                         (size.height - self.margins[self.mode].y)/2 + self.margins[self.mode].top - iconsize//2)
        # Draw icon
        if icon and ((style != 2 or not self.focus) or not event):
            dc.DrawBitmap( icon, rect.x + self.iconcurser.x + iconoffsetx, rect.y+self.iconcurser.y + iconoffsety,True)

        # determines how many pixels have been drawn
        filled = xpad + self.margins[self.mode].x

        if style:
            filled += self.closebutton.Size.width + xpad
        if icon and style !=2:
            filled += iconsize + xpad

        # set up font properties
        dc.SetFont(self.font[self.mode])
        dc.SetTextForeground(self.fontcolors[self.mode][state])#hook up font color

        # figure out space left for text
        txtrct = Rect(rect.x + self.label1curser.x, rect.y + self.label1curser.y,
                         size.width - filled -xpad, self.txtht)


        # draw label with truncating
        dc.DrawTruncatedText(self.label1, txtrct,alignment = ALIGN_LEFT | ALIGN_CENTER_VERTICAL)

        if event:
            # Set position of close button if actualy drawing the tab
            if style:
                self.closebutton.SetPosition(self.buttoncurser)

            # if manualy buffered separate DC then flush buffer
            if cdc:
                dc.SelectObject(NullBitmap)
                cdc.DrawBitmap(buffer, 0, 0, True)

    def GetActive(self):
        try:
            return self._active
        except AttributeError:
            return False

    def SetActive(self, switch=None):
        """
            If not active tells the page to run display code
            should only be used to set active, does not handle all deactivate
            functionality, instead use either parent.SetNextActive(self) or run
            .SetActive(True) on another tab
        """
        self._active = not self._active if switch is None else switch

        if self._active:
            self.state = Tab.ACTIVE_HOVER if self.focus else Tab.ACTIVE
            self.page.Display()
        else:
            self.state = Tab.HOVER if self.focus else Tab.NORMAL

        win = GetTopLevelParent(self)

        page = self.page
        icon = page.icon

        title = page.window_title if page.window_title is not None else page.title
        if title is not None:
            win.Title = title

        if icon is not None:
            win.SetFrameIcon(icon)

        self.SetNotify(False)
        self.OnActive()

        if self.Parent.side_tabs:
            self.Parent.ReVgenerate()
        else:
            self.Parent.Regenerate()

        self.Notebook.did_activate(page)

        self.Refresh(False)

    active = property(GetActive, SetActive)

    left_down_activates = prefprop('messaging.tabs.left_down_activates', False)

    def OnLeftDown(self, event):
        """
            When the left mouse button is downed over the tab
            if the curser is over the close button, pass the event on
            otherwise set mark of where mousedown occured
        """
        if hasattr(self, 'closebutton') and self.closebutton.hovered:
            self.closebutton.OnLeftDown(event)
        else:
            self.mark = event.Position

            if self.left_down_activates:
                self.active = True
        event.Skip()

    def OnLeftUp(self,event):
        """
            Removes mark on mouse up
            if mouse was downed inside the tab is set as the new
            active tab
        """
        self.mark = None
        if not (self.focus and event.LeftIsDown()):
            if self.focus: self.active = True
            self.OnMouseEnter(event)
            self.OnMotion(event)
        event.Skip()

    def OnMidUp(self, event):
        """
            Close tab on middle click
        """
        self.CloseTab()

    def OnRightDown(self, event):
        """
            Temporary right button down behavior
            Currently does nothing
            Should Open menu
        """
        #TODO: Menu, likely in TabBar though
        pass

    def OnMouseEnter(self, event):
        """
            When mouse enters the tab captures it and sets focus to true
            if another tab doesn't have capture and the mouse is within the
            cliptangle if there is one
        """
        cliptangle = RectS(self.Size)
        sy = self.Rect.y
        sw, sh = cliptangle.Size
        ph = self.Parent.Size.height-16
        if sy + sh > ph and pref('tabs.side_tabs', False):
            cliptangle = Rect(0, 0, sw, ph - sy)

        if cliptangle.Contains(event.Position):
            #TODO tactiveover conditioning
            if not self.HasCapture():
                self.CaptureMouse()
            if not event.LeftIsDown():
                self.focus=True
                self.state=2 if not self.active else 3

                if pref('tabs.style',2) == 2:
                    self.closebutton.Show(True)

                self.Refresh(False)

    def OnMouseLeave(self, event=None):
        """
            Unfocus tab and if mouse was dragged out starts dragging tabs
        """
        #if draging mouse out of tab and not from button
        cliptangle = RectS(self.Size)
        sy = self.Rect.y
        sw, sh = self.Size
        ph = self.Parent.Size.height-16
        if sy + sh > ph and pref('tabs.side_tabs', False):
            cliptangle = Rect(0, 0, sw, ph-sy)

        # Make sure the mouse isn't just over the close button
        if (not hasattr(self, 'closebutton') or not event or not self.closebutton.Rect.Contains(event.Position)) or not cliptangle.Contains(event.Position):

            self.ReleaseAllCapture()
            # if the left button was down and mouse draged out starts drag mode
            if not self.Parent.dragorigin and event and self.focus and event.LeftIsDown() and (not self.closebutton or not self.closebutton.hovered):
                # go into drag mode by notifying drag
                wx.CallAfter(self.Parent.OnDragStart, self)

            # if mouse out but not dragging, unfocus tab
            elif self.focus:
                self.focus=False

                self.state=1 if self._active else 0

                if pref('tabs.style', 2) == 2:
                    self.closebutton.Show(False)

        self.mark = None

        self.Refresh(False)

    def OnMotion(self,event):

        #if mouse is not down and not in focus, run the mouse in stuff
        if not (self.focus and event.LeftIsDown()):
            self.OnMouseEnter(event)

        position  = self.Parent.ScreenToClient(self.ClientToScreen(event.Position))
        mouseisin = self.Rect.Contains(position)

        #If dragging another tab, do D&D calculations
        if mouseisin and event.LeftIsDown() and self.Manager.source:
            self.Parent.DragCalc(self.Parent.ScreenToClient(GetMousePosition()))

        #Ensures a mouse leave occurs
        elif mouseisin and self.mark and ((abs(event.Position.x - self.mark.x) > 5) or (abs(event.Position.y - self.mark.y) > 5)):
            self.OnMouseLeave(event)

        #simulates onmouse in event if mouse over button
        elif self.HasCapture() and mouseisin and hasattr(self, 'closebutton'):
            if self.closebutton.Rect.Contains(event.Position):
                self.closebutton.OnMouseIn(event)
            elif self.closebutton.hovered:
                self.closebutton.OnMouseOut(event)

        #on mouse out insurance
        elif self.HasCapture() and not mouseisin:
            self.OnMouseLeave(event)

    @property
    def Notebook(self): return self.GrandParent

    @property
    def Manager(self):
        return self.Notebook.manager

    def OnButton(self, event = None):
        """
        Events for clicking the close button
        Closes tab and page
        """
        #self.__log.info('OnButton')
        while self.closebutton.HasCapture():
            self.closebutton.ReleaseMouse()
        wx.CallAfter(self.Close)
        wx.CallAfter(self.page.Close)

    CloseTab = OnButton

    def OnClose(self, event= None):
        """
        Call to close a tab,
        Automatically:
            -sets next tab active if currently active
            -tells the page to close itself
            -removes self from parent
            -hide/destroy itself
        """
        self.SetEvtHandlerEnabled(False)

        while self.HasCapture():
            self.ReleaseMouse()
        if self.active:
            self.Parent.SetNextActive(self)
        if self in self.Parent:
            self.Parent.Remove(self)

        if self.previewtabs:
            self.previewtabs.Stop()
            self.previewtabs = None

        if self.closebutton is not None and not wx.IsDestroyed(self.closebutton):
            self.closebutton.Close()
            self.closebutton = None

        if getattr(self, 'page', None):
            self.Notebook.did_remove(self.page.panel)

        if not wx.IsDestroyed(self):
            self.Show(False)
            #event.Skip()
            self.Destroy()

        return True

    def SetLabel(self, label1=None, windowtitle = None):
        """
            Sets the label(s) of the tab
            label1 is the label alwas shown
        """
        if label1 and label1 != self.label1:
            self.label1 = label1

            self.Calcumalate()
#            self.Refresh(False)

            if not self.Parent.side_tabs:
                self.Parent.Regenerate()

    def GetIcon(self):
        icon = self.page.icon
        return icon.ResizedSmaller(self.iconsize[self.mode]) if icon is not None else None

    Icon = property(GetIcon)

    def SetNotify(self, switch):
        '''
        Sets the notified state, and optionally starts a timer for drawing the
        notified state.
        '''
        #log.info('%r SetNotify(%r)', self, switch)

        self.notified = switch

        if switch: self.drawnotified.Start()
        else:      self.drawnotified.Stop()

        self.Parent.UpdateNotify()

        self.page.notified = switch

        self.Top.ProcessEvent(TabNotifiedEvent(tab = self))

        import hooks
        hooks.notify('digsby.overlay_icon_updated', self.page.Content)
