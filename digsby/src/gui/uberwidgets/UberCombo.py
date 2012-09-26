from __future__ import with_statement
import wx
import threading
from wx import RectS, Point, Bitmap, Rect, GetMousePosition, AutoBufferedPaintDC

from util import try_this
from gui import skin
from gui.uberwidgets.UberEvents import EVT_UB_OVER,EVT_UB_OUT
from UberButton import UberButton
from gui.textutil import default_font
from simplemenu import SimpleMenu, SimpleMenuItem
from gui.skin.skinobjects import SkinColor,Margins,MarginSizer
from gui.uberwidgets import UberWidget
from gui.validators import LengthLimit


from logging import getLogger; log = getLogger('ubercombo')

class UberCombo(wx.Window, UberWidget):
    'Skinnable Combobox'

    ForceTextFieldBackground = False

    def __init__(self, parent, value = None, typeable=False,
                 selectioncallback = None,
                 valuecallback = None,
                 skinkey = None, size = wx.DefaultSize,
                 pos = wx.DefaultPosition, maxmenuheight = None, minmenuwidth = None,
                 editmethod = None,
                 empty_text = None, # text to show in the display when it's not being edited
                 empty_text_hide = True,
                 ):
        """
        value - String in the Box
        typeable - if true can type in the text field
        selectioncallback - method called when item is selected
        Valuecallback - this is called when the text value in the combo changes
        skinkey - the key string for the skin YAML
        size - size
        pos - position
        maxmenuheight - max size of the menu
        minmenuwidth - the width of the menu
        editmethod - trigered when the value is being edited
        """

        wx.Window.__init__(self,parent,-1,pos,size)

        #Set Callbacks
        self.selectioncallback = selectioncallback
        self.valuecallback = valuecallback
        self._menuClick = False

        if size: self.Size = wx.Size(*size)


        self.content = wx.BoxSizer(wx.HORIZONTAL)


        self.SetSkinKey(skinkey,True)

        self.selection = None

        # Create the dropdown button
        self.dbutton = UberButton(self, -1, skin = self.ddbuttonskin,icon = self.dropdownicon,type = 'combo')
        self.dbutton.Bind(wx.EVT_LEFT_DOWN, self.OnDropdownLeftDown)
        self.dbutton.Bind(wx.EVT_LEFT_DCLICK, self.OnDropdownLeftDown)

        self.minmenuwidth = minmenuwidth

        # Create the menu for the combo
        self.menu = SimpleMenu(self, maxheight = maxmenuheight,
                                     width     = minmenuwidth if minmenuwidth != None else self.Size.width,
                                     skinkey   = self.menuskin,
                                     callback  = lambda *a, **k: (setattr(self, '_menuClick', True),
                                                                self.OnSelection(*a, **k)))

        # Create the display for the combobox
        disp = self.display = ComboDisplay(self, typeable = typeable,
                                           #size = (displaywidth,self.Size.height),
                                           empty_text = empty_text,
                                           empty_text_hide = empty_text_hide)
        disp.editmethod = editmethod

        self.content.Add(disp, 1, wx.EXPAND)
        self.content.Add(self.dbutton,0,wx.EXPAND)
        self.Layout()

        Bind=self.Bind
        Bind(wx.EVT_PAINT,            self.OnPaint)
        Bind(wx.EVT_SIZE,             self.OnSize)
        Bind(wx.EVT_MENU_CLOSE,       disp.OnMouseMove)
        Bind(EVT_UB_OVER,             disp.OnMouseIntoButton)
        Bind(EVT_UB_OUT,              disp.OnMouseOutOfButton)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)


        if value: self.ChangeValue(value)

        self.Sizer = MarginSizer(self.framesize, self.content)

    def OnDropdownLeftDown(self, e):
        self.OpenMenu()

    DropDownButton = property(lambda self: self.dbutton)

    def Enable(self, val):
#        self.cbutton.Enable(val)
        self.dbutton.Enable(val)
        self.display.Enable(val)


    def SetCallbacks(self, selection = sentinel, value = sentinel):
        'Sets callbacks for this combobox.'

        if selection is not sentinel: self.selectioncallback = selection
        if value is not sentinel:     self.valuecallback = value

    def GetCount(self):
        'Returns the number of choices in this combobox.'

        return self.menu.Count

    def GetIndex(self,item):
        return self.menu.GetItemIndex(item)

    Count = property(GetCount)

    def __contains__(self, item):
        return item in self.menu.spine.items

    def __getitem__(self, n):
        if not isinstance(n, int):
            raise TypeError

        return self.menu.spine.items[n]

    def __len__(self):
        return len(self.menu.spine.items)

    def Add(self, itemname, method = None):
        """Append a new item to the combo with an optional callback"""
        self.AppendItem( SimpleMenuItem(itemname, method = method) )

    def UpdateSkin(self):
        """
            This updates the skin elements from the skin provided
            can be used to update skins if the window changes, change the skin,
            or revert to native mode if called with None or no arguments
        """
        key = self.skinkey

        native = self.native = not key

        if native:
            self.padding  = Point(2,2)
            self.margins  = Margins([0,0,0,0])
            self.framesize  = Margins([0,0,0,0])


            bgc = wx.SystemSettings_GetColour(wx.SYS_COLOUR_LISTBOX)

            self.framebg  = SkinColor(wx.BLACK)
            self.normalbg = SkinColor(bgc, border=wx.Pen(wx.BLACK, 1))
            self.activebg = SkinColor(bgc, border=wx.Pen(wx.BLACK, 1))
            self.hoverbg  = SkinColor(bgc, border=wx.Pen(wx.BLACK, 1))

            fc = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOWTEXT)

            self.normalfc = fc
            self.activefc = fc
            self.hoverfc  = fc

            self.Font     = default_font()

            self.menuskin     = None
            self.ddbuttonskin = None
            self.dropdownicon = None

        else:

            s = lambda k, default: skin.get('%s.%s' % (key, k), default)

            self.padding  = s('padding', Point(2,2))
            self.margins  = s('margins', Margins([0,0,0,0]))
            self.framesize  = s('framesize', Margins([0,0,0,0]))

            self.framebg  = s('frame',              lambda: SkinColor(wx.BLACK))
            self.normalbg = s('backgrounds.normal', lambda: SkinColor(wx.WHITE))
            self.activebg = s('backgrounds.active', lambda: SkinColor(wx.WHITE))
            self.hoverbg  = s('backgrounds.hover',  lambda: SkinColor(wx.WHITE))

            self.normalfc = s('fontcolors.normal', wx.BLACK)
            self.activefc = s('fontcolors.active', wx.BLACK)
            self.hoverfc  = s('fontcolors.hover',  wx.BLACK)
            self.hintfc   = s('fontcolors.hint',   lambda: wx.Colour(128,128,128))

            self.Font     = s('font', lambda: default_font)

            self.menuskin     = s('menuskin', '')
            self.ddbuttonskin = s('dropdownbuttonskin','')
            self.dropdownicon = s('dropdownbuttonicon','')


        if getattr(self, 'dbutton', None):
            self.dbutton.SetSkinKey(self.ddbuttonskin)
            self.dbutton.SetIcon(self.dropdownicon)
        if getattr(self, 'menu', None):
            self.menu.SetSkinKey(self.menuskin)

        if self.Sizer:
            self.Sizer.SetMargins(self.framesize)


    def OnPaint(self, event):
        'Standard painting stuff.'

        dc = AutoBufferedPaintDC(self)
        self.framebg.Draw(dc, RectS(self.Size))

    def OnSize(self,event = None):
        'Resize the subcomponenets to fit when the combo is resized'

        self.Layout()
        self._update_menu_width()

    def OpenMenu(self):
        'Displays menu with correct width and combo as caller'

        self._update_menu_width()
        self.menu.Display(self,False)

    def _update_menu_width(self):
        widths = [self.Size.width]
        if self.minmenuwidth is not None:
            widths.append(self.minmenuwidth)

        self.menu.SetWidth(max(widths))

    def InsertItem(self,index,item):
        """
            Inserts an item the menu at the index
        """
        self.menu.InsertItem(index,item)

    def AppendItem(self, item):
        """
            Adds item to the end of the menu
        """
        self.menu.AppendItem(item)

    def Insert(self, index, *a, **kws):
        """
            Inserts a new item into the menu
        """
        self.menu.Insert(index, *a, **kws)

    def Append(self, *a, **kws):
        """
            Appends a new to the end of the menu
        """
        self.menu.Append(*a, **kws)

    def AppendSeparator(self):
        """
            Adds a separator to the end of the menu
        """
        self.menu.AppendItem(SimpleMenuItem(id=-1))

    def RemoveItem(self,item):
        """
            Removes the givin item from the menu
        """
        self.menu.RemoveItem(item)

    def RemoveAllItems(self):
        'Remove all the items in this combo box.'

        self.menu.SetItems([])

    def SetSelection(self,n):
        self.SetValue(self.menu.spine.items[n])

    def SelectNextItem(self, cycle = False):
        i = self.GetItemIndex(self.Value) + 1

        l = len(self)

        if i >= l:
            if cycle:
                i -= l
            else:
                return

        self.SetSelection(i)



    def SelectPrevItem(self, cycle = False):
        i = self.GetItemIndex(self.Value) - 1

        if not cycle and i<0:
            return

        self.SetSelection(i)

    def SetItems(self, menuitems,selectnow=None):
        self.menu.SetItems(menuitems)

        if selectnow != None and len(self):
            self.SetValue(self.menu.spine.items[selectnow])

    def SetEditable(self, editable):
        self.display.Editable = editable

    def GetEditable(self):
        self.display.Editable

    Editable = property(GetEditable, SetEditable)


    def SetValue(self,value, default=None):
        """
        Sets the value of the textfield to the value
        in typable mode expects a string
        otherwhys expects a ComboMenuItem
        """

        assert threading.currentThread().getName() == 'MainThread'

        self.display.SetValue(value,default)

    def EditValue(self, newvalue = None):
        """
            Show typing field and select all for replacement.
            with newvalue as the value of the field
        """
        self.display.TypeField(newvalue)

    def ChangeValue(self, value, default=None):
        'Changes the value of the textfield without firing an event.'
        self.display.ChangeValue(value, default)

    def GetValue(self):
        'Grabs the value of the display.'

        return self.display.GetValue()

    Value = property(GetValue, SetValue)

    def GetItemIndex(self, item):
        """
            Returns the index of the item
        """
        return self.menu.spine.items.index(item)

    def GetItems(self):
        """
            Returns a list of the SimpleMenuItems in the menu
        """
        return self.menu.spine.items

    def GetSelection(self):
        'Returns the curently selected item.'

        return self.selection

    Selection = property(GetSelection)

    def GetSelectionIndex(self):
        'Returns index of selected items.'

        return self.menu.spine.items.index(self.selection)

    def OnSelection(self,item):
        """
        Item selected 'event'
        calls the Selection Callback if availible
        then throws a EVT_COMBOBOX to parent
        """
        if self.selection is item:
            return
        else:
            self.selection = item

        if isinstance(item,int):
            item = self.menu.spine.items[item]

        self.display.SetFocus()
        self.display.SelectAll()

        if self.selectioncallback:
            self.selectioncallback(item)
        else:
            self.display.SetValue(item)

        event = wx.CommandEvent(10020, self.GetId())
        event.SetInt(try_this(lambda: self.menu.spine.items.index(item), -1))
        self.Parent.AddPendingEvent(event)

    def GetItemBy(self,attr,value):
        """
        Find an item by one of its attribute's values
            Returns first item or None if no matchin items were found
        attr - string naming the atribute
        value - the value you want the atribute of the item to be
        """
        items = self.menu.spine.items
        for item in items:
            if value == getattr(item, attr, None):
                return item

    def GetStringsAndItems(self):
        """
        Returns a list of string,item tuples
        a tuplefor each string in each item
        """
        alist = []
        items = self.menu.spine.items
        for item in items:
            for thing in item.content:
               if isinstance(thing, basestring):
                   alist.append((thing, item))

        return alist


    @property
    def TextField(self):
        return self.display.txtfld

    @property
    def defaultvalue(self):
        return self.display.defaultvalue

ComboDisplayStyle = wx.FULL_REPAINT_ON_RESIZE | wx.NO_BORDER

class ComboDisplay(wx.Window):
    'A sort of un-editable text field with picture support.'

    textfield_style = wx.NO_BORDER | wx.TE_PROCESS_ENTER

    def __init__(self,parent, id=-1, typeable=False, value='',
                 pos = wx.DefaultPosition, size = wx.DefaultSize, empty_text = None, empty_text_hide=True,
                 validator=None, ):
        """
        ComboDisplay constructor.

        value - what is initialy displayed
        """
        wx.Window.__init__(self, parent, id, pos, size, style = ComboDisplayStyle)

        Bind = self.Bind
        Bind(wx.EVT_PAINT,              self.OnPaint)
        Bind(wx.EVT_LEFT_DOWN,          self.OnLDown)
        Bind(wx.EVT_TEXT,               self.OnType)
        Bind(wx.EVT_TEXT_ENTER,         self.OnLoseFocus)
        Bind(wx.EVT_ERASE_BACKGROUND,   lambda e: None)
        Bind(wx.EVT_ENTER_WINDOW,       self.OnMouseEnter)
        Bind(wx.EVT_LEAVE_WINDOW,       self.OnMouseLeave)
        Bind(wx.EVT_MOTION,             self.OnMouseMove)
        Bind(wx.EVT_SIZE,               self.OnSize)

        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        self.value = self.lastvalue = value
        self.defaultvalue = ''
        self.empty_text = empty_text
        self.empty_text_hide = empty_text_hide
        self.hover=False

        if validator is None:
            validator = LengthLimit(20480)

        txt = self.txtfld = wx.TextCtrl(self, -1, style=self.textfield_style, validator=validator)
        txt.Show(False)
        txt.Bind(wx.EVT_KILL_FOCUS, self.OnLoseFocus)
        txt.Bind(wx.EVT_SET_FOCUS,  self.OnType)

        self._enabled = True
        self.Editable = typeable

        self.UpdateSkin()

    def UpdateSkin(self):
        """
            Updates the local skin references to the current values of the parent
        """

        txt, p = self.txtfld, self.Parent
        txt.Font = self.Font = p.Font
        txt.BackgroundColour = wx.Colour(*p.activebg)
        txt.ForegroundColour = wx.Colour(*p.activefc)

        padding = self.Parent.padding
        margins = self.Parent.margins

        txtheight = txt.Font.GetHeight() + txt.Font.Descent

        txt.MinSize = wx.Size(-1,txtheight)
        txt.Size = wx.Size(self.Size.width - (2 * padding.x + margins.x), txtheight)

        self.MinSize = wx.Size(-1, txtheight + margins.y + 2 * padding.y)

        self.Parent.Layout()
        self.Refresh(False)

    def OnSize(self,event=None):
        if event:
            event.Skip()

        txt = self.txtfld
        padding = self.Parent.padding
        margins = self.Parent.margins

        txt.Size = wx.Size(self.Size.width - (2 * padding.x + margins.x), txt.MinSize.height)


    def OnMouseIntoButton(self,event):
        if not self.typeable:
            self.hover = True
            self.Refresh(False)

    def OnMouseOutOfButton(self,event):
        if not self.typeable:
            self.hover=False
            self.Refresh(False)

    def OnMouseEnter(self,event):
        if not self.typeable:
            wx.CallAfter(self.Parent.dbutton.GetHover)
        if not self.HasCapture() and not self.Editable:
            self.CaptureMouse()

        if self.Editable:
            self.SetCursor(wx.StockCursor(wx.CURSOR_IBEAM))

        self.hover = True
        self.Refresh(False)

    def OnMouseMove(self,event):
        rect = RectS(self.Size)
        pos  = self.ScreenToClient(GetMousePosition())

        if not rect.Contains(pos):
            self.OnMouseLeave(event)
        elif not self.hover:
            self.OnMouseEnter(event)

    def OnMouseLeave(self,event):
        if not self.typeable:
            wx.CallAfter(self.Parent.dbutton.ReleaseHover)

        while self.HasCapture():
            self.ReleaseMouse()

        self.hover=False
        self.Refresh(False)
        self.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def Enable(self, val):
        self._enabled = val
        self.Editable = self.Editable # cause a cursor update

    def SetEditable(self, val):
        self.typeable = val
        self.SetCursor(wx.StockCursor(wx.CURSOR_IBEAM if val and self._enabled else wx.CURSOR_DEFAULT))

    def GetEditable(self):
        return self.typeable

    Editable = property(GetEditable, SetEditable)

    def SetValue(self,value, default = None):
        'Set a new display value. Calling the valuecallback'

        assert threading.currentThread().getName() == 'MainThread'

        if default != None:
            self.defaultvalue = default

        self.value = value

        valuestring = ''
        if isinstance(value,basestring):
            valuestring = value
        else:
            for thing in value.content:
                if isinstance(thing, basestring):
                    valuestring = thing
                    break

        if wx.IsDestroyed(self.txtfld):
            return

        self.txtfld.SetValue(valuestring)

        valuecallback = self.Parent.valuecallback
        if valuecallback: wx.CallAfter(valuecallback, valuestring)

        self.Refresh(False)

    def ChangeValue(self, value, default = None):
        'Sets the value without calling any callbacks.'


        if default != None:
            self.defaultvalue = default

        self.value = value
        self.txtfld.ChangeValue(value if isinstance(value, basestring) else value.GetContentAsString())
        self.Refresh(False)

    def SetDisplayLabel(self, text):
        self._displaylabel = text

    def GetDisplayLabel(self):
        text = getattr(self, '_displaylabel', None)
        return text if text is not None else self.value

    DisplayLabel = property(GetDisplayLabel, SetDisplayLabel)

    def SelectAll(self):
        'Select everthing in the text field'

        self.txtfld.SetInsertionPoint(0)
        self.txtfld.SetSelection(-1,-1)

    def GetValue(self):
        'Returns a value'

        return self.value

    def OnPaint(self,event):
        'EVT_PAINT handling'
        dc   = AutoBufferedPaintDC(self)
        rect = RectS(self.Size)

        # draw the background
        background = self.Parent.hoverbg if self.hover else self.Parent.normalbg
        background.Draw(dc, rect)

        margins = self.Parent.margins
        padding = self.Parent.padding

        # Font setup
        font = None
        sp  = self.Parent.menu.spine
        sel = sp.Selection
        if sel > len(sp.items): sel = sp.Selection = -1

        if sel != -1 and sel < len(sp.items) and sel >= 0 and sp.items[sel].font:
            font = sp.items[sel].font
            #font.PointSize=self.Font.PointSize
        else:
            font = self.Font

        dc.Font = font
        color = self.Parent.hoverfc if self.hover else self.Parent.normalfc
        dc.TextForeground = color
        fontHeight = font.Height

        # initial cursor setup

        if self.Parent.ForceTextFieldBackground:
            self.Parent.activebg.Draw(dc,rect)

        label = self.DisplayLabel

        # Draw text if value is just a string
        if isinstance(label, basestring):
            cursor =  Point(rect.x+margins.left+padding.x, margins.top+padding.y)
            if not label and self.empty_text:
                text = self.empty_text
                dc.SetTextForeground(self.Parent.hintfc)
            else:
                text = label

            text_rect = Rect(cursor.x, cursor.y, rect.width - cursor.x - margins.right - padding.x, fontHeight)
            text_rect, text = self.music_note_hack(dc, text_rect, text, fontHeight)
            dc.DrawTruncatedText(text.split('\n', 1)[0], text_rect, alignment = wx.ALIGN_LEFT| wx.ALIGN_TOP)

        # or draw each part of the value
        else:
            cursor =  Point(rect.x+margins.left+padding.x, ((rect.height - margins.top - margins.bottom) / 2)+ margins.top)
            if label is not None:
                for i in label.content:
                    if isinstance(i, Bitmap):
                        dc.DrawBitmapPoint(i, (cursor.x, cursor.y - i.Height/2), True)
                        cursor += Point(i.Width + padding.x, 0)

                    elif isinstance(i, basestring):
                        dc.DrawTruncatedText(i.split('\n', 1)[0], wx.Rect(cursor.x, cursor.y-fontHeight/2, rect.width - cursor.x-margins.right - padding.x, fontHeight), alignment =wx.ALIGN_LEFT| wx.ALIGN_CENTRE_VERTICAL)
                        cursor += Point(dc.GetTextExtent(i)[0] + padding.x, 0)

        # Draw a background for the textfield
        if self.txtfld.Shown:# or self.Parent.ForceTextFieldBackground:
#            dc.Brush = wx.Brush(self.Parent.activebg)
#            dc.Pen   = wx.TRANSPARENT_PEN
#
#            dc.DrawRectangleRect(rect)
            self.Parent.activebg.Draw(dc,rect)

    def music_note_hack(self, dc, text_rect, text, fontHeight):
        if text.startswith(u'\u266b'):
            music_icon = skin.get('appdefaults.icons.notes', None)
            if music_icon:
                icon_rect = wx.Rect(*text_rect)
                icon_rect.y += 2
                music_icon = music_icon.Resized(fontHeight+2).WXB
                music_icon.Draw(dc, icon_rect, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
                text_rect.x += music_icon.Width + 2
                text = text[1:]

        return text_rect, text


    def OnLDown(self, event=None):
        'Clicking to type in the combobox if enabled.'

        if self._enabled:
            if self.txtfld.Shown:
                pass
            elif self.typeable:
                self.TypeField()
            else:
                if len(self.Parent.menu):
                    self.Parent.OpenMenu()

    def TypeField(self, newvalue = None):
        'Show typing field and select all for replacement.'

        #print "TypeField",self.Top.Title,'\n','='*80,'\n','\n'.join(format_stack()),'\n','='*80
        self.lastvalue = self.value
        txt = self.txtfld
        padding = self.Parent.padding
        margins = self.Parent.margins

        txt.Position = wx.Point(padding.x + margins.left, margins.top + padding.y)

        txt.Show(True)
        txt.SetFocus()


        if newvalue is not None:
            self.txtfld.ChangeValue(newvalue)
        self.SelectAll()

        self.Refresh(False)

    def OnType(self,event):
        'Typing Events'

        if self.editmethod:
            self.editmethod()

        event.Id = self.Id
        self.Parent.AddPendingEvent(event)
        self.Refresh(False)

    def OnLoseFocus(self, event):
        'Textfield hides itself when it loses focus.'

        if self.txtfld.Shown:
            event.Id = self.Id
            self.GrandParent.AddPendingEvent(event)

            def fireValue():
                if not self.Parent._menuClick:
                    self.SetValue( self.txtfld.GetValue() )
                else:
                    self.Parent._menuClick = False

            wx.CallAfter(fireValue)
            self.txtfld.Show(False)
            self.Refresh(False)
