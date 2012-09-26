import cgui
from gui.skin import get as skinget
from wx import Colour, SYS_COLOUR_WINDOW
import wx
GetColour = wx.SystemSettings.GetColour

class SkinSplitter(cgui.SkinSplitter):
    '''
    UI for two panels that share the same space alowing the user to adjust how much of the space is alotted to each
    '''
    def __init__(self, parent, style):
        cgui.SkinSplitter.__init__(self, parent, style)
        self.UpdateSkin()

    def SplitHorizontally(self, *a, **k):
        cgui.SkinSplitter.SplitHorizontally(self, *a, **k)
        self.UpdateSkin()

    def SplitVertically(self, *a, **k):
        cgui.SkinSplitter.SplitVertically(self, *a, **k)
        self.UpdateSkin()

    def UpdateSkin(self):
        mode = self.SplitMode

        if mode == wx.SPLIT_HORIZONTAL:
            splitskin = skinget('HorizontalSizerBar', None)
        else:
            splitskin = skinget('VerticalSizerBar', None)
            if splitskin is None:
                splitskin = skinget('HorizontalSizerBar', None)

        if splitskin is None or (isinstance(splitskin, basestring) and splitskin.lower().strip() == 'native') or not hasattr(splitskin, 'get'):
            self.SetSashSize(-1)
            self.SetNative(True)
            return

        try:    sash_size = int(splitskin.thickness)
        except: sash_size = -1

        syscol = GetColour(SYS_COLOUR_WINDOW)

        bgs = splitskin.get('backgrounds', {})

        normal = bgs.get('normal', syscol)
        active = bgs.get('active', syscol)
        hover  = bgs.get('hover',  syscol)

        if not isinstance(normal, Colour): normal = syscol
        if not isinstance(active, Colour): active = syscol
        if not isinstance(hover,  Colour): hover  = syscol

        self.SetSashSize(sash_size)
        self.SetSplitterColors(normal, active, hover)
        self.SetNative(False)