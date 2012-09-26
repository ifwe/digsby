'''

Parses skin syntax.

'''
from __future__ import division, with_statement
import wx
from itertools import izip

from util.primitives.funcs import isint
from util.primitives.mapping import Storage as S
from util.primitives.misc import clamp
from path import path

from gui.toolbox import colorfor
from gui.textutil import default_font
from gui.skin.skinobjects import SkinGradient, SkinColor, Margins, SkinStack
from gui.skin import SkinException, skinpath

import cgui
if not hasattr(cgui, 'ImageDataFromSource'):
    cgui.ImageDataFromSource = cgui.ImageData
    cgui.SIRegion = cgui.Region

from cgui import SplitImage4, ImageData, ImageDataFromSource, Extend, SIRegion

from logging import getLogger; log = getLogger('skinparse')

sentinel = object()

# valid words in a font line

fontstyles  = ('slant', 'italic')    # -> wx.FONTSTYLE_%s
fontweights = ('light', 'bold')      # -> wx.FONTWEIGHT_%s
fontflags   = ('underline',) + fontstyles + fontweights

DEFAULT_ROUNDED_RADIUS = 6

# If true, split image offsets are all treated as positive offsets from an edge
SPLITIMAGE_POSITIVE_OFFSETS = True


# style:
# 0 - canvas resize, image does not
# 1 - stretch
# 2 - tile
regionTypes = S(static  = 0,
                stretch = 1,
                tile    = 2)


SIREGIONS = ('left', 'right', 'center', 'top', 'bottom')

SIEXTENDS = ('left', 'up', 'down', 'right')

regionAlignments = dict(
  h_center   = wx.ALIGN_CENTER_HORIZONTAL,
  v_center   = wx.ALIGN_CENTER_VERTICAL,
  h_left     = wx.ALIGN_LEFT,
  h_right    = wx.ALIGN_RIGHT,
  v_top      = wx.ALIGN_TOP,
  v_bottom   = wx.ALIGN_BOTTOM)

def makePadding(s):
    if isinstance(s, int):
        return s
    elif isinstance(s, basestring):
        return wx.Point(*(int(c) for c in s.split()))
    else:
        return wx.Point(*(s * 2 if len(s) == 1 else s))

def makeExtend(e):
    left, up, down, right = [(a in e) for a in SIEXTENDS]
    return Extend(up, down, left, right)

def makeRegion(rdict):
    '''
    left:
      hstyle: tile
      vstyle: static
      offset: 5 -5
      align: left
      extends: [left up down right]
    '''

    h = rdict.get('hstyle', regionTypes.stretch)
    v = rdict.get('vstyle', regionTypes.stretch)

    try:             offset = rdict['offset']
    except KeyError: offset = wx.Point()
    else:            offset = makePadding(offset)

    try: e = rdict.get('extend')
    except: e = Extend()
    else: e = makeExtend(e)

    align = rdict.get('align', wx.ALIGN_CENTER)

    return SIRegion(e, h, v, align, offset)

def solid_si4(name):
    'Return a no-cut SplitImage4 that stretches.'

    return si4(S(source = name))

def si4(imgdict):
    try:
        imgdict.source = unicode(skinpath(imgdict.source))
    except:
        pass

    if not path(imgdict.source).isfile():
        raise SkinException('cannot find file %s' % imgdict.source )

    idata = ImageDataFromSource(imgdict.source)

    for attr in ('x1', 'x2', 'y1', 'y2'):
        setattr(idata, attr, imgdict.get(attr, 0))

    if SPLITIMAGE_POSITIVE_OFFSETS:
        # splitimage4 expects negative numbers for x2/y2
        idata.x2 = -idata.x2 #+ (1 if idata.x2 else 0)
        idata.y2 = -idata.y2 #+ (1 if idata.x2 else 0)

    for attr in SIREGIONS:
        if attr in imgdict:
            region = makeRegion(imgdict[attr])
        else:
            region = SIRegion(Extend(), 1, 1, wx.ALIGN_CENTER, wx.Point())

        setattr(idata, attr, region)

    s = SplitImage4(idata)
    s.ytile = False
    s.idata = idata
    s.copy  = lambda *a: si4copy(s, *a)
    s.path = path(s.GetPath())
    return s

def si4copy(split, x1, y1, x2, y2):
    idata = ImageData(split.idata)

    idata.x1 = x1
    idata.y1 = y1
    idata.x2 = x2
    idata.y2 = y2

    if SPLITIMAGE_POSITIVE_OFFSETS:
        idata.x2 = -idata.x2
        idata.y2 = -idata.y2

    s = SplitImage4(idata)
    s.ytile = False
    s.idata = idata
    s.copy  = lambda *a: si4copy(s, *a)
    s.path = split.path

    return s

imageExts = ('jpg', 'jpeg', 'png', 'bmp', 'gif')

def makeImage(imagedesc):
    'Parses an image description, returning a SolidImage or SplitImage4.'

    imagedesc = imagedesc.strip()
    if not imagedesc: return None

    # use the image extension as the "split" point between the filename
    # and the options, so that spaces in image filenames are possible
    # without quotes.
    i = max(imagedesc.find('.' + ext) for ext in imageExts)
    if i == -1: raise SkinException('images end in %r' % (imageExts,))

    i = imagedesc.find(' ', i)
    if i == -1:
        # just "image.png" -- return a SolidImage.
        return solid_si4(imagedesc)

    filename, options = imagedesc[:i], imagedesc[i+1:]

    imgdict = S(source = filename)
    options = options.split()

    if options:
        # one-liner: image with cuts

        if isint(options[0]):
            # numbers...must be a splitimage
            n = len(options)
            for i, opt in enumerate(options):
                if not isint(opt):
                    n = i
                    break

            splits, options = options[:n], options[n:]
            if not splits: solid_si4(imgdict['source'])

            # parsing rules for splits are same as framesizes
            imgdict.update(izip(('x1', 'y1', 'x2', 'y2'), Margins(splits)))

        hstyle = vstyle = regionTypes.stretch
        align           = None
        posSpecified    = False
        offset          = []

        for option in options:
            if option.startswith('h_'):
                if option in ('h_right', 'h_center', 'h_left'):
                    hstyle = regionTypes.static
                    if align is None:
                        align = regionAlignments[option]
                    else:
                        align |= regionAlignments[option]
                else:
                    hstyle = regionTypes[option[2:]]
            elif option.startswith('v_'):
                if option in ('v_top', 'v_center', 'v_bottom'):
                    vstyle = regionTypes.static
                    if align is None:
                        align = regionAlignments[option]
                    else:
                        align |= regionAlignments[option]
                else:
                    vstyle = regionTypes[option[2:]]

            elif option == 'tile':
                hstyle = vstyle = regionTypes.tile

            elif isint(option):
                offset += [int(option)]

            else:
                log.warning('unknown skin option "%s"')

        if len(offset) == 0:     # no offsets given: use (0, 0)
            offset = [0, 0]
        elif len(offset) == 1:   # one offset: means it is used for both X and Y
            offset = offset * 2
        else:                    # more than two: use the last two numbers found
            offset = offset[-2:]

        if align is None:
            align = wx.ALIGN_CENTER

        for a in SIREGIONS:
            imgdict[a] = S(extend = [], hstyle = hstyle, vstyle = vstyle, align = align, offset = wx.Point(*offset))
        return si4(imgdict)
    else:
        return solid_si4(imgdict['source'])

image_exts = ('png', 'jpg', 'jpeg', 'bmp', 'ico', 'gif')

def makeBrush(brushdesc):
    '''
    Makes a rectangular skin brush given strings like

    red
    red white blue
    vertical green white
    red rounded
    red rounded 10
    blue shadow
    0xffffee 0x123456
    '''

    if isinstance(brushdesc, list):
        return SkinStack(makeBrush(e) for e in brushdesc)
    elif isinstance(brushdesc, int):
        return SkinColor(colorfor(brushdesc))
    elif brushdesc is None:
        return None

    elems = brushdesc.split()

    try:
        b = elems.index('border')
    except ValueError:
        border = None
    else:
        border = makeBorder(' '.join(elems[b:]))
        elems = elems[:b]

    first = elems[0]
    if any(first.endswith(e) for e in image_exts):
        return makeImage(brushdesc)

    shadow = highlight = rounded = False
    colors = []
    direction = 'vertical'

    for i, elem in enumerate(elems):
        elem = elem.lower()

        if elem in ('h','v', 'horizontal', 'vertical'):
            direction = {'h': 'horizontal',
                         'v': 'vertical'}.get(elem, elem)
        elif elem == 'rounded':
            if len(elems) > i + 1 and isint(elems[i+1]):
                rounded = float(elems[i+1])
            else:
                rounded = DEFAULT_ROUNDED_RADIUS
        elif elem == 'highlight': highlight = True
        elif elem == 'shadow':    shadow = True
        elif elem.endswith('%') and isint(elem[:-1]) and colors:
            # replace the last wxColor in colors with the same color and
            # a new alpha value, so strings like "blue red 40%" produce
            # [wx.Colour(0, 0, 255, 255), wx.Colour(255, 0, 0, 102)]
            #
            # (I know there is a wxColour.Set method but it didn't work for me)
            alpha_value = clamp(float(elem[:-1])/100.00 * 255.0, 0, 255)
            rgba = tuple(colors[-1])[:3] + (alpha_value,)
            colors[-1] = wx.Colour(*rgba)
        else:
            try: colors.append(colorfor(elem))
            except ValueError: pass

    kwargs = dict(rounded = rounded, shadow = shadow,
                  highlight = highlight, border = border)

    if len(colors) == 0:
        raise SkinException('no colors specified in "%s"' % brushdesc)
    elif len(colors) == 1:
        # one color -> SkinColor
        return SkinColor(colors[0], **kwargs)
    else:
        # multiple colors -> SkinGradient
        return SkinGradient(direction, colors, **kwargs)

def makeBorder(borderdesc):

    vals = borderdesc.split()

    if not vals: return wx.TRANSPARENT_PEN

    if vals[0].lower() == 'border':
        vals = vals[1:]

    d = S()
    for elem in vals:
        elem = elem.lower()
        if elem.endswith('px') and isint(elem[:-2]):
            d.size = int(elem[:-2])
        elif isint(elem):
            d.size = int(elem)
        else:
            penstyle = penstyle_aliases.get(elem, elem)
            if penstyle in penstyles:
                d.style = penstyle
            else:
                try: d.color = colorfor(elem)
                except ValueError: pass

    return _pen_from_dict(d)

def _pen_from_dict(d):
    '''
    Give {color: 'blue', width:5, style:'dot'}, makes the appropriate
    wxPen object.
    '''

    color = colorfor(d.get('color', 'black'))

    width = int(d.get('size', 1))

    style = d.get('style', 'solid')

    if not style: style = 'solid'

    if not style in penstyles:
        raise SkinException('invalid pen style: "%s"' % style)

    import wx
    style = getattr(wx, style.upper())

    if not isinstance(color, wx.Colour):
        raise TypeError('not a color: %r' % color)

    return wx.Pen(color, width, style)

penstyles = set(
    ('solid',
     'transparent',
     'dot',
     'long_dash',
     'short_dash',
     'dot_dash',
     'stipple',
     'user_dash',
     'bdiagonal_hatch',
     'crossdiag_hatch',
     'fdiagonal_hatch',
     'cross_hatch',
     'horizontal_hatch',
     'vertical_hatch'))

penstyle_aliases = dict(dashed = 'long_dash')

def makeFont(fontdesc, defaultFace = None, defaultSize = None):
    '''
    Returns a wxFont for the following skin syntax:

    Arial 12 bold Underline

    or

    Comic Sans MS 14 italic strikethrough
    '''
    from gui.skin import font_multiply_factor
    system_font = default_font()

    if not fontdesc:
        return system_font
    elif isinstance(fontdesc, int):
        system_font.SetPointSize(int(fontdesc))
        return system_font


    # arguments to wx.Font constructor
    opts = dict(faceName  = defaultFace if defaultFace is not None else system_font.FaceName,
                pointSize = defaultSize if defaultSize is not None else system_font.PointSize,
                style     = wx.FONTSTYLE_NORMAL,
                weight    = wx.FONTWEIGHT_NORMAL,
                underline = False,
                family    = wx.FONTFAMILY_DEFAULT)

    fontdesc = fontdesc.strip()
    elems = fontdesc.split()

    # find the last number -- that will be the size. everything before becomes
    # the face name, and everything after is treated as flags.
    lastsize = -1
    for i, elem in enumerate(elems[::-1]):
        if isint(elem):
            lastsize = len(elems) - i - 1  # since the indices are reversed
            break

    if lastsize == -1:
        flagi = -1
        for i, elem in enumerate(elems):
            if elem in fontweights or elem in fontstyles or elem in ('underline', 'underlined'):
                flagi = i
                break

        size = defaultSize if defaultSize is not None else system_font.PointSize

        if flagi != -1:
            splitpoint = fontdesc.rfind(elems[flagi])
            facename   = fontdesc[:splitpoint].strip()
            flags      = fontdesc[splitpoint:].strip()
        else:
            facename = fontdesc.strip()
            flags = ''
    else:
        splitpoint = fontdesc.rfind(elems[lastsize])
        facename = fontdesc[:splitpoint].strip()
        size     = int(elems[lastsize])
        flags    = fontdesc[splitpoint + len(elems[lastsize]):]

    if facename:
        opts['faceName'] = facename

    opts['pointSize'] = int(size)

    # parse remaining flags
    for elem in flags.split():
        elem = elem.lower()

        if elem in fontweights:
            opts['weight'] = getattr(wx, 'FONTWEIGHT_' + elem.upper())
        elif elem in fontstyles:
            opts['style']  = getattr(wx, 'FONTSTYLE_'  + elem.upper())
        elif elem in ('underline', 'underlined'):
            opts['underline'] = True

    o = opts
    return wx.Font(o['pointSize'], o['family'], o['style'], o['weight'],
                o['underline'], o['faceName'])

