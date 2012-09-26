from util.ffi import cimport, Struct
from ctypes.wintypes import DWORD, WCHAR
from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
from ctypes import c_ushort, sizeof

from gui.native.win.winutil import WinStruct
from gui.textutil import default_font
from cgui import PyGetFontUnicodeRanges


# constants used in AddFontResourceEx function
FR_PRIVATE  = 0x10
FR_NOT_ENUM = 0x20

def loadfont(fontpath, private = True, enumerable = False):
    '''
    Makes fonts located in file "fontpath" available to the font system.

    private  if True, other processes cannot see this font, and this font
             will be unloaded when the process dies

    enumerable  if True, this font will appear when enumerating fonts

    see http://msdn2.microsoft.com/en-us/library/ms533937.aspx
    '''

    if isinstance(fontpath, str):
        pathbuf = create_string_buffer(fontpath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExA
    elif isinstance(fontpath, unicode):
        pathbuf = create_unicode_buffer(fontpath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExW
    else:
        raise TypeError('fontpath must be a str or unicode')

    flags = (FR_PRIVATE if private else 0) | (FR_NOT_ENUM if not enumerable else 0)

    numFontsAdded = AddFontResourceEx(byref(pathbuf), flags, 0)

    return bool(numFontsAdded)

def unloadfont(fontpath, private = True, enumerable = False):
    '''
    Unloads the fonts in the specified file.

    see http://msdn2.microsoft.com/en-us/library/ms533925.aspx
    '''

    if isinstance(fontpath, str):
        pathbuf = create_string_buffer(fontpath)
        RemoveFontResourceEx = windll.gdi32.RemoveFontResourceExA
    elif isinstance(fontpath, unicode):
        pathbuf = create_unicode_buffer(fontpath)
        RemoveFontResourceEx = windll.gdi32.RemoveFontResourceExW
    else:
        raise TypeError('fontpath must be a str or unicode')


    flags = (FR_PRIVATE if private else 0) | (FR_NOT_ENUM if not enumerable else 0)
    return bool(RemoveFontResourceEx(byref(pathbuf), flags, 0))



_fontranges = {}

# TODO: bloom filters?

def MemoizedFontRanges(font):
    key  = hash(font.NativeFontInfoDesc)

    if key in _fontranges:
        return _fontranges[key]
    else:
        return _fontranges.setdefault(key, PyGetFontUnicodeRanges(font))

def font_has_char(font, char):
    ranges = MemoizedFontRanges(font)
    char = ord(unicode(char))

    for start, len in ranges:
        end = start + len
        if start <= char < end:
            return True

    return False


def main():
    import wx
    dc = wx.MemoryDC()
    dc.SetFont(default_font())

    size = GetFontUnicodeRanges(dc.GetHDC(), 0)
    if not size: raise Exception(GFURerror)

    numRanges = (size - sizeof(DWORD) * 4) / sizeof(WCRANGE)

    class GLYPHSET(WinStruct):
        _fields_ = [('cbThis', DWORD),
                    ('flAccel', DWORD),
                    ('cGlyphsSupported', DWORD),
                    ('cRanges', DWORD),
                    ('ranges', WCRANGE * numRanges),
                    ]

    g = GLYPHSET(cbThis = size, ranges = [WCRANGE() for x in xrange(numRanges)])


    if not GetFontUnicodeRanges(dc, glyphset.ptr):
        raise Exception(GFURerror)

    print g

GFURerror = 'GetFontUnicodeRanges failed, see http://msdn2.microsoft.com/en-us/library/ms533944(VS.85).aspx'

if __name__ == '__main__':
    import wx
    a = wx.PySimpleApp()
    main()
