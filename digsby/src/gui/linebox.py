'''
Surrounds a panel with lines and a label.

Use like a wxPanel, specify label in the constructor.

>>> f = wx.Frame(None)
>>> box = LineBox(f, label = 'My Controls')
>>> button = wx.Button(box, -1, 'Push')
'''

import wx, gui



class LineBox(wx.Panel):
    border = 30

    def __init__(self, parent, id = -1, label = '', **kws):
        wx.Panel.__init__(self, parent, id, **kws)
        self.label_pos = wx.Point(25, 5)
        self.padding = wx.Size(5, 5)

        self.Sizer = sz = wx.BoxSizer(wx.VERTICAL)
        if isinstance(label, basestring):
            self.set_label(wx.StaticText(self, -1, label))

        self.BackgroundColour = wx.WHITE

        self.BBind(PAINT = self.on_paint,
                   SIZE  = self.on_size,)

        self.color1, self.color2 = wx.BLACK, wx.WHITE

        self.on_size()

    def on_size(self, e = None):
        sz = self.Size

        y = self.label.Size.height + self.label_pos.y + self.padding.height
        self.lines = [ ((self.label_pos.x - self.padding.width, 0, 2, sz.height), wx.SOUTH),
                       ((0, y, sz.width, 2), wx.EAST)   ]
        if e: e.Skip()

    def set_label(self, label):
        if hasattr(self, 'label') and self.label:
            self.label.Destroy()

        self.label = label
        sz = label.MinSize

        self.Sizer.AddSpacer(self.label_pos.y)
        s = wx.BoxSizer(wx.HORIZONTAL)
        s.AddSpacer(self.label_pos.x)
        s.Add(label)
        self.Sizer.Add(s)

    def on_paint(self, e):
        dc = wx.PaintDC(self)
        for rect, direction in self.lines:
            dc.GradientFillLinear(rect, self.color1, self.color2, direction)
        e.Skip(True)

    def Add(self, control):
        self.Sizer.Add(control, 1, wx.EXPAND | wx.WEST , self.border)


class LineBoxOld(wx.Panel):
    def __init__(self, parent, id = -1, label = '', **kws):
        wx.Panel.__init__(self, parent, id, **kws)
        self.label = label

        self.BBind(PAINT = self.on_paint,
                   SIZE  = self.on_size,
                   ERASE_BACKGROUND = lambda e: None)

        self.lines  = []
        self.color1 = wx.BLACK
        self.color2 = wx.WHITE
        self.center = wx.Point(20, 20)
        self.margin = 10
        self.BackgroundColour = wx.WHITE

    def on_size(self, e = None):
        extra = 10
        linewidth = 2

        # Resize the lines
        self.lines = [ (wx.Rect(self.center.x - extra, self.center.y,
                                self.Size[0], linewidth), wx.EAST),
                       (wx.Rect(self.center.x, self.center.y - extra,
                                linewidth, self.Size[1]), wx.SOUTH)]

        children = self.GetChildren()
        assert len(children) == 1
        panel = children[0]
        r = self.Rect
        xoff, yoff = self.center.x + self.margin, self.center.y + self.margin
        panel.Rect = wx.Rect(r.x + xoff, r.y + yoff,
                             r.Width - xoff, r.Height - yoff)


        size = wx.Size(*panel.Sizer.MinSize) + wx.Size(*self.center) + (10,10)
        self.SetMinSize( size )
        self.Refresh()

    def on_paint(self, e):
        dc = wx.AutoBufferedPaintDC(self)

        # if 'wxMac' not in wx.PlatformInfo:
        dc.Brush = wx.WHITE_BRUSH
        dc.Pen = wx.TRANSPARENT_PEN
        dc.DrawRectangle(*self.Rect)

        font = wx.SystemSettings.GetFont( wx.SYS_DEFAULT_GUI_FONT )
        font.Weight = wx.FONTWEIGHT_BOLD
        dc.Font = font
        dc.DrawText(self.label, self.center.x + 6, self.center.y - 15)

        for line in self.lines:
            rect, direction = line
            dc.GradientFillLinear(rect, self.color1, self.color2, direction)

def buildbox(parent, box_dict):
    label = box_dict.keys()[0]

    linebox = wx.StaticBox(parent, -1, label)
    sz = wx.StaticBoxSizer(linebox, wx.VERTICAL)

    for pref in box_dict[label]:
        if isinstance(pref, (str, unicode)):
            # Checkbox
            check = wx.CheckBox(parent, label = pref)
            sz.Add(check, flag = wx.ALL, border = 3)
        elif isinstance(pref, dict):
            k = pref.keys()[0]
            if k == 'custom':
                v = pref.values()[0]
                control = globals()['prefs_' + v.replace(' ', '_')](parent)
                sz.Add(control, flag = wx.ALL, border = 3)
    return sz



if __name__ == '__main__':
    app = wx.PySimpleApp()
    f = wx.Frame(None, -1, 'Linebox Test')

    sizer = wx.BoxSizer(wx.VERTICAL)
    box = LineBox(f, label = 'Test Preference Group')

    grid = wx.GridSizer(2,2)
    grid.Add(wx.Button(box, -1, 'one'))
    grid.Add(wx.Button(box, -1, 'two'))
    grid.Add(wx.Button(box, -1, 'three'))
    grid.Add(wx.Button(box, -1, 'four'))
    box.Add(grid)


    sizer.Add(box, 1, wx.EXPAND)

    f.SetSizer(sizer)
    f.Show(True)
    app.MainLoop()