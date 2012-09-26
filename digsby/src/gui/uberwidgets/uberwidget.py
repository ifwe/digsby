import sys
import wx
from types import NoneType
from gui import skin
import gui.native.extensions

import ctypes
from ctypes import byref
from ctypes import create_unicode_buffer

try:
    uxtheme     = ctypes.windll.uxtheme
    OpenTheme   = uxtheme.OpenThemeData
    CloseTheme  = uxtheme.CloseThemeData
    DrawThemeBG = uxtheme.DrawThemeBackground
    IsAppThemed = uxtheme.IsAppThemed
    uxthemeable = True
except:
    uxthemeable = False


class UberWidget(object):
    def __init__(self,nativekey):
        global uxthemeable
        self.uxthemeable = uxthemeable
        self.nativekey=nativekey
        self.nativetheme = None
        self.Bind(wx.EVT_CLOSE,self.OnThisWidgetClose)

    def SetSkinKey(self, key, update = False):
        if not isinstance(key, (basestring,NoneType)):
            raise TypeError('skin keys must be strings or NoneType; is %s'%type(key))

        if not key or ((skin.get('%s.mode'%key,'') or '').lower()=='native' or key.lower()=='native'):
            key=None

        self.skinkey = key
        if update: self.UpdateSkin()

    def OpenNativeTheme(self):
        if hasattr(self,'nativetheme') and self.nativetheme:
            CloseTheme(self.nativetheme)
        try:
            self.nativetheme = OpenTheme(self.Handle,byref(create_unicode_buffer(self.nativekey))) if OpenTheme else None
            return bool(self.nativetheme)
        except:
            return False

    def CloseNativeTheme(self):
        if self.nativetheme:
            CloseTheme(self.nativetheme)
            self.nativetheme = None

    def OnThisWidgetClose(self,event):
        self.CloseNativeTheme()
        event.Skip()

    def DrawNativeLike(self,dc,part,state,rect,DrawNativeFallback=None):
        if "wxMSW" in wx.PlatformInfo and hasattr(self, 'nativetheme') and self.nativetheme:
            DrawThemeBG(self.nativetheme, dc.GetHDC(), part, state, byref(rect.RECT), None)
        elif DrawNativeFallback:
            DrawNativeFallback(dc,part,state,rect)
