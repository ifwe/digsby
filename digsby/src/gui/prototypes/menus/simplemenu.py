from gui.textutil import GetTextWidth
from gui.prototypes.menus.cml import CustomMenuInterface, CreateCML
from util import default_timer

import wx.lib.newevent
NewEvent = wx.lib.newevent.NewEvent
NewCommandEvent = wx.lib.newevent.NewCommandEvent
SimpleMenuItemClickedEvent, EVT_SMI_CLICKED = NewCommandEvent()
SimpleMenuOpenEvent, EVT_SM_OPENED = NewEvent()
SimpleMenuCloseEvent, EVT_SM_CLOSED = NewEvent()

class RecapTimer(wx.Timer):
    "This timer tells the curent lowest level menu to recapture the mouse, along with it's parent tree "
    def __init__(self):
        wx.Timer.__init__(self)

    def Start(self, target):
        wx.Timer.Start(self, 10)
        self.target=target

    def Notify(self):
        target = self.target
        mp = target.Parent.ScreenToClient(wx.GetMousePosition())

        if (not target.Rect.Contains(mp) or target.ClientRect.Contains(mp)) and not wx.GetMouseState().LeftDown():
            self.Stop(target)

    def Stop(self,target):
        wx.Timer.Stop(self)
        target.CaptureMouse()

recaptimer = RecapTimer()


class SimpleMenuBase(CustomMenuInterface):
    '''
    A simple implementation of the CustomMenuInterface
    Expects it's subclass to also inherit from a data provider modeled after wxControlWithItems
    '''

    def __init__(self, parent, maxHeight = -1,  minWidth = -1, maxWidth=-1, skinkey = 'simplemenu'):

        self._customMenu = CreateCML(parent, self, self, skinkey=skinkey)

        self.minWidth  = minWidth
        self.maxWidth  = maxWidth
        self.maxHeight = maxHeight

    def PopUp(self, pos):
        self._customMenu.Display(pos)

    def Dismiss(self):
        self._customMenu.Dismiss()

    def CMLHover(self):
        return self._customMenu.GetSelection()


    def CMLCalcSize(self, skin):
        height = 0

        for n in xrange(self.GetCount()):
            height += self.CMLMeasureItem(n, skin)

        height += skin["framesize"].top + skin["framesize"].bottom

        if self.maxHeight != -1:
            height = min(height, self.maxHeight)

        width = self.CMLCalcMenuWidth(skin)

        return wx.Size(width, height)

    def CMLCalcMenuWidth(self, skin):

        maxWidth = self.maxWidth
        minWidth = self.minWidth

        if maxWidth == minWidth and maxWidth != -1:
            return maxWidth

        width = max(GetTextWidth(item, skin['font']) for item in self.GetStrings())

        width += skin['padding'].x*2 + skin["framesize"].left + skin["framesize"].right

        if maxWidth != -1:
            width = min(width, maxWidth)

        if minWidth != -1:
            width = max(width, minWidth)

        return width


    def CMLMeasureItem(self, n, skin):
        return skin['font'].GetHeight() + (2 * skin["padding"].y)


    def CMLDrawBackground(self, dc, rect, skin):
        skin['backgrounds.menu'].Draw(dc, rect)

    def GetHover(self):
        return self._customMenu.GetSelection()

    def CMLDrawItemBG(self, dc, rect, n, skin):
        selbg = skin['backgrounds.selection']
        itembg = skin['backgrounds.item']

        if self.GetHover() == n and selbg:
            selbg.Draw(dc, rect)
        elif itembg:
            itembg.Draw(dc, rect)

    def CMLDrawItem(self, dc, rect, n, skin):
        item = self.GetString(n)

        dc.Font = skin["font"]
        dc.TextForeground = skin["fontcolors.selection"] if self.GetHover() == n else skin["fontcolors.normal"]

        drawrect = wx.Rect(rect.x + skin["padding"].x, rect.y, rect.width - skin["padding"].x*2, rect.height)

        dc.DrawTruncatedText(item, drawrect, alignment = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

    def CMLMouseMotion(self, event):
        cM = self._customMenu
        mp = cM.Parent.ScreenToClient(wx.GetMousePosition())

        while  cM.HasCapture() and cM.Rect.Contains(mp) and not cM.ClientRect.Contains(mp):
            cM.ReleaseMouse()
            global recapTimer
            recaptimer.Start(cM)

    def CMLDisplay(self, pos, size):
        #TODO: Open event?
        self._customMenu._frame.Show(True)

    def CMLDismiss(self):
        #TODO: Close Event?
        self._customMenu._frame.Show(False)

    def CMLLeftUp(self, event):
        cM = self._customMenu
        mp = cM.ScreenToClient(wx.GetMousePosition())
        i  = cM.HitTest(mp)

        if i != -1 and cM.ScreenRect.Contains(wx.GetMousePosition()):
            pass
        #TODO: Event

class SimpleMenuedControl(wx.PyControl, SimpleMenuBase):
    '''
    Basic implementation of a control with a custom menu attached to it
    Can be used for controls such as comboboxs
    '''

    def __init__(self, parent, id = -1, pos = wx.DefaultPosition, size = wx.DefaultSize, maxMenuHeight = -1,  minMenuWidth = -1, maxMenuWidth=-1, skinkey = 'simplemenu'):
        wx.PyControl.__init__(self, parent, id, pos, size, style = wx.BORDER_NONE)
        SimpleMenuBase.__init__(self, parent, maxMenuHeight, minMenuWidth, maxMenuWidth, skinkey)

    def SetMenuSkinKey(self, skinkey):
        self._customMenu.SetSkinKey(skinkey)

    def CMLDisplay(self, pos, size):
        se = SimpleMenuOpenEvent()
        self.AddPendingEvent(se)
        self._customMenu._frame.Show(True)

    def CMLDismiss(self):
        se = SimpleMenuCloseEvent()
        self.AddPendingEvent(se)
        self._customMenu._frame.Show(False)

    def CMLMouseCaptureLost(self, event):
        se = SimpleMenuCloseEvent()
        self.AddPendingEvent(se)


    def CMLLeftUp(self, event):
        cM = self._customMenu
        mp = cM.ScreenToClient(wx.GetMousePosition())
        i  = cM.HitTest(mp)

        if i != -1 and cM.ScreenRect.Contains(wx.GetMousePosition()):
            se = SimpleMenuItemClickedEvent(0)
            se.SetInt(i)
            self.AddPendingEvent(se)


'''
A basic implementation of a data provider
'''
class BasicMenuData(object):
    def __init__(self):
        self._items = []
        self._clientData = {}
        self._lastItemChange = default_timer()
        self._lastSelChange = default_timer()
        self._selection = -1

    def Append(self, string, clientData = None):
        self._items.append(string)
        self._clientData[len(self._items) -1] = clientData
        self._changed(True, False)
        return self._items.index(string)

    def SetItems(self, strings):
        self._items = list(strings)
        self._clientData[len(self._items) - 1] = None
        self._changed(True, True)

    def Clear(self):
        self._items = []
        self._clientData = {}
        self._selection = -1
        self._changed(True, True)

    def _changed(self, item, selection):
        if item:
            self._lastItemChange = default_timer()

        if selection:
            self._lastSelChange = default_timer()

        if self._customMenu.IsShown():
            self._customMenu.CalcSize()

    def Delete(self, n):
        self._items.remove(self._items[n])
        if n in self._clientData:
            self._clientData.pop(n)
        self._changed(True, False)

    def FindString(self, string, caseSensitive = False):

        if caseSensitive:
            for i in xrange(len(self._items)):
                if self._items[i] == string:
                    return i

        else:
            for i in xrange(len(self._items)):
                if self._items[i].lower() == string.lower():
                    return i
        return -1

    def GetClientData(self, n):
        return self._clientData.get(n, None)

    def GetClientObject(self, n):
        return self._clientData.get(n, None)

    def GetCount(self):
        return len(self._items)

    def GetSelection(self):
        return self._selection

    def GetString(self, n):
        return self._items[n]

    def GetStrings(self):
        return self._items

    def GetStringSelection(self):
        if self._selection == -1:
            return None

        return self._items[self._selection]

    def Insert(self, string, n, clientData = None):
        self._items.insert(n, string)
        self._clientData[n] = clientData

    def IsEmpty(self):
        return len(self._items) == 0

    def Number(self):
        return len(self._items)

    def Select(self, n):
        self._selection = n
        self._changed(False, True)

    SetSelection = Select

    def SetClientData(self, n, data):
        self._clientData[n] = data

    def SetClientObject(self, n, data):
        self._clientData[n] = data

    def SetString(self, n, string):
        self._items[n] = string

    def SetStringSelection(self, string):
        try:
            self._selection = self._items.index(string)
        except ValueError:
            self._selection = -1

        self._changed(False, True)

class BasicMenu(SimpleMenuBase, BasicMenuData):
    '''
    A basic popup menu example
    '''

    def __init__(self, parent, maxMenuHeight = -1,  minMenuWidth = -1, maxMenuWidth=-1, skinkey = 'menu'):
        BasicMenuData.__init__(self)
        SimpleMenuBase.__init__(self, parent, maxMenuHeight, minMenuWidth, maxMenuWidth, skinkey)

    def Reposition(self, rect):
        self._customMenu.CalcSize()
        menuSize = self._customMenu.GetMinSize()
        pos = wx.Point(rect.GetLeft(), rect.GetBottom() + 1)

        from gui.toolbox import Monitor
        monRect = Monitor.GetFromPoint(pos, True).Geometry
        if pos.y + menuSize.height > monRect.bottom:
            pos = wx.Point(rect.GetLeft(), rect.GetTop() - menuSize.height - 1)

        return pos

    def PopUp(self, rect):
        pos = self.Reposition(rect)
        return SimpleMenuBase.PopUp(self, pos)

    def CMLDisplay(self, pos, size):
        #TODO: Open event?
        self._customMenu._frame.Show(True)

    def CMLDismiss(self):
        #TODO: Close Event?
        self._customMenu._frame.Show(False)

    def CMLLeftUp(self, event):
        cM = self._customMenu
        mp = cM.ScreenToClient(wx.GetMousePosition())
        i  = cM.HitTest(mp)

        if i != -1 and cM.ScreenRect.Contains(wx.GetMousePosition()):
            pass

        #TODO: Event
        se = SimpleMenuItemClickedEvent(0)
        se.SetInt(i)
        cM._frame.AddPendingEvent(se)

        cM.Dismiss()

    def IsShown(self):
        return self._customMenu._frame.IsShown()

    def SetItems(self, items):
        # Maintain string selection.
        selected_string = None
        i = self._customMenu.Selection
        if i != -1 and i < len(self._items):
            selected_string = self._items[i]

        super(BasicMenu, self).SetItems(items)

        if selected_string is not None:
            i = self.FindString(selected_string, True)
            if i != -1:
                self._customMenu.SetSelection(i)

