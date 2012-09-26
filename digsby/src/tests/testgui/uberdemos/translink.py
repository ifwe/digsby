import wx
from gui.textutil import CopyFont,default_font
from gui.uberwidgets.pseudosizer import PseudoSizer
from gui.uberwidgets.cleartext import ClearText
from gui.uberwidgets.clearlink import ClearLink
from util.primitives.funcs import Delegate


a=wx.PySimpleApp()
f=wx.Frame(None,size=(450,450))
f.Font=CopyFont(default_font(),pointSize=15)
p=wx.Panel(f)

p.Sizer=wx.BoxSizer(wx.HORIZONTAL)

#l=ClearLink(p,-1,'Super link of epic proportions','google.com')
#l.VisitedColour=wx.BLUE
#x=ClearLink(p,-1,'Mega Tokyo','megatokyo.com')
#y=ClearLink(p,-1,'Errant Story','errantstory.com')
#z=ClearLink(p,-1,'VG Cats','vgcats.com')
#t=PseudoSizer()
#t.Add(x)
#t.Add(y)
#t.Add(z)

#t=ClearText(p,label='Test')
#t.SetPosition((0,50))

st= """Dreams come true: Capcom has confirmed that Harvey Birdman: Attorney At Law, their game based on the hilarious Adult Swim cartoon courtroom comedy, will come to Wii as............ well."""
#
#Capcom also said that all three versions -- Wii, PS2, and PSP -- will hit retail on November 13. If you want motion control with your lawyering, you'll have to pay up, as the Wii version will run you $40 while the Sony versions only cost $30.
#
#Totally worth it."""


b=wx.Bitmap('c:/b.jpg')
def paint(event):
    dc=wx.AutoBufferedPaintDC(p)
    b2=wx.BitmapFromImage(wx.ImageFromBitmap(b).Scale(*p.Size))
    dc.DrawBitmap(b2,0,0,True)

    p.ChildPaints(dc)

def OnSize(event):
    ct.Wrap(p.Size.width - 4,4)
    event.Skip()

p.Bind(wx.EVT_PAINT,paint)
p.Bind(wx.EVT_SIZE,lambda e: (p.Layout(),p.Refresh()))
p.Bind(wx.EVT_ERASE_BACKGROUND,lambda e: None)
p.Bind(wx.EVT_SIZE,OnSize)
p.ChildPaints = Delegate()
#p.Sizer.Add(wx.ComboBox(p,-1,"test1"),0,0)
ct = ClearText(p, st)
ct.FontColor = wx.GREEN
ct.Font = f.Font

p.Sizer.Add(ct,0,0)

#p.Sizer.Add(wx.Button(p,-1,"test"),0,0)

#l.Position=(10,10)
f.Show(True)
a.MainLoop()
