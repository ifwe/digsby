from gui.toolbox.monitor import Monitor
import wx
from gui.skin.skinobjects import SkinColor, Margins
from gui.textutil import default_font, GetFonts, GetTextExtent
from gui.prototypes.menus.simplemenu import SimpleMenuedControl, BasicMenuData, EVT_SMI_CLICKED, EVT_SM_CLOSED
from gui.prototypes.newskinmodule import NewSkinModule

import config

if config.platformName == "win":
    from cgui import FitFontToRect

from gui import skin

from util import default_timer



def MakeDropIcon(color = None):

    if color == None:
        color = wx.BLACK #@UndefinedVariable
    fillcolor =  wx.WHITE if not color.IsSameAs(wx.WHITE) else wx.BLACK #@UndefinedVariable

    ico = wx.EmptyBitmap(7, 4, -1)

    mdc = wx.MemoryDC()
    mdc.SelectObject(ico)


    mdc.Pen = wx.TRANSPARENT_PEN #@UndefinedVariable
    mdc.Brush = wx.Brush(fillcolor)
    mdc.DrawRectangle(0, 0, 7, 4)

    mdc.Pen = wx.Pen(color, 1, wx.SOLID)
    mdc.Brush = wx.TRANSPARENT_BRUSH #@UndefinedVariable


    s = 0
    e = 0
    for x in xrange(7):
        mdc.DrawLine(x,s,x,e)
        e += (1 if x<3 else -1)

    mdc.SelectObject(wx.NullBitmap) #@UndefinedVariable

    #ico.SetMaskColour(fillcolor)

    return ico

fontnames = []

def FontFromFacename(facename):
    return wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, facename)

FontDropDownSkinDefaults = {
    'padding'           : lambda: wx.Point(2,2),
    'margins'           : lambda: Margins([0,0,0,0]),
    'framesize'         : lambda: Margins([0,0,0,0]),
    'frame'             : lambda: SkinColor(wx.BLACK), #@UndefinedVariable
    'backgrounds.normal': lambda: SkinColor(wx.WHITE), #@UndefinedVariable
    'backgrounds.hover' : lambda: SkinColor(wx.BLACK), #@UndefinedVariable
    'backgrounds.down'  : lambda: SkinColor(wx.BLACK), #@UndefinedVariable
    'backgrounds.active': lambda: SkinColor(wx.BLACK), #@UndefinedVariable
    'fontcolors.normal' : lambda: wx.BLACK, #@UndefinedVariable
    'fontcolors.hover'  : lambda: wx.WHITE, #@UndefinedVariable
    'fontcolors.down'   : lambda: wx.WHITE, #@UndefinedVariable
    'fontcolors.active' : lambda: wx.WHITE, #@UndefinedVariable
#    'fontcolors.hint'   : lambda: wx.Color(128,128,128),
    'font'              : lambda: default_font(),
    'menuskin'          : lambda: None,
    'menuicon'          : lambda: skin.get('appdefaults.dropdownicon')
}

menuobjects = {}


class SharedFontDropDownData(BasicMenuData):
    '''
    Extension on the BasicMenuData provider to be shared among all font menus saving memory
    '''
    def __init__(self):
        BasicMenuData.__init__(self)

        global fontnames
        global menuobjects


        if not fontnames:
            fontnames = GetFonts()

        self._items = fontnames
        self._clientData = menuobjects

        self._lastItemChange = default_timer()
        self._lastSelChange = default_timer()

class FontDropDown(SharedFontDropDownData, SimpleMenuedControl, NewSkinModule):
    '''
    Custom drop down selector that shows all font names in that font
    '''
    #wxChoice(parent, id,pos, size,  name = "choice")
    def __init__(self, parent, id = -1, pos = wx.DefaultPosition, size = wx.DefaultSize, skinkey = None):


#        s = default_timer()
        #self.itemSize = 22
        self.isDown = False
        self.isActive = False

        self.SetSkinKey(skinkey, FontDropDownSkinDefaults)


        SharedFontDropDownData.__init__(self)

        SimpleMenuedControl.__init__(self, parent, id, pos, size, 10, 212, 212, skinkey = "simplemenu")

        self.SetMinSize(wx.Size(-1, 12 + 2*self.skinFDD['padding'].y))
        self.itemSize = 12 + 2*self._customMenu.skinCML['padding'].y

        self.MakeFont(0)
        self.SetSelection(0)


        Bind = self.Bind

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        Bind(wx.EVT_PAINT, self.OnPaint)
        Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        Bind(   EVT_SMI_CLICKED, self.OnItemClicked)
        Bind(   EVT_SM_CLOSED, self.OnMenuClose)
        Bind(wx.EVT_MOTION, self.OnMouseMotion)
        Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
        Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)

#        e = default_timer()
#        print "FontDD created: ", e - s


    def MakeFont(self, n):

        fontname = self.GetString(n)
        font = FontFromFacename(fontname) #FitFontToRect(FontFromFacename(fontname), wx.RectS(wx.Size(212, self.itemSize - 2*self._customMenu.skinCML['padding'].y)), fontname, False)
        self.SetClientData(n, font)

    def OnMouseCaptureLost(self, event):
        pass

    def SetSelection(self, n):

        if not isinstance(self.GetClientData(n), wx.Font):
            self.MakeFont(n)

        BasicMenuData.SetSelection(self, n)

        self.Refresh()

    def GetSkinProxy(self):
        return self.skinFDD if hasattr(self, 'skinFDD') else None

    def DoUpdateSkin(self, skin):
        self.skinFDD = skin

    def OnItemClicked(self, event):
        self._customMenu.Dismiss()

        sel = event.GetInt()
        self.SetSelection(sel)
        cEvent = wx.CommandEvent(wx.EVT_COMMAND_CHOICE_SELECTED, self.GetId())
        cEvent.SetInt(sel)
        cEvent.SetClientData(self.GetClientData(sel))
        cEvent.SetString(self.GetString(sel))
        self.AddPendingEvent(cEvent)

    def OnMenuClose(self, event):
        self.isActive = False
        self.Refresh()

    def OnMouseMotion(self, event):
        self.Refresh()

    def CMLMeasureItem(self, n, skin):
        return self.itemSize

    def CMLCalcSize(self, skin):
        width = self.maxWidth
        height = (self.maxHeight * self.itemSize) + skin['framesize'].x

        return wx.Size(width, height)

    def OnLeftDown(self, event):
        self.OpenMenu()


    def OpenMenu(self):
        rect = self.GetScreenRect()

        self._customMenu.CalcSize()
        menuSize = self._customMenu.GetMinSize()

        pos = wx.Point(rect.GetLeft(), rect.GetBottom() + 1)

        monRect = Monitor.GetFromPoint(pos, True).Geometry
        if pos.y + menuSize.height > monRect.bottom:
            pos = wx.Point(rect.GetLeft(), rect.GetTop() - menuSize.height - 1)

        self.PopUp(pos)

        self.isActive = True
        self.Refresh()


    def OnMouseEnter(self, event):
        self.Refresh()
        if not self.HasCapture():
            self.CaptureMouse()
        event.Skip()

    def OnMouseLeave(self, event):
        self.Refresh()
        while self.HasCapture():
            self.ReleaseMouse()
        event.Skip()

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectS(self.Size)

        skin = self.skinFDD
        icon = skin['menuicon']

        isActive = self.isActive
        hasHover = self.ScreenRect.Contains(wx.GetMousePosition())

        skin['backgrounds.active' if isActive else 'backgrounds.hover' if hasHover else 'backgrounds.normal'].Draw(dc, rect)

        iw = icon.GetWidth()
        ih = icon.GetHeight()

        ix = rect.right - skin['padding'].x - skin['margins'].right - iw
        iy = rect.top + (rect.height/2 - ih/2)

        dc.DrawBitmap(icon, ix, iy, True)
        text = self.GetStringSelection()

        if text is None:
            return

        dc.Font = self.GetClientData(self.GetSelection())
        dc.TextForeground = skin['fontcolors.active' if isActive else 'fontcolors.hover' if hasHover else 'fontcolors.normal']



        tx = skin['margins'].left + skin['padding'].x
        ty = skin['margins'].top  + skin['padding'].y
        tw = ix - skin['padding'].x*2
        th = rect.height - (skin['margins'].y + skin['padding'].y*2)

        trect = wx.Rect(tx, ty, tw, th)

        dc.DrawTruncatedText(text, trect, alignment = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)


    def CMLDrawItem(self, dc, rect, n, skin):


        item = self.GetString(n)

        if not isinstance(self.GetClientData(n), wx.Font):
            self.MakeFont(n)

        dc.Font = self.GetClientData(n)
        dc.TextForeground = skin["fontcolors.selection"] if self.GetHover() == n else skin["fontcolors.normal"]

        drawrect = wx.Rect(rect.x + skin["padding"].x, rect.y, rect.width - skin["padding"].x*3, rect.height)

        dc.DrawTruncatedText(item, drawrect, alignment = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
#        dc.SetBrush(wx.TRANSPARENT_BRUSH)
#        dc.SetPen(wx.RED_PEN)
#        dc.DrawRectangleRect(drawrect)
