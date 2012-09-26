import wx

if 'wxMSW' in wx.PlatformInfo:
    from .bugreporterguiold import show_dialog
else:
    from .bugreportergui import show_dialog

from .crashgui import CrashDialog
