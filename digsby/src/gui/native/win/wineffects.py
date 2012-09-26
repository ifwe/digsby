'''
Windows platform specific effects.
'''

import sys
import wx
import ctypes
from ctypes.wintypes import RECT, byref
from wx import Rect
from platform import platform
from util import Storage

user32 = ctypes.windll.user32
gdi32  = ctypes.windll.gdi32
controls = Storage(
    captionclose        = (1, 0x0000),
    captionmin          = (1, 0x0001),
    captionmax          = (1, 0x0002),
    captionrestore      = (1, 0x0003),
    captionhelp         = (1, 0x0004),

    menuarrow           = (2, 0x0000),
    menucheck           = (2, 0x0001),
    menubullet          = (2, 0x0002),
    menuarrowright      = (2, 0x0004),
    scrollup            = (3, 0x0000),
    scrolldown          = (3, 0x0001),
    scrollleft          = (3, 0x0002),
    scrollright         = (3, 0x0003),
    scrollcombobox      = (3, 0x0005),
    scrollsizegrip      = (3, 0x0008),
    scrollsizegripright = (3, 0x0010),

    buttoncheck        = (1, 0x0000),
    buttonradioimage   = (4, 0x0001),
    buttonradiomask    = (4, 0x0002),
    buttonradio        = (4, 0x0004),
    button3state       = (4, 0x0008),
    buttonpush         = (4, 0x0010),
)

states = Storage(
    inactive           =0x0100,
    pushed             =0x0200,
    checked            =0x0400,

    transparent        =0x0800,
    hot                =0x1000,

    adjustrect         =0x2000,
    flat               =0x4000,
    mono               =0x8000,
)

def rect2wx(winRECT):
    'Converts a winapi RECT to a wxRect.'

    return Rect(winRECT.left,
                winRECT.top,
                winRECT.right - winRECT.left,
                winRECT.bottom - winRECT.top)


_smokeFrame=None

try:
    from cgui import ApplySmokeAndMirrors
except ImportError:
    print >> sys.stderr, 'WARNING: using slow ApplySmokeAndMirrors'
    def ApplySmokeAndMirrors(win, shape = None, ox = 0, oy = 0):
        '''
        Sets the shape of a window.

        shape (integer) a windows handle to a Windows Region
              (wx.Region) a wx.Region specifying the shape
              (wx.Bitmap or wx.Image) an image to use alpha or mask information for a shape
        '''
        global _smokeFrame
        if _smokeFrame is None:
            _smokeFrame = wx.Frame(wx.FindWindowByName('Buddy List'), -1, '', style = wx.FRAME_SHAPED)

            def on_destroy(e):
                # On shutdown, the smoke frame might be destroyed--make sure that ApplySmokeAndMirros
                # is replaced with a stub.
                e.Skip()
                if e.EventObject is _smokeFrame:
                    globals()['ApplySmokeAndMirrors'] = lambda win, shape = None, ox = 0, oy = 0: None

            _smokeFrame.Bind(wx.EVT_WINDOW_DESTROY, on_destroy)

        if isinstance(shape, (int, type(None))):
            return user32.SetWindowRgn(win.Handle, shape, True)

        rgn = gdi32.CreateRectRgn(0, 0, *win.Size)

        if shape:
            if isinstance(shape, wx.Region):
                region = shape
            else:
                if not shape.GetMask():
                    image = wx.ImageFromBitmap(shape)
                    image.ConvertAlphaToMask(200)
                    bitmap = wx.BitmapFromImage(image)
                else:
                    bitmap = shape

                region = wx.RegionFromBitmap(bitmap)

            _smokeFrame.SetShape(region)
            user32.GetWindowRgn(_smokeFrame.Handle, rgn)
            gdi32.OffsetRgn(rgn, -1 + ox, -1 + oy)
        user32.SetWindowRgn(win.Handle, rgn, True)
        gdi32.DeleteObject(rgn)

def GetRgn(win):
    rgn = gdi32.CreateRectRgn(0, 0, *win.Size)
    type = user32.GetWindowRgn(win.Handle, rgn)

    if not type:
        rgn = gdi32.CreateRectRgn(0, 0, win.Rect.Right,win.Rect.Bottom)

    return rgn

def SmokeAndMirrorsBomb(win,windows):
    rgn = gdi32.CreateRectRgn(0,0,0,0)

    shown = [window for window in windows if window.Shown]
    rgns  = [GetRgn(window) for window in shown]

    for i in xrange(len(shown)):
        gdi32.OffsetRgn(rgns[i],*shown[i].Position)
        gdi32.CombineRgn(rgn,rgn,rgns[i],2)# 2 is C constaing RGN_OR
        gdi32.DeleteObject(rgns [i])

#        gdi32.OffsetRgn(rgn,-1,-1)
    user32.SetWindowRgn(win.Handle, rgn, True)
    gdi32.DeleteObject(rgn)

SB_HORZ = 0
SB_VERT = 1
SB_BOTH = 3
WS_EX_LAYERED = 0x00080000

_user32 = ctypes.windll.user32

GetWindowLongA = _user32.GetWindowLongA
SetWindowLongA = _user32.SetWindowLongA
try:
    GetLayeredWindowAttributes = _user32.GetLayeredWindowAttributes
    SetLayeredWindowAttributes = _user32.SetLayeredWindowAttributes
except AttributeError:
    # Windows 2000 is teh suck
    pass
from ctypes import c_byte

LWA_COLORKEY = 1

def SetColorKey(window, rgb_color_tuple):
    assert len(rgb_color_tuple) == 3
    color = ctypes.c_uint((0xff000000 & 0) |
                          (0x00ff0000 & rgb_color_tuple[0]) |
                          (0x0000ff00 & rgb_color_tuple[1]) |
                          (0x000000ff & rgb_color_tuple[2]))

    hwnd = window.Handle

    # make WS_EX_LAYERED if necessary.
    style = GetWindowLongA(hwnd, 0xffffffecL)
    layered_style = style | WS_EX_LAYERED
    if layered_style != style:
        SetWindowLongA(hwnd, 0xffffffecL, layered_style)

    SetLayeredWindowAttributes(hwnd, byref(color), 0, LWA_COLORKEY)

def ShowScrollbar(window, show):
    hwnd = window.GetHandle()
    scrollbar = SB_VERT
    _user32.ShowScrollBar(hwnd, scrollbar, show)

def _setalpha_wxMSW_ctypes(window, alpha):
    '''Use SetLayeredWindowAttributes in user32.dll to adjust a
    window's transparency.'''

    hwnd    = window.GetHandle()
    oldStyle = style = GetWindowLongA(hwnd, 0xffffffecL)

    if alpha == 255:
        style &= ~WS_EX_LAYERED
    else:
        style |= WS_EX_LAYERED

    if oldStyle != style:
        SetWindowLongA(hwnd, 0xffffffecL, style)

    SetLayeredWindowAttributes(hwnd, 0, alpha, 2)
    window._alpha = alpha

def _donealpha_wxMSW_ctypes(window):
    if not window: return
    hwnd = window.GetHandle()
    oldStyle = style = GetWindowLongA(hwnd, 0xffffffecL)
    style &= ~WS_EX_LAYERED
    if getattr(window, '_alpha', 255) == 0:
        window.Hide()
    if oldStyle != style:
        SetWindowLongA(hwnd, 0xffffffecL, style)
    window._alpha = 255

def _getalpha_wxMSW_ctypes(window):
    "Returns a window's transparency."

    return getattr(window, '_alpha', 255)
    hwnd = window.GetHandle()
    alpha = c_byte()
    try:
        GetLayeredWindowAttributes(hwnd, 0, alpha, 2)
        return alpha.value
    except AttributeError:
        return getattr(window, '_alpha', 255)

def _drawnativecontrol_wxMSW(handle, rect, control, state=0):
    'Use DrawFrameControl in user32.dll to draw a native control.'

    _user32.DrawFrameControl(handle, rect, control[0], control[1] | state)

setalpha = _setalpha_wxMSW_ctypes
getalpha = _getalpha_wxMSW_ctypes
donealpha = _donealpha_wxMSW_ctypes

def DrawSubMenuArrow(dc, rect):
    from gui.native.win.winextensions import wxRectToRECT
    rect = wxRectToRECT(rect)

    _drawnativecontrol_wxMSW(dc.GetHDC(), byref(rect), controls.menuarrow, 0)

if platform().startswith('Windows-2000'):
    setalpha = lambda *a: None
    getalpha = lambda *a: 255

    fadein  = lambda win, *a, **k: win.Show(True)
    def fadeout(win, speed = 'normal', on_done = None, from_ = None):
        win.Show(False)
        if on_done is not None:
            on_done()
