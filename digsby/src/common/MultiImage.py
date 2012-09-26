from util import print_timing
from util import to_storage
import util
import syck
import wx


class MultiImage(object):
    '''
    Creates displayable bitmaps from a skinning language description.s
    '''

    def __init__(self,image_list):
        self.images = []
        self.tags = {}
        from SplitImage2 import SplitImage2
        self.images = [SplitImage2(image) for image in image_list]

        # record anchors
        for image in self.images:
            if 'anchors' in image.image_dictionary:
                for anchor in image.image_dictionary.anchors:
                    if 'tag' in anchor and anchor['tag'] is not None:
                        self.tags[anchor['tag']] = image

    def __contains__(self, tagname):
        "Returns True if the specified tag name is in this multi image's tags."

        return tagname in self.tags

    def tag_rect(self, tagname):
        "Returns a wx.Rect for the requested tag."

        if not tagname in self.tags:
            raise ValueError('tag %s not in this MultiImage' % tagname)

        return self.drawrects[self.tags[tagname]]

    def make_bitmap(self, width, height, mask_color = wx.BLACK):
        '''
        Creates a wx.Bitmap with the specified size, drawing this MultiImage's
        total contents onto the bitmap.

        @param mask_color an optional parameter for the bitmap's mask
        '''
        bitmap = wx.EmptyBitmap(width, height)

        if not hasattr(self, 'temp_dc'):
            self.temp_dc = wx.MemoryDC();

        self.temp_dc.SelectObject(bitmap);
        self.draw(self.temp_dc, wx.Rect(0,0,width,height))
        self.temp_dc.SelectObject(wx.NullBitmap)

        bitmap.SetMask(wx.Mask(bitmap, mask_color))

        return bitmap

#    @print_timing(1)
    def draw(self, dc, rect):
        '''

        @param dc: dc to draw on
        @param rect: rectangle to draw this combined image into
        '''
        self.drawrects = {}

        # compute the local size/position of each image
        [self.compute_rect(i, rect)
         for i in self.images if i not in self.drawrects]
        self.region = wx.Region(0, 0, 0, 0)
        one = False
        for image in self.images:
            drect = wx.Rect(*self.drawrects[image])
            drect.Offset((rect.x,rect.y))
            if dc:
                image.draw(dc, drect)
                self.region.UnionRegion(image.region)

    def compute_rect(self, image, dcrect):
        # count anchors to
        myanchors = image.get_anchors_to()
        numanchors = len(myanchors)

        #if stretch/tile, assert 0 < numanchorsto < 3
        if image.image_dictionary.style != 'static':
            assert(numanchors == 1 or numanchors == 2)

            # if 1, use dc + image offset/align as other "to"
            # compute anchor position(self, DCsize, (0,0))
            # map 0,0 of self to that position
            if numanchors == 1:
                anchorfrom = to_storage(myanchors[0])
                tag = anchorfrom.to
                imageto = self.tags[tag]

                anchorto = to_storage([anchor for anchor in imageto.image_dictionary.anchors if
                            anchor['tag'] == tag][0])
                if imageto not in self.drawrects:
                    self.compute_rect(imageto, dcrect)

                rectto1 = self.drawrects[imageto]
                rectto2 = (0,0,dcrect.width,dcrect.height)

                positionto1 = compute_anchor_position(anchorto, rectto1[2:], rectto1[:2])
                positionto2 = compute_anchor_position(get_SI2_anchor(image), rectto2[2:], rectto2[:2])

                #relative position (local anchors)
                positionfrom1 = compute_anchor_position(anchorfrom, [image.imgw, image.imgh],
                                                  [0,0])
                positionfrom2 = (0,0)
                diffxto = abs(positionto1[0] - positionto2[0])
                diffyto = abs(positionto1[1] - positionto2[1])
                diffxlocal = abs(positionfrom1[0] - positionfrom2[0])
                diffylocal = abs(positionfrom1[1] - positionfrom2[1])

                increasex = diffxto - diffxlocal
                increasey = diffyto - diffylocal

                newsizew = image.imgw + increasex
                newsizeh = image.imgh + increasey

                newlocalanchorposition = positionto2
                positiontodrawat = (positionfrom2[0] + newlocalanchorposition[0],
                                    positionfrom2[1] + newlocalanchorposition[1])
                self.drawrects[image] = (positiontodrawat[0], positiontodrawat[1],
                                         newsizew, newsizeh)
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
            if numanchors == 0:

                positiontodrawat = compute_anchor_position(get_SI2_anchor(image), (dcrect.width, dcrect.height),
                                       [0,0])
                #rect = our offset and size
                self.drawrects[image] = (positiontodrawat[0], positiontodrawat[1],
                                         image.imgw, image.imgh)
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
                positionfrom = compute_anchor_position(anchorfrom, [image.imgw, image.imgh],
                                                  [0,0])
                positiontodrawat = (positionto[0] - positionfrom[0],
                                    positionto[1] - positionfrom[1])
                self.drawrects[image] = (positiontodrawat[0], positiontodrawat[1],
                                         image.imgw, image.imgh)
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
    retval = to_storage({})
    if hasattr(image.image_dictionary, 'offset'):
        retval['offset'] = image.image_dictionary.offset
    if hasattr(image.image_dictionary, 'valign'):
        retval['valign'] = image.image_dictionary.valign
    if hasattr(image.image_dictionary, 'halign'):
        retval['halign'] = image.image_dictionary.halign
    return retval

def main(images):
    temp_dc = wx.MemoryDC();
    temp_dc.SelectObject(destbitmap);
    mimg = MultiImage(images)
    drawrect = wx.Rect(10,10,220,440)
    mimg.draw(temp_dc, drawrect)

    temp_dc.SelectObject(wx.NullBitmap)



if __name__ == '__main__':
    import util
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
