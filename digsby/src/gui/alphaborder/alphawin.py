import wx

from ctypes import windll, Structure, c_byte, c_long, c_int, byref, WinError, GetLastError

user32, kernel32 = windll.user32, windll.kernel32

GetDC = user32.GetDC
UpdateLayeredWindow = user32.UpdateLayeredWindow

AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
ULW_ALPHA = 2
WS_EX_LAYERED = 0x00080000


class CPoint(Structure):
    _fields_ = (('x', c_long),
                ('y', c_long))
class BLENDFUNCTION(Structure):
    '''
    The BLENDFUNCTION structure controls blending by specifying the blending
    functions for source and destination bitmaps.
    '''

    # see http://msdn2.microsoft.com/en-us/library/ms532306.aspx

    _fields_ = (('BlendOp',     c_byte),
                ('BlendFlags',  c_byte),
                ('SourceConstantAlpha', c_byte),
                ('AlphaFormat', c_byte))

def setLayered(win, layered):
    hwnd = win.Handle
    style = user32.GetWindowLongA(hwnd, 0xffffffecL)
    oldlayered = bool(WS_EX_LAYERED & style)

    if layered == oldlayered: return

    if layered: style |= WS_EX_LAYERED
    else:       style &= ~WS_EX_LAYERED

    user32.SetWindowLongA(hwnd, 0xffffffecL, style)

def makeBlendFunction(alpha):
    if not isinstance(alpha, int) or alpha < 0 or alpha > 255:
        raise TypeError('alpha must be an integer from 0 to 255')

    f = BLENDFUNCTION()
    f.BlendOp     = AC_SRC_OVER
    f.BlendFlags  = 0
    f.SourceConstantAlpha = alpha
    f.AlphaFormat = AC_SRC_ALPHA

    return f

def ApplyAlpha(win, bitmap, sourceAlpha = 255):
    setLayered(win, True)

    r = win.Rect
    pos  = CPoint(); pos.x,  pos.y  = r[:2]
    size = CPoint(); size.x, size.y = r[2:]

    memdc = wx.MemoryDC(bitmap)

    imgpos = CPoint(); imgpos.x = imgpos.y = 0

    colorkey = c_int(0)
    blendPixelFunction = makeBlendFunction(sourceAlpha)

    res = UpdateLayeredWindow(win.Handle,
                              GetDC(None),
                              byref(pos),
                              byref(size),
                              memdc.GetHDC(),
                              byref(imgpos),
                              colorkey,
                              byref(blendPixelFunction),
                              ULW_ALPHA)

    if not res:
        raise WinError(GetLastError())


    memdc.SelectObject(wx.NullBitmap)