'''
This is the basic shared logic for the UI of any custom skinned menus

Note: This was written to be easily ported down to C++ code, doing so should offer speed improvements
'''

from util import default_timer
from gui.skin.skinobjects import Margins, SkinColor
from gui.textutil import default_font
import wx

from gui.prototypes.newskinmodule import NewSkinModule

from gui.vlist.skinvlist import SkinVListBox

#from traceback import print_exc
#===============================================================================
#TODO: platform specific code, check for other platforms as well

wxMSW = 'wxMSW' in wx.PlatformInfo

if wxMSW:
    from ctypes import windll
    ReleaseCapture_win32 = windll.user32.ReleaseCapture

def ClearMouseCapture():

    if wxMSW:
        ReleaseCapture_win32()


#===============================================================================
wxEVT_ENTER_WINDOW = 10032
wxEVT_LEAVE_WINDOW = 10033

MenuSkinDefaults = {
    'framesize': lambda: Margins([0,0,0,0]),
    'frame': lambda: SkinColor(wx.BLACK), #@UndefinedVariable

    'padding': lambda: wx.Point(2,2),
    'backgrounds.menu':  lambda: SkinColor(wx.WHITE), #@UndefinedVariable
    'backgrounds.item':  lambda: None,
    'backgrounds.selection': lambda: SkinColor(wx.BLACK), #@UndefinedVariable
    'font': lambda: default_font(),
    'fontcolors.normal':    lambda: wx.BLACK, #@UndefinedVariable
    'fontcolors.selection': lambda: wx.WHITE, #@UndefinedVariable
    'separatorimage': lambda: None
}



class CustomMenuFrame(wx.PopupTransientWindow, NewSkinModule):
    def __init__(self, parent):
        wx.PopupTransientWindow.__init__(self, parent)
        self.SetPosition((-50000,-50000))
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.content = None

    def SetContent(self, content):
        self.content = content

    def OnPaint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        rect = wx.RectPS(wx.Point(0,0), self.GetSize())

        if self.content:
            skin = self.content.skinCML
            skin["frame"].Draw(dc, rect)
        else:
            dc.SetBrush(wx.BLACK_BRUSH) #@UndefinedVariable
            dc.SetPen(wx.TRANSPARENT_PEN) #@UndefinedVariable
            dc.DrawRectangleRect(rect)


def CreateCML(parent, customcalls, data, id = -1, style = 0, skinkey = None):
        frame = CustomMenuFrame(parent)
        cmlb = CustomMenuListBox(frame, customcalls, data, id, style, skinkey)
        frame.SetContent(cmlb)
        return cmlb

class CustomMenuListBox(SkinVListBox, NewSkinModule):
    '''
    This is the base UI for any new menu, expects

    @param frame The frame that will b the menus parent
    @param customcalls An object implementing CustomMenuInterface
    @param data An object expected to follow the same interface as wxControlWithItems
    '''

    def __init__(self, frame, customcalls, data, id = -1, style = 0, skinkey = None):

        SkinVListBox.__init__(self, frame, id, style = style)

        self._frame = frame
        self._customcalls = customcalls
        self._data = data

        self.SetSkinKey(skinkey, MenuSkinDefaults)

        Bind = self.Bind
        Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)
        Bind(wx.EVT_MOUSE_EVENTS, self.OnAllMouseEvents)
        Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        self.mouseEventHandlers = {wx.wxEVT_MOTION    : self._MouseMotion,
                                   wxEVT_ENTER_WINDOW : self._MouseEnter,
                                   wxEVT_LEAVE_WINDOW : self._MouseLeave,
                                   wx.wxEVT_LEFT_DOWN : self._LeftDown,
                                   wx.wxEVT_LEFT_UP   : self._LeftUp,
                                   wx.wxEVT_RIGHT_DOWN: self._RightDown,
                                   wx.wxEVT_RIGHT_UP  : self._RightUp}

        self._lastCalced = 0

    def GetSkinProxy(self):
        return self.skinCML if hasattr(self, 'skinCML') else None

    def DoUpdateSkin(self, skin):

        self.skinCML = skin

        frame = self._frame

        framesizer = frame.GetSizer()

        if framesizer and not wx.IsDestroyed(framesizer):
            frame.Sizer.Clear()

        frame.SetSizer(skin["framesize"].Sizer(self))

        self._lastSkinChange = default_timer()

    def Display(self, pos):

        self.CalcSize()

        self._frame.SetPosition(pos)
        self._customcalls.CMLDisplay(pos, self.GetSize())

        ClearMouseCapture()

        if not self.HasCapture():
            self.CaptureMouse()

        wx.CallAfter(self._frame.Show)

    def Dismiss(self):

        while self.HasCapture():
            self.ReleaseMouse()

        self._customcalls.CMLDismiss()

    def CalcSize(self):

        if self._lastCalced > max(self._data._lastItemChange, self._lastSkinChange):
            return

        self._lastCalced = default_timer()

        self.SetItemCount(self._data.GetCount())

        size = self._customcalls.CMLCalcSize(self.skinCML)

#        if size.height == -1:
#            size.height = 0
#            for n in xrange(self._data.GetCount()):
#                size.height += self.OnMeasureItem(n)
#
#        if size.width == -1:
#            size.width = self.CalcMenuWidth(self.skinCML)

        size.width  -= (self.skinCML["framesize"].left + self.skinCML["framesize"].right)
        size.height -= (self.skinCML["framesize"].top + self.skinCML["framesize"].bottom)

        self.SetMinSize(size)

        self._frame.Fit()
        self._frame.Sizer.Layout()

    def OnMeasureItem(self, n):
        return self._customcalls.CMLMeasureItem(n, self.skinCML)

    def CalcMenuWidth(self):
        return self._customcalls.CMLCalcMenuWidth(self.skinCML)

    def PaintMoreBackground(self, dc, rect):
        self._customcalls.CMLDrawBackground(dc, rect, self.skinCML)

    def OnDrawBackground(self, dc, rect, n):
        self._customcalls.CMLDrawItemBG(dc, rect, n, self.skinCML)

    def OnDrawItem(self, dc, rect, n):
        self._customcalls.CMLDrawItem(dc, rect, n, self.skinCML)

    def OnDrawSeparator(self, dc, rect, n):
        self._customcalls.CMLDrawSeparator(dc, rect, n, self.skinCML)

    def OnMouseCaptureLost(self, event):
        self._customcalls.CMLMouseCaptureLost(event)

    def OnAllMouseEvents(self, event):

        self._customcalls.CMLAllMouseEvents(event)

        try:   eventHandler = self.mouseEventHandlers[event.EventType]
        except KeyError:
            print "Unhandled event type: ", event.EventType

            event.Skip()

        else:  eventHandler(event)


    def _MouseMotion(self, event):
        mp = event.GetPosition()
        i = self.HitTest(mp) if self.ClientRect.Contains(mp) else -1
        s = self.GetSelection()

        if i != s:
            self.SetSelection(i)

        self._customcalls.CMLMouseMotion(i)

    def _MouseEnter(self, event):

        self._MouseMotion(event)

        self._customcalls.CMLMouseEnter(event)

    def _MouseLeave(self, event):

        self._MouseMotion(event)
        self._customcalls.CMLMouseLeave(event)

    def _LeftDown(self, event):

        if not self.Rect.Contains(event.Position):
            self.Dismiss()

        self._customcalls.CMLLeftDown(event)

    def _LeftUp(self, event):
        self._customcalls.CMLLeftUp(event)

    def _RightDown(self, event):

        if not self.Rect.Contains(event.Position):
            self.Dismiss()

        self._customcalls.CMLRightDown(event)

    def _RightUp(self, event):
        self._customcalls.CMLRightUp(event)

    def OnMouseWheel(self, event):
        self._customcalls.CMLMouseWheel(event)

    def OnKeyDown(self, e):
        keycode = e.KeyCode
        i = self.GetSelection()

        if keycode == wx.WXK_DOWN:
            self.SetSelection((i + 1) % self._data.GetCount())
        elif keycode == wx.WXK_UP:
            self.SetSelection((i - 1) % self._data.GetCount())
        elif keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            from gui.prototypes.menus.simplemenu import SimpleMenuItemClickedEvent
            se = SimpleMenuItemClickedEvent(0)
            se.SetInt(self.Selection)
            self._frame.AddPendingEvent(se)
            self.Dismiss()
        else:
            e.Skip()

class CustomMenuInterface(object):
    '''
    Interface expected to be implemented by custom menus
    '''

    def GetHover(self):
        return -1

    def CMLDisplay(self, pos, size):
        pass

    def CMLDismiss(self):
        pass

    def CMLCalcSize(self, skin):
        return wx.Size(-1, -1)

    def CMLCalcMenuWidth(self, skin):
        return -1

    def CMLMeasureItem(self, n, skin):
        return -1

    def CMLDrawBackground(self, dc, rect, skin):
        pass

    def CMLDrawItemBG(self, dc, rect, n, skin):
        pass

    def CMLDrawItem(self, dc, rect, n, skin):
        pass

    def CMLDrawSeparator(self, dc, rect, n, skin):
        pass

    def CMLMouseCaptureLost(self, event):
        self.Dismiss()

    def CMLAllMouseEvents(self, event):
        pass

    def CMLMouseOverItem(self, event):
        pass

    def CMLMouseEnter(self, event):
        pass

    def CMLMouseLeave(self, event):
        pass

    def CMLLeftDown(self, event):
        pass

    def CMLLeftUp(self, event):
        pass

    def CMLRightDown(self, event):
        pass

    def CMLRightUp(self, event):
        pass

    def CMLMouseWheel(self, event):
        pass
