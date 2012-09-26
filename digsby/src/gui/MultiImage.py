from util import print_timing
from util import to_storage, Storage
import wx
from gui.toolbox import TransparentBitmap
from logging import getLogger
log = getLogger('MultiImage'); info = log.info; error = log.error

class MultiImage(object):
    'Creates displayable bitmaps from a skinning language description.'

    def __init__(self, images):
        self.images = images
        self.tags = {}
        self.drawrects = {}

        # record anchors
        for image in self.images:
            if hasattr(image, 'anchors'):
                for anchor in image.anchors:
                    if 'tag' in anchor and anchor['tag'] is not None:
                        self.tags[anchor['tag']] = image

        self.cached_result = Storage(bitmap=None, size=(0,0))

    def __repr__(self):
        from pprint import pformat
        return '<MultiImage:' + pformat(self.drawrects) + '>'

    def __contains__(self, tagname):
        "Returns True if the specified tag name is in this multi image's tags."

        return tagname in self.tags

    def tag_rect(self, tagname):
        "Returns a wx.Rect for the requested tag."

        if not tagname in self.tags:
            raise ValueError('tag %s not in this MultiImage' % tagname)

        return self.drawrects[self.tags[tagname]]

    def Draw(self, dc, rect):
        position, size = rect[:2], rect[2:]
        self.w, self.h = size

        if not self.cached_result.bitmap or self.cached_result.size != size:
            info('new size, making bitmap')

            self.recalc()
            self.cached_result.size = size
            self.cached_result.bitmap = self.make_bitmap(*size)

        dc.DrawBitmapPoint(self.cached_result.bitmap, position)


    def make_bitmap(self, width, height):
        '''
        Creates a wx.Bitmap with the specified size, drawing this MultiImage's
        total contents onto the bitmap.

        @param mask_color an optional parameter for the bitmap's mask
        '''
        size = (width, height)
        bitmap = TransparentBitmap(size)


        if not hasattr(self, 'temp_dc'):
            self.temp_dc = wx.MemoryDC();

        self.temp_dc.SelectObject(bitmap);
        self.drawtodc(self.temp_dc, wx.Rect(0,0,*size))
        self.temp_dc.SelectObject(wx.NullBitmap)

        self.region = wx.RegionFromBitmapColour(bitmap, (0,0,0,0))
#       gui.toolbox.toscreen(self.region.ConvertToBitmap(),500,500)


        return bitmap

    def recalc(self):
        self.drawrects.clear()

        # compute the local size/position of each image
        for i in self.images:
            if i not in self.drawrects:
                self.compute_rect(i, wx.Rect(0,0,self.w,self.h))

    def drawtodc(self, dc, rect):
        '''

        @param dc: dc to draw on
        @param rect: rectangle to draw this combined image into
        '''

        #[self.compute_rect(i, rect)
        # for i in self.images if i not in self.drawrects]

        for image in self.images:
            drect = wx.Rect(*self.drawrects[image])
            drect.Offset((rect.x, rect.y))
            image.Draw(dc, drect)

    def compute_rect(self, image, dcrect):
        # count anchors to
        myanchors = image.get_anchors_to()
        numanchors = len(myanchors)

        #if stretch/tile, assert 0 < numanchorsto < 3
        if image.style != 'static':
            if not (numanchors == 1 or numanchors == 2):
                raise AssertionError('%r is not static but has anchors %r' % (image, image.anchors))

            # if 1, use dc + image offset/align as other "to"
            # compute anchor position(self, DCsize, (0,0))
            # map 0,0 of self to that position
            if numanchors == 1:
                anchorfrom = to_storage(myanchors[0])
                tag = anchorfrom.to
                imageto = self.tags[tag]

                anchorto = to_storage([anchor for anchor in imageto.anchors if
                            anchor['tag'] == tag][0])
                if imageto not in self.drawrects:
                    self.compute_rect(imageto, dcrect)

                rectto1 = self.drawrects[imageto]
                rectto2 = (0,0,dcrect.width,dcrect.height)

                positionto1 = compute_anchor_position(anchorto, rectto1[2:], rectto1[:2])
                positionto2 = compute_anchor_position(get_SI2_anchor(image), rectto2[2:], rectto2[:2])

                #relative position (local anchors)
                positionfrom1 = compute_anchor_position(anchorfrom, [image.width, image.height],
                                                  [0,0])
                positionfrom2 = (0,0)
                diffxto = abs(positionto1[0] - positionto2[0])
                diffyto = abs(positionto1[1] - positionto2[1])
                diffxlocal = abs(positionfrom1[0] - positionfrom2[0])
                diffylocal = abs(positionfrom1[1] - positionfrom2[1])

                increasex = diffxto - diffxlocal
                increasey = diffyto - diffylocal

                newsizew = image.width + increasex
                newsizeh = image.height + increasey

                newlocalanchorposition = positionto2
                positiontodrawat = (positionfrom2[0] + newlocalanchorposition[0],
                                    positionfrom2[1] + newlocalanchorposition[1])
#                print 'positiontodrawat1', positiontodrawat
                self.drawrects[image] = (positiontodrawat[0], positiontodrawat[1],
                                         newsizew, newsizeh)
#                print "self.drawrects[image]", self.drawrects[image]
                return
            #if 2, whatever
            elif numanchors == 2:
                #local anchors
                anchorfrom1, anchorfrom2 = myanchors
                tag1, tag2 = anchorfrom1['to'], anchorfrom2['to']
                imageto1, imageto2 = self.tags[tag1], self.tags[tag2]
                #remote anchors
                anchorto1 = [anchor for anchor in imageto1.get_anchors_to() if
                            anchor['tag'] == tag1]
                anchorto2 = [anchor for anchor in imageto2.get_anchors_to() if
                            anchor['tag'] == tag2]

                if imageto1 not in self.drawrects:
                    self.compute_rect(imageto1, dcrect)
                if imageto2 not in self.drawrects:
                    self.compute_rect(imageto2, dcrect)
                rectto1 = self.drawrects[imageto1]
                rectto2 = self.drawrects[imageto2]
                #absolute position (remote anchors)
                positionto1 = compute_anchor_position(anchorto1, rectto1[2:], rectto1[:2])
                positionto2 = compute_anchor_position(anchorto2, rectto2[2:], rectto2[:2])

                #relative position (local anchors)
                positionfrom1 = compute_anchor_position(anchorfrom1, [image.imgw, image.imgh],
                                                  [0,0])
                positionfrom2 = compute_anchor_position(anchorfrom2, [image.imgw, image.imgh],
                                                  [0,0])
                #CAS: check relative positioning here

                diffxto = abs(positionto1[0] - positionto2[0])
                diffyto = abs(positionto1[1] - positionto2[1])
                diffxlocal = abs(positionfrom1[0] - positionfrom2[0])
                diffylocal = abs(positionfrom1[1] - positionfrom2[1])

                increasex = diffxto - diffxlocal
                increasey = diffyto - diffylocal

                newsizew = image.imgw + increasex
                newsizeh = image.imgh + increasey
                #compute new position of one local anchor on new size
                newlocalanchorposition = compute_anchor_position(anchorfrom1, newsizew,newsizeh,[0,0])
                #subtract from position of remote anchor to find the absolute position of this image

                positiontodrawat = (positionto1[0] - newlocalanchorposition[0],
                                    positionto1[1] - newlocalanchorposition[1])
#                print 'positiontodrawat2', positiontodrawat
                self.drawrects[image] = (positiontodrawat[0], positiontodrawat[1],
                                         newsizew, newsizeh)
                return
            else:
                raise AssertionError("invalid skin, wrong number"
                                     " (%d) of anchors for "
                                     "image of type %s!" %
                                     (numanchors,
                                      image.image_dictionary['style']))
        #else assert -1 < numanchors < 2
        else:
            assert(numanchors == 0 or numanchors == 1)
            #if 0, use dc + image offset/align as "to"
            #compute anchor position(self, DCsize, (0,0))
            #draw at that position
            #print numanchors, image
            if numanchors == 0:
#                print "image", image
#                print dir(image)
#                print "anchor", get_SI2_anchor(image)

                positiontodrawat = compute_anchor_position(get_SI2_anchor(image), (dcrect.width, dcrect.height),
                                       [0,0])
#                print 'positiontodrawat3', positiontodrawat
                #rect = our offset and size
                #print "adding", image.image_dictionary, "to drawrects"
                self.drawrects[image] = (positiontodrawat[0], positiontodrawat[1],
                                         image.width, image.height)
#                print "self.drawrects[image]", self.drawrects[image]
                return
                #draw this image there
            #if 1, whatever
            elif numanchors == 1:
                anchorfrom = image.get_anchors_to()[0]
                tag = anchorfrom['to']
                imageto = self.tags[tag]
                anchorto = [anchor for anchor in imageto.get_anchors_to() if
                            anchor['tag'] == tag]
                if imageto not in self.drawrects:
                    self.compute_rect(imageto, dcrect)
                rectto = self.drawrects[imageto]
                #absolute position
                positionto = compute_anchor_position(anchorto, rectto[2:], rectto[:2])
                #relative position
                positionfrom = compute_anchor_position(anchorfrom, [image.width, image.height],
                                                  [0,0])
                positiontodrawat = (positionto[0] - positionfrom[0],
                                    positionto[1] - positionfrom[1])
#                print 'positiontodrawat4', positiontodrawat
                self.drawrects[image] = (positiontodrawat[0], positiontodrawat[1],
                                         image.width, image.height)
                return
            else:
                raise AssertionError("invalid skin, wrong number"
                                     " (%d) of anchors for "
                                     "image of type %s!" %
                                     (numanchors,
                                      image.image_dictionary['style']))
        #compute anchor position on self, do magic to figure out
        #where that goes on the dc
    #if they have no anchors to anything:
        #assume anchor is to make-believe image (dc)
    #else:
        #compute anchors to, resize/reposition as necessary

def compute_anchor_position(anchor, size, offset):
    '''
    calculates the position of an anchor on an image

    @param anchor: the (single) anchor dictionary
    @param size: the size of the image on which the anchor is placed
    @param offset: the offset of the image on which the anchor is placed

    @return: tuple(x,y)
    '''
    if 'halign' in anchor:
        halign = anchor.halign
    else:
        halign = 'left'
    if 'valign' in anchor:
        valign = anchor.valign
    else:
        valign = 'top'
    if 'offset' in anchor:
        off = anchor.offset
    else:
        off = [0,0]

    #CAS: integer rounding
    if isinstance(off[0], int):
        myoffsetx = off[0]
    else:
        myoffsetx = int(str(off[0])[:-1]) * size[0] / 100

    if isinstance(off[1], int):
        myoffsety = off[1]
    else:
        myoffsety = int(str(off[1])[:-1]) * size[1] / 100

    off = [myoffsetx, myoffsety]

    tup = (offset[0], offset[1], size[0], size[1])
    if halign == 'left':
        x = 0
    elif halign == 'right':
        x = tup[2]
    else:
        x = tup[2]/2
    x = x + tup[0] + off[0]
    if valign == 'top':
        y = 0
    elif valign == 'bottom':
        y = tup[3]
    else:
        y = tup[3]/2
    y = y + tup[1] + off[1]
    return (x,y)

def get_SI2_anchor(image):
    retval = Storage()
    if hasattr(image, 'offset'):
        retval['offset'] = image.offset
    if hasattr(image, 'valign'):
        retval['valign'] = image.valign
    if hasattr(image, 'halign'):
        retval['halign'] = image.halign
    return retval

def main(images):
    temp_dc = wx.MemoryDC();
    temp_dc.SelectObject(destbitmap);
    mimg = MultiImage(images)
    drawrect = wx.Rect(10,10,220,440)
    mimg.draw(temp_dc, drawrect)

    temp_dc.SelectObject(wx.NullBitmap)



if __name__ == '__main__':
    import util, syck
    from skins import images as imgmngr
    from skins import skins
    app = wx.PySimpleApp()

#    image['source'] = 'skins/default/checkerboard9.png'
    skins.res_path = "../../res/"
    destbitmap = imgmngr.get('skins/default/blue-flower.jpg')
    f = file("../../res/skins/skinExample")
    
    images = to_storage(syck.load(f)).Images
    f.close()
    util.profile(main, images)
    destbitmap.SaveFile('C:/workspace/Digsby/res/skins/default/output.png',
                     wx.BITMAP_TYPE_PNG)
