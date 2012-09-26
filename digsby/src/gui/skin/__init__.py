'''

Skin management

'''
from __future__ import with_statement
from wx import Image, BITMAP_TYPE_ANY, BitmapFromImage, GetApp, ImageFromString

from path import path
from logging import getLogger; log = getLogger('skin')
from types import FunctionType
from util.data_importer import zipopen
from util.primitives import Storage
import time

class SkinException(Exception):
    'Thrown when the structure of a skin file is invalid.'

def skinpath(name, exc = True):
    respaths = GetApp().skin.paths
    return skinfile(name, respaths, exc)

def skinfile(name, paths, exc = True):
    #fast loop
    for p in reversed(paths):
        imgpath = p / name
        if imgpath.isfile():
            return imgpath
    #slow loop
    for p in reversed(paths):
        imgpath = p / name
        try:
            foo = zipopen(imgpath).read()
        except Exception:
            pass
        else:
            if foo is not None:
                return imgpath

    if exc:
        raise SkinException('could not find skinfile %s (paths: %r)' % (name, paths))
    else:
        return None

def basepath(name, exc = True):
    path = GetApp().skin.path
    return skinfile(name, paths=[path], exc=exc)

#from gui.skin import skintree

def skininit(pth, skinname = 'default'):

    if not hasattr(pth, 'abspath'):
        pth = path(pth)

    set_resource_paths([pth.abspath()])

    global _css_fonts
    _css_fonts = None
    set_active(skinname)

def reload():
    'Reloads the active skin.'

    t = time.clock()
    from common import pref
    global _css_fonts
    _css_fonts = None
    set_active(pref('appearance.skin'), pref('appearance.variant'), True)
    log.info('skin reloaded in %ss', (time.clock() - t))

def set_resource_paths(resource_paths):
    '''
    Tell the skin system where the resource path is.

    This path should contain a "skins" directory.
    '''

    from gui.skin import skintree
    skintree.resource_paths = [path(p).abspath() for p in resource_paths]

def get_resource_paths():
    '''
    Returns the resource path.
    '''

    from gui.skin import skintree
    return skintree.resource_paths

from skintree import set_active, list_skins, skindesc, get as skintree_get

sentinel = object()

def resourcedir():
    return get_resource_paths()[0]

class LazyImage(object):
    def __init__(self, pth, return_bitmap):
        self.pth = pth
        self.return_bitmap = return_bitmap

    def _lazy_skin_load(self):
        return _loadimage(self.pth, return_bitmap = self.return_bitmap)

    def Ok(self):
        return True

class SkinStorage(Storage):
    '''
    lazy loads skin images
    '''

    def __getitem__(self, key, gi = dict.__getitem__):
        return self._lazy_load(key, gi(self, key))

    def get(self, key, default=sentinel):
        if default is sentinel:
            val = Storage.get(self, key)
        else:
            val = Storage.get(self, key, default)

        return self._lazy_load(key, val)

    def _lazy_load(self, key, val):
        if hasattr(val, '_lazy_skin_load'):
            img = val._lazy_skin_load()
            self[key] = img
            return img
        else:
            return val

    def __getattr__(self, key, ga = dict.__getattribute__, gi = __getitem__):
        try:
            return ga(self, key)
        except AttributeError:
            try:
                return gi(self, key)
            except KeyError:
                msg = repr(key)
                if len(self) <= 20:
                    keys = sorted(self.keys())
                    msg += '\n  (%d existing keys: ' % len(keys) + str(keys) + ')'
                raise AttributeError, msg


def get(dotted_path, default = sentinel):

    if dotted_path.startswith('skin:'):
        dotted_path = dotted_path[5:]

    v = skintree_get(dotted_path, default = default)
    if v is sentinel:
        raise SkinException('not found: "%s"' % dotted_path)
    elif v is default:
        return v() if isinstance(v, FunctionType) else v
    else:
        return v



def load_bitmap(name, return_bitmap = True):
    return LazyImage(skinpath(name), return_bitmap)
    #return _loadimage(skinpath(name), return_bitmap = return_bitmap)

def load_image(name):
    return load_bitmap(name, False)


def _loadimage(path, return_bitmap = False):
    try:
        if path.isfile():
            img = Image(path, BITMAP_TYPE_ANY)
        else:
            f = None
            try:
                f = zipopen(path)
                if f is None:
                    raise IOError('Image ' + path + ' does not exist')
                img = ImageFromString(f.read())
            finally:
                if f is not None:
                    f.close()

        if not img.HasAlpha():
            img.InitAlpha()

        val = img if not return_bitmap else BitmapFromImage(img)
        val.path = path
        return val

    except Exception, err:
        raise AssertionError(err)


import urllib2

try:
    urllib2.urlopen('')  # ensure an opener is present
except Exception, e:
    pass

class SkinHandler(urllib2.BaseHandler):
    def skin_open(self, req):
        from util import Storage
        val = get(req.get_host())
        return Storage(read=lambda:val)

urllib2._opener.add_handler(SkinHandler())

from gui.skin.skinobjects import Margins
ZeroMargins = Margins()

from gui.skin.skinparse import \
    makeBrush as brush, \
    makeFont  as font

font_multiply_factor = 1.0


def build_font_css():
    import wx
    from gui.textutil import default_font
    from util import Point2HTMLSize

    h = Storage()

#-------------------------------------------------------------------------------
#       Code for TagFont function
#----------------------------------------
    h.header   = get('infobox.fonts.header', default_font)
    h.title    = get('infobox.fonts.title', default_font)
    h.major    = get('infobox.fonts.major', default_font)
    h.minor    = get('infobox.fonts.minor', default_font)
    h.link     = get('infobox.fonts.link',  default_font)

    h.headerfc = get('infobox.fontcolors.header', wx.BLACK).GetAsString(wx.C2S_HTML_SYNTAX)
    h.titlefc  = get('infobox.fontcolors.title', wx.BLACK).GetAsString(wx.C2S_HTML_SYNTAX)
    h.majorfc  = get('infobox.fontcolors.major', wx.BLACK).GetAsString(wx.C2S_HTML_SYNTAX)
    h.minorfc  = get('infobox.fontcolors.minor', lambda: wx.Color(128, 128, 128)).GetAsString(wx.C2S_HTML_SYNTAX)
    h.linkfc   = get('infobox.fontcolors.link', wx.BLUE).GetAsString(wx.C2S_HTML_SYNTAX)

    import io
    sio = io.StringIO()
    for name in ('major', 'minor', 'header', 'title', 'link'):
        writeline = lambda s: sio.write(s+u'\n')
        if name == 'link':
            sio.write(u'a, ')

        writeline('.%s {' % name)
        writeline('\tcolor: %s;' % getattr(h, '%sfc' % name))
        writeline('\tfont-family: "%s";' % h[name].FaceName)
        writeline('\tfont-size: %spt;' % h[name].PointSize)
        if h[name].Style == wx.ITALIC:
            writeline('\tfont-style: italic;')
        else:
            writeline('\tfont-style: normal;')

        if h[name].Weight == wx.BOLD:
            writeline('\tfont-weight: bold;')
        else:
            writeline('\tfont-weight: normal;')

        if h[name].Underlined:
            writeline('\ttext-decoration: underline;')
        else:
            writeline('\ttext-decoration: none;')

        writeline('}')

    return sio.getvalue()

_css_fonts = None
def get_css_fonts():
    '''
    return some generated CSS related to fonts
    '''
    global _css_fonts
    if _css_fonts is None:
        _css_fonts = build_font_css()
    return _css_fonts

def get_css_images():
    '''
    return some generated CSS with stuff related to images (?)
    '''
    import path

    sep1 = get('infobox.shortseparatorimage')
    sep2 = get('infobox.longseparatorimage')
    return ('''
hr {
 border-style: none;
 height: %spx;
 background: url("%s");
}''' % (sep1.Size.height, path.path(sep1.Path).url())) +\
('''
hr[type="2"] {
 border-style: none;
 height: %spx;
 background: url("%s");
}
''' % (sep2.Size.height, path.path(sep2.Path).url()))

def get_css_layout():
    '''
    return some generated CSS with stuff related to padding, margins, borders, etc.
    '''
    pad = get('infobox.margins')
    try:
        l, t, r, b = pad
    except TypeError:
        try:
            (l, t,), (r, b) = pad, pad
        except TypeError:
            t = l = b = r = pad

    return '''
body {
 margin: %spx %spx %spx %spx;
}
''' % (t, r, b, l)

def get_social_css():
    import wx
    minor_color = get('infobox.fontcolors.minor', lambda: wx.Color(128, 128, 128)).GetAsString(wx.C2S_HTML_SYNTAX)
    postrow_hover_color =  get('infobox.backgrounds.socialhovercolor', lambda: wx.Color(128, 128, 128)).GetAsString(wx.C2S_HTML_SYNTAX)
    return '''
.minor_border {{
    border-color: {minor_color};
}}
.social_background_hover:hover {{
    background-color: {postrow_hover_color};
}}
.social_background_hover_on {{
    background-color: {postrow_hover_color};
}}
'''.format(**locals())

def get_css():
    return '\n'.join((get_css_fonts(), get_css_images(), get_css_layout(), get_social_css()))
