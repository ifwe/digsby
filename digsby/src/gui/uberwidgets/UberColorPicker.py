import wx
from gui.skin import skininit
from gui import skin
#from PIL import Image
#import StringIO
#from StringIO import StringIO
#import ImageEnhance

class UberColorPicker(wx.PopupTransientWindow):
    def __init__(self,parent):
        wx.PopupTransientWindow.__init__(self,parent)

        events=[
            (wx.EVT_PAINT,self.OnPaint)
        ]
        [self.Bind(event,method) for (event,method) in events]

        self.skin = skin.get('colorpicker')

        colors=[
            (0,0,0),(0,0,128),(0,0,255),(0,128,0),
            (0,128,128),(0,255,0),(0,255,255),(128,0,0),
            (128,0,128),(128,128,0),(128,128,128),(255,0,0),
            (255,0,255),(255,255,0),(255,255,255),(192,192,192)
        ]

        padding=5
        size=28
        cx=padding
        cy=padding

        self.swashes=[]
        count=0
        for color in colors:
            self.swashes.append(ColorBlock(self,color,(cx,cy),(size,size)))
            cx+=size+padding
            count+=1
            if count==4:
                cx=padding
                cy+=size+padding
                count=0

        self.SetSize((cy,cy))

    def OnPaint(self,event):
        dc=wx.PaintDC(self)
        rect=wx.RectS(self.GetSize())

        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)

        dc.DrawRectangleRect(rect)

class ColorBlock(wx.Window):
    def __init__(self,parent,color,pos,size):
        wx.Window.__init__(self,parent,pos=pos,size=size)

        events=[
            (wx.EVT_PAINT,self.OnPaint)
        ]
        [self.Bind(event,method) for (event,method) in events]

        self.color=color

    def OnPaint(self,event):
        pdc=wx.PaintDC(self)
        mdc=wx.MemoryDC()
        bitmap=wx.EmptyBitmap(*self.GetSize())
        mdc.SelectObject(bitmap)

        rect=wx.RectS(self.GetSize())

        mdc.SetBrush(wx.WHITE_BRUSH)
        mdc.SetPen(wx.TRANSPARENT_PEN)

        mdc.DrawRectangleRect(rect)

        mdc.SetBrush(wx.Brush(wx.Color(*self.color)))

        mdc.SetPen(wx.Pen(
        wx.Color(self.color[0]/2,self.color[1]/2,self.color[2]/2),
        1,
        wx.SOLID
        ))

        mdc.DrawRoundedRectangleRect(rect,5)
        mdc.SelectObject(wx.NullBitmap)
#        image=Image.new('RGB',(bitmap.GetWidth(),bitmap.GetHeight()))
#        image.fromstring(bitmap.ConvertToImage().GetData())
#
#        enhancer = ImageEnhance.Sharpness(image)
#        image=enhancer.enhance(0)
#
#        wximage=wx.EmptyImage(*image.size)
#        wximage.SetData(image.convert('RGB').tostring())


        #wx.BitmapFromBuffer(Image.string)
        pdc.DrawBitmap(bitmap,0,0)#wximage.ConvertToBitmap(),0,0)


class F(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self,None)

        events=[
            (wx.EVT_BUTTON,self.OnButton)
        ]
        [self.Bind(event,method) for (event,method) in events]

        self.b1=wx.Button(self,label='color')
        self.cp=UberColorPicker(self)

    def OnButton(self,event):
        self.cp.SetPosition(wx.GetMousePosition())
        self.cp.Popup()

class A(wx.App):
    def OnInit(self):
        f=F()
        f.Show(True)
        return True

if __name__=='__main__':
    skininit('../../res')
    assert gSkin() is not None
    a=A(0)
    a.MainLoop()