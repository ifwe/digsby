'''

Cross-platform lists with arbitrary controls backed by data models of any type.

'''

from __future__ import with_statement
from util.primitives.structures import oset

import wx
from wx.lib.scrolledpanel import ScrolledPanel
from wx import FindWindowAtPointer, RectS, wxEVT_MOTION, wxEVT_MOUSE_CAPTURE_LOST

from gui.skin.skinobjects import SkinColor
from gui.textutil import default_font
from util.primitives.error_handling import traceguard
from util.primitives.misc import clamp
from gui.uberwidgets.umenu import UMenu

import cPickle
from gui.toolbox.scrolling import WheelScrollMixin

editable_controls = (wx.CheckBox, wx.HyperlinkCtrl, wx.StaticBitmap)
syscol = wx.SystemSettings_GetColour

from logging import getLogger; log = getLogger('anylists'); info = log.info; warning = log.warning
from util import default_timer

bgcolors = [
    wx.Color(238, 238, 238),
    wx.Color(255, 255, 255),
]

selbgcolor = wx.Color(180, 180, 180)
hovbgcolor = wx.Color(220, 220, 220)

class AnyRow(wx.Panel):
    'One row in an AnyList.'

    checkbox_border = 10
    row_height = 40

    def __init__(self, parent, data, use_checkbox = True, linkobservers = True):
        wx.Panel.__init__(self, parent, style = wx.FULL_REPAINT_ON_RESIZE)
#        self.text_controls = []
        oldChildren = set(self.Children)
        self.data = data

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.selectedbg = SkinColor(syscol(wx.SYS_COLOUR_HIGHLIGHT))
        self.bg = SkinColor(wx.WHITE)

        self.padding = wx.Point(5, 5)

        # Construct and layout GUI elements
        self.construct(use_checkbox)
        self.layout()

        # Observe the data object for changes
        if linkobservers:
            try:
                data.add_observer(self.on_data_changed)
            except AttributeError:
                pass
        self.on_data_changed(data)

        # Bind events
        Bind = self.Bind
        Bind(wx.EVT_PAINT, self._paint)
        Bind(wx.EVT_ERASE_BACKGROUND, lambda e: e.Skip(False))
        Bind(wx.EVT_MOTION, self.on_motion)
        Bind(wx.EVT_KILL_FOCUS, self.Parent.on_lost_focus)
        Bind(wx.EVT_LEFT_DCLICK, self.on_doubleclick)
        Bind(wx.EVT_RIGHT_UP, self.on_right_up)
        Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.on_mouse_lost)


        # Bind special mouse events that fall through to parent
        controls = [self] + list(set(self.Children) - oldChildren)
        for win in controls:
            winBind = win.Bind
            winBind(wx.EVT_LEFT_DOWN  , self.on_left_down)
            winBind(wx.EVT_RIGHT_DOWN , self.on_right_down)
            winBind(wx.EVT_RIGHT_UP   , self.on_right_up)
            winBind(wx.EVT_LEFT_DCLICK, self.on_doubleclick)
            winBind(wx.EVT_KILL_FOCUS , self.Parent.on_lost_focus)

        self.CalcColors(False)
        self.UpdateSkin()

        self.SetDropTarget(AnyListDropTarget(self))

    def UpdateSkin(self):
        # overridden in subclasses
        pass

    def on_data_changed(self, src, *a):
        'Invoked when the data object this row represents changes.'

        if not self:
            objget = lambda x:object.__getattribute__(self, x)
            log.error('%r object has been deleted.', objget('__class__'), )#objget('data'))

        if wx.IsDestroyed(self):
            return self._cleanup()

        with self.Frozen():
            self.PopulateControls(self.data)
            self.Refresh()

    @property
    def image(self):
        return wx.EmptyBitmap(32, 32)

    def PopulateControls(self, data):
        if isinstance(data, bytes):
            data, _data = data.decode('utf8'), data

        self.text = data

        if hasattr(self, 'checkbox'):
            self.checkbox.Value = bool(data)

    def on_doubleclick(self, e):
        'Cause the parent list to emit a LISTBOX_DOUBLECLICK event'
        self.Parent.emit_doubleclick_event(self.Index)

    def on_close(self, e = None):
        for c in self.Children + [self]:
            c.ReleaseAllCapture()

        # NOTE: wx maintains the capture stack as a static variable.
        # As a result, we can end up with the parent and child controls
        # setting focus to each other as the stack is popped, and so
        # even after removing the capture from the parent and all children,
        # we'll still get "capture == this" errors on deletion. To stop that,
        # this code completely unwinds and pops the stack.
        count = 0
        #CAS: short circuit in case the broken behavior of wx mouse capture
        #     changes
        while count < 100 and self.GetCapture():
            count += 1
            self.ReleaseMouse()

        self._cleanup()

    def _cleanup(self):
        if hasattr(self.data, 'remove_observer'):
            self.data.remove_observer(self.on_data_changed)

    def on_mouse_lost(self,event):
        while self.HasCapture():
#            print "Parent releasing mouse"
            self.ReleaseMouse()

        i = self.Parent.GetIndex(self)
        if i == self.Parent.Hovered:
            self.Parent.Hovered = -1

            self.Refresh()

    def MouseCaptureSystem(self,event,mouseinactions,mouseoutactions):
        winatpoint = FindWindowAtPointer()
        isover     = winatpoint == self or winatpoint in self.Children

        if not RectS(self.Size).Contains(event.Position) or not isover:
            self.ReleaseAllCapture()
            mouseoutactions()

        else:
            if not self.HasCapture():
#                print "parent capturing mouse"
                self.CaptureMouse()

                mouseinactions()

            def childwithmouse(p = event.Position):
                for child in self.Children:
                    if child.Shown and child.Rect.Contains(p):
                        return child

            passto = childwithmouse()

            if passto and not passto.HasCapture():

                def passback(e, passto = passto):
                    if not RectS(passto.Size).Contains(e.Position) or FindWindowAtPointer()!=passto:
                        while passto.HasCapture():

#                            print "child releasing capture"
                            passto.ReleaseMouse()
                            passto.Parent.AddPendingEvent(e)
                        discon()
                    e.Skip()

                def passlost(e,passto=passto):
#                    print "child disconecting"
                    discon()
                    #e.Skip()

                passto.Connect(passto.Id,passto.Id, wxEVT_MOTION,passback)
                passto.Connect(passto.Id,passto.Id, wxEVT_MOUSE_CAPTURE_LOST,passlost)

                def discon(passto=passto):
                    passto.Disconnect(passto.Id,passto.Id, wxEVT_MOTION)
                    passto.Disconnect(passto.Id,passto.Id, wxEVT_MOUSE_CAPTURE_LOST)
#                    print "disconected child capture"

#                print "parent giving mouse to child"
                passto.CaptureMouse()

    def on_motion(self, event):

        # Is the motion a drag event?
        if event.LeftIsDown() and event.Dragging() and self.Parent.dragging:
            ds = AnyRowDropSource(self)

            data = wx.CustomDataObject(self.Parent.data_format)
            data.SetData(cPickle.dumps(self.Index))
            ds.SetData(data)
            ds.DoDragDrop(wx.Drag_AllowMove)
            self.Parent.drag = -1
            self.Parent.dragging = False
            self.Parent.Refresh()
        else:
            if self.Parent.ClickTogglesCheckbox:
                self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

            self.Parent.dragging = False

            def MouseInActions():
                i = self.Parent.GetIndex(self)
                if i != self.Parent.Hovered:
                    self.Parent.Hovered = i

                    self.Refresh()

            def MouseOutActions():
                i = self.Parent.GetIndex(self)
                if i == self.Parent.Hovered:
                    self.Parent.Hovered = -1

                    self.Refresh()

            self.MouseCaptureSystem(event,MouseInActions,MouseOutActions)

        event.Skip(True)

    def on_left_down(self, e = None, right_click=False):
        # For things like checkboxes and hyperlinks, allow the click to fall
        # through so they work normally.
        if e and isinstance(e.EventObject, (editable_controls)):
            if not e.ButtonDClick():
                e.Skip(True)
                return

        p = self.Parent

        if p.SelectionEnabled:
            p.SetSelections([self.Index])
            self.CalcColors()

        if p.DraggableItems:
            p.dragging = True

        # a single click in a row with a checkbox simulates a click on the checkbox
        elif not right_click and p.ClickTogglesCheckbox and hasattr(self, 'checkbox'):
            e = wx.CommandEvent(wx.EVT_COMMAND_CHECKBOX_CLICKED, self.checkbox.Id)
            e.SetInt(not self.checkbox.Value)
            e.EventObject = self.checkbox
            self.checkbox.Command(e)

        p.SetFocus()

    def CalcColors(self, selected = None):
        if selected is None:
            selected = self.IsSelected()

        # The colors, including the background color, are dependent on if
        # this item is selected.
        if selected and self.Parent.show_selected:
            self.BackgroundColour = selbgcolor
        elif self.IsHovered():
            self.BackgroundColour = hovbgcolor
        else:
            self.BackgroundColour = bgcolors[self.Index % len(bgcolors)]

        self.bg = SkinColor(self.BackgroundColour)

    def on_right_down(self, e):
        self.on_left_down(right_click=True)

    def on_right_up(self, e):
        popup = self.popup
        if popup is not None:
            self.Parent._menurow = self
            popup.PopupMenu()

    @property
    def popup(self):
        try:
            return self._popupmenu
        except AttributeError:
            self._popupmenu = menu = UMenu(self)

            menu.AddItem(_('&Edit'),   callback = self.on_edit)
            menu.AddItem(_('&Remove'), callback = self.on_delete)
            return menu

    def on_edit(self):
        return self.Parent.on_edit(self.data)

    def on_delete(self):
        return self.Parent.OnDelete(self.data)

    def _paint(self, e):
        dc  = wx.AutoBufferedPaintDC(self)
        pad = self.padding
        sz  = self.ClientSize

        selected = self.IsSelected()
        self.CalcColors(selected)

        # Draw a background rectangle
        bg = self.bg#getattr(self, 'selectedbg' if selected else 'bg')
        bg.Draw(dc, wx.RectS(sz), self.Index)


        x = 0
        if hasattr(self, 'checkbox'):
            x += self.checkbox_border * 2 + self.checkbox.Size.width

        x += pad.x

        image = self.image
        if image:
            dc.DrawBitmap(image, x, sz.height/2 - self.image.Height/2, True)
            x += image.Width + pad.x

        self.draw_text(dc, x, sz)

        # Paint additional things from subclasses
        self.PaintMore(dc)

        # Paint the drag indication (if needed)
        self.draw_drag_indication(dc, self.Parent.drag)

        return dc

    def draw_text(self, dc, x, sz):
        '''
        Draws the main text label for this row.

        Subclasses may override this for custom behavior.
        '''

        dc.Font = self.Font
        dc.TextForeground = wx.BLACK#syscol(wx.SYS_COLOUR_HIGHLIGHTTEXT if self.IsSelected() else wx.SYS_COLOUR_WINDOWTEXT)

        labelrect = (x, 0, sz.width - x, sz.height)
        dc.DrawLabel(self.get_text(), labelrect, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)

    def get_text(self):
        return self.text

    def draw_drag_indication(self, dc, dragi):
        idx = self.Index

        if dragi == idx:
            y = 0
        elif dragi == idx + 1:
            y = self.Size.height - 1
        else: # No drag indication
            return

        # Drag indication
        dc.Pen = wx.Pen(wx.Colour(140,140,140))#BLACK_PEN
        dc.DrawLine(0, y, self.Size.width, y)
#        for i in (2, 3):
#            dc.DrawLine(i, y, 0, y-i)
#            dc.DrawLine(i, y, 0, y+i)


    def construct(self, use_checkbox):
        self.text = ''

        if use_checkbox:

            self.checkbox = wx.CheckBox(self, -1, style=wx.CHK_3STATE)
#            def bg(e):
#                dc = wx.ClientDC(self.checkbox)
#                dc.Pen = wx.TRANSPARENT_PEN
#                dc.Brush = wx.Brush(self.BackgroundColour)
#                dc.DrawRectangle(*self.checkbox.Rect)

            self.checkbox.Bind(wx.EVT_CHECKBOX, self.on_checkbox)

        self.ConstructMore()

    def IsChecked(self):
        return self.checkbox.Get3StateValue() == wx.CHK_CHECKED

    def on_checkbox(self, e):
        '''Intercepts checkbox events coming from children of this row, adds
        this row's index under the wxCommandEvents "Int" property, and then
        happily sends the events back on their way.'''

        e.SetInt(self.Index)
        e.Skip(True)

    def layout(self):
        self.Sizer = sz = wx.BoxSizer(wx.HORIZONTAL)
        pad = self.padding
        width = 0

        if hasattr(self, 'checkbox'):
            sz.Add(self.checkbox, 0, wx.EXPAND | wx.ALL, self.checkbox_border)
            width += self.checkbox.Size.width + self.checkbox_border*2

        height = max(getattr(self.image, 'Height', 0), self.Font.Height) + pad.y * 2
        height = max(getattr(self, 'min_row_height', 0), height)
        width += getattr(self.image, 'Width', 0)
        sz.Add((width, height), 0, 0)

        self.LayoutMore(sz)


    # Overridden in subclasses
    def LayoutMore(self, sizer): pass
    def ConstructMore(self): pass
    def PaintMore(self, dc): pass

    def GetIndex(self):
        return self.Parent.GetIndex(self)

    Index = property(GetIndex)

    def IsSelected(self):
        return self.Parent.IsSelected(self.Index)

    def IsHovered(self):
        return self.Parent.Hovered == self.Index

SCROLL_RATE = 20

class AnyList(WheelScrollMixin, ScrolledPanel):
    sizer_args = (0, wx.EXPAND)
    default_row_control = AnyRow
    default_velocity = 175
    SelectionEnabled = True
    ClickTogglesCheckbox = False

    if 'wxMac' in wx.PlatformInfo: scroll_sizes = ()
    else: scroll_sizes = (5, 1)

    def __init__(self, parent, data,
                 row_control = None,
                 multiselect = False,
                 edit_buttons = None,
                 draggable_items = True,
                 style = 0,
                 velocity=None):
        super(AnyList, self).__init__(parent, -1, style = wx.FULL_REPAINT_ON_RESIZE|style)

        self.data_format = wx.CustomDataFormat('AnyList-%s'%id(self))

        self.SetSizer(self.create_sizer())
        self.Font = default_font()

        if edit_buttons is not None:
            edit = dict((child.Id, child) for child in edit_buttons)

            if not hasattr(self, 'OnNew') or not hasattr(self, 'OnDelete'):
                raise AssertionError('to use the edit_buttons parameter you must implement OnNew and OnDelete (in class %s)' % self.__class__.__name__)

            edit[wx.ID_NEW].Bind(wx.EVT_BUTTON, self.OnNew )
            edit[wx.ID_DELETE].Bind(wx.EVT_BUTTON, self.OnDelete)

            self.delete_button = edit[wx.ID_DELETE]
            self.delete_button.Enable(False)
        else:
            self.delete_button = None

        self.velocity = velocity or self.default_velocity

        # List set up
        self.show_selected = True
        self.rows = []
        self.DraggableItems = draggable_items
        self._selection = set()
        self._hovered = -1

        if row_control is None: self.row_control = self.default_row_control
        else: self.row_control = row_control

        # Check to make sure data is observable
        self.data = data
        if hasattr(data, 'add_observer') and callable(data.add_observer):
            # Watch the observable list for changes.
            data.add_observer(self.on_data_changed)

        self.on_data_changed()

        self.multiselect = multiselect

        self.SetAutoLayout(True)
        self.SetupScrolling(False, True, *self.scroll_sizes)

        Bind = self.Bind
        Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.BindWheel(self)
        Bind(wx.EVT_KILL_FOCUS, self.on_lost_focus)
        Bind(wx.EVT_KEY_DOWN, self.on_key)
        Bind(wx.EVT_CHILD_FOCUS, Null) # to nullify bad effects of ScrolledPanel
        Bind(wx.EVT_SCROLLWIN_LINEDOWN, lambda e: self.Scroll(0, self.ViewStart[1] + SCROLL_RATE))
        Bind(wx.EVT_SCROLLWIN_LINEUP, lambda e: self.Scroll(0, self.ViewStart[1] - SCROLL_RATE))

        self.drag = -1
        self.dragging = False

    def on_left_down(self, e):
        self.SetSelections([])

    def on_key(self, e):
        if e.KeyCode == wx.WXK_UP:
            if self.Selection > 0:
                self.SetSelections([self.Selection-1])
        elif e.KeyCode == wx.WXK_DOWN:
            self.SetSelections([self.Selection+1])
        else:
            e.Skip()

    def on_lost_focus(self, e):
        self.Refresh()

    def on_close(self):
        try:
            self.data.remove_observer(self.on_data_changed)
        except AttributeError:
            pass

        for row in self.rows:
            row.on_close()

    def drag_item(self, fromindex, toindex):
        # Not a valid drag? Get outta here.
        if toindex is None: return

        info('drag_item %d -> %d (%d rows)', fromindex, toindex, len(self.rows))
        # If the source is lower than the destination, change the destination
        # index because of the offset created by the "gap"
        if fromindex < toindex: toindex -= 1

        # Actually rearrange the data
        data = self.data

        with self.Frozen():
            with traceguard:

                insert = lambda: data.insert(toindex, data.pop(fromindex))

                if hasattr(self.data, 'freeze'):
                    self.data.freeze()
                    insert()
                    self.data.thaw()
                else:
                    insert()

            self.SetSelections([toindex])

    def ScrollLines(self, lines):
        dist = 0
        a = b = None
        try:
            if len(self) > 1:
                a = self[1].Position.y
                b = self[0].Position.y
            else:
                dist = 0
        except Exception:
            dist = 0
        else:
            if a is not None and b is not None:
                dist = a - b
        if dist:
            dist = lines * dist - getattr(self, 'borrowed_dist', 0)
            self.borrowed_dist = int(round(dist)) - dist
            self.Scroll(0, self.ViewStart.y + int(round(dist)))
        else:
            super(AnyList, self).ScrollLines(lines)

    def indicate_drag(self, x, y):
        # Accounting for scrolling, find out how many pixels down we are
        unuseddx, dy = self.GetScrollPixelsPerUnit()
        y += dy * self.ViewStart[1]    # account for scrolling

        def finddrag(y):
            'Returns the index between children the dragging cursor is over.'

            for i, row in enumerate(self.rows):
                h = row.Size.height
                if y < h / 2: return i
                elif y < h: return i + 1
                y -= row.Size.height

            return -1

        newdrag = finddrag(y)

        if newdrag != self.drag:
            self.drag = newdrag
            self.Refresh()

    def on_data_changed(self, *args):
        'Invoked when the observable data list changes.'
        if wx.IsDestroyed(self):
            return

        with self.Frozen():
            sz = self.Sizer
            rows = self.rows

            oldrowcount = len(rows)
            scrolly = self.GetScrollPos(wx.VERTICAL)

            dataset = oset(self.data)
            prevset = oset(row.data for row in rows)

            oldset = prevset - dataset
            newset = dataset - prevset

            for i_, row in list(enumerate(rows)):
                sz.Detach(row)
                if row.data in oldset:
                    if i_ == self.Hovered:
                        self._hovered = -1
                    rows.remove(row)
                    row.ReleaseAllCapture()
                    row.on_close()
                    row.Destroy()

            # Create a new row control for each data element, and add it to
            # sizer.
            for elem in newset:
                control = self.row_control(self, elem)
                rows.append(control)

            idxs = {}
            for i, d in enumerate(self.data): idxs[d] = i
            rows.sort(key = lambda r: idxs.get(r.data))

            for row in rows:
                sz.Add(row, *self.sizer_args)

            self.Layout()

            # Restore the old scroll position.
            newrowcount = len(rows)
            if oldrowcount != 0 and oldrowcount != newrowcount:
                self.SetupScrolling(False, True, *self.scroll_sizes)

                # on MSW, scrolling immediately doesn't work.
                wx.CallAfter(self.Scroll, 0, scrolly)

    def RemoveItem(self, child):
        if isinstance(child, int):
            del self.data[child]
        else:
            self.data.remove(child)

        if not hasattr(self.data, 'observers'):
            self.on_data_changed()

    def GetIndex(self, child):
        'Get the index of the specified child.'

        try:
            return self.rows.index(child)
        except ValueError:
            return -1

    def GetDataObject(self, index):
        'Returns the data model object at the specified index.'

        if not isinstance(index, int):
            raise TypeError('index must be an integer')

        try:
            return self.rows[index].data
        except IndexError:
            return None

    def GetRow(self, index):
        try:
            return self.rows[index]
        except IndexError:
            return None

    def IsSelected(self, n):
        'Returns True if the item at the nth position is selected.'

        return n in self._selection

    def GetSelection(self):
        'Returns the index of the currently selected element, or -1 if none.'
        if not getattr(self, '_selection', False):
            return wx.NOT_FOUND

        if len(self._selection) != 1:
            raise AssertionError('GetSelection used on a multiselection list?')

        return list(self._selection)[0]

    def GetSelections(self):
        '''Returns a list containing the integer indices of the selected
        elements in the list.'''

        return list(self._selection)

    def SetSelections(self, sel):
        'Set the selection state of this list. sel must be iterable'

        if not self.SelectionEnabled:
            return

        myclamp = lambda x: clamp(x, 0, len(self.data)-1)

        torefresh = self._selection.copy()
        self._selection = set(myclamp(x) for x in sel)

        if not len(self.rows): self._selection = set()
        for i in self._selection: assert i >= 0 and i < len(self.rows)


        for i in self._selection.difference(torefresh):
            self.emit_selected_event(i)
        for i in torefresh.difference(self._selection):
            self.emit_deselected_event(i)

        if self.delete_button:
            self.delete_button.Enable(bool(self._selection))

        if not self.rows: return

        for i in set(myclamp(x) for x in torefresh.union(self._selection)):
            try:
                if i != myclamp(i): continue
                self.rows[i].Refresh()
            except IndexError, ie:
                import sys
                print >> sys.stderr, 'index:', i
                raise ie

    Selection  = property(GetSelection)
    Selections = property(GetSelections, SetSelections)

    def SetHovered(self,i):
        n = self._hovered
        oldhov = self[n] if n != -1 else None
        try:
            newhov = self[i] if i != -1 else None
        except IndexError, ie:
            import sys
            print >> sys.stderr, 'index:', i
            raise ie

        self._hovered = i

        if oldhov:
            oldhov.Refresh()
            self.emit_hovered_event(n)

        if newhov:
            newhov.Refresh()
            self.emit_hovered_event(i)



    def GetHovered(self):
        return self._hovered

    Hovered = property(GetHovered,SetHovered)

    def create_sizer(self):
        return wx.BoxSizer(wx.VERTICAL)

    def emit_event(self,n,type):
        e = wx.CommandEvent(type)
        e.SetEventObject(self)
        e.SetInt(n)
        self.AddPendingEvent(e)

    def emit_hovered_event(self,n):
        self.emit_event(n,wx.wxEVT_COMMAND_LIST_ITEM_FOCUSED)

    def emit_selected_event(self, n):
        self.emit_event(n,wx.wxEVT_COMMAND_LIST_ITEM_SELECTED)

    def emit_deselected_event(self, n):
        self.emit_event(n,wx.wxEVT_COMMAND_LIST_ITEM_DESELECTED)

    def emit_doubleclick_event(self, n):
        self.emit_event(n,wx.wxEVT_COMMAND_LISTBOX_DOUBLECLICKED)

    def __contains__(self, x):
        return self.data.__contains__(x)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, n):
        return self.rows[n]

# drag and drop

class AnyRowDropSource(wx.DropSource):
    def __init__(self, window):
        wx.DropSource.__init__(self, window)
        self.window = window

class AnyListDropTarget(wx.PyDropTarget):
    #VELOCITY = 100
    def __init__(self, row):
        wx.PyDropTarget.__init__(self)

        self.lasttick = None

        self.row = row
        self.parent_list = row.GetParent()

        self.dragged = wx.CustomDataObject(self.parent_list.data_format)
        self.SetDataObject(self.dragged)

        self.id = id(self.parent_list)

    def OnEnter(self, x, y, d):
        return d

    def OnLeave(self):
        self.lasttick = None

    def OnDrop(self, x, y):
        return True

    def OnDragOver(self, x, y, d):
        if not self.parent_list.dragging:
            return wx.DragCancel

        plist = self.parent_list

        y += self.row.Position.y # account for y position of the row

        # draw the drag indicator line
        self.parent_list.indicate_drag(x, y)

        listrect = wx.RectS(plist.Size)

        topdif = y - listrect.y
        botdif = listrect.bottom - y
        ply = plist.ViewStart[1]

        if topdif < 7 or botdif < 7:
            if self.lasttick is None:
                self.lasttick = default_timer()

            now = default_timer()

            # clamp to 0: negative time deltas--from floating point roundoff errors?
            diff = max(0, now - self.lasttick)
            toscroll = int(diff * self.velocity)

            if toscroll >= 1:
                self.lasttick = now

                if topdif < 5:
                    plist.Scroll(0, ply - toscroll)
                elif botdif < 5:
                    plist.Scroll(0, ply + toscroll)

        return wx.DragMove

    @property
    def velocity(self):
        return self.parent_list.velocity

    def OnData(self, x, y, d):
        "Called when OnDrop returns True. Get data and do something with it."

        if not self.GetData():     # Copies data from drag source to self.dragging
            return wx.DragNone

        list    = self.parent_list
        toindex = list.drag

        with traceguard:
            fromindex = cPickle.loads(self.dragged.Data)

            if toindex != -1:
                list.drag_item(fromindex, toindex)
                return wx.DragMove

        return wx.DragError




def main():
    from util.observe import ObservableList, Observable

    app = wx.PySimpleApp()

    f = wx.Frame(None, -1, 'AnyList Test')
    f.Sizer = sz = wx.BoxSizer(wx.VERTICAL)

    class Foo(Observable):
        def __init__(self, name):
            Observable.__init__(self)
            self.name = name

        def __call__(self):
            wx.Bell()

        def __repr__(self): return '<Foo %s>' % self.name

    def on_doubleclick(e):
        print e

    foos = [Foo(n) for n in 'one two three four five six seven eight nine'.split()]
    data = ObservableList(foos)

    splist = AnyList(f, data)
    splist.Bind(wx.EVT_LISTBOX_DCLICK, on_doubleclick)

    sz.Add(splist, 1, wx.EXPAND | wx.SOUTH, 15 if 'wxMac' in wx.PlatformInfo else 0)
    splist.Bind(wx.EVT_CHECKBOX, lambda e: e.EventObject.Parent.data())

    f.Show()
    app.MainLoop()



if __name__ == '__main__':
    main()
    #testColors()
