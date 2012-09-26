'''

Applies transformations to the skin tree before it goes to the application.

'''

from __future__ import division
from gui.toolbox import colorfor
import wx
from util.primitives import strlist, LowerStorage, autoassign
import traceback, sys
from gui.textutil import CopyFont,default_font
from logging import getLogger; log = getLogger('skintransform')

from gui.skin import SkinException
from gui.skin.skinparse import makeBrush, makeImage, makeFont, makePadding
from gui.skin.skinobjects import Margins

# the character to use for string substitution
SUBSIGIL = '$'

def which_rule(k):
    k = k.lower()
    for rule in erules:
        if k.endswith(rule):
            return rule

def subs_common(s, common):
    '''
    >>> subs_common('$one $two $three', {'one': 'a', 'two': 'b', 'three': 'c'})
    'a b c'
    '''
    words = s.split()

    for i, word in enumerate(list(words)):
        if word.startswith(SUBSIGIL):
            val = common.get(word[1:].lower(), None)
            if val is None:
                continue
            words[i] = val

    return ' '.join(unicode(w) for w in words)


def transform(skintree, do_string_subs = True):

    if do_string_subs:
        common = skintree.setdefault('common', {})
    else:
        common = {}

    #
    # replace all $variables with their values from the "common" root key
    #
    # todo: replace only the word...problem is numbers
    #
    def apply_string_substitution(elem):
        if isinstance(elem, dict):
            for k, v in elem.iteritems():

                if isinstance(v, basestring):
                    elem[k] = subs_common(v, common)
                else:
                    elem[k] = apply_string_substitution(v)
        elif isinstance(elem, list):
            newlist = []
            for e in elem:
                if isinstance(e, basestring):
                    e = subs_common(e, common)

                newlist.append(e)
            elem[:] = newlist
        return elem

    #
    # apply all skin transformation rules defined in functions in this file
    #
    def recursive_transform(elem):
        if isinstance(elem, dict):
            for k, v in elem.iteritems():
                if k in rules:
                    elem[k] = rules[k](v)
                elif (not k.lower() in erule_excludes) and k.lower().endswith(tuple(erules.keys())):
                    elem[k] = erules[which_rule(k)](v)
                else:
                    recursive_transform(v)
        return elem

    if do_string_subs:
        return recursive_transform(apply_string_substitution(skintree))
    else:
        return recursive_transform(skintree)



# r_item means the key has to EQUAL "item"
# er_item means the kye has to END WITH "item"

def r_backgrounds(v):
    if v is None:
        return v

    for key, value in v.iteritems():
        v[key] = makeBrush(value)

    return v

def r_background(v):
    return makeBrush(v)

def r_frame(v):
    return makeBrush(v)

def r_size(s):
    return makePadding(s)

def r_framesize(s):
    return Margins(s)

def er_margins(s):
    return Margins(s)

def er_padding(s):
    return makePadding(s)

def er_colors(v):
    for colorname, color in v.iteritems():
        v[colorname] = colorfor(color)
    return v

def er_color(v):
    return colorfor(v)

def er_icons(v):
    from gui import skin
    for iconname, iconpath in v.iteritems():
        v[iconname] = skin.load_bitmap(iconpath)

    return v

def er_icon(v):
    from gui import skin
    if v.startswith('skin:'):
        return skin.get(v[5:], v)

    bitmap = skin.load_bitmap(v)
    if not bitmap.Ok():
        raise SkinException('invalid bitmap %s' % v)
    else:
        return bitmap

def er_images(v):
    for key, value in v.iteritems():
        v[key] = makeImage(value)
    return v

def er_image(v):
    return makeBrush(v)


def r_directionicons(v):
    from gui import skin as skincore; img = skincore.load_image
    up    = img(v.up)    if 'up'    in v else None
    down  = img(v.down)  if 'down'  in v else None
    left  = img(v.left)  if 'left'  in v else None
    right = img(v.right) if 'right' in v else None

    count = len(filter(None, [up, down, left, right]))

    if count==2 and not (left and right or up and down):
        if not left:  left = right.Mirror(True)
        if not right: right = left.Mirror(True)
        if not up:    up = down.Mirror(False)
        if not down:  down = up.Mirror(False)
    elif count!=4:
        while not (up and down and left and right):
            if not up:    up    = left.Rotate90()
            if not right: right = up.Rotate90()
            if not down:  down  = right.Rotate90()
            if not left:  left  = down.Rotate90()


    return LowerStorage({'up':    wx.BitmapFromImage(up),
                         'down':  wx.BitmapFromImage(down),
                         'left':  wx.BitmapFromImage(left),
                         'right': wx.BitmapFromImage(right)})

def r_color(v):
    return wx.Brush(colorfor(v))


def er_fonts(v):
    for key, value in v.iteritems():
        v[key] = r_font(value)

    return v

def r_fontcolor(v):
    return colorfor(v)

def r_font(v):
    return makeFont(v)

# Make a "rules" dictionary with all the functions in this module that begin
# with r_ (the r_ is chopped off for the keys in the dictionary, the values
# are the callable functions themselves)

erule_excludes=[
    'emoticon',
    'emoticons',
    'buddyicons',
]

rules = {}
for func in locals().values():
    if callable(func) and func.__name__.startswith('r_'):
        rules[func.__name__[2:]] = func

erules={}

for func in locals().values():
    if callable(func) and func.__name__.startswith('er_'):
        erules[func.__name__[3:]] = func
