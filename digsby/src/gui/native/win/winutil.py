import wx
import ctypes.wintypes
from gui.native.win.winconstants import WM_USER
from ctypes.wintypes import UINT, HWND, DWORD
from util.ffi import Struct
from util import memoize

def _win_id_gen():
    i = 100
    while True:
        i += 1
        yield WM_USER + i

_win_id_gen = _win_id_gen()

def win_id():
    return _win_id_gen.next()


class WinStruct(Struct):
    'A struct that calculates its own cbSize for you.'

    cbSize = property(lambda self: len(self), lambda self, val: None)

class FLASHWINFO(WinStruct):
    _fields_ = [('cbSize',    UINT),
                ('hwnd',      HWND),
                ('dwFlags',   DWORD),
                ('uCount',    UINT),
                ('dwTimeout', DWORD)]

@memoize
def is_vista():
    'Returns True if the system is running Windows Vista or higher.'

    import wx
    return 'wxMSW' in wx.PlatformInfo and hasattr(ctypes.windll, 'dwmapi')

def disable_callback_filter():
    '''
    Exceptions in WM_PAINT (and other messages...?) on 64-bit versions of Windows
    are silently ignored.  It's a known issues and there's a hotfix here:
    
    http://support.microsoft.com/kb/976038

    If that hotfix is installed, kernel32.dll exports two extra functions that
    fix the behavior at runtime. This function will use those functions to make
    exceptions go to the debugger and return True.
    
    If the hotfix isn't installed, this function does nothing and returns
    False.
    '''

    from ctypes import byref
    k = ctypes.windll.kernel32

    PROCESS_CALLBACK_FILTER_ENABLED = 0x1

    dwflags = DWORD()

    try:
        GetProcessUserModeExceptionPolicy = k.GetProcessUserModeExceptionPolicy
        SetProcessUserModeExceptionPolicy = k.SetProcessUserModeExceptionPolicy
    except AttributeError:
        pass # hotfix not installed
    else:
        if GetProcessUserModeExceptionPolicy(byref(dwflags)):
            return SetProcessUserModeExceptionPolicy(dwflags.value & ~PROCESS_CALLBACK_FILTER_ENABLED)

    return False


get_glass_color = None

if 'wxMSW' in wx.PlatformInfo:
    from ctypes import c_uint32

    class DWMCOLORIZATIONPARAMS(ctypes.Structure):
        _fields_ = [
            ('ColorizationColor', c_uint32),
            ('ColorizationAfterglow', c_uint32),
            ('ColorizationColorBalance', c_uint32),
            ('ColorizationAfterglowBalance', c_uint32),
            ('ColorizationBlurBalance', c_uint32),
            ('ColorizationGlassReflectionIntensity', c_uint32),
            ('ColorizationOpaqueBlend', c_uint32),
        ]

    p = DWMCOLORIZATIONPARAMS()

    try:
        DwmGetColorizationParameters = ctypes.windll.dwmapi[127] # ordinal 127 is the unexported function
    except Exception:
        pass
    else:
        disable_gcp = False
        def _get_glass_color(active=False):
            global disable_gcp

            VISTA_GLASS_COLOR = wx.Color(189, 211, 239)

            if disable_gcp:
                return VISTA_GLASS_COLOR

            try:
                DwmGetColorizationParameters(ctypes.byref(p))
            except ValueError:
                # function is undocumented and has a different signature on Vista...just return bluish
                # if so
                # TODO: this value is also accessible in the registry--maybe that's a safer way to do this?
                disable_gcp = True
                return VISTA_GLASS_COLOR
            else:
                extra_alpha_percent = p.ColorizationColorBalance/64.0 if active else 0
                return alpha_blend_on_white(p.ColorizationColor, extra_alpha_percent)

        get_glass_color = _get_glass_color

    def alpha_blend_on_white(c, extra_alpha_percent=0):
        '''where c is a ARGB packed int, returns a wxColor with 255 alpha of the
        resulting color if you had blitted c onto pure white.'''

        r, g, b = (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF
        a = ((c >> 24) & 0xff)/255.0 + extra_alpha_percent
        white = (1-a)*255

        return wx.Color(white + a*r, white + a*g, white + a*b)

try:
    IsThemeActive = ctypes.windll.uxtheme.IsThemeActive
except Exception:
    IsThemeActive = lambda: False

def rgbdword_to_color(c):
    return wx.Color((c & 0xFF),
                     (c & 0xFF00) >> 8,
                     (c & 0xFF0000) >> 16)

def _get_active_caption_color(active):
    COLOR_ACTIVECAPTION = 2
    return rgbdword_to_color(ctypes.windll.user32.GetSysColor(COLOR_ACTIVECAPTION))

def get_frame_color(active):
    if IsThemeActive() and get_glass_color is not None:
        return get_glass_color(active)
    else:
        if IsThemeActive():
            return _get_active_caption_color(active)
        else:
            return wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE)

