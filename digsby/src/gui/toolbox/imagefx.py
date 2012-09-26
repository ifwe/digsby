'''

Efficient image effects and transformations.

'''

DISABLE_ALL_CACHING = False  # slow!
NUM_IMAGES_TO_CACHE = 80

import wx
from wx import ImageFromDataWithAlpha, BitmapFromImage, BitmapFromIcon, \
    ImageFromBitmap, IMAGE_QUALITY_HIGH, Point

from PIL import Image, ImageFilter, ImageMath, ImageOps, ImageEnhance
from PIL.Image import BICUBIC, ANTIALIAS
from functools import wraps
from uuid import uuid1

_imagecache = None

def _get_imagecache():
    global _imagecache
    if _imagecache is None:
        from util.lrucache import LRU
        _imagecache = LRU(NUM_IMAGES_TO_CACHE)
        
    return _imagecache

def cachesize():
    return sum(img.DecodedSize for img in _get_imagecache.values())

CORNERS = (
   ("tl", None),
   ("tr", Image.ROTATE_270),
   ("bl", Image.FLIP_TOP_BOTTOM),
   ("br", Image.ROTATE_180),
)

#
# the idea here is that each function gets an LRU cache keyed by
# images and arguments, with result images as values, so that
# redrawing the same image transformations over and over results
# in no work with a small enough memory tradeoff.
#
def cacheing(func):
    name = func.__name__

    @wraps(func)
    def wrapper(img, *a):
        try:
            cachekey = img.cachekey
        except AttributeError:
            try:
                cachekey = (img.path,)
            except AttributeError:
                img.path = str(uuid1())
                cachekey = (img.path,)

        key = cachekey + (name + repr(a) ,)

        imagecache = _get_imagecache()
        try:
            return imagecache[key]
        except KeyError:
            img = func(img, *a)
            img.cachekey = key
            imagecache[key] = img
            return img

    wrapper.nocache = func

    return wrapper

if DISABLE_ALL_CACHING:
    import sys
    print >> sys.stderr, 'WARNING: image caching is disabled'

    objmemoize = refmemoize = cacheing = lambda f: f
else:
    refmemoize = objmemoize = cacheing

#
#--- conversions between image types
#

@cacheing
def wxbitmap_to_wximage(wxbitmap):
    return wxbitmap.ConvertToImage()

@refmemoize
def wxbitmap_to_pil(wxbitmap):
#    print 'wxbitmap_to_pil', wxbitmap
    return wximage_to_pil(wxbitmap_to_wximage(wxbitmap))

@cacheing
def wxicon_to_pil(wxicon):
    return wxbitmap_to_pil(BitmapFromIcon(wxicon))

@cacheing
def wxicon_to_bitmap(wxicon):
    return BitmapFromIcon(wxicon)


@refmemoize
def wximage_to_pil(wximage):
#   print 'wximage_to_pil', wximage

    size = (wximage.Width, wximage.Height)
    img = Image.new('RGB', size)
    img.fromstring(wximage.Data)
    r, g, b = img.split()

    if wximage.HasAlpha() or wximage.HasMask():
        a = Image.new('L', wximage.GetSize())

        # images that come from formats like GIF don't have an alpha channel
        # but DO have a mask color set
        if wximage.HasMask():
            if not wximage.HasAlpha():
                # uses that mask color to generate an alpha channel.
                wximage.InitAlpha()

        if wximage.HasAlpha():
            a.fromstring(wximage.AlphaData)

        img = Image.merge('RGBA', (r, g, b, a))
    else:
        img = Image.merge('RGB', (r, g, b))

    return img

def wximage_to_wxbitmap(wximage, depth = 32):
    return BitmapFromImage(wximage)

@objmemoize
def pil_to_wxbitmap(pilimg):
#   print 'pil_to_wxbitmap', pilimg
    return wximage_to_wxbitmap(pil_to_wximage(pilimg), 32)

@objmemoize
def pil_to_wximage(pilimg):
#   print 'pil_to_wximage', pilimg

    #TODO: there has to be a more efficient way to get the data from
    # PIL then 'tostring'

    pilimage = pilimg if pilimg.mode == 'RGBA' else pilimg.convert('RGBA')
    w, h = pilimg.size

    rgb     = pilimage.tostring('raw', 'RGB')
    alpha   = pilimage.tostring('raw', 'A')
    return ImageFromDataWithAlpha(w, h, rgb, alpha)

@cacheing
def wxbitmap_inverted(wxbitmap):
    return ImageOps.invert(pilimg_convert(wxbitmap.PIL, 'RGB')).WXB

def has_transparency(i):
    return any(i.histogram()[768:1024])

def pil_to_white_gif(i):
    bg = Image.new('RGBA', i.size, (255, 255, 255, 255))
    bg.paste(i, i)
    return pil_to_gif(bg)

def pil_to_gif(i):
    import cStringIO
    s = cStringIO.StringIO()

    r, g, b, a = i.split()
    rgb = Image.merge('RGB', (r,g,b))
    rgb = rgb.convert('P', palette=Image.ADAPTIVE, colors=255, dither=Image.NONE)
    pal = rgb.getpalette()

    if len(pal) < 256*3:
        # If there's room in the palette for a transparent color, create one.
        r1, g1, b1 = pal[::3], pal[1::3], pal[2::3]
        rv = (set(xrange(256)) - set(r1)).pop()
        gv = (set(xrange(256)) - set(g1)).pop()
        bv = (set(xrange(256)) - set(b1)).pop()
        pal[-3:] = [rv, gv, bv]
        rgb.putpalette(pal, rawmode='RGB')
        a2 = a.point(lambda p: 0 if p >= 128 else 255)
        rgb.paste(255, (0,0), a2)
        rgb.save(s, 'GIF', transparency=255, interlace=False)
    else:
        # Otherwise, just save the GIF.
        rgb.putpalette(pal, rawmode='RGB')
        rgb.save(s, 'GIF', interlace=False)

    return s.getvalue()

#
#--- resizing images
#

@refmemoize
def wxbitmap_resizedwh(wxbitmap, w, h):
#   print 'wxbitmap_resizedwh', wxbitmap, w, h
    return pil_to_wxbitmap(pilimg_resizedwh(wximage_to_pil(wxbitmap_to_wximage(wxbitmap)), w, h))

@refmemoize
def wxbitmap_resized(wxbitmap, size):
    '''
    Returns a resized version of a bitmap.

    "size" can either be an integer or a sequence of two integers.
    '''
#   print 'wxbitmap_resized', wxbitmap, size
    try:
        # sequence: width and height were given
        w, h = size
    except TypeError:
        # one integer: place the image in a square of width and height "size"
        return wxbitmap_in_square(wxbitmap, size)
    else:
        return wxbitmap_resizedwh(wxbitmap, w, h)

def wxbitmap_resized_smaller(wxbitmap, size):
    if max(wxbitmap.Width, wxbitmap.Height) > size:
        return wxbitmap.Resized(size)
    else:
        return wxbitmap

def pil_resized_smaller(pil, size):
    return pil.Resized(size) if max(pil.size) > size else pil

@objmemoize
def pilimg_resized(pilimg, size):
#   print 'pilimg_resized', pilimg, size

    try:
        w, h = size
    except TypeError:
        return pilimg_in_square(pilimg, size)
    else:
        return pilimg_resizedwh(pilimg, w, h)


@objmemoize
def pilimg_convert(pilimg, mode):
    return pilimg.convert(mode)

@objmemoize
def pilimg_resizedwh(pilimg, w, h):
#   print 'pilimg_resizedwh', pilimg, w, h

    w = pilimg.size[0] if w == -1 else int(w)
    h = pilimg.size[1] if h == -1 else int(h)
    size = (w, h)

    if pilimg.mode == 'P': # resizing paletted images doesn't antialias
        pilimg = pilimg_convert(pilimg, 'RGBA')

    return pilimg.resize(size, Image.ANTIALIAS if min(size) < min(pilimg.size) else Image.BICUBIC)

@objmemoize
def pilimg_in_square(img, squaresize):
    '''
    Resizes a PIL Image to a square, maintaining aspect ratio.

    squaresize must be an integer
    '''
#   print 'pilimg_in_square', img, squaresize

    w, h = img.size

    if img.mode == 'P': # resizing paletted images doesn't antialias
        img = pilimg_convert(img, 'RGBA')

    # make a completely transparent square
    new = Image.new('RGBA', (squaresize, squaresize), (0, 0, 0, 0))

    if w > h:
        new_height = int(h/float(w) * squaresize)
        img = img.resize((squaresize, new_height), BICUBIC if squaresize > w else ANTIALIAS)
        new.paste(img, (0, (squaresize - new_height)/2))
    else:
        new_width = int(w/float(h) * squaresize)
        img = img.resize((new_width, squaresize), BICUBIC if squaresize > h else ANTIALIAS)
        new.paste(img, ((squaresize - new_width)/2, 0))

    return new

@objmemoize
def pil_resize_canvas(img, w, h, alignment = wx.ALIGN_CENTER):
#   print 'pil_resize_canvas', img, w, h, alignment
    if alignment != wx.ALIGN_CENTER:
        raise NotImplementedError

    ow, oh = img.size
    new = Image.new('RGBA', (w, h), (0, 0, 0, 0))

    new.paste(img, (w / 2 - ow / 2, w / 2 - oh / 2))

    return new

def pil_setalpha(img, alpha):
    'Multiplies "alpha" by the images existing alpha channel. In place.'

#   print 'pil_setalpha', img, alpha

    assert hasattr(img, 'size'), 'Image must be a PIL Image'
    assert 0 <= alpha <= 1, 'alpha must be 0 <= alpha <= 1'

    channels = img.split()
    if len(channels) == 4:
        r, g, b, a = channels
    elif len(channels) == 3:
        a = Image.new('L', img.size, 'white')
    else:
        raise AssertionError('Cannot set alpha, image does not have 3 or 4 bands.')

    img.putalpha(ImageEnhance.Brightness(a).enhance(alpha))



@refmemoize
def wxbitmap_in_square(bmp, squaresize, scaleup = True):
#   print 'wxbitmap_insquare', bmp, squaresize, scaleup

    w, h = bmp.Width, bmp.Height

    if w > squaresize or h > squaresize or scaleup:
        img = ImageFromBitmap(bmp)
        if w > h:
            new_height = int(h/float(w) * squaresize)
            img = img.Scale(squaresize, new_height, IMAGE_QUALITY_HIGH)
            offset = Point(0, (squaresize - new_height) / 2)
        else:
            new_width = int(w/float(h) * squaresize)
            img = img.Scale(new_width, squaresize, IMAGE_QUALITY_HIGH)
            offset = Point((squaresize - new_width) / 2, 0)

        return BitmapFromImage(img)

    return bmp

#
#--- image effects
#

@refmemoize
def wxbitmap_greyed(bitmap):
    'Returns a greyscale version of the bitmap.'

    return wximage_to_wxbitmap(wxbitmap_to_wximage(bitmap).ConvertToGreyscale())

@objmemoize
def pilimg_greyed(pil):
    pil = pil.copy()

    # save the alpha channel if there is one.
    alpha = 'A' in pil.getbands()
    if alpha: r, g, b, a = pil.split()

    # convert to greyscale
    pil = ImageOps.grayscale(pil)

    # reapply alpha channel (if necessary)
    if alpha: pil.putalpha(a)

    return pil



def drop_shadow(image, offset=(5, 5), background=(0, 0, 0, 0), shadow=0x444444,
                border=8, iterations=3):
  """
  Add a gaussian blur drop shadow to an image.

  image       - The image to overlay on top of the shadow.
  offset      - Offset of the shadow from the image as an (x,y) tuple.  Can be
                positive or negative.
  background  - Background colour behind the image.
  shadow      - Shadow colour (darkness).
  border      - Width of the border around the image.  This must be wide
                enough to account for the blurring of the shadow.
  iterations  - Number of times to apply the filter.  More iterations
                produce a more blurred shadow, but increase processing time.
  """
  image = image.PIL

  # Create the backdrop image -- a box in the background colour with a
  # shadow on it.
  totalWidth = image.size[0] + abs(offset[0]) + 2*border
  totalHeight = image.size[1] + abs(offset[1]) + 2*border
  back = Image.new(image.mode, (totalWidth, totalHeight), background)

  # Place the shadow, taking into account the offset from the image
  shadowLeft = border + max(offset[0], 0)
  shadowTop = border + max(offset[1], 0)
  back.paste(shadow, [shadowLeft, shadowTop, shadowLeft + image.size[0],
    shadowTop + image.size[1]])

  # Apply the filter to blur the edges of the shadow.  Since a small kernel
  # is used, the filter must be applied repeatedly to get a decent blur.
  n = 0
  while n < iterations:
    back = back.filter(ImageFilter.BLUR)
    n += 1

  # Paste the input image onto the shadow backdrop
  imageLeft = border - min(offset[0], 0)
  imageTop  = border - min(offset[1], 0)
  back.paste(image, (imageLeft, imageTop))

  return back

def pil_combine(imgs, direction = wx.HORIZONTAL, align = wx.ALIGN_CENTER):
    'Combines images horizontally or vertically.'

    imgs = [img.PIL for img in imgs]
    length_idx = [wx.HORIZONTAL, wx.VERTICAL].index(direction)
    breadth_idx = 0 if length_idx else 1

    length = breadth = 0

    for img in imgs:
        size = img.size
        length += size[length_idx]
        breadth = max(breadth, size[breadth_idx])

    newsize = (length, breadth) if direction == wx.HORIZONTAL else (breadth, length)
    newimg = Image.new('RGBA', newsize, (0, 0, 0, 0))

    pos = (0, 0)
    for img in imgs:
        newimg.paste(img, pos)
        if direction == wx.HORIZONTAL:
            pos = (pos[0] + img.size[0], pos[1])
        else:
            pos = (pos[0], pos[1] + img.size[1])

    return newimg

def rounded_corners(corner_size = 1, rounded_imgs = {}):
    if not isinstance(corner_size, int):
        import util
        corner_size = util.try_this(lambda: int(bool(corner_size)), 1)
    else:
        corner_size = max(0, min(corner_size, 3))

    try: return rounded_imgs[corner_size]
    except KeyError: pass

    imgs = []

    from gui import skin
    rounded_img = Image.open(skin.resourcedir() / ('corner' + str(corner_size) + '.gif')).convert('L')

    for name, rotation in CORNERS:
        mask = rounded_img.transpose(rotation) if rotation is not None else rounded_img
        imgs.append(mask)

    return rounded_imgs.setdefault(corner_size, imgs)

def rounded_mask(size, cornersize = 1):
    '''
    Returns a grayscale image with the specified size, with alpha values
    dropping off at the corners.
    '''

    img = Image.new('L', size, 255)
    w, h = size
    p, r = img.paste, rounded_corners(cornersize)
    i = r[0]; p(i, (0, 0, i.size[0], i.size[1]))    # top left
    i = r[1]; p(i, (w-i.size[0], 0, w, i.size[1]))    # top right
    i = r[2]; p(i, (0, h-i.size[1], i.size[0], h)) # bottom left
    i = r[3]; p(i, (w-i.size[0], h-i.size[1], w, h))         # bottom right

    return img

@objmemoize
def pilimg_rounded(image, cornersize = 1):
    '''
    Return a copy of the image (wx.Image, wx.Bitmap, or PIL.Image) with the
    corners rounded.

    cornersize can be 1, 2, or 3, specifying the size of the corners to
    chop off
    '''

    # at each pixel, take the minimum of the rounded mask and the alpha
    # channel of the original image
    newimage = image.copy()
    newimage.putalpha(ImageMath.eval('convert(min(a,b), "L")',
                                 a = newimage.split()[-1],
                                 b = rounded_mask(newimage.size, cornersize)))
    return newimage


@refmemoize
def wxbitmap_rounded(wxbitmap, cornersize = 1):
#    print 'wxbitmap_rounded', wxbitmap, cornersize

    if cornersize == 0:
        return wxbitmap
    else:
        return pil_to_wxbitmap(pilimg_rounded(wximage_to_pil(wxbitmap_to_wximage(wxbitmap)), cornersize))

def wxbitmap_decodedsize(b):
    return b.Width * b.Height * (3 if not b.HasAlpha() else 4)

def wximage_decodedsize(i):
    return i.Width * i.Height * 4

def pil_decodedsize(p):
    width, height = p.size
    bpp = {'RGBA': 4, 'RGB': 3, 'L': 1}.get(p.mode, 0)
    return width * height * bpp


#
#--- patching methods into classes
#

Image.Image.Resized = pilimg_resized
Image.Image.ResizedSmaller = pil_resized_smaller
Image.Image.Rounded = pilimg_rounded
Image.Image.WXB     = property(lambda pil: pil_to_wxbitmap(pil))
Image.Image.WX      = property(lambda pil: pil_to_wximage(pil))
Image.Image.Greyed  = property(pilimg_greyed)
Image.Image.ResizeCanvas = pil_resize_canvas
Image.Image.PIL     = property(lambda pil: pil)
Image.Image.DecodedSize = property(lambda self: pil_decodedsize(self))

wx.Bitmap.Resized = wxbitmap_resized
wx.Bitmap.ResizedSmaller = wxbitmap_resized_smaller
wx.Bitmap.Greyed  = property(wxbitmap_greyed)
wx.Bitmap.Rounded = wxbitmap_rounded
wx.Bitmap.WXB     = property(lambda self: self)
wx.Bitmap.WX      = property(lambda wxb: wxbitmap_to_wximage(wxb))
wx.Bitmap.PIL     = property(lambda self: wxbitmap_to_pil(self))
wx.Bitmap.Inverted = property(wxbitmap_inverted)
wx.Bitmap.DecodedSize = property(lambda self: wxbitmap_decodedsize(self))

wx.Image.WX  = property(lambda self: self)
wx.Image.WXB = property(lambda self: wximage_to_wxbitmap(self, 32))
wx.Image.PIL = property(lambda self: wximage_to_pil(self))
wx.Image.DecodedSize = property(lambda self: wximage_decodedsize(self))

wx.Icon.PIL       = property(lambda self: wxicon_to_pil(self))
wx.Icon.WXB       = property(lambda self: wxicon_to_bitmap(self))


# non-caching image conversion functions
def pil_to_wxb_nocache(pil):
    return wx.BitmapFromImage(pil_to_wximage.nocache(pil))

def wxb_to_pil_nocache(wxb):
    return wximage_to_pil.nocache(wxb.ConvertToImage())

if __name__ == '__main__':
    from tests.testapp import testapp
    from gui.skin import get
    a = testapp('../../..')

    img = Image.new('RGBA', (40, 50), 'red')#get('appdefaults.taskbaricon')
    img.Resized(100).Show()


    a.MainLoop()
