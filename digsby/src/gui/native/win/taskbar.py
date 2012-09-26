'''
simple interface to windows 7 taskbar apis
'''

import wx
import cgui

tab_notebook_attr = '_tab_notebook'

def get_tab_notebook(tlw):
    try:
        return getattr(tlw, tab_notebook_attr)
    except AttributeError:
        nb = cgui.TabNotebook(tlw)
        setattr(tlw, tab_notebook_attr, nb)
        return nb

def app_taskbar_notebook():
    nb = None
    others = []
    for win in wx.GetTopLevelWindows():
        if win.IsShown() and win.OnTaskbar:
            nb = get_tab_notebook(win)
            break

    return nb

def set_overlay_icon(icon, tlw=None):
    if icon is None:
        icon = wx.NullBitmap

    if tlw is None:
        nb = app_taskbar_notebook()
    else:
        nb = get_tab_notebook(tlw)
        
    if nb is not None:
        return nb.SetOverlayIcon(icon)
    else:
        return False

