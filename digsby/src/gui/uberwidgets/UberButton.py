import wx
from wx import Size, VERTICAL, HORIZONTAL, AutoBufferedPaintDC, Color, Rect, RectS
LEFT_VCENTER = wx.ALIGN_LEFT| wx.ALIGN_CENTRE_VERTICAL


from gui.textutil import GetTextExtent,DeAmp,TruncateText
import UberEvents
from gui import skin
from gui.windowfx import ApplySmokeAndMirrors #@UnresolvedImport
from util.primitives.funcs import do
from gui.skin.skinobjects import SkinGradient,Margins
from common import prefprop
from gui.textutil import default_font
from gui.uberwidgets import UberWidget

NATIVE_BACKGROUNDS = [4,
                      1,
                      3,
                      2,
                      3,
                      3,
                      2
                      ]

from gui.uberwidgets.keycatcher import KeyCatcher

class UberButton(UberWidget, wx.PyControl):
    '''
    Skinnable buttons.

    Also acts as a wrapper for wx.Bitmap button to draw native looking buttons
    with icons and labels can be also used to make menu buttons and checkbox
    like toggle buttons.
    '''

    def __init__(self, parent, id = -1, label='', skin=None, icon=None,
                 pos=wx.DefaultPosition, size=None, style=HORIZONTAL,
                 type=None, menu=None, menubarmode=False, onclick = None):
        """
        Usage:
            UberButton(parent,id,label,skin,icon,pos,size,style,type,menu)
            -skin  - instead of detecting skins presence lke most UberGUI
                     this takes the skin as an argument from the parent
                     this allows different skins to be set to different
                     buttons at the same time
                     if not assigned will look OS native

            -icon  - The icon to show up on the button
                     Note: the button resizes to fit the icon, not vice versa

            -pos   - position of the button

            -size  - size of the button, this is actualy ignored and will
                     likely be adjusted to affect restraint size later

            -style - wx.HORIZONTAL - Icon centered over label centered on button
                     wx.VERTICAL - Icon spaced from left with label to the right

            -type  - None - normal button
                     combo - no behavior changes, only changes the drawing code
                             on native butons
                     toggle - button toggles True and False, needs visual
                              notification in native mode
                     menu - does not return an event, adds a dropdown icon
                            to the rightside of the button, when toggled on
                            displays the menu associated to it
            -menu  - the menu to drop down when the button is clicked if
                     type is menu
        """

        wx.PyControl.__init__(self, parent, id=id, pos=pos, style = wx.NO_BORDER | wx.FULL_REPAINT_ON_RESIZE)

        if type=="combo":
            UberWidget.__init__(self, 'COMBOBOX' )
        else:
            UberWidget.__init__(self, "button" )



        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.label=label
        if label:
            self.RegAccel(label)

        self.notified = False
        self.active   = False
        self.isdown   = False
        self.hovered  = False

        self.state = 1
        self.menu = menu if type == 'menu' else None
        if menu is not None and hasattr(menu,'OnDismiss'):
            menu.OnDismiss += lambda: self.AddPendingEvent(wx.MenuEvent(wx.wxEVT_MENU_CLOSE, menu.Id))

        if icon:
            self.icon = icon
            self.MakeDicon()
        else:
            self.icon = None

        self.style = style
        self.type  = type
        self.menubarmode = menubarmode
        self.ssize = wx.Size(0,0)
        self.staticwidth = None

        if size:
            self.autoscale = False
        else:
            self.autoscale=True

        self.native = None
        self.Sizer  = wx.BoxSizer(HORIZONTAL)

        self.SetSkinKey(skin,True)

        Bind = self.Bind
        Bind(wx.EVT_MOVE, lambda e: self.Refresh()),
        Bind(wx.EVT_PAINT, self.OnPaint),
        Bind(wx.EVT_SET_FOCUS,lambda e: self.Refresh()),
        Bind(wx.EVT_KEY_DOWN,self.OnKeyDown),
        Bind(wx.EVT_KEY_UP,self.OnKeyUp),
        Bind(wx.EVT_KILL_FOCUS,self.OnKillFocus),
        Bind(wx.EVT_LEFT_DOWN,self.OnLeftDown),
        Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown),
        Bind(wx.EVT_LEFT_UP,self.OnLeftUp),
        Bind(wx.EVT_ENTER_WINDOW,self.OnMouseIn),
        Bind(wx.EVT_LEAVE_WINDOW,self.OnMouseOut),
        Bind(wx.EVT_MOTION,self.OnMotion),
        Bind(wx.EVT_MENU_CLOSE, lambda e: (self.Active(False),self.OnMouseOut()))
        Bind(wx.EVT_SHOW,         self.OnShow)

        if onclick is not None:
            if not hasattr(onclick, '__call__'):
                raise TypeError('onclick must be callable')
            self.Bind(wx.EVT_BUTTON, lambda e: (e.Skip(), onclick()))

    def __repr__(self):
        try:
            return '<UberButton \'%s\'>' % self.label
        except:
            return '<UberButton %s>' % id(self)

    def SetAlignment(self,alignment):
        self.style=alignment
        self.Calcumalate()

    def GetAlignment(self):
        return self.style

    Alignment = property(GetAlignment,SetAlignment)


#    def SetSize(self,size = None):
#
#        self.autoscale = not size
#
#        wx.Window.SetSize(self,size or self.ssize)
#
#    Size = property(wx.Window.GetSize,SetSize)


    def SetStaticWidth(self,width=None):
        """This forces the button to not auto resize it's width."""

        self.staticwidth = width
        self.Calcumalate()

    def OnMotion(self,event):
        """Ensures mouse release."""

        if self.native:
            event.Skip()
            return

        r = RectS(self.Size)
        if self.HasCapture() and not event.LeftIsDown() and \
            not r.Contains(event.Position):
            self.ReleaseAllCapture()

    @property
    def KeyCatcher(self):
        try:
            return self.Top._keycatcher
        except AttributeError:
            k = self.Top._keycatcher = KeyCatcher(self.Top)
            return k

    def UpdateSkin(self):
        'Simply gets a skin and sets it all up.'

        key = self.skinkey
        native= not key


        if native and self.uxthemeable:
            self.rendernative = True
            self.destroy_native()
            self.OpenNativeTheme()

            skinget = skin.get

            self.menuicon = skinget('appdefaults.dropdownicon')
            self.padding  = (5,5)
            self.margins  = Margins([0,0,0,0])
            self.Font     = default_font()

            self.fontcolors = [wx.BLACK] * 7

            self.backgrounds = NATIVE_BACKGROUNDS
            self.Cut()

        elif native:
            if not self.native:
                self.native = wx.Button(self,style=wx.BU_EXACTFIT)
                self.native.SetLabel(self.label)
                self.Sizer.Add(self.native, 1, wx.EXPAND)
                self.Layout()
                self.Cut()

        else:
            self.rendernative = False
            self.destroy_native()
            skinget = skin.get
            skinroot = skin.get(key)
            #s = lambda k, default = sentinel: skinget('%s.%s' % (key, k), default)

            s = skinroot.get
            self.menuicon = s('menuicon', skinget('appdefaults.dropdownicon'))
            self.padding  = s('padding', (5,5))
            self.margins  = s('margins', Margins([0,0,0,0]))
            self.Font     = s('font',    default_font())


            fc = skinroot.get('fontcolors', {})
            s = fc.get
            self.fontcolors = [s('disabled',    Color(125,125,125)),
                               s('normal',      wx.BLACK),
                               s('active',      wx.BLACK),
                               s('hover',       wx.BLACK),
                               s('activehover', wx.BLACK),
                               s('down',        wx.BLACK),
                               s('notify',      wx.WHITE)]

            bgs = skinroot.get('backgrounds', {})
            def s(key, default):
                try: return bgs[key]
                except: return default()

            disabled    = s('disabled',    lambda: SkinGradient('vertical', [Color(125,125,125), Color(237,237,237)]))
            normal      = s('normal',      lambda: SkinGradient('vertical', [Color(200,255,200), Color(85,255,85)]))
            active      = s('active',      lambda: SkinGradient('vertical', [Color(200,255,238), Color(85,255,238)]))
            hover       = s('hover',       lambda: normal)
            activehover = s('activehover', lambda: active)
            down        = s('down',        lambda: SkinGradient('vertical', [Color(0,125,0),     Color(00,204,00)]))
            notify      = s('notify',      lambda: SkinGradient('vertical', [Color(255,255,200), Color(255,255,85)]))

            self.backgrounds = [disabled,
                                normal,
                                active,
                                hover,
                                activehover,
                                down,
                                notify]

        self.Calcumalate()
        self.Refresh()

    def destroy_native(self):
        '''Destroys the native peer button, if there is one.'''

        if self.native:
            self.native.Show(False)
            self.Sizer.Detach(self.native)
            self.native.Destroy()
            self.native = None

    def Enable(self,switch=True):
        """
        Enables or disables the button
        Enables by default
        (maybe change to toggle?)
        """
        if not self.native:
            wx.PyControl.Enable(self, switch)
            if switch:
                events=[
                    (wx.EVT_LEFT_DOWN,    self.OnLeftDown),
                    (wx.EVT_LEFT_DCLICK,  self.OnLeftDown),
                    (wx.EVT_LEFT_UP,      self.OnLeftUp),
                    (wx.EVT_ENTER_WINDOW, self.OnMouseIn),
                    (wx.EVT_LEAVE_WINDOW, self.OnMouseOut)
                ]
                do(self.Bind(event, method) for (event,method) in events)

            else:
                events=[wx.EVT_LEFT_DOWN,
                        wx.EVT_LEFT_DCLICK,
                        wx.EVT_LEFT_UP,
                        wx.EVT_ENTER_WINDOW,
                        wx.EVT_LEAVE_WINDOW]
                do(self.Unbind(event) for event in events)

            self.state=(1 if switch else 0)

            if self.ScreenRect.Contains(wx.GetMousePosition()):
                self.GetHover()
            else:
                self.ReleaseHover()

        else:
            self.native.Enable(switch)

        self.Refresh()

    def SetMenuBarMode(self,switch=None):
        """
        This turns on menubarmode

        This effects
            - the showing of the dropmenu icon
            - Ampersan denoted underlining
            - Informing a menubar about focus events
            - and some size and mouse capture logic differences logic
        """
        if switch:
            self.menubarmode=switch
        else:
            self.menubarmode= not self.menubarmode

    def MakeDicon(self):
        'Greys out an icon.'

        self.dicon = self.icon.Greyed.WXB

    def SetIcon(self, icon = None):
        """
        Changes icon for the button
        if no arguments speified or None, removes the icon from the button
        """
        if icon:
            self.icon = icon
            self.MakeDicon()
        else:
            self.icon = self.dicon = None

        self.Calcumalate()
        self.Refresh()

    def SetNotify(self, switch):
        self.notified = switch
        self.Refresh()

    def RegAccel(self,label = ""):
#        oldLabel = self.label
#        i = oldLabel.find('&')
#        if i != -1 and i < len(oldLabel) - 1 and oldLabel[i+1] != '&':
#            self.KeyCatcher.RemoveDown('alt+%s' % oldLabel[i+1], self.FakeClick)

        i = label.find('&')
        if i != -1 and i < len(label) - 1 and label[i+1] != '&':
#            print self, 'adding alt+%s' % label[i+1]
            self.KeyCatcher.OnDown('alt+%s' % label[i+1], self.FakeClick)

    def SetLabel(self,label =""):
        """
        Changes icon for the button
        if no arguments speified or an empty string, removes the label from the button
        """

        self.RegAccel(label)

        self.label=label
        if self.native:
            self.native.SetLabel(label)
        self.Calcumalate()
        self.Refresh()


    def GetLabel(self):
        return self.label

    Label = property(GetLabel,SetLabel)

    def FakeClick(self, event = None):
        if self.type == 'toggle':
            # If this button is a toggle button, we need to switch
            # states and throw a different type of command event.
            self.Active()
            self.SendButtonEvent(wx.wxEVT_COMMAND_TOGGLEBUTTON_CLICKED)
        if self.type=='menu' and not self.active:
            self.CallMenu()
        elif not self.type == 'menu':
            self.SendButtonEvent()

    def Calcumalate(self):
        """
        Calculates the positioning of all content of the button and
        sets the size of the button based off of these calculations
        """
        if self.native:
            self.Size = self.MinSize = self.native.BestSize
            #self.Fit()
            self.Parent.Layout()
            ApplySmokeAndMirrors(self)
            return

        label = DeAmp(self.label)

        if self.icon:
            iconwidth, iconheight = self.icon.Width, self.icon.Height
        else:
            iconwidth, iconheight = (0, 0)
        if label != '':
            labelwidth, labelheight = GetTextExtent(label, self.Font)[0], self.Font.Height
        else:
            labelwidth, labelheight = (0, 0)

        self.labelsize = Size(labelwidth, labelheight)

        margins=self.margins

        sx, sy = self.padding
        swidth  = 0
        sheight = 0

        #icon & label caclulations
        if self.icon and label != '':
            if self.style == HORIZONTAL:
                swidth += iconwidth + labelwidth + 3*sx
                if iconheight>labelheight:
                    sheight+=iconheight+2*sy
                    iy=sy
                else:
                    sheight+=labelheight+2*sy
                    iy=sy+labelheight//2-iconheight//2

                self.iconcurser  = wx.Point(sx,iy)
                self.labelcurser = wx.Point(self.iconcurser.x+iconwidth+sx,self.iconcurser.y+iconheight/2-labelheight/2)

                if self.menu and not self.menubarmode and self.menuicon:
                    swidth+=self.menuicon.Width+sx

                self.ssize = Size(margins.left+swidth+margins.right,margins.top+sheight+margins.bottom)

            elif self.style == VERTICAL:
                labelwin = labelwidth > iconwidth
                if labelwin:
                    swidth += labelwidth + 2 * sx
                else:
                    swidth += iconwidth + 2 * sx
                sheight += iconheight + labelheight + 3 * sy

                lx=sx
                if labelwin:
                    self.iconcurser  = wx.Point(lx + labelwidth/2-iconwidth/2,sy)
                    self.labelcurser = wx.Point(lx,self.iconcurser.y+iconheight+sy)
                else:
                    self.iconcurser  = wx.Point(lx,sy)
                    self.labelcurser = wx.Point(lx + iconwidth/2-labelwidth/2,self.iconcurser.y+iconheight+sy)


                if self.menu and not self.menubarmode:
                    swidth += self.menuicon.Width+sx

                self.ssize = Size(margins.left + swidth  + margins.right,
                                  margins.top  + sheight + margins.bottom)

        # Just icon caclulations
        elif self.icon:
            swidth  += iconwidth  + 2 * sx
            sheight += iconheight + 2 * sy

            self.iconcurser = wx.Point(sx, sy)

            if self.menu and not self.menubarmode:
                swidth += self.menuicon.Width + sx

            self.ssize = Size(margins.left + swidth  + margins.right,
                              margins.top +  sheight + margins.bottom)

        # Just label caclulations
        elif label != '':
            swidth  += labelwidth  + 2 * sx
            sheight += labelheight + 2 * sy

            self.labelcurser = wx.Point(sx, sy)

            if self.menu and not self.menubarmode:
                swidth += self.menuicon.Width + sx


            self.ssize = Size(margins.left + swidth + margins.right, margins.top + sheight + margins.bottom)

        elif self.menu is not None and not self.menubarmode:
            swidth  += self.menuicon.Width
            sheight += self.menuicon.Height

            self.ssize = Size(swidth + 2 * sx + margins.x, sheight + 2 * sy+margins.y)
        else:
            self.ssize = Size(16, 16)

        if self.staticwidth:
            self.ssize.width = self.staticwidth

        self.MinSize = self.ssize
        self.InvalidateBestSize()

        self.Parent.Layout()

    def DoGetBestSize(self):
        self.CacheBestSize(self.ssize)
        return self.ssize

    side_tabs = prefprop('tabs.side_tabs', False)

    def OnPaint(self,event):
        "Draws the button's background."

        # excape if native
        if self.native:
            event.Skip()
            return

        rect = RectS(self.Size)


        parent, grandparent = self.Parent, self.GrandParent
        if parent.__class__.__name__ == "Tab" and self.side_tabs:
            #Clipping the button for when partualy hidden
            cliptangle = RectS(self.Size)
            sy  = self.Rect.y
            sw, sh  = self.Size
            py  = parent.Position.y
            pph = grandparent.Size.height - 16

            if parent.Position.y + parent.Size.height > grandparent.Size.height-16 and \
               sy + sh + py > pph:
                cliptangle = Rect(0,0,sw,pph-(sy+py))
                dc = wx.PaintDC(self)
                dc.SetClippingRect(cliptangle)
        else:
            dc = AutoBufferedPaintDC(self)

        # actual drawing of background
        currentstate=5 if self.isdown else \
                     6 if self.state and self.notified else \
                     self.state+(self.hovered*2) if self.state else \
                     0

        if self.rendernative:

            nrect = rect if self.type=='combo' else rect.Inflate(1,1)
            #wx.RendererNative.Get().DrawPushButton(self,dc,nrect,self.backgrounds[currentstate])
            part = 1
            state = self.backgrounds[currentstate]
            self.DrawNativeLike(dc,part,state,nrect)
        else:
            background = self.backgrounds[currentstate]
            from cgui import SplitImage4
            if isinstance(background,SplitImage4):
                ApplySmokeAndMirrors(self, background.GetBitmap(self.Size))
            else:
                ApplySmokeAndMirrors(self)
            background.Draw(dc, rect)

        #TODO: Backgroundless icon buttons

        if not (self.type == 'combo' and self.rendernative):
            self.DrawContent(dc)

    def OnShow(self, e):
        'Invoked on EVT_SHOW'

        # Don't leave menus stranded if the button is being hidden.
        if not e.GetShow() and self.menu and not wx.IsDestroyed(self.menu) and self.menu.IsShown():
            self.menu.Hide()

    def DrawContent(self,dc):
        'Draws the contents of the button to the DC provided.'
        offset = ((self.Size.width / 2 - self.ssize[0] / 2) if (not self.menu or self.label!='' and self.icon and self.style==VERTICAL or self.label=='') and not (self.label!='' and self.icon and self.style==HORIZONTAL) else 0,self.Size.height / 2 - self.ssize[1] / 2)
        ml, mt, mr, mb = self.margins

        #Draw Icons
        if self.icon:
            dc.DrawBitmap(self.icon if self.IsEnabled() else self.dicon,
                          self.iconcurser[0] + offset[0] + ml, self.iconcurser[1] + offset[1] + mt, True)
        #Draw Labels
        if self.label != '':

            dc.Font=self.Font

            #Set the font color
            currentstate = 6 if  self.state and self.notified else \
                           5 if self.isdown else \
                           self.state + (self.hovered * 2) if self.state else \
                           0

            dc.TextForeground = self.fontcolors[currentstate]

            dc.Font=self.Font
            labelcurser = self.labelcurser

            loffset=(max(offset[0],0),max(offset[1],0))
            w=min(self.labelsize.x,self.Rect.Width - labelcurser.x - loffset[0] - self.padding[0] - mr - ((self.menuicon.Width +self.padding[0]) if self.menu and not self.menubarmode else 0))+2
            lrect = Rect(labelcurser.x + loffset[0] + ml,labelcurser.y + loffset[1] + mt,w,self.labelsize[1])

#            dc.Pen=wx.Pen(wx.Color(0,255,0))
#            dc.Brush=wx.TRANSPARENT_BRUSH
#            dc.DrawRectangleRect(lrect)

            dc.DrawLabel(TruncateText(self.label.replace('&', ''), w, None, dc),
                         lrect, LEFT_VCENTER,
                         indexAccel = self.label.find('&'))

        #Lastly draw the dropmenu icon if there is a menu
        if self.type == 'menu' and not self.menubarmode:
            dc.DrawBitmapPoint(
                self.menuicon,
                wx.Point(self.Size.width-self.menuicon.Width - self.padding[0] - mr,
                (self.Size.height-(mt+mb))/2+mt-self.menuicon.Height/2),
                True
            )


    def Active(self, switch=None):
        """
        Used for menu and toggle buttons.

        Toggles active state or sets it to the provided state.
        """

        if self.state:
            old_active = self.active
            self.active = not self.active if switch is None else switch
            self.state = 2 if self.active else 1

            if old_active != self.active:
                self.Refresh(False)

    def IsActive(self):
        return self.active

    def OnKillFocus(self,event):
        """
        Part of an attempted tab-traversal fix, might work, might not.
        """

        if self.native:
            event.Skip()
            self.Refresh()
            return

        if self.isdown:
            self.OnMouseOut(event)
        self.Refresh()

    def OnKeyDown(self,event):
        """
        Used to allow spacebar to emulate mousedown
        """

        if self.native:
            event.Skip()
            self.Refresh()
            return

        if event.KeyCode==wx.WXK_SPACE:
            if not self.isdown and not wx.LeftDown(): self.OnLeftDown(event)
        else:
            event.Skip()
            self.Refresh()

    def OnKeyUp(self,event):
        """
        Allow spacebar to emulate mouse up
        """

        if self.native:
            event.Skip()
            self.Refresh()
            return

        if event.KeyCode==wx.WXK_SPACE:
            if self.isdown and not wx.LeftDown(): self.OnLeftUp(event)
        else:
            event.Skip()

    def OnLeftDown(self,event=None):
        'Left mouse down handling.'

        if self.native:
            self.isdown=True
            event.Skip()
            self.Refresh()
            return

        if self.isdown:
            self.OnMouseOut(event)
            return

        self.isdown=True

        if not self.HasCapture():
            self.CaptureMouse()

        self.SetFocus()

        if self.type == 'menu':
            if not self.active:
                self.CallMenu()
            elif self.menu:
                self.Active(False)
                self.menu.Dismiss()

        self.Refresh()

    def SendButtonEvent(self, type = None):
        """
        fakes a button event
        """
        eventType = type or wx.wxEVT_COMMAND_BUTTON_CLICKED
        evt = wx.CommandEvent(eventType, self.Id)
        evt.EventObject = self
        self.AddPendingEvent(evt)

    def OnLeftUp(self,event):
        'Left mouse up handling.'

        if self.native:
            self.isdown=False
            event.Skip()
            self.Refresh()
            return

        self.ReleaseAllCapture()

        if self.isdown:
            self.isdown=False

            #If mouse is released over the button
            if (event.m_x>=0 and event.m_x<=self.Size.x and event.m_y>=0 and event.m_y<=self.Size.y) or hasattr(event,'KeyCode') and event.KeyCode==wx.WXK_SPACE:
                if self.type == 'toggle':
                    # If this button is a toggle button, we need to switch
                    # states and throw a different type of command event.
                    self.Active()
                    self.SendButtonEvent(wx.wxEVT_COMMAND_TOGGLEBUTTON_CLICKED)
                elif not self.type == 'menu':
                    self.SendButtonEvent()

            self.Refresh()

    def GetHover(self):
        """
        Mouse over detection for hover state and menubar mouse over open
        """

        self.hovered = True
        self.Refresh()

        event = UberEvents.UBOver(source=self)
        self.Parent.AddPendingEvent(event)

    def OnMouseIn(self,event):
        "Mouse over handling."

        if not event.LeftIsDown() or self.menubarmode:
            self.GetHover()

        if self.native:
            event.Skip()
            return

        elif self.HasCapture():
            # Mouse left is still down, has come back to our rectangle: depress
            self.isdown = True
            self.Refresh()

    def OnMouseOut(self,event = None):
        'Mouse out handling.'

        self.isdown = False

        if self.native:
            event.Skip()
            return

        if self.menubarmode:
            self.ReleaseAllCapture()

#        if not self.menubarmode:
        self.ReleaseHover()

        self.Refresh()

    def ReleaseHover(self):
        'Un-hover the button.'

        self.hovered=False
        self.Refresh()

        event=UberEvents.UBOut(source=self)
        self.Parent.AddPendingEvent(event)

    def CallMenu(self):
        'Click (down then up) handling.'

        self.Active()
        if self.active:
            event = wx.MenuEvent(wx.wxEVT_MENU_OPEN, -1)
            event.SetEventObject(self.menu)
            self.Top.ProcessEvent(event)
            self.ReleaseAllCapture()
            self.menu.Display(self)


    def GetValue(self):
        return self.active

    def SetValue(self,v):
        self.active = v
        self.Refresh()

    Value = property(GetValue, SetValue)

    def AcceptsFocusFromKeyboard(self):
        return not self.menubarmode

    def AcceptsFocus(self):
        return not self.menubarmode
