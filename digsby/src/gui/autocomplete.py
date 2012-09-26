import wx
import cgui

from gui.prototypes.menus.simplemenu import EVT_SMI_CLICKED
from gui.toolbox.monitor import Monitor
from gui.prototypes.menus.simplemenu import SimpleMenuItemClickedEvent

menu_keys = frozenset((wx.WXK_UP, wx.WXK_DOWN, wx.WXK_PAGEUP,
    wx.WXK_PAGEDOWN, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_HOME,
    wx.WXK_END, wx.WXK_TAB))

class AutoCompleteDropDown(cgui.SkinVList):
    max_height = 500
    frame_border_size = 1
    def __init__(self, parent):
        self.frame = AutoCompleteFrame(parent)
        self.frame.SetSize((300, self.max_height+self.frame_border_size*2))
        cgui.SkinVList.__init__(self, self.frame)
        self.frame.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.frame.Sizer.Add(self, 1, wx.EXPAND | wx.ALL, self.frame_border_size)
        self.frame.SetBackgroundColour(wx.Color(0x77, 0x77, 0x77))
        self.frame.Layout()
        self.SetDrawCallback(self.OnPaint)
        self.Bind(wx.EVT_MOTION, self.__OnMouseMotion)
        self.Bind(wx.EVT_LEFT_UP, self.__OnLeftUp)
        self.Bind(wx.EVT_KEY_DOWN, self.__OnKeyDown)

    def __OnKeyDown(self, e):
        keycode = e.KeyCode

        if keycode == wx.WXK_UP:
            sel = self.GetSelection() - 1
            if sel >= 0: self.SetSelection(sel)

        elif keycode == wx.WXK_DOWN:
            sel = self.GetSelection() + 1
            if sel < self.GetItemCount(): self.SetSelection(sel)

        elif keycode == wx.WXK_PAGEUP:
            self.PageUp()
            self.SetSelection(self.GetFirstVisibleLine())

        elif keycode == wx.WXK_PAGEDOWN:
            self.PageDown()
            self.SetSelection(self.GetFirstVisibleLine())

        elif keycode == wx.WXK_END:
            self.SetSelection(self.GetItemCount()-1)

        elif keycode == wx.WXK_HOME:
            self.SetSelection(0)

        elif keycode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB):
            self.EmitClick(self.Selection)

        else:
            e.Skip()

    def __OnLeftUp(self, e):
        e.Skip()
        self.EmitClick(self.Selection)

    def EmitClick(self, i):
        if i != -1:
            se = SimpleMenuItemClickedEvent(0)
            se.SetInt(i)
            self.AddPendingEvent(se)

    def __OnMouseMotion(self, e):
        e.Skip()
        self.SetSelection(self.HitTest(e.Position))

    item_height = 26

    def CalcHeight(self):
        return self.item_height * len(self.items) + self.frame_border_size*2

    def SetItems(self, items):
        selected_item = None
        if hasattr(self, 'items'):
            try:
                selected_item = self.items[self.Selection]
            except ValueError:
                pass

        #print 'selected_item', selected_item
        self.items = items
        self.SetHeights([self.item_height]*len(items))
        height = min(self.max_height, self.CalcHeight())
        self.frame.SetSize((self.frame.Size.width, height))

        for i, item in enumerate(items):
            if selected_item is not None and item == selected_item:
                break
        else:
            i = 0

        self.SetSelection(i)


    def PopUp(self, rect):
        self.rect = rect
        monarea = Monitor.GetFromRect(rect).ClientArea

        below = wx.Point(rect.BottomLeft)
        above = wx.Point(rect.TopLeft - wx.Point(0, self.frame.Size.height))
        
        if getattr(self, 'valign', 'bottom') == 'top':
            prefer, second = above, below
        else:
            prefer, second = below, above

        if monarea.ContainsRect(wx.RectPS(prefer, self.frame.Size)):
            chose = prefer
        else:
            chose = second

        self.frame.SetPosition(chose)

        if not hasattr(self, 'valign'):
            self.valign = 'bottom' if chose == below else 'top'

        return self.frame.ShowNoActivate(True)

    def Dismiss(self):
        return self.frame.Hide()

class AutoCompleteFrame(wx.Frame):
    style = wx.FRAME_SHAPED | wx.NO_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, style=self.style)
        


def autocomplete(textctrl, items, controller):
    def update_popup(new=False):
        @wx.CallAfter
        def after():
            items = controller.complete(textctrl.Value, textctrl.InsertionPoint)
            if items is not None:
                a.SetItems(items)
                if new or a.Selection == -1:
                    a.SetSelection(0)
                a.PopUp(get_popup_rect())
            else:
                a.Dismiss()

    def onkey(e):
        e.Skip()
        keycode = e.KeyCode
        if a.frame.IsShown():
            if keycode == wx.WXK_ESCAPE:
                a.Dismiss()
                e.Skip(False)
            elif keycode in menu_keys:
                a.ProcessEvent(e)
                return
            else:
                if not a.should_ignore_key(e):
                    update_popup()
        else:
            if keycode == wx.WXK_BACK:
                update_popup()

    textctrl.Bind(wx.EVT_KEY_DOWN, onkey)

    try:
        a = textctrl._autocomplete
    except AttributeError:
        # TODO: don't import twitter here. duh
        from twitter.twitter_gui import TwitterAutoCompleteDropDown
        a = textctrl._autocomplete = TwitterAutoCompleteDropDown(textctrl)
        def onmenu(e):
            selection = a.items[e.GetInt()].user['screen_name']
            result = controller.finish(textctrl.Value, textctrl.InsertionPoint, selection)
            a.SetSelection(0)
            if result is not None:
                val, cursor = result
                textctrl.SetValue(val)
                textctrl.SetInsertionPoint(cursor)
                update_popup()
        textctrl.Bind(EVT_SMI_CLICKED, onmenu)
        def onkillfocus(e):
            e.Skip()

            # dismiss on focus lost, unless we're clicking the popup itself
            if wx.FindWindowAtPointer() is not a:
                a.Dismiss()

        textctrl.Bind(wx.EVT_KILL_FOCUS, onkillfocus)

    if not a.frame.IsShown():
        update_popup(True)

    def get_popup_rect():
        coords = textctrl.IndexToCoords(textctrl.InsertionPoint)
        rect = wx.RectPS(textctrl.ClientToScreen(coords), wx.Size(0, textctrl.CharHeight))
        return rect

    return a

