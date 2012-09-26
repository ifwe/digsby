import wx
from math import radians
from util.primitives.funcs import do
from gui.windowfx import ApplySmokeAndMirrors
from common import pref
from logging import getLogger; log = getLogger('OverlayImage')

class SimpleOverlayImage(wx.PopupWindow):
    """
        Used for tab previews when dragging them around
    """
    def __init__(self,parent,host):
        """
            Usses the OnPaint function of host to draw and region itself
            host.OnPaint(otherdc,otherwindow)
        """
        wx.PopupWindow.__init__(self,parent)

        events=[
            (wx.EVT_PAINT, self.OnPaint)
        ]
        do(self.Bind(event, method) for (event,method) in events)

        self.host=host
        self.Size=host.Size

    def OnPaint(self,event):
        if not wx.IsDestroyed(self):
            self.host.OnPaint(otherdc = wx.PaintDC(self), otherwindow = self)

    def Transition(self,dest):
        """
            Animated move to destination (x,y)
            NOT YET IMPLEMENTED!!!
        """
        pass

    def Teleport(self,dest):
        """
            Move to location, but uses center point as opposed to upper left
        """
        self.Move((dest[0]-(self.Size.width/2),dest[1]-(self.Size.height/2)))
        self.Refresh()

    @property
    def alpha(self):
        return pref('tabs.preview_alpha',200)

class OverlayImage(wx.PopupWindow):
    """
        Image that overlaps the window
    """
    def __init__(self,parent,image,size= wx.Size(-1,-1),rot=0):
        """
            image - wx.Image of the item
        """
        wx.PopupWindow.__init__(self,parent)

        events=[
            (wx.EVT_PAINT,self.onPaint),
            (wx.EVT_MOVE,self.OnMove)
        ]
        do(self.Bind(event, method) for (event,method) in events)

        self.parent=parent

        self.rot    = rot

        if size != wx.Size(-1, -1):
            self.SetSize(size)

        if isinstance(image, wx.Bitmap):
            self.bitmap = image
        else:
            self.SetImage(image, size)

    def SetImage(self, image, size = wx.Size(-1,-1)):
        log.info('Overlay Image has been updated')

        self.image  = image
        prebitmap = wx.ImageFromBitmap(image.GetBitmap(size))
        prebitmap.ConvertAlphaToMask()
        self.bitmap = wx.BitmapFromImage(prebitmap)

        self.width, self.height = self.bitmap.Width, self.bitmap.Height
        self.GenBitmap()

    def OnMove(self,event):
        self.Refresh()

    def onPaint(self,event):
        dc = wx.PaintDC(self)
        dc.DrawBitmap(self.bitmap,0,0,False)

    def GenBitmap(self):
        """
            Generates a local cached bitmap from the bitmap
            then sets the region
        """
        if self.rot:
            self.bitmap=wx.BitmapFromImage(self.bitmap.ConvertToImage().Rotate(radians(90*self.rot),(0,0)))
        if self.Size != (self.bitmap.Width+1,self.bitmap.Height+1):
            wx.PopupWindow.SetSize(self,(self.bitmap.Width+1,self.bitmap.Height+1))
        ApplySmokeAndMirrors(self, self.bitmap)


    def SetBitmapSize(self,size):
        'Change the size of the image, sizes 0 and lower keep it the same.'

        if size == self.Size: return

        if size[0] > 0: self.width  = size[0]
        if size[1] > 0: self.height = size[1]

        prebitmap=self.image.GetBitmap((self.width,self.height)).ConvertToImage()
        prebitmap.ConvertAlphaToMask()
        self.bitmap=wx.BitmapFromImage(prebitmap)
        self.GenBitmap()


    def SetRotation(self,rot=0):
        self.rot=rot

    def Transition(self,dest):
        """
            Animated move to destination (x,y)
            NOT YET IMPLEMENTED!!!
        """
        pass

    def Teleport(self,dest):
        """
        Move to location, but uses center point as opposed to upper left
        """
        self.Move((dest[0]-(self.Size.width//2),dest[1]))#-(self.Size.height//2)
