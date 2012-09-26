import wx

from gui.uberwidgets.UberButton import UberButton
from gui.uberwidgets.UberCombo import UberCombo
from gui.uberwidgets.simplemenu import SimpleMenuItem
from gui.skin.skinparse import makeFont
from cgui import SimplePanel
from gui.anylists import AnyList
from gui.toolbox import AutoDC

from wx import BoxSizer, BOTTOM, TOP, LEFT, RIGHT, EXPAND, VERTICAL, HORIZONTAL

wxMac = 'wxMac' in wx.PlatformInfo

def PrefCollection(*workers,**options):
    '''
    Build all the components passed in as workers if they ned building and put them in a panel
    '''

    if 'layout' in options:
        layout = options['layout']
    else:
        layout = wx.GridSizer(rows=0,cols=1)

    if 'itemoptions' in options:
        itemoptions = options['itemoptions']
    else:
        itemoptions = (0, EXPAND)

    def Factory(parent, prefix = ''):

        panel       = wx.Panel(parent, style = wx.FULL_REPAINT_ON_RESIZE)
        panel.Sizer = layout
        for workerortuple in workers:

            if isinstance(workerortuple, tuple):
                worker     = workerortuple[0]
                addoptions = workerortuple[1:]
            else:
                worker     = workerortuple
                addoptions = None

            if callable(worker):
                window = worker(panel, prefix)
            elif isinstance(worker, wx.WindowClass):
                window = worker
                window.Reparent(panel)

            panel.Sizer.Add(window, *(addoptions or itemoptions))

        return panel
    return Factory


pref_sizer_style  = EXPAND | LEFT | RIGHT | BOTTOM
combo_sizer_flags = LEFT | RIGHT, 7

if wxMac:
    header_sizer_flags = wx.ALIGN_BOTTOM,
    space_over_header = 3
    space_under_header = 8
else:
    header_sizer_flags = LEFT | wx.ALIGN_CENTER_VERTICAL, 7
    space_over_header = 0
    space_under_header = 5

class PrefPanel(SimplePanel):
    def __init__(self, parent, content=None, title='', buttonlabel='', buttoncb=None, titlemaker=None, prefix=''):
        SimplePanel.__init__(self, parent, wx.FULL_REPAINT_ON_RESIZE)

        sizer = self.Sizer = BoxSizer(VERTICAL)
        self.headersizer = BoxSizer(HORIZONTAL)
        self.bodysizer = BoxSizer(VERTICAL)
        sizer.Add(self.headersizer, 0, EXPAND | TOP, space_over_header)
        sizer.Add(self.bodysizer, 1, EXPAND | TOP, space_under_header)

        self.title      = None
        self.combo      = None
        self.button     = None
        self.content    = None
        self.contents   = {}
        self.titlemaker = titlemaker
        if wxMac:
            self.menuitems = {}

        if title and isinstance(title, basestring):
            self.title = wx.StaticText(self, -1, ' ' + title + ' ', style = wx.ALIGN_CENTER_VERTICAL)

            #need grey backgound behind label on mac to hide the line
            if wxMac:
                self.title.BackgroundColour=wx.Color(232,232,232)
            self.title.Font = self.HeaderFont
            self.headersizer.Add(self.title, 0, *header_sizer_flags)

        if callable(content):
            content = self.content = content(self, prefix)
            self.bodysizer.Add(self.content, 1, pref_sizer_style, 7)
        elif isinstance(content, wx.WindowClass):
            content.Reparent(self)
            self.content = content
            self.bodysizer.Add(self.content, 1, pref_sizer_style, 7)
        elif isinstance(content, list):
            self.SetContents(content)

        if buttoncb:
            self.SetButton(buttonlabel, buttoncb)

        Bind = self.Bind
        Bind(wx.EVT_PAINT, self.OnPaint)

        #darker border if mac so it is visible for now
        if not wxMac:
            self.pen = wx.Pen(wx.Colour(213,213,213))
        else:
            self.pen = wx.Pen(wx.Colour(155,155,155))

    def SetTitle(self, title):
        self.title.SetLabel(title)

    @property
    def HeaderFont(self):
        try:
            return self._headerfont
        except AttributeError:
            if not wxMac:
                PrefPanel._headerfont = makeFont('arial 8 bold')
            else:
                PrefPanel._headerfont = makeFont('9 bold')
            return self._headerfont

    _fg_brush = \
    _bg_brush = \
    _fg_pen = \
    _bg_pen = lambda self: None

    def get_bg_brush(self):
        return self._bg_brush() or wx.WHITE_BRUSH
    def get_fg_brush(self):
        return self._fg_brush() or wx.TRANSPARENT_BRUSH
    def get_bg_pen(self):
        return self._bg_pen() or wx.TRANSPARENT_PEN
    def get_fg_pen(self):
        return self._fg_pen() or self.pen

    bg_brush = property(get_bg_brush)
    fg_brush = property(get_fg_brush)
    bg_pen = property(get_bg_pen)
    fg_pen = property(get_fg_pen)

    def OnPaint(self,event):
        size = self.Size
        dc = AutoDC(self)

        if not wxMac:
            # Non mac: white background, rounded rectangle around controls
            rect = wx.RectS(size)
            dc.Brush = self.bg_brush   #background
            dc.Pen =   self.bg_pen     #background border
            dc.DrawRectangleRect(rect)
            ypos = self.headersizer.Size.height // 2 + space_over_header
            gc = wx.GraphicsContext.Create(dc)
            gc.SetBrush(self.fg_brush)   #foreground
            gc.SetPen(self.fg_pen)     #foreground
            gc.DrawRoundedRectangle(0, ypos, size.width-1, size.height-ypos-1, 5)
        else:
            # Mac: normal grey background, horizontal line above controls
            ypos = self.headersizer.Size.height // 2 + space_over_header + 2
            dc.Pen = self.fg_pen
            button_width = 0 if self.button is None else (self.button.Size.width)
            dc.DrawLine(10, ypos, self.headersizer.Size.width - 10 - button_width, ypos)

        content = self.content
        if isinstance(content, AnyList): # TODO: don't special case
            crect = wx.Rect(*content.Rect)
            crect = crect.Inflate(1, 1)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(self.pen)
            dc.DrawRectangleRect(crect)

    def ChangeShownContent(self, *a):
        if self.content:
            self.content.Show(False)

        if wxMac:
            menu_item = self.menuitems[self.combo.GetStringSelection()]
        else:
            menu_item = self.combo.Value

        self.content = self.contents[menu_item]
        self.content.Show(True)
        self.Layout()

    def SetButton(self,label,callback):
        if self.button:
            self.headersizer.Detach(self.button)
            self.button.Destroy()

        # native button on mac instead of the vista clone button
        if not wxMac:
            self.button = UberButton(self, -1, label, skin = 'AppDefaults.PrefButton')
        else:
            self.button = wx.Button(self, -1, label)
            self.button.SetWindowVariant(wx.WINDOW_VARIANT_SMALL)

        self.button.Bind(wx.EVT_BUTTON, lambda e: callback(self.button))

        self.headersizer.AddStretchSpacer(1)
        self.headersizer.Add(self.button, 0, wx.ALIGN_CENTER_VERTICAL | RIGHT, 7)

    @property
    def MenuItems(self):
        combo = self.combo
        if wxMac:
            return [combo.GetClientData(i) for i in xrange(combo.Count)]
        else:
            return combo.menu.spine.items

    def SetContents(self, content, destroyold = False):
        if destroyold:
            if not self.contents:
                self.content.Destroy()
            for content in self.contents.values():
                content.Destroy()

        # the currently showing pane in a multiple pane pref panel
        if self.content:
            self.content.Show(False)
            self.content = None

        self.bodysizer.Clear()
        contents = self.contents = {}

        titlemaker = self.titlemaker

        if self.combo is None:
            if not wxMac:
                self.combo = UberCombo(self, value='', skinkey='AppDefaults.PrefCombo', valuecallback = self.ChangeShownContent)
            else:
                # use a native ComboBox on mac
                self.combo = wx.ComboBox(self, style = wx.CB_DROPDOWN | wx.CB_READONLY)
                self.combo.Bind(wx.EVT_COMBOBOX, self.ChangeShownContent)
            newcombo = True
        else:
            self.combo.RemoveAllItems()
            newcombo = False

        for object in content:
            if isinstance(object, tuple):
                window, label = object
            elif isinstance(object, wx.WindowClass):
                window = object
                label  = titlemaker(window) if titlemaker else object.Label

            window.Show(False)
            window.Reparent(self)
            assert window.Parent is self
            self.bodysizer.Add(window, 1, pref_sizer_style, 7)

            menuitem = SimpleMenuItem(label)
            contents[menuitem] = window

            if wxMac:
                itemname = menuitem.GetContentAsString()
                self.combo.Append(itemname)
                self.menuitems[itemname] = menuitem
            else:
                self.combo.AppendItem(menuitem)

        if self.combo:
            if wxMac:
                self.combo.SetSelection(0)
                self.ChangeShownContent()
            else:
                self.combo.Value = self.combo[0]

        if self.combo is not None and newcombo:
            self.headersizer.Add(self.combo, 1, *combo_sizer_flags)

