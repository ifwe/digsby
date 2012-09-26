import wx

import config
from gui.textutil import GetTextExtent,default_font
from util.primitives.funcs import do
from util.primitives.error_handling import try_this
from gui import skin
from cgui import SplitImage4
from gui.windowfx import ApplySmokeAndMirrors
from gui.skin.skinobjects import SkinColor
from gui.uberwidgets import UberWidget

class UberProgressBar(wx.Gauge, UberWidget):
    """
    Skinable progress bar, works simular to wx.Gauge

    -posible features
        -optional percentage display
        -vertical progress bar?
    """
    def __init__(self, parent, id = -1, range = 100, skinkey = None,
                 showlabel = False, style = wx.GA_SMOOTH,
                 pos = wx.DefaultPosition,
                 size = wx.DefaultSize):

        wx.Gauge.__init__(self,parent,-1,range, pos, size, style)
        self.style = style
        self.range = range
        self.value = 0
        self.showlabel = showlabel

        events=[(wx.EVT_PAINT, self.OnPaint),
                (wx.EVT_ERASE_BACKGROUND, self.OnBGPaint),
                (wx.EVT_SIZE, self.OnSize)]

        do(self.Bind(event, method) for (event, method) in events)
        self.SetSkinKey(skinkey,True)

        self.Calcumalate()

    def UpdateSkin(self):
        """
            Updates all the local skin references
        """
        key = self.skinkey

        s = lambda k, default = sentinel: skin.get(key + '.' + k, default)

        mode = try_this(lambda: str(s('mode', '')), '')
        if config.platformName != "mac" and key and mode.lower() != 'native':
            self.native=False

            self.repeat   = try_this(lambda: str(s('style',  '')).lower(), '') == 'repeat'
            self.padding  = s('padding', 0)
            self.Font     = s('font', lambda: default_font())

            self.bg       = s('backgrounds.normal', None)
            self.fg       = s('backgrounds.fill',   lambda: SkinColor(wx.BLUE))

            self.normalfc = s('fontcolors.normal', wx.BLACK)
            self.fillfc   = s('fontcolors.fill',   wx.WHITE)

        else:
            self.native   = True

        self.OnSize()

    def OnSize(self,event=None):
        """
            Reaply smoke and mirrors when the bar is resized
        """
        if not self.native and isinstance(self.bg, SplitImage4):
            ApplySmokeAndMirrors(self, self.bg.GetBitmap(self.Size))
        else:
            ApplySmokeAndMirrors(self)

#-----------------------Code Ror Centered Label-----------------------
#
#        labelsize = wx.Size(*GetTextExtent('100%',self.Font))
#        size=self.Size
#        self.labelrect = wx.RectPS((size.x/2-labelsize.x/2,size.y/2-labelsize.y/2),labelsize)

#---------------------------------------------------------------------
    def OnBGPaint(self,event):
        if self.native:
            event.Skip()

    def OnPaint(self,event):
        """
            Painting when skined, otherwise it lets the system handle it
        """
        if self.native:
            event.Skip()
            return

        dc=wx.AutoBufferedPaintDC(self)

        rect=wx.RectS(self.Size)

        #Background drawing
        if self.bg:
            self.bg.Draw(dc,rect)


        rect.width=int(float(self.value)/float(self.range)*self.Size.x)

        #forground drawing
        if self.repeat:
            curser = wx.Point(self.padding,0)
            while curser.x<self.fill:
                self.fg.Draw(dc, wx.RectPS(curser,(self.fg.width,rect.height)))
                curser.x += self.fg.width+self.padding

        else:
            self.fg.Draw(dc,wx.RectS((self.fill,rect.height)))

#-----------------------Code For Centered Label-----------------------

#        if self.showlabel:
#            dc.SetFont(self.font)
#            dc.SetTextForeground(self.labelcolor1)
#            dc.DrawLabel(str(self.value)+'%',self.labelrect,wx.ALIGN_CENTER)
#            if rect.Intersects(self.labelrect):
#                dc.SetClippingRect(rect.Intersect(self.labelrect))
#                dc.SetTextForeground(self.labelcolor2)
#                dc.DrawLabel(str(self.value)+'%',self.labelrect,wx.ALIGN_CENTER)

#---------------------------------------------------------------------

    def Calcumalate(self):
        """
            Calculates the number of pixels to the width that is the same
            ratio as the value to the range
        """
        if self.native:
            return
        self.fill=self.Size.width*(float(self.value)/float(self.range))
        #if self.fill<self.fg.width:
        #    self.fill=self.fg.width
        self.Refresh()

    def SetRange(self, range):
        """
            Set how high the progress bar mesures
        """
        self.range=range
        wx.Gauge.SetRange(self,range)
        self.Calcumalate()

    def SetValue(self, value):
        """
            Sets the curent count of the progress bar
        """
        self.value = value
        wx.Gauge.SetValue(self, value)
        self.Calcumalate()

    def GetRange(self):
        """
            Return the Range
        """
        return self.range

    def GetValue(self):
        """
            Return the Value
        """
        return self.value
