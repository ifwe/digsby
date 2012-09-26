from gui.prototypes.newskinmodule import NewSkinModule, SkinProxy
from gui.uberwidgets.UberButton import UberButton

from gui.skin.skinobjects import Margins, SkinColor
from gui.prototypes.fontdropdown import FontDropDown

import wx
from cgui import SimplePanel
from util.primitives.funcs import do

ToolBarSkinDefaults = {
    'padding'               : lambda: wx.Point(2,2),
    'margins'               : lambda: Margins([2,2,2,2]),
    'background'            : lambda: SkinColor(wx.SystemSettings_GetColour(wx.SYS_COLOUR_3DFACE)),
    'buttonskin'            : lambda: None,
    'menuskin'              : lambda: None,
}

class ToolBar(SimplePanel, NewSkinModule):

    def __init__(self, parent, id = wx.ID_ANY, skinkey = None, name = 'ToolBar', alignment = None):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)
        self.children = []

        self.content = wx.BoxSizer(wx.HORIZONTAL)
        self.Sizer = Margins().Sizer(self.content)

        self.SetSkinKey(skinkey, ToolBarSkinDefaults)

        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def Insert(self, pos, object, expand = False):

        skin = self.skinTB

        #TODO: This is stupid, should be done some other way
        if isinstance(object, UberButton):
            object.SetSkinKey(skin['buttonskin'], True)
            if object.menu is not None:
                object.menu.SetSkinKey(skin["menuskin"])
        elif isinstance(object, FontDropDown):
            object.SetSkinKey(skin['buttonskin'])
            object.SetMenuSkinKey(skin["menuskin"])

        self.content.Insert(pos, object, expand, wx.RIGHT | wx.EXPAND, self.skinTB['padding'].x)
        self.children.insert(pos, object)

    def Add(self, object, expand = False):

        skin = self.skinTB

        #TODO: Still stupid, see Insert
        if isinstance(object, UberButton):
            object.SetSkinKey(skin['buttonskin'], True)
            if object.menu is not None:
                object.menu.SetSkinKey(skin["menuskin"])
        elif isinstance(object, FontDropDown):
            object.SetSkinKey(skin['buttonskin'])
            object.SetMenuSkinKey(skin["menuskin"])

        self.content.Add(object, expand, wx.RIGHT | wx.EXPAND, self.skinTB['padding'].x)
        self.children.append(object)

    def Detach(self, object):
        return self.content.Detach(object)

    def AddMany(self, objects, expand = False):
        for object in objects:
            self.Add(object, expand)

    def DoUpdateSkin(self, skin):
        self.skinTB = skin

        self.Sizer.SetMargins(skin['margins'])

        #Even stupider; see Add and Insert
        do(item.SetSkinKey(skin["buttonskin"]) for item in self.children if isinstance(item, (UberButton, FontDropDown)))
        for item in self.children:
            if isinstance(item, UberButton) and item.menu is not None:
                item.menu.SetSkinKey(skin["menuskin"])
            elif isinstance(item, FontDropDown):
                item.SetMenuSkinKey(skin["menuskin"])

        for child in self.content.Children:
            child.SetBorder(skin["padding"].x)

    def GetSkinProxy(self):
        return self.skinTB if hasattr(self, 'skinTB') else None

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)

        self.skinTB['background'].Draw(dc, rect)
        self.OnPaintMore(dc)

    def OnPaintMore(self, dc):
        pass

class SkinnedToolBar(ToolBar):
    '''
    given an indirect_skinkey, looksup the correct toolbar skin on creation and
    on UpdateSkin.
    '''

    def __init__(self, *a, **k):
        from gui.uberwidgets.formattedinput2.formattingbar import FormattingBarSkinDefaults
        skinkey = k.pop('indirect_skinkey')
        k['skinkey'] = None

        ToolBar.__init__(self, *a, **k)
        self.SetSkinKey(skinkey, FormattingBarSkinDefaults)

    def DoUpdateSkin(self, skin):
        self.skinTTB = skin
        ToolBar.DoUpdateSkin(self, SkinProxy(skin['toolbarskin'], ToolBarSkinDefaults))

    def GetSkinProxy(self):
        return self.skinTTB if hasattr(self, 'skinTTB') else None

