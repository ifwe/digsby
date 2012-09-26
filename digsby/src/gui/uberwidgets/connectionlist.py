'''

Connection list, showing IM accounts in the buddylist.

'''

import wx
from wx import AutoBufferedPaintDC, RectS, Point, Rect, Size, MemoryDC, CallLater

from gui import skin
from gui.skin.skinobjects import SkinColor,Margins,MarginSizer
from gui.textutil import default_font,CopyFont, Wrap,GetTextWidth
from gui.uberwidgets.uberwidget import UberWidget
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.umenu import UMenu

from cgui import SimplePanel

from common.Protocol import ProtocolStatus,OfflineReason
from common import profile, pref, actions
from gui.toolbox.scrolling import WheelScrollMixin

accounts = None

SCROLLCONST = 20

ShowNothingStates = set([ProtocolStatus.CONNECTING,
                         ProtocolStatus.AUTHENTICATING,
                         ProtocolStatus.INITIALIZING,
                         ProtocolStatus.LOADING_CONTACT_LIST])

class ConnectionsPanel(SimplePanel, UberWidget):
    """
        Panel that holds the list of accounts, used for frame and holding button
    """
    def __init__(self, parent):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        content = self.content = wx.BoxSizer(wx.VERTICAL)

        self.SetSkinKey('AccountPanels', True)

        cl = self.cl = ConnectionList(self)
        content.Add(cl, 1, wx.EXPAND)

        statebutton = self.statebutton = UberButton(self, icon = self.iconshow, skin = self.buttonskin)
        self.button_has_been_pressed = False
        statebutton.Bind(wx.EVT_BUTTON, self.__OnButtonClick)

        if self.expandup:
            content.Add(statebutton, 0, wx.EXPAND)
        else:
            content.Insert(0, statebutton, 0, wx.EXPAND)

        self.Sizer = MarginSizer(self.framesize, content)

        Bind = self.Bind
        Bind(wx.EVT_SIZE,  self.OnSize)
        Bind(wx.EVT_PAINT, self.OnPaint)

        profile.prefs.add_observer(self.WhenOrderChanges,'buddylist.order') #@UndefinedVariable




    def WhenOrderChanges(self,*a):

        order = pref('buddylist.order', [])

        try:
            cli = order.index('clist')
            bli = order.index('blist')
        except ValueError: #not in list
            self.expandup = False
        else:
            self.expandup = bli<cli


        self.iconshow = self.iconup if self.expandup else self.icondown
        self.iconhide = self.icondown if self.expandup else self.iconup


        if hasattr(self,'statebutton'):
            statebutton = self.statebutton
            content = self.content

            self.content.Detach(self.statebutton)

            if self.expandup:
                content.Add(statebutton, 0, wx.EXPAND)
            else:
                content.Insert(0, statebutton, 0, wx.EXPAND)
            self.statebutton.SetSkinKey(self.buttonskin)
            self.statebutton.SetIcon(self.iconhide if self.cl.ShowAll else self.iconshow)


    def UpdateSkin(self):
        """
            The usual.
        """
        key = self.skinkey
        s= lambda k,d=None: skin.get('%s.%s'%(key,k),d)

        self.framebg        = s('Frame',      lambda: SkinColor(wx.BLACK))
        self.framesize      = s('FrameSize',  lambda: Margins([0,0,0,0]))
        self.iconup         = s('icons.show', None)
        self.icondown       = s('icons.hide', lambda: wx.BitmapFromImage(wx.ImageFromBitmap(self.iconup).Mirror(False)))
        self.buttonskin     = s('buttonskin', None)

        self.WhenOrderChanges()

        if self.Sizer:
            self.Sizer.SetMargins(self.framesize)

    def __OnButtonClick(self, e):
        self.button_has_been_pressed = True
        return self.ToggleState(e)

    def ToggleState(self, event = None):
        """
            Toggles the List between Show All mode and hide Online/Offline mode
        """
        cl = self.cl
        cl.ShowAll = not cl.ShowAll

        if cl.ShowAll:
            cl.SetFocus()

        self.statebutton.SetIcon(self.iconhide if cl.ShowAll else self.iconshow)

        wx.CallAfter(self.Layout)

    def OnSize(self,event):
        """
            Relayout on resize
        """
        event.Skip()
        self.Layout()

    def OnPaint(self,event):
        """
            Standard paints.
        """
        dc   = AutoBufferedPaintDC(self)
        rect = RectS(self.Size)

        self.framebg.Draw(dc,rect)

panel_flags = wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT

class ConnectionList(WheelScrollMixin, wx.ScrolledWindow, UberWidget):
    """
        This is a scrollable list of all accounts associated to the profile.
        Its size is the height of all shown panels up to a certain height defined
        in the prefs.  Has two modes. In ShowAll mode all accounts are shown
        regardless of state. When ShowAll is false only those accounts that have
        an error, or are currently in between offline and online states are shown.
        Once a state is online or offline it will disappear after a period of time.
        When the list of accounts changes, the list destroys all existing panels,
        and recreates them in the correct order.
    """
    def __init__(self,parent):
        super(ConnectionList, self).__init__(parent)

        #set here so that when a profile change occurs the reference updates correctly
        global accounts
        accounts = profile.account_manager.accounts

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetScrollRate(0,1)
        self.SetSkinKey('accountpanels',True)
        self.ShowAll = False

        self.oldaccounts = []
        self.panels      = {}

        accounts.add_observer(self.WhenListChanges)
        profile.account_manager.add_observer(self.InitShow,'accounts_loaded')

        self.menu = UMenu(self)

        Bind = self.Bind
        Bind(wx.EVT_PAINT, self.OnPaint)
        Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
        Bind(wx.EVT_SIZE,self.OnSize)
        self.BindWheel(self)
        Bind(wx.EVT_SCROLLWIN_LINEDOWN, lambda e: self.Scroll(0,self.ViewStart[1]+SCROLLCONST))
        Bind(wx.EVT_SCROLLWIN_LINEUP, lambda e: self.Scroll(0,self.ViewStart[1]-SCROLLCONST))
        Bind(wx.EVT_SCROLLWIN, lambda e: (e.Skip(), wx.CallAfter(self.Refresh)))
        Bind(wx.EVT_KEY_DOWN, self.OnKey)

    def OnKey(self,event):

        key = event.KeyCode

        if key == wx.WXK_PAGEDOWN:
            self.ScrollPages(1)
        elif key == wx.WXK_PAGEUP:
            self.ScrollPages(-1)
        else:
            event.Skip()

    def UpdateSkin(self):
        key = self.skinkey
        s = lambda k, d = None: skin.get('%s.%s' % (key,k), d)

        self.bg = s('backgrounds.behind', SkinColor(wx.WHITE))
        self.spacing = s('spacing', 0)

        wx.CallAfter(self.WhenListChanges)

    def OnPaint(self, event):
        self.bg.Draw(AutoBufferedPaintDC(self), RectS(self.ClientSize))

    def _on_mousewheel(self, e):
        """
            Handles mouse wheel scroll events to make the list scroll with mouse
            wheel use.
        """
        super(ConnectionList, self)._on_mousewheel(e)
        if not self.bg.ytile:
            self.Refresh()

    def get_wheel_lines(self, rotation, e):
        val = rotation / float(e.GetWheelDelta()) * e.LinesPerAction
        return val / 2.0 # 2-line panels

    def rotation_for_lines(self, lines, e):
        return float(e.GetWheelDelta()) / e.LinesPerAction * lines * 2.0

    def ScrollLines(self, lines):
        dist = 0
        a = b = None
        try:
            accts = list(accounts)
            if len(accts) > 1:
                a = self.panels[accts[1]].Position.y
                b = self.panels[accts[0]].Position.y
            else:
                dist = 0
        except Exception:
            dist = 0
        else:
            if a is not None and b is not None:
                dist = a - b
        if dist:
            dist = lines * dist - getattr(self, 'borrowed_dist', 0)
            self.borrowed_dist = int(round(dist)) - dist
            self.Scroll(0, self.ViewStart.y + int(round(dist)))
        else:
            super(ConnectionList, self).ScrollLines(lines)

    def InitShow(self,*a):
        """
            Because accounts are loaded late, the decision to show most happen
            later.  Decides the initial show based off if the account
        """

        #ShowAll is True if no accounts autoLogin
        def show():
            if not self.Parent.button_has_been_pressed: # don't toggle state if user has already clicked.
                self.ShowAll = not any(getattr(account, 'autologin', False) for account in profile.account_manager.accounts)
                self.Parent.statebutton.icon = self.Parent.iconhide if self.ShowAll else self.Parent.iconshow#Label = 'Hide' if self.ShowAll else 'Show'

        self.showtimer = CallLater(500, show)

    def SetShowAll(self, show):
        """
        Set the ShowAll mode True or False
        True    - Show all accounts
        False   - Show only accounts in error or between states
        """
        self.showall = show
        self.UpdateChildrenShown()

    def GetShowAll(self):
        "Returns ShowAll mode True or False"

        return self.showall

    ShowAll = property(GetShowAll, SetShowAll)

    def UpdateChildrenShown(self):
        """
        Loop through the children showing or hiding the ones affected by the
        a ShowAll switch.
        """
        for child in self.Children:
            if hasattr(child, 'DetermineShow'):
                child.DetermineShow()

        wx.CallAfter(self.SelfSize)

    def OnSize(self, event = None):
        """
        When the list has a change in size sets the virtual size and calls
        SelfSize to firgure out the appropriate MinSize
        """
        if event is not None:
            event.Skip()

        # Make sure virtual Width is the same as the Client Width
        self.SetVirtualSizeHints(self.ClientSize.width, -1, self.ClientSize.width, -1)

        if self.Size.width == self.lastwidth:
            return

        wx.CallAfter(self.SelfSize)

    def WhenListChanges(self, *a):
        self.Freeze()
        try:
            scrolly = self.GetScrollPos(wx.VERTICAL)
            accts = list(accounts)

            # Early exit hack here if the accounts list is not empty and equal
            # to our cached one in self.oldaccounts--the logic for preserving
            # the scroll is always a few pixels off, so don't do anything if we
            # don't have to.
            if accts and self.oldaccounts == accts:
                return

            self.Sizer.Clear(deleteWindows = False)
            oldaccts, panels = self.oldaccounts, self.panels
            old, new = set(oldaccts), set(accts)

            for acct in old - new:
                panel = panels.pop(acct)
                panel.OnDestroy()
                panel.Destroy()

            for acct in new - old:
                panels[acct] = ConnectionPanel(self, acct)

            # Add a spacer to make sure the first visible item obeys the spacing between
            # itself and the edge of the list
            self.Sizer.AddSpacer(self.spacing)

            # create a new panel for each account and place it in the sizer

    #        try:
            for acct in accts:
                self.Sizer.Add(panels[acct], 0, panel_flags, self.spacing)

            self.oldaccounts = accts

            wx.CallAfter(self.SelfSize)
            wx.CallAfter(self.Scroll, 0, scrolly)
        finally:
            wx.CallAfter(self.Thaw)

    def SelfSize(self):
        """
            Figures out the maximum height of the list by the smaller of shown elements
            or the pref connectionlist.max_height
        """

        #h is the minimum of height of all items + spacing or the height specified in prefs
        h = min(sum(child.MinSize.height+self.spacing for child in self.Children if child.Shown) + self.spacing, pref('connectionlist.max_height', 200))
        #Hide if no items shown
        self.Show(h > self.spacing)

        self.MinSize = wx.Size(-1, h)
        self.GrandParent.Layout()

        if self.Shown:
            wx.CallAfter(self.Layout)
            wx.CallAfter(self.Refresh)
            wx.CallAfter(self.EnsureVirtualHeight)

        self.lastwidth = self.Size.width

    def EnsureVirtualHeight(self):
        """
            This is called to make sure that the VirtualHeight is correct
        """
        vheight = self.VirtualSize.height
        cheight = self.Sizer.MinSize.height

        if vheight != cheight:
            self.VirtualSize = (-1, cheight)


class ConnectionPanel(SimplePanel, UberWidget):
    """
        This panel corresponds to an individual IM account and displays data about it.
        It displays the account's username, it's offline reason or state if no
        reason is available, a link that will connect if offline or disconnect
        if online, a dismiss button if the list is not set to ShowAll and the
        account is either online or offline, the protocol icon, and the state icon
        if the list is in ShowAll.
    """
    def __dtor__(self):
        from gui.toolbox.refreshtimer import refreshtimer
        refreshtimer().UnRegister(self)

    def __init__(self, parent, account):

        self.initover = False

        SimplePanel.__init__(self, parent)

        self.Show(False)

        self.account=account

        #Refernce for the timer for delayed hide
        self.willhide = None

        self.SetSkinKey('AccountPanels',True)

        self.title = account.username

        self.account.add_observer(self.WhenStateChange,'offline_reason')
        self.account.add_observer_callnow(self.WhenStateChange,'state')

        #Becasue the width affects the content and the content effects the height
        #   this is used to store the last size so the widths can be compared
        #   perventing an infinit loop of size adjustments
        self.lastsizedto=self.Size

        #These are used for faking a button
        self.buttonstate = 0 #visual state: Idle; 1: hover; 2: down
        self.buttonisdown = False #because if the button is down and shown down can differ
        self.buttonshown= False #Is the button visible?

        self.linkhovered = False #True if mouse is in the link rect
        self.linkdown = False #True if the mouse button was pushed while in link rect

        Bind = self.Bind

        Bind(wx.EVT_PAINT,        self.OnPaint)
        Bind(wx.EVT_SIZE,         self.OnSize)
        Bind(wx.EVT_ENTER_WINDOW, self.OnMouseIn)
        Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseOut)
        Bind(wx.EVT_MOTION,       self.OnMouseMotion)
        Bind(wx.EVT_LEFT_DOWN,    self.OnLeftDown)
        Bind(wx.EVT_LEFT_UP,      self.OnLeftUp)
        Bind(wx.EVT_RIGHT_UP,     self.OnMenu)
        Bind(wx.EVT_KEY_DOWN,     self.OnKey)

        self.initover = True

    def OnKey(self, event):
        self.Parent.ProcessEvent(event)

    def OnMenu(self, e = None):
        if e: e.Skip()
        menu    = self.Parent.menu
        account = self.account

        menu.RemoveAllItems()
        menu.AddItem(_('&Edit'), callback = lambda: profile.account_manager.edit(account))
        menu.AddSep()

        if account.connection:
            actions.menu(self, account.connection, menu)
            actions.menu(self, account, menu)
        else:
            menu.AddItem(_('&Connect'), callback = lambda: account.connect())

        menu.PopupMenu()

    def WhenStateChange(self, acct, attr, old, new):
        """
        When the account state changes this calls everything that sets up the
        the elements of the panel and determines whether it shows or hides
        """
        # An if self check becasue it's posible the callback could trigger between
        # the time the object is destroyed and the observer is removed
        account = self.account

        #When in the WILL_RECONNECT state, registered to refresh every 1 second
        from gui.toolbox.refreshtimer import refreshtimer
        if account.offline_reason == OfflineReason.WILL_RECONNECT:
            self.reason = lambda: profile.account_manager.state_desc(self.account)
            refreshtimer().Register(self)
        else:
            self.reason = profile.account_manager.state_desc(account) if account.state==ProtocolStatus.OFFLINE and account.offline_reason else _(account.state)
            refreshtimer().UnRegister(self)

        self.stateicon = account.statusicon.ResizedSmaller(16)

        if not wx.IsDestroyed(self):
            self.MakeLink()
            self.CalcLayout()
            self.Refresh()
            #Tells DetermineShow to delay the hide if state changed to ONLINE or OFFLINE
            delayed = (account.state == ProtocolStatus.ONLINE) or (account.state == ProtocolStatus.OFFLINE and account.offline_reason == OfflineReason.NONE)
            self.DetermineShow(delayed)
            self.Parent.SelfSize()
            self.GrandParent.Parent.Layout()

    def MakeLink(self):
        """
            Gets the link information for the current state of the account
        """
        self.link,self.linkcallback = self.account.get_link()

    def UpdateSkin(self):
        """
            The usual update skin
        """
        key = self.skinkey
        s = lambda k,d=None: skin.get('%s.%s'%(key,k),d)

        self.bg             = s('backgrounds.account',lambda: SkinColor(wx.WHITE))
        self.majorfont      = s('Fonts.Account', default_font)
        self.minorfont      = s('Fonts.StateAndLink',default_font)
        self.linkfont       =  CopyFont(self.minorfont, underline=True)
        self.majorfc        = s('FontColors.Account', wx.BLACK)
        self.statefc        = s('FontColors.State',lambda: wx.Colour(125,125,125))
        self.linkfc         = s('FontColors.Link', wx.BLUE)
        self.closeicon      =  [None]*3
        self.closeicon[0]   = s('Icons.Close',skin.get('AppDefaults.removeicon')).ResizedSmaller(16)
        self.closeicon[1]   = s('Icons.CloseHover',self.closeicon[0]).ResizedSmaller(16)
        self.closeicon[2]   = s('Icons.CloseDown',self.closeicon[1]).ResizedSmaller(16)
        self.liconsize      = s('ServiceIconSize',16)
        self.padding        = s('Padding',lambda: wx.Point(3,3))


        self.stateicon = self.account.statusicon.ResizedSmaller(16)

        self.licon = self.account.serviceicon.Resized(self.liconsize)

        if self.initover:
            self.CalcLayout()

    def CalcLayout(self):
        """
        Calculates the layout and height of the pannel based off of it's
        width and the size of the elements
        """
        dc = MemoryDC()

        #x and y are the cursor for were the next item will be placed
        #padx and pady are just local refs to padding.x and padding.y
        x,y = padx, pady = self.padding

        sz = self.Size

        linkfont  = self.linkfont
        minorfont = self.minorfont
        majorfont = self.majorfont

        licon   = self.licon
        link    = self.link

        #Positiong the service icon and the status/close icon to the left or
        #   right respectivly
        self.liconpos = Point(x, y)
        self.riconpos = Point(sz.width - 16 - padx, y)

        #incriment x position to right of icon
        x += licon.Width + padx

        #Which is taller, the label or the icon
        h = max(majorfont.Height, 16)

        #Place title rect with the erlier calculated values and width whats left
        #   of the overall width for the width left for the label
        self.titlerect = Rect(x, y, sz.width-4*padx-licon.Width-16,h)

        #incriment y to below the filled space
        y += h+pady

        #Find the link width because it's needed to know how much room the
        #   reason rect needs
        linkwidth = GetTextWidth(link,linkfont)

        #Determine the horizantal space left for the reason, then wrap it
        reasonwidth = sz.width - x - (linkwidth + 2*padx)
        reason = self.reason() if callable(self.reason) else self.reason
        wrappedreason = self.wrappedreason = Wrap(reason, reasonwidth, minorfont, dc)

        #Get the height needed for the label from the wraped string
        reasonheight = dc.GetMultiLineTextExtent(wrappedreason,minorfont)[1]

        #combine into a rectangle
        self.reasonrect = Rect(x,y,reasonwidth,reasonheight)

        #Figure the rest of the link size information
        self.linksize = Size(linkwidth,linkfont.LineHeight)

        #figure out the height the panel has to be in order to fit the content
        h = max(y+reasonheight+pady,self.liconsize+2*padx)

        newSize = Size(self.MinSize.width,h)
        if self.MinSize != newSize:
            self.MinSize = newSize

        self.Refresh()

    def DetermineShow(self, later=False):
        """
            Decides weither the panel should show or hide.
            If 'later' is True, hiding is delayed by the pref connectionlist.online_linger
        """
        account = self.account

        #Initialise or stop a delayed hide
        if later and not self.Parent.ShowAll and self.Shown:
            if not self.willhide:
                self.willhide = wx.CallLater(pref('connectionlist.online_linger',1000),self.WillShowFalse)
        else:
            if self.willhide:
                self.willhide.Stop()
                self.willhide = None

            #figures if it should show if parent is set to ShowAll or Offline with a reason and not achknowledged or the state is not OFFLINE or ONLINE
            shouldshow = self.Parent.ShowAll or ((account.state==ProtocolStatus.OFFLINE and account.offline_reason and not account.error_acked) or account.state not in (ProtocolStatus.OFFLINE,ProtocolStatus.ONLINE))
            self.Show(bool(shouldshow))
        self.DoLinkPos()

    def WillShowFalse(self):
        """
        Callback for the delayed hide of DetermineShow
        Hides the panel and takes the stepss to correct the layout for the
        change
        """
        self.Show(False)
        self.Parent.SelfSize()
        self.GrandParent.Parent.Layout()

    def OnSize(self,event):
        """
        When the panel is width is change, runs CalcLayout to position elements
        and figure new height
        """
        event.Skip()
        # Make sure the width actualy changed before calculating new positions and height
        if self.lastsizedto.width != self.Size.width:
            self.lastsizedto = self.Size
            self.CalcLayout()
        self.DoLinkPos()

    def DoLinkPos(self):
        "Positions the link in the lower right hand corner of the panel."
        sz = self.Size
        linksz = self.linksize
        padx,pady = self.padding

        # Link goes in lower right hand corner
        self.linkrect = wx.Rect(sz.width - padx - linksz.width, sz.height - pady - linksz.height,*linksz)


    def OnPaint(self,event):
        dc   = AutoBufferedPaintDC(self)
        rect = RectS(self.Size)
        self.bg.Draw(dc, rect)

        # Draw service icon
        icon = self.licon if self.account.is_connected else self.licon.Greyed

        dc.DrawBitmapPoint(icon, self.liconpos, True)

        #The right icon can either be the close icon, the state icon, or nothing
        #Shows the state icon if the list is in ShowAll or nothing if state is CONNECTING, AUTHENTICATING,INITIALIZING, or LOADING_CONTACT_LIST
        #   Otherwise it shows the close button
        ricon = self.stateicon if self.Parent.ShowAll else (self.closeicon[self.buttonstate] if self.account.state not in ShowNothingStates else None)
        if ricon:
            rconpos = self.riconpos + Point(8 - ricon.Width // 2, 8 - ricon.Height // 2)
            dc.DrawBitmapPoint(ricon, rconpos, True)
        self.buttonshown = bool(ricon)

        # Draw the account name
        dc.Font = self.majorfont
        dc.TextForeground = self.majorfc
        dc.DrawTruncatedText(self.title, self.titlerect)

        # Draws the offline reason or state
        dc.Font = self.minorfont
        dc.TextForeground = self.statefc
        if callable(self.reason):
            self.wrappedreason = Wrap(self.reason(), self.reasonrect.Width, self.minorfont, dc )
        dc.DrawLabel(self.wrappedreason,self.reasonrect)

        # Draw the link
        dc.Font = self.linkfont
        dc.TextForeground = self.linkfc
        dc.DrawLabel(self.link,self.linkrect)

    def OnDestroy(self):
        """
        When the panel is destroyed, this removes the panel as an observer
        of the account
        """
        self.account.remove_observer(self.WhenStateChange,'offline_reason')
        self.account.remove_observer(self.WhenStateChange,'state')

    def OnLeftDown(self,event):
        """
        Detects left mouse button down events for emulation of links and
        buttons
        """

        event.Skip()

        # if the button is being hovered
        if self.buttonstate == 1:
            # it is now down
            self.buttonstate = 2
            self.buttonisdown = True
            self.Refresh()

        elif self.linkhovered:
            self.linkdown = True

    def OnLeftUp(self,event):
        """
            Detects left mouse button up events for emulation of links and
            buttons
        """

        event.Skip()

        #if the buttons state is down, set it to idle and close the panel
        #   ackknowledging the the error
        if self.buttonstate == 2:
            self.buttonstate = 0
            self.account.error_acked = True
            self.DetermineShow()
            self.Parent.SelfSize()

        self.buttonisdown = False

        #If link is down
        if self.linkdown:
            #And if the pointer is over the link
            if self.linkhovered:
                #call the callback for the link
                self.linkcallback()
            self.linkdown = False

        self.OnMouseMotion(event)

        self.Refresh()

    def OnMouseMotion(self,event):
        """
            Ensures mouse in and mouse out capture events occure, also handels
            hover for the button and link
        """

        #If the left mouse button is not down, make sure the panel gets/losses
        # capture accordingly
        if not event.LeftIsDown():
            mouseisin = wx.FindWindowAtPointer() is self

            if mouseisin and not self.HasCapture():
                self.OnMouseIn(event)

            elif not mouseisin and self.HasCapture():
                self.OnMouseOut(event)

        #Handle button statethings on mouse over
        if not self.Parent.ShowAll and self.HasCapture() and self.buttonshown:
            bstate = self.buttonstate
            bisdown = self.buttonisdown
            mouseinb = wx.RectPS(self.riconpos,(16,16)).Contains(event.Position)
            if bstate == 0 and mouseinb:
                self.buttonstate = 2 if bisdown else 1
                self.Refresh()
            elif bstate in (1,2) and not mouseinb:
                self.buttonstate = 0
                self.Refresh()

        #handle link mouseover
        mouseinl = self.linkhovered = self.linkrect.Contains(event.Position)
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND if mouseinl else wx.CURSOR_DEFAULT))

    def OnMouseIn(self,event):
        """
            Captures the mouse when the cursor enters the panel
        """
        if not self.HasCapture() and not event.LeftIsDown():
            self.CaptureMouse()

    def OnMouseOut(self,event):
        """
            Releases the mouse when the cursor leaves the panle
        """
        if not event.LeftIsDown():
            while self.HasCapture():
                self.ReleaseMouse()
