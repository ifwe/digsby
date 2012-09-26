from __future__ import with_statement
from tab import Tab
from gui import skin
from OverlayImage import OverlayImage
from navigation_arrows import Navi
from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.UberEvents import EVT_DRAG_START
import wx
from wx import RectS, Rect, RectPS
from util.primitives.funcs import do
from common import pref, profile, prefprop
from gui.uberwidgets import UberWidget
from cgui import SimplePanel
#from traceback import print_stack,format_stack

CUPID   = wx.NewId()
CDOWNID = wx.NewId()

CLOSE_TAB = wx.NewId()
CLOSE_OTHER_TABS = wx.NewId()

class TabBar(SimplePanel, UberWidget):
    """
        Where the tabs live, handles all display and organization functionality
    """
    def __init__(self, parent, skinkey):
        SimplePanel.__init__(self, parent)

        self.tabs     = [] # a list of all the tabs
        self.rows     = [] # a list of all the visible row, each a list of all the tabs in that row
        self.rowindex = 0  # the first visible row
        self.tabindex = 0  # the first tab of the first visible row
        self.tabendex = 0  # the last tab of the last visible row

        events = [(wx.EVT_PAINT, self.OnPaint),
                  (wx.EVT_SIZE, self.OnSize),
                  (wx.EVT_BUTTON, self.OnButton),
                  (wx.EVT_MOUSEWHEEL, self.OnWheel),
                  (wx.EVT_MOTION,self.OnMotion)]

        for event, method in events: self.Bind(event, method)


        self.flagedrows = set()
        self.lastsize=self.Size

        self.rowheight=0#height of a row in pixels

        self.SetSkinKey(skinkey,True)

        #buttons for verticle alignment
        self.cupb = UberButton(self, CUPID, skin=self.scrollbuttonskin, icon=self.upicon)
        self.cupb.Show(False)

        self.cdownb = UberButton(self, CDOWNID, skin=self.scrollbuttonskin, icon=self.downicon)
        self.cdownb.Show(False)

        #the navigation box
        self.navi=Navi(self)


        self.dragorigin = None#when draging the tab that you are dragging
        self.dragtarget = None#when dragging the mouse is over and at that point released on

        # the arrow image shown when dragging tabs
        self.dropmarker=OverlayImage(self, self.dropmarkerimage)

        # self.dropmarker = Storage(Show = lambda v=True: None)
        self.dragside=None#was the tab droped on the left or right of the target tab

        #linking prefs
        link = profile.prefs.link #@UndefinedVariable
        link('tabs.rows',      self.Generate, False)
        link('tabs.tabbar_x',  self.Generate, False)
        link('tabs.hide_at_1', self.Generate, False)
        link('tabs.side_tabs', self.SkinRedirect, False)

        self.Top.Bind(wx.EVT_MENU, self.OnMenuEvent)

    side_tabs = prefprop('tabs.side_tabs')
    tab_rows = prefprop('tabs.rows', 2)

    def UpdateSkin(self):
        key = self.tabskin = self.skinkey
        g   = lambda k, default = sentinel: skin.get(key + '.' + k, default)
        sg   = lambda k, default = sentinel: skin.get('side' + key + '.' + k, default)

        elems = (('spacing', 'spacing',          2),
                 ('bg', 'backgrounds.bar'),
                 ('dropmarkerimage', 'dropmarker.image'),
#                 ('dropmarkeroverlay', 'dropmarker.overlay', 0),
                 ('dropmarkeroffset', 'dropmarker.offset', 0),
                 ('closebuttonskin', 'closebuttonskin', ''),
                 ('closeicon', 'icons.close', None),
                 ('scrollbuttonskin', 'scrollbuttonskin', ''),
                 ('lefticon', 'icons.left', ''),
                 ('righticon', 'icons.right', ''),
                 ('upicon', 'icons.up', ''),
                 ('downicon', 'icons.down', ''))

        for elem in elems:
            setattr(self, 'top' + elem[0], g(*elem[1:]))
            setattr(self, 'side' + elem[0], sg(elem[1],getattr(self,'top' + elem[0])))
            setattr(self, elem[0], getattr(self, ('side' if self.side_tabs else 'top') + elem[0]))


        if hasattr(self,'dropmarker'):
            self.dropmarker.SetImage(self.dropmarkerimage)
            self.dropmarker.SetRotation((self.side_tabs and not self.dropmarkerimage))

        navi = getattr(self, 'navi', None)
        if navi is not None:
            self.cdownb.SetSkinKey(self.scrollbuttonskin)
            self.cupb.SetSkinKey(self.scrollbuttonskin)
            self.cdownb.SetIcon(self.downicon)
            self.cupb.SetIcon(self.upicon)

            self.navi.closebutton.SetSkinKey(self.closebuttonskin)

            self.navi.closebutton.SetIcon(self.closeicon)

            scrollskin = self.scrollbuttonskin

            navi.prevb.SetSkinKey(scrollskin)
            navi.nextb.SetSkinKey(scrollskin)
            navi.upb.SetSkinKey(scrollskin)
            navi.downb.SetSkinKey(scrollskin)

            navi.prevb.SetIcon(self.lefticon)
            navi.nextb.SetIcon(self.righticon)
            navi.upb.SetIcon(self.upicon)
            navi.downb.SetIcon(self.downicon)

        wx.CallAfter(self.Generate)


    def SkinRedirect(self,val=None):
        elems = ('spacing',
                 'bg',
                 'dropmarkerimage',
                 #'dropmarkeroverlay',
                 'closebuttonskin',
                 'closeicon',
                 'scrollbuttonskin',
                 'lefticon',
                 'righticon',
                 'upicon',
                 'downicon'
                 )

        for elem in elems:
            setattr(self, elem, getattr(self,('side' if self.side_tabs else 'top') + elem))

        self.UpdateChildSkins()

    def UpdateChildSkins(self):
        self.cdownb.SetSkinKey(self.scrollbuttonskin,True)
        self.cupb.SetSkinKey(self.scrollbuttonskin,True)

        navi, sbs = self.navi, self.scrollbuttonskin
        navi.closebutton.SetSkinKey(self.closebuttonskin,True)
        navi.prevb.SetSkinKey(sbs, True)
        navi.nextb.SetSkinKey(sbs, True)
        navi.upb.SetSkinKey(sbs, True)
        navi.downb.SetSkinKey(sbs, True)

        self.UpdateChildrenIcons()

        for tab in self.tabs:
            tab.UpdateMode()

        self.Generate()

    def __repr__(self):
        return '<TabBar %r>' % self.tabs

    def OnDragStart(self, tab):
        'Catches the tab drag event and starts the tab dragging system.'

        self.NotifyDrag(tab)

    def OnMotion(self,event):
        'Positioning updates during drag and drop'

        if event.LeftIsDown() and (self.dragorigin or self.Manager.source):
            self.DragCalc(event.Position)

    def __getitem__(self, index):
        return self.tabs[index]

    def OnPaint(self, event):
        dc   = wx.PaintDC(self)
        rect = RectS(self.Size)
        if not self.side_tabs:
            rcount = min(len(self.rows), pref('tabs.rows', 2))
            height = self.tabs[0].Size.height

            y=0
            for unused_i in xrange(rcount):
                self.bg.Draw(dc, Rect(rect.x, y, rect.width, height))
                y += height

        else:
            self.bg.Draw(dc,rect)

    def Add(self, page, focus, resort = True):
        """
            Adds a tab to the bar.  Should only be used by parent NoteBook.
            page - page in PageContainer the tab is to be associated with
            focus - whether that tab should steal focus from current tab
        """
        tab = Tab(self, page, skinkey = self.tabskin)
        tab.Bind(wx.EVT_CONTEXT_MENU, self.ShowMenu)
        tab.Show(False)
        self.tabs.append(tab)

        if focus:
            wx.CallAfter(tab.SetActive, True)

        elif resort:
            if self.side_tabs:
                self.ReVgenerate()
            else:
                self.Regenerate(True)

        return tab

    def ShowMenu(self, e):
        self._menutab = e.EventObject

        try:
            menu = self._tabmenu
        except AttributeError:
            from gui.uberwidgets.umenu import UMenu
            menu = self._tabmenu = UMenu(self)
            menu.AddItem('Close &Other Tabs', id = CLOSE_OTHER_TABS)
            menu.AddSep()
            menu.AddItem('&Close Tab', id = CLOSE_TAB)

        menu.PopupMenu()

    def OnMenuEvent(self, e):
        '''Invoked when a tab context menu item is clicked.'''

        if e.Id == CLOSE_TAB:
            self._menutab.CloseTab()
        elif e.Id == CLOSE_OTHER_TABS:
            menutab = self._menutab

            # switch to that tab first
            menutab.active = True

            with self.Frozen():
                for tab in self.tabs[:]:
                    if tab is not menutab:
                        tab.CloseTab()
        else:
            e.Skip()

    def Generate(self, val=None):
        self.navi.closebutton.Show(pref('tabs.tabbar_x', False))

        if self.side_tabs:
            self.ReVgenerate(True)
        else:
            self.Regenerate()

    def ReVgenerate(self,total=False, safe=False, dotoggle=True):
        """
        It's like Doo... err.. Regenerate, only vertical
        """

#        print "Starting: Regenerate",self.Top.Title,'\n'#,'='*80,'\n','\n'.join(format_stack())
#        print '='*80

        #TODO: Should we be careful about the tab leaving the bar?
        tabs = self.tabs

        if not tabs: return

        do(tab.Show(False) for tab in self.tabs)
        for tab in self.tabs: tab.row = None
        del self.rows[:]

        # Safty precautions prevent list access errors
        if self.tabindex < 0 or self.tabindex >= len(tabs):
            self.tabindex = 0

        # Preset variables
        n = self.tabindex   # the first tab shown
        self.rowheight = tabs[0].GetMinHeight()
        area = self.Notebook.Size.height - 32 # Height in pixels of the tabbar

        # number of fully visible rows in the given area at the given height
        i = area//self.rowheight

        count = len(tabs)

        #one tab per row
        for r in xrange(count): tabs[r].row=r

        rows = self.rows
        size = self.Size

        #Sets navimode and position
        navi = self.navi
        navi.ShowNav(4)
        navi.Hide()
        navi.Position = wx.Point(size.width - navi.Size.width,0)

        # Totally reconstructs the list if it's told to or there are not tabs in the rows or
        # if there isn't one more tab than there is room for and there is enough room to fit
        # them all and number of tabs in the row equals the number of tabs
        if total or not rows or (i + 1 != len(rows[0])) and not (i > len(rows[0])) and len(rows[0]) == len(tabs):
            rows.append([])
            col = rows[0]

            #if all tabs fit
            if i >= count:
                n=0
                self.tabindex=0
                do(col.append(tab) for tab in tabs)
                av=col[0].MinSize.height
            #calculate and show range
            else:
                for t in xrange(n,n+i+1):
                    if t < len(tabs):col.append(tabs[t])

                # populate with earlier stuff
                while len(col) < i and n > 0:
                    n-=1
                    col.insert(0,tabs[n])

                if col: av = col[0].MinSize.height
        else:
            #just leave the new values the same as the old
            col = rows[0]
            av  = col[0].MinSize.height

        # Show all tabs in the bar
        count = 16
        for t in col:
            t.Size = (self.Size.width,av)
            t.Position = (0,count)
            count += av
            t.Show()

        self.tabindex=n
        endex = self.tabendex=n+len(col)

        if dotoggle:
            self.Toggle()

        cupb, cdownb = self.cupb, self.cdownb


        cupb.Enable(self.tabindex != 0)
        cdownb.Enable(endex < len(tabs) or tabs[endex - 1].Position.y +
                           tabs[endex-1].Size.height > size.height - 16)


        self.UpdateNotify()

    def Regenerate(self, safe = False, dotoggle=True):
        '''
        Regenerates layout information.

        safe is a flag to indicate if we should try to keep the currently active
        tab in view at all times. (This doesn't occur when scrolling, for
        instance.)
        '''

#        print "Starting: Regenerate",self.Top.Title,'\n','='*80,'\n','\n'.join(format_stack())
#        print '='*80
        # early exit for when the tabbar isn't visible.
        if not self.IsShown() and len(self.tabs) == 1:
            return

        with self.Frozen():
            self._Regenerate(safe = safe, dotoggle = dotoggle)

        self.Refresh(False)

    def _Regenerate(self, safe = False, dotoggle = True):
        self.cupb.Show(False)
        self.cdownb.Show(False)
        parentpage = self.Parent.pagecontainer

        # style is the number of rows (or 0 for single)
        style = self.tab_rows

        # Should we be careful about the tab leaving the bar?
        careful = not safe and parentpage.active

        # Hide all tabs preparation for refilling
        for tab in self.tabs:
            tab.Show(False)
            tab.row = None
        del self.rows[:]

        # navi set up, see if arrows are needed and placement
        tally = sum(tab.MinSize.width for tab in self.tabs) #total size of tabs

        navi = self.navi
        tabs = self.tabs
        rows = self.rows

        if not tabs: return

        # Tab alignment calculations

        # Saftey precautions prevent list access errors
        if self.tabindex < 0 or self.tabindex >= len(tabs):
            self.tabindex = 0

        # Preset variables
        n = self.tabindex   # the first tab shown
        i = n
        row = 0
        self.rowheight = tabs[0].MinHeight


        my_w, nav_w = self.Size.width, navi.Size.width

        # Decide what kind of navigation panel, if any, to use...
        if tally >= my_w - nav_w and not style:
            navi.ShowNav(1) # arrows left and right
        elif tally >= (my_w - nav_w):
            navi.ShowNav(3) # arrows up and down next to the X
        else:
            navi.ShowNav(0)

        #Where to put navigation panel.
        navi.Freeze()
        navi.Show(True)
        navi.Fit()
        navi.Position = wx.Point(self.Size.width-navi.Size.width,0)
        navi.Size = wx.Size(-1,self.Size.height)
        navi.Thaw()

        #More preparing vars
        area = self.Notebook.Size.width - navi.Size.width

        #While more tabs are not in a row
        while len(tabs) > i:
            tally = tabs[i].MinSize.width
            rows.append([])

            # Loop through each visible tab, fitting tabs on the right.
            while i < len(tabs) and tally < area:
                i += 1
                if i < len(tabs):
                    tally += tabs[i].MinSize.width

            #Be carefull that the active tab doesn't scroll off the bar
            if careful and not style:
                activeindex = tabs.index(parentpage.active.tab)
                change=False

                #add tabs until the active tab is visible
                while activeindex>=i and n!=i:
                    i += 1
                    tally += tabs[i].MinSize.width
                    change = True

                #Remove tab if more tabs than room
                if tally >= area and change:
                    tally -= tabs[n].MinSize.width
                    n += 1
                    self.tabindex=n




            # If extra space, fit tabs to the right of the row
            if not style: # if single row,
                while n > 0 and area - tally > tabs[n-1].MinSize.width:
                    n -= 1
                    self.tabindex = n
                    tally += tabs[n].MinSize.width


            # Injects tabs calculated to fit in that row into that row
            if range(n, i):
                rows[row] = [tabs[t] for t in xrange(n, i)]
                for tab in rows[row]:
                    tab.row=row
            else:
                rows[row].append(tabs[i])
                i += 1

            if not style: break # If we're in single row, break now.
            row += 1
            n = i
        # Row calculation

        if self.rowindex >= len(rows):
            self.rowindex = len(rows) - 1

        #cycle through visible rows
        row = self.rowindex
        visible = self.tab_rows or 1

        if careful and style:
            #print "Being Careful"
            active = parentpage.active.tab
            #print active
            for ir,r in enumerate(rows):
                #print ir,r
                if active in r:
                    if ir<row:
                        #print "moving index down"
                        row = self.rowindex = ir
                    elif ir >= row + visible:
                        #print "moving index up"
                        row = ir - (visible - 1)


        # If we're closing tabs above where is visible, keep the visible
        # index "where it is"
        if len(rows) - (row + 1) < visible and len(rows) >= visible:
            row = len(rows) - visible
            self.rowindex = row

        # Place tabs!
        while row < len(rows) and row < self.rowindex + visible and len( rows[row] ) != 0:

            # if this is a row that needs to be scrunched...
            if rows.index(rows[row]) == len(rows)-1 and \
                (style or len(rows[row]) == len(tabs)):

                for t in xrange(0,len(rows[row])):
                    thistab = rows[row][t]
                    thistab.SetSize(thistab.MinSize)
                    if not t:
                        # The first tab is set to it's minimum width at x: 0
                        thistab.SetPosition((0, self.rowheight*(row-self.rowindex)))
                    else:
                        # Every other tab is placed right next to the tab
                        # before it.
                        thistab.SetPosition((rows[row][t-1].Position.x \
                                             + rows[row][t-1].Size.width,
                                             self.rowheight*(row-self.rowindex)))
                    thistab.Show(True)

            # If there are more rows than the current row...
            elif len(rows) > row:
                # Get a list of tab indices, widest to smallest.
                ordered = [rows[row].index(t)
                           for t in sorted(rows[row],
                                           key=lambda o: o.MinSize.width,
                                                         reverse=True) ]
                length = len(ordered)
                reserved=0
                o=0 # o_O ?

                # Average width of tab if all tabs are the same size, and
                # fill up all the area.
                av = (area - reserved) / (length - o)
                mark = 0
                while o < length:
                    # Loop from "current" tab to the end
                    for t in xrange(o, length):
                        tab = rows[row][ordered[t]]

                        # If this tab is larger than average...
                        if tab.GetMinSize()[0] > av:
                            # Make it it's minimum, and keep track of it
                            tab.SetSize(tab.MinSize)
                            reserved += tab.MinSize.width
                            o += 1
                            mark = o

                            # If we're not on the last tab, recalc average
                            if (length - o):
                                av=(area-reserved)/(length-o)
                        else:
                            o += 1
                            break

                # For tabs less than the average, set them to average
                for t in xrange(mark, length):
                    tab = rows[row][ordered[t]]
                    tab.SetSize((av, tab.MinSize.height))

                # For every tab in the row
                for t, tab in enumerate(rows[row]):
                    if not t: # If it's the first tab:
                        if length==1:
                            # If the row is so small it can only fit one tab,
                            # make due.
                            tab.Size = wx.Size(area, tab.MinSize.height)
                        tab.Position = wx.Point(0, self.rowheight * (row - self.rowindex))
                    else:
                        tab.Position = wx.Point(rows[row][t-1].Position.x + rows[row][t-1].Size.width,
                                                self.rowheight * (row - self.rowindex))

                    tab.Show(True)
            row += 1
        if dotoggle:
            self.Toggle()

        # If total rows is less than total rows being shown, shrink the
        # tab area so that it's only just big enough.
        if len(rows) < style or not style:
            rows_shown = len(rows)
        else:
            rows_shown = style
        if  self.Parent.SashPosition != rows_shown * self.rowheight:#self.MinSize.height
            self.MinSize = wx.Size(-1, rows_shown * self.rowheight)
            self.Parent.SetSashPosition(self.MinSize.height)
#            self.Size=self.MinSize

        # Determine if the Navi needs to enable or show arrows
        navi.Enabler()
        #self.Parent.Layout()    # Relayout self
        self.tabendex = i-1     # final tab being shown

        self.UpdateNotify()

        navi.Size = wx.Size(-1,rows_shown * self.rowheight)

    def Remove(self, target):
        'Removes the tab specified from the bar.'

        index=self.tabs.index(target)
        self.tabs.remove(target)
        #if no more tabs close window
        if len(self.tabs)==0:
            self.Notebook.window.Close()
        else:
            #if index is between index and endex and bring one tab from the left
            if index>self.tabindex and index<self.tabendex and self.tabindex>0:
                self.tabindex-=1

            if self.side_tabs:
                self.ReVgenerate(total=True)
            else:
                self.Regenerate(safe = True)


    def OnSize(self, event):
        'ReLayout the tabs if the bar on event of a resize'
        event.Skip()

        if self.side_tabs and self.tabs:
            cupb   = self.cupb
            cdownb = self.cdownb
            size   = self.Size
            tabs = self.tabs
            endex = self.tabendex

            # position and size buttons
            cupb.Position = (0,0)
            cupb.Size = (size.width, 16)
            cupb.Show()
            cupb.Enable(self.tabindex != 0)

            cdownb.Position = (0, size.height - 16)
            cdownb.Size     = (size.width, 16)
            cdownb.Show()
            cdownb.Enable(endex < len(tabs) or tabs[endex - 1].Position.y +
                           tabs[endex-1].Size.height > size.height - 16)


        sz = self.Size
        if ((sz.width != self.lastsize.width and not self.side_tabs) or (sz != self.lastsize and self.side_tabs)) and self.IsShownOnScreen():
            self.lastsize = sz
            if self.side_tabs:
                self.ReVgenerate(dotoggle = False)
            else:
                self.Regenerate(False,dotoggle = False)

        try:
            wx.CallAfter(wx.CallAfter,self.Parent.pagecontainer.active.panel.input_area.expandEvent)
        except AttributeError:
            pass

        self.Refresh(False)


    def GetTabCount(self):
        """
            Returns the number of tabs in the bar
        """
        return len([t for t in self if t])

    def NextTab(self):
        self.SetNextActive(self.ActiveTab, wrap = True)

    def PrevTab(self):
        self.SetLastActive(self.ActiveTab, wrap = True)


    def SetNextActive(self, origin,wrap=False):
        """
            Sets the tab after the curent active
            -if it does not exist does the previbus
            -or the first if wrap is true
        """
        if origin in self.tabs:
            index=self.tabs.index(origin)
            if not index < len(self.tabs)-1 and wrap:
                self.tabs[0].SetActive(True)
            elif index < len(self.tabs)-1:
                self.tabs[index+1].SetActive(True)
            elif index>0:
                self.tabs[index-1].SetActive(True)
            self.Refresh(False)

    def SetLastActive(self, origin, wrap = False):
        """
            Sets the tab before the curent active
            -if it does not exist does the next
            -or the last if wrap is true
        """
        if origin in self.tabs:
            index=self.tabs.index(origin)
            if not index > 0 and wrap:
                self.tabs[len(self.tabs)-1].SetActive(True)
            elif index >0:
                self.tabs[index-1].SetActive(True)
            elif index<0:
                self.tabs[index+1].SetActive(True)
            self.Refresh(False)

    def SyncActive(self,atab):
        """
            Moves the index and endex so that the active tab is in the bar
        """
        if not atab: return

        if self.side_tabs:
            if atab < self.tabindex:
                self.tabindex=atab
                self.ReVgenerate(True)
            else:
                thetab=self.tabs[atab]
                while atab >= self.tabendex or thetab.Position.y+thetab.Size.height > self.Size.height-16:
                    self.tabindex+=1
                    self.ReVgenerate(True)
        else:
            style = self.tab_rows
            if atab < self.rowindex:
                self.rowindex=atab
                self.Regenerate()
            elif atab > self.rowindex+style-1:
                self.rowindex=atab-style+1
                self.Regenerate()

    def OnWheel(self,event):
        """
            Event that handles mouse wheeling,
            maps the events to SetNextActive and SetLastActive
        """
        if RectS(self.Size).Contains(event.Position):
            direction = event.GetWheelRotation()
            if direction<0:
                self.SetNextActive(self.ActiveTab, True)
            elif direction>0:
                self.SetLastActive(self.ActiveTab, True)

    @property
    def Notebook(self):
        return self.Parent

    @property
    def Manager(self):
        return self.Notebook.manager

    @property
    def ActiveTab(self):
        active = self.Notebook.pagecontainer.active
        if active is not None:
            return active.tab

    def OnButton(self,event):
        """
            The button events for vertical alignment for up and down
        """
        if event.GetId()==CUPID:
            if self.tabindex > 0:
                self.tabindex -= 1
                self.ReVgenerate(total = True)
        elif event.GetId()==CDOWNID:
            if self.tabendex<len(self.tabs) or self.tabs[self.tabendex-1].Position.y+self.tabs[self.tabendex-1].Size.height>self.Size.height-16:
                self.tabindex+=1
                self.ReVgenerate(total=True)

        self.UpdateNotify()

    def NotifyDrag(self, origin):
        """
            When a tab is dragged this is called to start the tabbar handling dragging
            origin - tab being dragged
        """
        # Lets the TabMan know a tab as been dragged
        self.dragorigin = origin
        origin.SetCursor(wx.StockCursor(wx.CURSOR_NO_ENTRY))
        self.Manager.Notify(self.Notebook)


    def DragCalc(self,point):
        """
            This does the dragging calculations for the tabs
        """

        sidetabs = self.side_tabs

        # if here is no local origin tab but there is a remote source identified in TabMan
        if not self.dragorigin and self.Manager.source:
            #setting a local drag origin
            master = self.Manager.source
            dragorigin=master.tabbar.dragorigin
            # announcing to TabMan it is expecting a tab
            self.Manager.Request(self.Notebook)
        # if there is a local origin use that
        else:
            dragorigin=self.dragorigin

        # if dragtarget is out of date find what you're dragging to
        if not self.dragtarget or not self.dragtarget.Rect.Contains(point):

            wap = wx.FindWindowAtPointer()
            self.dragtarget = wap if isinstance(wap,Tab) else None
            self.dragside   = None

        # if there is a tab as target
        if self.dragtarget and self.dragtarget != dragorigin:
            dtrect=self.dragtarget.Rect
            # data to decide what side the tab would be dropped on
            if not sidetabs:
                x  = point[0] - dtrect.x
                x2 = dtrect.width / 2
            else:
                x  = point[1] - dtrect.y
                x2 = dtrect.height / 2
            # make the left/top or right/bottom decision
            if x <= x2:#left/top
                if self.dragside!=False:
                    self.dragside=False
                    if not sidetabs:
                        self.DrawDropMarker(dtrect.x, dtrect.y)# + (dtrect.height // 2)
                    else:
                        self.DrawDropMarker(dtrect.x, dtrect.y)# + dtrect.width // 2

            elif not self.dragside:#right/bottom
                self.dragside=True
                if not sidetabs:
                    self.DrawDropMarker(dtrect.x+dtrect.width,dtrect.y)#+(dtrect.height//2)
                else: self.DrawDropMarker(dtrect.x,dtrect.y+dtrect.height)#+dtrect.width//2
            self.SetFocus()
        # if being dropped in the whitespace of the TabBar
        elif (dragorigin and self.dragtarget!=dragorigin) or (dragorigin==None and self.dragtarget==None) and self.Rect.Contains(point):
            # find what row the tab is being dropped in
            if not sidetabs:
                row=self.rows[(point[1]//self.rowheight)+self.rowindex]
                tab=row[len(row)-1]
                self.dragside=True
            # or in vertical if at the beginning or end
            else:
                if point.y>self.rowheight:
                    tab=self.rows[0][len(self.rows[0])-1]
                    self.dragside=True
                else:
                    tab=self.rows[0][0]
                    self.dragside=False
            dtrect=tab.Rect
            #Place marker
            if not sidetabs: self.DrawDropMarker(dtrect.x+dtrect.width,dtrect.y)#+(dtrect.height//2)
            elif self.dragside==True: self.DrawDropMarker(dtrect.x,dtrect.y+dtrect.height)#+dtrect.width//2
            else: self.DrawDropMarker(dtrect.x+dtrect.width/2,dtrect.y)
            self.SetFocus()
            #cleanup
            self.dragtarget=tab

        else:#if not in tabbar anymore don't show arrow
            self.dropmarker.Show(False)

    def DragFinish(self,new=False):
        """
        Ends dragging and does any rearranging if required
        """

        if not wx.IsDestroyed(self.dragorigin):
            self.dragorigin.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

        if self.dragorigin and self.dragorigin.previewtabs:
            # Destroy the preview tab
            self.dragorigin.previewtabs.Stop()
            self.dragorigin.previewtabs = None

        rect       = RectPS(self.Notebook.ClientToScreen(self.Position), self.Size)
        parentrect = self.Notebook.window.Rect
        mousepos   = wx.GetMousePosition()
        manager    = self.Manager

        #if released out of the window...
        if not new and ((manager.destination and not parentrect.Contains(mousepos)) or not rect.Contains(mousepos)):
            if self.ActiveTab==self.dragorigin:
                self.SetNextActive(self.dragorigin)
            self.dragorigin.Show(False)

            #If no or invalid destination in manager create a new window and sets it destination
            dest = manager.destination
            if not dest or not dest.tabbar.Rect.Contains(dest.ScreenToClient(wx.GetMousePosition())):
                # FIXME: SWIG doesn't like subtracting a wx.Size from a wx.Point, so do it the hard way
                # until the SIP migration is finished.
                originsize = self.dragorigin.GetSize()
                newpoint = wx.Point(mousepos[0] - originsize[0], mousepos[1] - originsize[1])
                destination = self.Notebook.winman.NewWindow(newpoint, self.Notebook.window.GetSize()).notebook
            #else set the destination to the manager's destination
            else:
                destination = dest

            #clear tabman's destination
            manager.Request()

            # Grab a reference to the tab's page
            page = self.dragorigin.page

            # Make the tab "forget" about the page
            self.Notebook.did_remove(page.panel)
            del self.dragorigin.page
            del page.tab

            # Remove the tab from the tabs list, and destroy the wxWindow
            self.tabs.remove(self.dragorigin)

            self.dragorigin.Close()

            # remove page from this notebook and insert it into the target notebook
            #page.Parent.RemoveChild(page)
            destination.Insert(page, False)

            # cleanup
            manager.Notify()
            self.dragorigin=None

            # re-sort tabs
            if self.side_tabs:
                self.ReVgenerate(True)
            else:
                self.Regenerate(safe = True)

        # if released inside of the window
        # used both for moving within a window and as the last step of a
        # interwindow move in case of interwindow tab has already been moved to
        # this window at the end of the list and all that is left is to move it
        # to the correct position.
        elif self.dragtarget and self.dragorigin and self.dragorigin!=self.dragtarget and self.Rect.Contains(self.Notebook.ScreenToClient(mousepos)):
            #remove the tab from the list
            self.tabs.remove(self.dragorigin)

            #decide which side of the target the tab should be dropped
            pos = self.tabs.index(self.dragtarget) + (1 if self.dragside else 0)

            # Reinsert the tab in it's new position
            self.tabs.insert(pos, self.dragorigin)

            after = self.tabs[pos+1] if pos+1 < len(self.tabs) else None
            if after is not None:
                after = after.page.panel

            # call after so that windows are all in their correct places
            wx.CallAfter(self.Notebook.did_rearrange, self.dragorigin.page.panel, after)

#            # Resort
            if self.side_tabs:
                self.ReVgenerate(True)
            else:
                self.Regenerate()
        elif new:
            if self.side_tabs:
                self.ReVgenerate(True)
            else:
                self.Regenerate()

        #if there is a dragorigin run onMouseLeave on it to reset it's look
        if self.dragorigin:
            self.dragorigin.OnMouseLeave()

        #local cleanup
        self.dropmarker.Show(False)
        self.dragorigin=None
        self.dragtarget=None

        #destination and manager cleanup
        dest = manager.destination
        if dest:
            dest.tabbar.dragorigin=None
            dest.tabbar.dragtarget=None

        manager.Request()
        manager.Notify()

        if len(self.tabs)==0: self.Notebook.window.Close()

    def DrawDropMarker(self,x,y):
        """
        Places the marker for where to drop the tab
        x and y are center position, saves calculation that way
        """

#        if self.side_tabs:
#            self.dropmarker.SetSize((self.Size.width - self.dropmarkeroverlay, -1))
#        else:
#            self.dropmarker.SetSize((-1, self.rowheight - self.dropmarkeroverlay))
        self.dropmarker.Teleport(self.ClientToScreen((x, y+self.dropmarkeroffset)))

        if not self.dropmarker.IsShown():
            self.Manager.ShowDropMarker(self.dropmarker)

    def Toggle(self, switch = None):
        'Toggle whether the tabbar is hidden or shown.'

        if pref('tabs.hide_at_1', True) and len(self.tabs) <= 1 and not switch:
            self.Notebook.Split(False)

            #make sure the content of the IM win resizes if tabbaar hides
            self.ProcessEvent(wx.CommandEvent(wx.wxEVT_SIZE))
        else:
            self.Notebook.Split(True)


    def UpdateNotify(self):

        frows = self.flagedrows
        frows.clear()

        # Resort
        if self.side_tabs:
            tabs=self.tabs
            for i, tab in enumerate(tabs):
                if tab.notified:
                    frows.add(i)
                elif i in self.flagedrows:
                    frows.remove(i)

            self.cupb.SetNotify(len(frows) and min(frows) < self.tabindex)
            self.cdownb.SetNotify(len(frows) and (max(frows) >= self.tabendex or
                                                  tabs[max(frows)].Position.y + tabs[max(frows)].Size.height > self.Size.height - 16))
        else:
            for i, row in enumerate(self.rows):
                flaged = False
                for tab in row:
                    if tab and tab.notified:
                        flaged = True
                        frows.add(i)
            self.navi.upb.SetNotify(len(frows) and min(frows)<self.rowindex)
            self.navi.downb.SetNotify(len(frows) and max(frows)>self.rowindex + self.tab_rows - 1)

