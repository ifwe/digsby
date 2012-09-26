'''
Various util fictions to convert back and forth between wxFont/wxStyle objects and various python data structures
'''

from util import Storage, try_this
import wx
from wx import Font, FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, FONTWEIGHT_NORMAL


def FontFromFacename(facename):
    return Font(10, FONTFAMILY_DEFAULT, FONTSTYLE_NORMAL, FONTWEIGHT_NORMAL, False, facename)

def FamilyNameFromFont(font):
    return font.GetFamilyString()[2:].lower()

FontAttrs = 'pointSize family style weight underline faceName encoding'.split()

def FontToTuple(font):
    args = []
    for a in FontAttrs:
        if a == 'underline':
            a = 'Underlined'
        else:
            a = str(a[0].upper() + a[1:])

        if a == 'Encoding':
            # FontEncoding is an enum, we must int it
            args.append(int(getattr(font, a)))
        else:
            args.append(getattr(font, a))
    return tuple(args)

if getattr(wx, 'WXPY', False):
    #
    # This is a hack for the WXPY bindings until it deals with enums in a more
    # sane way.
    #
    def TupleToFont(t):
        t = list(t)
        if len(t) >= 7:
            t[6] = wx.FontEncoding(t[6])

        return Font(*t)

else:
    def TupleToFont(t):
        return Font(*t)

def StorageToFont(s):
    font = Font(s.size,
                FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_ITALIC if s.italic else wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD  if s.bold else wx.FONTWEIGHT_NORMAL,
                s.underline,
                s.face)

    fgc  = s.foregroundcolor
    bgc  = s.backgroundcolor

    return font, fgc, bgc

def StyleToStorage(textattr):

        font = textattr.Font

        return Storage(
            backgroundcolor = tuple(textattr.BackgroundColour),
            foregroundcolor = tuple(textattr.TextColour),
            family = FamilyNameFromFont(font),
            face = font.FaceName,
            size = font.PointSize,
            underline = font.Underlined,
            bold = font.Weight == wx.BOLD,
            italic = font.Style == wx.ITALIC)

def StyleToDict(textattr):

    return dict(TextColour = tuple(textattr.GetTextColour()),
                BackgroundColour = tuple(textattr.GetBackgroundColour()),
                Font = FontToTuple(textattr.GetFont()))

def StorageToStyle(s):
    font, fgc, bgc = StorageToFont(s)
    fgc  = try_this(lambda: wx.Colour(*fgc), None) or wx.BLACK
    bgc  = try_this(lambda: wx.Colour(*bgc), None) or wx.WHITE
    return wx.TextAttr(fgc, bgc, font)
