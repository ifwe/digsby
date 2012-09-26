import wx
from util.primitives.funcs import do
from util.primitives.mapping import to_storage, Storage
#from util.introspect import print_timing


from gui.toolbox import get_wxColor

from gui import skin

class SplitImage2(object):
    def __init__(self,image_dict):
        '''
        Sets up this image, splitting what is necessary and preparing the cache.

        @param image_dict: a descriptive dictionary for how to load and draw
        this image it is probably a good idea to pass in a copy if this
        dictionary will be used elsewhere.
        '''
        imgs = self.image_dictionary = to_storage(image_dict)
        image = skin.load_image(imgs.source)
        self.cache = Storage()

        clipcolor = imgs.get('clipcolor', None)
        if clipcolor is not None:
            self.cache.clipcolor = get_wxColor(imgs.clipcolor)
            image.SetMask(wx.Mask(image, self.cache.clipcolor))

        imgw = image.GetWidth()
        self.imgw = imgw
        imgh = image.GetHeight()
        self.imgh = imgh
        self.draw_commands = []
        #if corners exit
        if imgs.corners:
            self.regions_to_draw = None
            cornw = imgs.cornw = imgs.corners.size[0]
            cornh = imgs.cornh = imgs.corners.size[1]
            #else:
                #do 4-section magic
                #not really! just 2 sections, corners just drawn
            if imgs.corners.side == 'left':
                self.corners_to_draw = ['top_left', 'bottom_left']
                #cache big right
                if imgw - cornw > 0:
                    self.cache.large_right = \
                    image.GetSubBitmap(wx.Rect(cornw, 0, imgw - cornw, imgh))
                    self.regions_to_draw = ['left','large_right']
                else:
                    self.regions_to_draw = ['left']
                #stretch the right from x pixels off
            elif imgs.corners.side == 'right':
                self.corners_to_draw = ['top_right', 'bottom_right']
                if imgw - cornw > 0:
                    self.cache.large_left = \
                    image.GetSubBitmap(wx.Rect(0, 0, imgw - cornw, imgh))
                    self.regions_to_draw = ['large_left','right']
                else:
                    self.regions_to_draw = ['right']
            elif imgs.corners.side == 'top':
                self.corners_to_draw = ['top_left', 'top_right']
                if imgh - cornh >0:
                    self.cache.large_bottom = \
                    image.GetSubBitmap(wx.Rect(0, cornh, imgw, imgh - cornh))
                    self.regions_to_draw = ['top','large_bottom']
                else:
                    self.regions_to_draw = ['top']
            elif imgs.corners.side == 'bottom':
                self.corners_to_draw = ['bottom_left', 'bottom_right']
                if imgh - cornh >0:
                    self.cache.large_top = \
                    image.GetSubBitmap(wx.Rect(0, 0, imgw, imgh - cornh))
                    self.regions_to_draw = ['large_top','bottom']
                else:
                    self.regions_to_draw = ['bottom']
            #if all corners:
            #else if image.corners.side == 'all':
            else:
                #go do 9-section magic
                #not really! just 5 sections, corners just drawn
                self.corners_to_draw = ['top_left', 'top_right',
                                   'bottom_left', 'bottom_right']
                self.regions_to_draw = ['left','right','top','bottom','center']

            [self.draw_commands.append((getattr(self,'draw_' + corner + '_corner'),None))
                                       for corner in self.corners_to_draw]
            if 'top_left'     in self.corners_to_draw:
                #cache this corner
                self.cache.top_left = \
                image.GetSubBitmap(wx.Rect(0, 0, cornw, cornh))
            if 'top_right'    in self.corners_to_draw:
                self.cache.top_right = \
                image.GetSubBitmap(wx.Rect(imgw - cornw, 0, cornw, cornh))
            if 'bottom_left'  in self.corners_to_draw:
                self.cache.bottom_left = \
                image.GetSubBitmap(wx.Rect(0, imgh - cornh, cornw, cornh))
            if 'bottom_right' in self.corners_to_draw:
                self.cache.bottom_right = \
                image.GetSubBitmap(wx.Rect(imgw - cornw, imgh - cornh, cornw, cornh))
            if 'left'   in self.regions_to_draw:
                self.cache.left = \
                image.GetSubBitmap(wx.Rect(0, cornh, cornw, imgh - cornh*2))
            if 'right'  in self.regions_to_draw:
                self.cache.right = \
                image.GetSubBitmap(wx.Rect(imgw - cornw, cornh, cornw, imgh - cornh*2))
            if 'top'    in self.regions_to_draw:
                self.cache.top = \
                image.GetSubBitmap(wx.Rect(cornw, 0, imgw - cornw*2, cornh))
            if 'bottom' in self.regions_to_draw:
                self.cache.bottom = \
                image.GetSubBitmap(wx.Rect(cornw, imgh - cornh, imgw - cornw*2, cornh))
            if 'center' in self.regions_to_draw:
                self.cache.center = \
                image.GetSubBitmap(wx.Rect(cornw, cornh, imgw - cornw*2, imgh - cornh*2))
        else:
            #default (stretch/tile) everything
            self.cache.total = image
            #no - assert(image.style == 'stretch' or image.style == 'tile')
            self.cache["totalch"] = 'left'
            self.cache["totalcv"] = 'top'
            self.cache["totalco"] = [0,0]
            self.regions_to_draw = ["total"]
            #image.style to everything
        for region in self.regions_to_draw:
            if region in self.image_dictionary.regions:
                region_dict = self.image_dictionary.regions[region]
                style = region_dict['style']
                self.draw_commands.append((getattr(self,'draw_' + region),style))
                if style == 'static' or self.image_dictionary.style == 'static':
                    color = get_wxColor(region_dict['color'])
                    if color is not None:
                        self.cache[region + "cb"] = wx.Brush(color)
                    else:
                        self.cache[region + "cb"] = None
                    self.cache[region + "ch"] = region_dict['halign']
                    self.cache[region + "cv"] = region_dict['valign']
                    self.cache[region + "co"] = region_dict['offset']
            else:
                self.draw_commands.append((getattr(self,'draw_' + region), self.image_dictionary['style']))
    def get_num_anchors_to(self):
        return len(self.get_anchors_to())

    def get_anchors_to(self):
#       print self.image_dictionary
        return [anchor for anchor in self.image_dictionary['anchors']
                    if 'to' in anchor and anchor['to'] is not None]

    def draw_total(self, type):
        args = ('total', 0, 0, self.rect.width, self.rect.height)
        getattr(self,'draw_region_' + type)(*args)


    def draw_top_left_corner(self, unused):
        self.dc.DrawBitmap(self.cache.top_left,self.rect.x,self.rect.y, True)

    def draw_top_right_corner(self, unused):
        self.dc.DrawBitmap(self.cache.top_right,
                           self.rect.x + self.rect.width -
                           self.cache.top_right.GetWidth(),
                           self.rect.y,True)

    def draw_bottom_left_corner(self, unused):
        self.dc.DrawBitmap(self.cache.bottom_left, self.rect.x,
                   self.rect.y + self.rect.height -
                   self.cache.bottom_left.GetHeight(), True)

    def draw_bottom_right_corner(self, unused):
        self.dc.DrawBitmap(self.cache.bottom_right,
                   self.rect.x + self.rect.width -
                   self.cache.bottom_right.GetWidth(),
                   self.rect.y + self.rect.height -
                   self.cache.bottom_right.GetHeight(), True)

    def draw_left(self, type):
        args = ('left', 0, self.image_dictionary.cornh,
                                 self.image_dictionary.cornw,
                                 self.rect.height - self.image_dictionary.cornh*2)
        getattr(self,'draw_region_' + type)(*args)
    def draw_right(self, type):
        args = ('right', self.rect.width - self.image_dictionary.cornw,
                                 self.image_dictionary.cornh,
                                 self.image_dictionary.cornw,
                                 self.rect.height - self.image_dictionary.cornh*2)
        getattr(self,'draw_region_' + type)(*args)
    def draw_top(self, type):
        args = ('top', self.image_dictionary.cornw, 0,
                                 self.rect.width - self.image_dictionary.cornw*2,
                                 self.image_dictionary.cornh)
        getattr(self,'draw_region_' + type)(*args)
    def draw_bottom(self, type):
        args = ('bottom', self.image_dictionary.cornw,
                                 self.rect.height - self.image_dictionary.cornh,
                                 self.rect.width - self.image_dictionary.cornw*2,
                                 self.image_dictionary.cornh)
        getattr(self,'draw_region_' + type)(*args)
    def draw_center(self, type):
        args = ('center', self.image_dictionary.cornw,
                                 self.image_dictionary.cornh,
                                 self.rect.width - self.image_dictionary.cornw*2,
                                 self.rect.height - self.image_dictionary.cornh*2)
        getattr(self,'draw_region_' + type)(*args)
    def draw_large_left(self, type):
        args = ('large_left', 0, 0,
                                 self.rect.width - self.image_dictionary.cornw,
                                 self.rect.height)
        getattr(self,'draw_region_' + type)(*args)
    def draw_large_right(self, type):
        args = ('large_right',
                                 self.image_dictionary.cornw,
                                 0,
                                 self.rect.width - self.image_dictionary.cornw,
                                 self.rect.height)
        getattr(self,'draw_region_' + type)(*args)
    def draw_large_top(self, type):
        args = ('large_top',
                                 0,0,
                                 self.rect.width,
                                 self.rect.height - self.image_dictionary.cornh)
        getattr(self,'draw_region_' + type)(*args)
    def draw_large_bottom(self, type):
        args = ('large_bottom',
                                 0, self.image_dictionary.cornh,
                                 self.rect.width,
                                 self.rect.height - self.image_dictionary.cornh)
        getattr(self,'draw_region_' + type)(*args)

    def draw_region_stretch(self, img_string, dest_x, dest_y, dest_w, dest_h):
#        print "draw_region_stretch", "img_string", img_string, "x:", dest_x, "y:", dest_y, "w:",dest_w, "h:",dest_h
        '''
        draws a stretched region

        @param img_string: the key to a bitmap in the cache
        @param dest_x: x coordinate to draw at, relative to the origin of the
        rectangle for this image
        @param dest_y: y coordinate to draw at, relative to the origin of the
        rectangle for this image
        @param dest_w: width to draw this section of the image
        @param dest_h: height to draw this section of the image
        '''
        if dest_w > 0 and  dest_h > 0:
            myimg = self.cache[img_string]

            if img_string + 's' not in self.cache or \
            self.cache[img_string + 's'].GetWidth() != dest_w or \
            self.cache[img_string + 's'].GetHeight() != dest_h:
                temp = myimg.ConvertToImage()
                temp.Rescale(dest_w,dest_h)
                self.cache[img_string + 's'] = wx.BitmapFromImage(temp)
                self.cache[img_string + 'sr'] = wx.RegionFromBitmap( self.cache[img_string + 's'] )
                if not self.cache[img_string + 'sr'].IsEmpty():
                    self.cache[img_string + 'sr'].Offset(self.rect.x + dest_x, self.rect.y + dest_y)
            self.dc.DrawBitmap(self.cache[img_string + 's'], self.rect.x + dest_x,
                               self.rect.y + dest_y, True)
            #r for region
            self.rs.append(self.cache[img_string + 'sr'])


    def draw_region_tile(self, img_string, dest_x, dest_y, dest_w, dest_h):
        '''
        draws a tiled region

        @param img_string: the key to a bitmap in the cache
        @param dest_x: x coordinate to draw at, relative to the origin of the
        rectangle for this image
        @param dest_y: y coordinate to draw at, relative to the origin of the
        rectangle for this image
        @param dest_w: width to draw this section of the image
        @param dest_h: height to draw this section of the image
        '''
        if dest_w > 0 and  dest_h > 0:
            if (img_string + "t") not in self.cache:
                self.cache[img_string + "t"] = wx.Brush(wx.RED)
                self.cache[img_string + "t"].SetStipple(self.cache[img_string])
                if 'clipcolor' in self.image_dictionary:
                    self.cache[img_string + "t"].SetStyle(wx.STIPPLE)
            r = wx.Region(self.rect.x + dest_x, self.rect.y + dest_y, dest_w, dest_h)
            self.rs.append(r)


            if 'clipcolor' in self.image_dictionary:
                bmp = wx.EmptyBitmap(dest_w, dest_h, 32)
                memdc = wx.MemoryDC()
                memdc.SelectObject(bmp)
                memdc.SetBrush(self.cache[img_string + "t"])
                memdc.DrawRectangle(0,0, dest_w, dest_h)
                memdc.SelectObject(wx.NullBitmap)
                memdc.SetBrush(wx.NullBrush)
                bmp.SetMask(wx.Mask(bmp, self.cache.clipcolor))
                self.dc.DrawBitmap(bmp, self.rect.x + dest_x, self.rect.y + dest_y)
            else:
                self.dc.SetBrush(self.cache[img_string + "t"])
                self.dc.SetPen(wx.TRANSPARENT_PEN)
                self.dc.DrawRectangle(self.rect.x + dest_x, self.rect.y + dest_y,
                                      dest_w, dest_h)
                self.dc.SetPen(wx.NullPen)
                self.dc.SetBrush(wx.NullBrush)

    def draw_region_static(self, img_string, dest_x, dest_y, dest_w, dest_h):
        '''
        draws a tiled region.  alignment, offset, and background color are
        pulled from the cache

        @param img_string: the key to a bitmap in the cache
        @param dest_x: x coordinate to draw at, relative to the origin of the
        rectangle for this image
        @param dest_y: y coordinate to draw at, relative to the origin of the
        rectangle for this image
        @param dest_w: width to draw this section of the image
        @param dest_h: height to draw this section of the image
        '''
        if dest_w > 0 and  dest_h > 0:
            myimg = self.cache[img_string]
            halign = self.cache[img_string + "ch"]
            valign = self.cache[img_string + "cv"]
            offset = self.cache[img_string + "co"]
            if halign == 'left':
                x = 0
            elif halign == 'right':
                x = dest_w - myimg.GetWidth()
            else:
                x = dest_w/2 - myimg.GetWidth()/2
            x = x + dest_x + self.rect.x + offset[0]
            if valign == 'top':
                y = 0
            elif valign == 'bottom':
                y = dest_h - myimg.GetHeight()
            else:
                y = dest_h/2 - myimg.GetHeight()/2
            y = y + dest_y + self.rect.y + offset[1]

            self.dc.SetClippingRegion(self.rect.x + dest_x, self.rect.y + dest_y,
                                      dest_w, dest_h)
            #c for statiC
            if img_string + "cb" in self.cache and self.cache[img_string + "cb"] is not None:
                self.dc.SetBrush(self.cache[img_string + "cb"])
                self.dc.SetPen(wx.TRANSPARENT_PEN)
                self.dc.DrawRectangle(self.rect.x + dest_x, self.rect.y + dest_y,
                                          dest_w, dest_h)
                self.dc.SetPen(wx.NullPen)
                self.dc.SetBrush(wx.NullBrush)
            self.dc.DrawBitmap(myimg, x,y, True)
            #r for region
            if img_string + "r" not in self.cache:
                new = (wx.RegionFromBitmap( myimg ), x,y)
                self.cache[img_string + "r"] = new
                if not new[0].IsEmpty():
                    new[0].Offset(x,y)
            else:
                old, oldx, oldy = self.cache[img_string + "r"]
                if not old.IsEmpty():
                    old.Offset(x-oldx, y-oldy)
                self.cache[img_string + "r"] = (old, x,y)
            self.rs.append(self.cache[img_string + "r"][0])
            self.dc.DestroyClippingRegion()

    #@print_timing(num_runs=1000)
    def draw(self, dc, rect):
        '''
        draws this image into the specified rectangle of the drawing context
        given, per the dictionary given to the constructor

        @param dc: a wx.DC to draw into
        @param rect: a wx.Rect as a description of where/how big to draw
        '''
        self.dc = dc
        self.rect = rect
        self.rs = []
        do(func(args) for (func,args) in self.draw_commands)
        self.region = wx.Region(0, 0, 0, 0)
        for region in self.rs:
            if not region.IsEmpty():
                self.region.UnionRegion(region)
        self.dc = None
        self.rect = None

if __name__ == '__main__':
    from skins import images,skins
    app = wx.PySimpleApp()
    image = Storage()
    image['style'] = 'static'
    image['source'] = 'skins/default/checkerboard9.png'
#    image['clipcolor'] = '0xFF00DD'
    image['corners'] = {}
#    image['corners']['size'] = [10,10]
#    image['corners']['side'] = 'none'
    image['halign'] = 'left'
    image['valign'] = 'top'
    image['offset'] = [50,50]
    image['regions'] = dict(
        center = dict(
            style = 'static',
            color = 'red',
            valign = 'center',
            halign = 'center',
            offset = [50,50]
        )
    )
    skins.res_path = "res/"
    destbitmap = images.get('skins/default/blue-flower.jpg')
#    bitmap2 = wx.EmptyBitmap(bitmap.GetWidth()*5, bitmap.GetHeight()*5, bitmap.GetDepth())
#    testsize = 30
#    bitmap2 = wx.EmptyBitmap(testsize, testsize, bitmap.GetDepth())

    temp_dc = wx.MemoryDC();
    temp_dc.SelectObject(destbitmap);
    splitimg = SplitImage2(image)
    splitimg.draw(temp_dc, wx.Rect(50,50,200,200))

    temp_dc.SelectObject(wx.NullBitmap)

    destbitmap.SaveFile('C:/workspace/Digsby/res/skins/default/output.png',
                     wx.BITMAP_TYPE_PNG)


