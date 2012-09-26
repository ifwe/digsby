import wx
from gui.uberwidgets.uberwidget import UberWidget
from gui.textutil import CopyFont,default_font,GetTextWidth
from gui.skin.skinobjects import SkinColor
from gui import skin

from gui.toolbox.refreshtimer import refreshtimer

#TODO: This should be replaced with Tenjin templates similar to how Social Networks are handled
class ErrorPanel(wx.Panel,UberWidget):
    """
        Panel used to display errors in the infobox
    """
    def __init__(self,parent):
        wx.Panel.__init__(self,parent,-1)

        self.link = ''
        self.linkhovered = False #True if mouse is in the link rect
        self.linkdown = False #True if the mouse button was pushed while in link rect

        self.message = None

        self.UpdateSkin()

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, lambda e:None)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ENTER_WINDOW,self.OnMouseIn)
        self.Bind(wx.EVT_LEAVE_WINDOW,self.OnMouseOut)
        self.Bind(wx.EVT_MOTION,self.OnMouseMotion)
        self.Bind(wx.EVT_LEFT_DOWN,self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP,self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK,lambda e: (self.OnLeftDown(e),self.OnLeftUp(e)))


        self.Show(False)

    def OnSize(self,event):
        """
            This changes the link position when the size of the error panel
            changes.
        """
        if self.link:
            linksize=self.linkrect.Size
            if self.link:
                self.linkrect = wx.Rect(self.Size.width-linksize.width-self.padding.x,self.Size.height-linksize.height-self.padding.y,*linksize)
        self.Refresh(False)


    def UpdateSkin(self):
        """
            The Usual
        """
        key = 'infobox'

        if skin.get(key,False):
            s = lambda k,d: skin.get('%s.%s'%(key,k),d)
        else:
            s = lambda k,d: d

        self.padding = s('padding', lambda: wx.Point(2, 2))
        self.labelf = s('fonts.title',lambda: default_font())
        self.labelfc = s('fontcolors.title', wx.BLACK)
        self.linkf = CopyFont(s('fonts.link',lambda: default_font()), underline=True)
        self.linkfc = s('fontcolors.link', wx.BLUE)
        self.bg = s('backgrounds.email', lambda: SkinColor(wx.WHITE))

    def OnPaint(self,event):
        """
            Custom paint, nothing special
        """
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)

        dc.Font = self.labelf
        dc.TextForeground = self.labelfc

        self.bg.Draw(dc,rect)

        rect2 = wx.Rect(0,0,self.Size.width,self.Size.height-(self.linkrect.Size.height if self.link else 0))


        message = self.message
        dc.DrawLabel(message() if callable(message) else message,rect2,wx.ALIGN_CENTER)

        if self.link:
            dc.Font = self.linkf
            dc.TextForeground = self.linkfc
            dc.DrawLabel(self.link,self.linkrect)


    def Error(self, message = None, link = None, callback = None):
        """
            This shows the panel with the message provided.
            Has a link in the lower right if a link string and callback are provided.
            If message is None, the panel is hidden.
            If the message is a callable, then the panel is added to the refresh
            timer and message is called every 1 second, expecting a string to be
            returned.
        """

        self.message = message

        #destroy old link if there is one
        self.link=''

        if message:
            # if link and callback are provided, make a ClearLink object
            if link and callback:
                self.linkcb = lambda *a: (wx.GetTopLevelParent(self).Hide(), callback(*a))
                self.link = link
                linksize = wx.Size(GetTextWidth(link,self.linkf),self.linkf.Height)
                self.linkrect = wx.Rect(self.Size.width-linksize.width-self.padding.x,self.Size.height-linksize.height-self.padding.y,*linksize)

            self.Show(True)

            self.MinSize = wx.Size(-1, 5 * max(self.labelf.Height, self.linkf.Height))

            self.GrandParent.DoSizeMagic()
            self.Refresh()
        else:
            self.Show(False)

        #if message is a callable, register with refresh timer
        if callable(message):
            refreshtimer().Register(self)
        else:
            refreshtimer().UnRegister(self)


    def SkimIt(self,height):
        """
            This is just for compatibility with EmailList and ProfileBox
        """
        return height

    def OnLeftDown(self,event):
        """
            Detects left mouse button down events for emulation of links and
            buttons
        """

        if self.linkhovered:
            self.linkdown = True

    def OnLeftUp(self,event):
        """
            Detects left mouse button up events for emulation of links and
            buttons
        """

        #If link is down
        if self.linkdown:
            #And if the pointer is over the link
            if self.linkhovered:
                #call the callback for the link
                self.linkcb()
            self.linkdown = False

        self.OnMouseMotion(event)

        self.Refresh()

    def OnMouseMotion(self,event):
        """
            Insures mouse in and mouse out capture events occure, also handels
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

        #handle link mouseover
        if self.link:
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

