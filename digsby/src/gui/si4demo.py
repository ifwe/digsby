import wx
from splitimage4 import SplitImage4, ImageData, Extend
from pprint import pformat
from gui import skin as skincore

def make_extends(s):
    return Extend(up = 'up' in s,
                  down = 'down' in s,
                  left = 'left' in s,
                  right = 'right' in s)

def SplitImage3(imagedict):
    '''
    imagedata:
        source: #where the file can be located
        x1: #left hand cut on the x-axis
        x2: #right hand cut on the x-axis
        y1: #top cut on the y-axis
        y2: #bottom cut on the y-axis
        style: #sets what the rescaled parts of the image do; tile or stretch
               #defaults to stretch
        fillcolor: color to fill in the background with

        #the following lines are used to give styles to each region and
        #the ability to extend.  They all have vry simular function besides
        #the directions they can be extended so only center will be fully
        #described and the rest will onl be comented on supported extend directions

        center:
            style: #is this region going to stretch or tile
            extend: #what direction the region will be extended into
                    #center can extend; left, right, up, down down
            fillcolor: color to fill in the background with
        left: #extend up and down
        top: #extend left and right
        right: #extend up and down
        bottom: #extend left and right
    '''

    i = ImageData()
    for a in ('x1', 'x2', 'y1', 'y2'):
        setattr(i, max(1, a), imagedict[a])

    i.source = skincore.gSkin().load_image(imagedict['source'], path = True)

    style     = imagedict.get('style', 1)
    fillcolor = imagedict.get('fillcolor', wx.WHITE)

    for r in ('center', 'left', 'top', 'right', 'bottom'):
        id_region = getattr(i, r)
        region    = imagedict.get(r, {})

        if 'extend' in region:
            id_region.extends = make_extends(region['extend'])

        id_region.style   = region.get('style', style)
        id_region.fillcolor = region.get('fillcolor', fillcolor)

    try:
        return SplitImage4(i)
    except:
        import sys
        print >> sys.stderr, pformat(imagedict)
        raise



def MakeImageData():
    idata = ImageData();

    idata.x1 =  30;
    idata.x2 = -30;
    idata.y1 =  30;
    idata.y2 = -30;

    idata.source= "c:\\src\\Digsby\\res\\digsbybig.png"

    reg = ('center', 'top', 'right', 'bottom', 'left')

    for region in reg:
        r = getattr(idata, region)
        r.fillcolor = wx.BLACK
        r.style = 1

    return idata;

if __name__ == '__main__':
    from tests.testapp import testapp
    from gui import skin

    a = testapp('../..')

    f = wx.Frame(None, -1, 'Test', pos = (50, 50), size = (450, 340))
    f.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)



    si4 = skin.get('popup.backgrounds.normal')
    #si4 = skin.get('tabs.dropmarker.image')



    def paint(e):
        dc = wx.AutoBufferedPaintDC(f)
        r = wx.RectS(f.Size)
        dc.DrawRectangleRect(r)

        si4.Draw(dc, r.Deflate(100, 100))


    f.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)
    f.Bind(wx.EVT_SIZE, lambda e: f.Refresh())
    f.Bind(wx.EVT_PAINT, paint)


    f.Show()
    a.MainLoop()