'''
Vista visual polish and effects.
'''
from gui.textutil import default_font
from gui.toolbox import TransparentBitmap

import ctypes, wx

# Use dwmapi.dll
dwm = ctypes.windll.dwmapi
ux  = ctypes.windll.uxtheme

from ctypes.wintypes import RECT, DWORD, BOOL, HRGN, COLORREF, POINT, LPARAM
from ctypes import byref, c_int32, c_void_p, Structure

# These controls' default font will be changed.
adjusted_controls = [
    wx.StaticText,
    wx.CheckBox,
    wx.TextCtrl,
    wx.Button,
    wx.HyperlinkCtrl,
    wx.StaticBox,
    wx.RadioBox,
    wx.RadioButton,
    wx.Choice,
    wx.ComboBox,
    wx.FilePickerCtrl,
    wx.DirPickerCtrl,
]

# Substitute in a nicer console font for PyCrust
from wx.py.editwindow import FACES
FACES['mono'] = 'Consolas'

def _change_font(ctrl):
    'Changes the default font of a control after its construction.'

    oldinit = ctrl.__init__

    def newinit(self, *a, **k):
        try:
            oldinit(self, *a, **k)
        except:
            # WXPYHACK
            from util import funcinfo
            import sys
            print >> sys.stderr, '_change_font failed at %s' % funcinfo(oldinit)
            raise
        self.SetFont(default_font())

    ctrl.__init__ = newinit

for ctrl in adjusted_controls:
    _change_font(ctrl)

class DWM_BLURBEHIND(Structure):
    _fields_ = [
        ('dwFlags', DWORD), # A bitwise combination of DWM Blur Behind Constants values indiciating which members are set.
        ('fEnable', BOOL),  # true to register the window handle to DWM blur behind; false to unregister the window handle from DWM blur behind.
        ('hRgnBlur', HRGN), # The region within the client area to apply the blur behind. A NULL value will apply the blur behind the entire client area.
        ('fTransitionOnMaximized', BOOL) # TRUE if the window's colorization should transition to match the maximized windows; otherwise, FALSE.
    ]

class DTTOPTS(Structure):
    _fields_ = [
        ('dwSize',          DWORD),
        ('dwFlags',         DWORD),
        ('crText',          COLORREF),
        ('crBorder',        COLORREF),
        ('crShadow',        COLORREF),
        ('iTextShadowType', c_int32),
        ('ptShadowOffset',  POINT),
        ('iBorderSize',     c_int32),
        ('iFontPropId',     c_int32),
        ('iColorPropId',    c_int32),
        ('iStateId',        c_int32),
        ('fApplyOverlay',   BOOL),
        ('iGlowSize',       c_int32),
        ('pfnDrawTextCallback', c_void_p),
        ('lParam',          LPARAM),
    ]


DWM_BB_ENABLE = 0x01
DWM_BB_BLURREGION = 0x02
DWM_BB_TRANSITIONONMAXIMIZED = 0x04

#
# glass effects with dwmapi.dll
#

def glassExtendInto(win, left = -1, right = -1, top = -1, bottom = -1):
    """
    Extends a top level window's frame glass into the client area by the
    specified margins. Returns True upon success.

    If desktop composition is not enabled, this function will do nothing
    and return False.
    """
    rect = RECT(left, right, top, bottom)

    if IsCompositionEnabled():
        dwm.DwmExtendFrameIntoClientArea(win.Handle, byref(rect))
        return True
    else:
        return False

def glassBlurRegion(win, region = 0):
    bb = DWM_BLURBEHIND()
    bb.dwFlags = DWM_BB_ENABLE
    bb.fEnable = 1
    bb.hRgnBlur = region

    return dwm.DwmEnableBlurBehindWindow(win.Handle, byref(bb))

def IsCompositionEnabled():
    'Returns True if the WDM is allowing composition.'

    enabled = c_int32(0)
    dwm.DwmIsCompositionEnabled(byref(enabled))
    return bool(enabled)
#
#    HRESULT DrawThemeTextEx(
#        HTHEME hTheme,
#        HDC hdc,
#        int iPartId,
#        int iStateId,
#        LPCWSTR pszText,
#        int iCharCount,
#        DWORD dwFlags,
#        LPRECT pRect,
#        const DTTOPTS *pOptions
#    );


class ThemeMixin(object):
    def __init__(self, window):
        self._hTheme = ux.OpenThemeData(window.Handle, u"globals")
        print 'hTheme', self._hTheme

    def __del__(self):
        # Closes the theme data handle.
        ux.CloseThemeData(self._hTheme)

#
# text constants
#

DTT_COMPOSITED = 8192
DTT_GLOWSIZE = 2048
DTT_TEXTCOLOR = 1

DT_TOP        = 0x00000000
DT_LEFT       = 0x00000000
DT_CENTER     = 0x00000001
DT_RIGHT      = 0x00000002
DT_VCENTER    = 0x00000004
DT_WORDBREAK  = 0x00000010
DT_SINGLELINE = 0x00000020
DT_NOPREFIX   = 0x00000800

def DrawThemeTextEx(win, handle, text):
    # Draw the text
    dto = DTTOPTS()
    uFormat = DT_SINGLELINE | DT_CENTER | DT_VCENTER | DT_NOPREFIX

    dto.dwFlags = DTT_COMPOSITED | DTT_GLOWSIZE
    dto.iGlowSize = 10

    rcText2 = RECT(0,0,150,30)
    #rcText2 -= rcText2.TopLeft() # same rect but with (0,0) as the top-left

#HRESULT DrawThemeTextEx(
#    HTHEME hTheme,
#    HDC hdc,
#    int iPartId,
#    int iStateId,
#    LPCWSTR pszText,
#    int iCharCount,
#    DWORD dwFlags,
#    LPRECT pRect,
#    const DTTOPTS *pOptions
#);

    ux.DrawThemeTextEx ( win._hTheme, handle,
                         0, 0, unicode(text), -1,
                         uFormat, byref(rcText2), byref(dto) );

class ThemedFrame(wx.Frame, ThemeMixin):
    def __init__(self, *a, **k):
        wx.Frame.__init__(self, *a, **k)
        ThemeMixin.__init__(self, self)

# when the system changes
#case WM_THEMECHANGED:
#   CloseThemeData (hTheme);
#   hTheme = OpenThemeData (hwnd, L"MyClassName");

if __name__ == '__main__':
    app = wx.PySimpleApp()
    f = ThemedFrame(None)

    #f.Bind(wx.EVT_ERASE_BACKGROUND, lambda e: None)

    f.Sizer = sz = wx.BoxSizer(wx.VERTICAL)


    def paint(e):
        dc = wx.PaintDC(f)
        dc.Brush, dc.Pen = wx.BLACK_BRUSH, wx.TRANSPARENT_PEN
        #dc.DrawRectangle(0,0,*f.Size)

        bmap = TransparentBitmap(f.Size)
        dc2  = wx.MemoryDC()
        dc2.SelectObject(bmap)
        dc2.Font = default_font()
        dc2.TextForeground = wx.RED
        dc2.DrawText('hello', 0, 0)

        #DrawThemeTextEx(f, dc2.GetHDC(), u'Hello World')
        dc.DrawBitmap(bmap, 0, 0)
        e.Skip(True)









    f.Bind(wx.EVT_PAINT, paint)
    #glassBlurRegion(f)



    f.Show(True)
    app.MainLoop()
