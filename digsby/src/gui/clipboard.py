'''
clipboard utilities
'''

import wx
import path

def CopyToClipboard(s):
    '''
    Copies string s to the clipboard.
    '''
    if not s:
        return
    if not isinstance(s, basestring):
        raise TypeError

    clip = wx.TheClipboard

    if clip.Open():
        try:
            clip.SetData(wx.TextDataObject(s))
            return True
        finally:
            clip.Close()

    return False

copy = CopyToClipboard

_clipboard_types = {wx.DF_BITMAP: (wx.BitmapDataObject, 'Bitmap'),
                    wx.DF_TEXT:   (wx.TextDataObject,   'Text'),
                    wx.DF_FILENAME: (wx.FileDataObject, 'Filenames'),
                    }

def clipboard_get(df_type):
    '''
    Get contents of clipboard. df_type must be one of:

    wx.DF_TEXT
    wx.DF_BITMAP

    Returns None if the format was not in the clipboard.
    '''
    df = wx.DataFormat(df_type)

    clip = wx.TheClipboard
    if clip.Open():
        try:
            if clip.IsSupported(df):
                obj_type, obj_attr = _clipboard_types[df_type]
                obj = obj_type()
                clip.GetData(obj)
                return getattr(obj, obj_attr)
        finally:
            clip.Close()

def get_bitmap():
    return clipboard_get(wx.DF_BITMAP)

def get_text():
    return clipboard_get(wx.DF_TEXT)

def get_files():
    res = clipboard_get(wx.DF_FILENAME)
    if res is None:
        return res
    
    else:
        return map(path.path, res)
        
