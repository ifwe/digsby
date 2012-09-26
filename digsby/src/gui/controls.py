'Easy gui.'

import wx

def Button(parent, text, callback, **kwargs):
    button = wx.Button(parent, -1, _(text), **kwargs)
    button.Bind(wx.EVT_BUTTON, lambda *e: callback())
    return button

def Text(parent, text, *args, **kwargs):
    return wx.StaticText(parent, -1, text, *args, **kwargs)

def CheckBox(parent, text, value = sentinel, **kwargs):
    checkbox = wx.CheckBox(parent, -1, _(text), **kwargs)
    if value is not sentinel:
        checkbox.Value = value
    return checkbox

def TextInput(parent, value = sentinel, *args, **kwargs):
    textctrl = wx.TextCtrl(parent, -1, *args, **kwargs)
    if value is not sentinel:
        textctrl.Value = value
    return textctrl


def BoxSizer(type, *elems, **opts):
    s = wx.BoxSizer({'H': wx.HORIZONTAL,
                        'V': wx.VERTICAL}[type])

    border = opts.get('border', 6)
    return add_all(elems, s, border)

def add_all(elems, s, border):
    for elem in elems:
        if elem == 'stretch': s.AddStretchSpacer()
        else:
            s.Add(elem, 0, wx.ALL | wx.EXPAND, border)
    return s

def HSizer(*elems, **opts):
    return BoxSizer('H', *elems, **opts)

def VSizer(*elems, **opts):
    return BoxSizer('V', *elems, **opts)

def FGridSizer(rows, cols, *elems, **opts):
    s = wx.FlexGridSizer(rows, cols, vgap=opts.get('vgap', 0), hgap=opts.get('hgap', 0))
    border = opts.get('border', 6)
    add_all(elems, s, border)
    return s

class CustomControls(object):
    def __init__(self, parent):
        self.parent = parent

    class _TextInput(wx.TextCtrl):
        def __init__(self, controls, parent, value = sentinel, get_=None, set_=None, *args, **kwargs):
            self.controls = controls
            self.get_ = get_
            self.set_ = set_
            wx.TextCtrl.__init__(self, parent, -1, *args, **kwargs)

        def GetValue(self):
            return self.get_(wx.TextCtrl.GetValue(self)) if self.get_ is not None else wx.TextCtrl.GetValue(self)
        def SetValue(self,x):
            return wx.TextCtrl.SetValue(self, self.set_(x)) if self.set_ is not None else wx.TextCtrl.SetValue(self, x)
        Value = property(GetValue, SetValue)

    def TextInput(self, *a, **k):
        return self._TextInput(self, parent = self.parent, *a, **k)

    def LabeledTextInput(self, label, *a, **k):
        label_ = Text(self.parent, label)
        text = self.TextInput(*a, **k)
        return label_, text

    def intBox(self, *a, **k):
        return self.TextInput(get_=int, set_=str)

class RadioPanel(wx.BoxSizer):
    'Radio button group without a surrounding box.'

    def __init__(self, parent, choices, clique = None):
        wx.BoxSizer.__init__(self, wx.VERTICAL)
        self.Buttons = []

        for i, choice in enumerate(choices):
            b = wx.RadioButton(parent, -1, choice)
            b.Bind(wx.EVT_RADIOBUTTON,
                   lambda e, i=i: setattr(self, 'Value', i))
            self.Buttons.append(b)
            if clique is not None: clique.add(b)
            self.Add(b, 0, wx.ALL, b.GetDefaultBorder())

    def GetValue(self):
        return self.Value

    def SetValue(self, val):
        val = int(val) if val != '' else 0
        self.Buttons[val].SetValue(True)
        self.Value = val
