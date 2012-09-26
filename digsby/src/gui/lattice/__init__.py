from peak.events import trellis
import protocols
import wx
from util.lego.blocks import IBindableValue

class GUIChangeListener(trellis.Component):
    def __init__(self, model):
        self.model = model

    def bind(self, func):
        assert func
        self.func = func
        self.model.Bind(self.evt_type, self.on_change)

    def unbind(self):
        self.model.Unbind(self.evt_type, handler=self.on_change)
        del self.func

    def on_change(self, e):
        self.func()

class ChoiceListener(GUIChangeListener):
    protocols.advise(asAdapterForTypes=[wx.Choice],
                     instancesProvide=[IBindableValue])

    evt_type = wx.EVT_CHOICE

    @property
    def value(self):
        return self.model.GetSelection()

class CheckListener(GUIChangeListener):
    protocols.advise(asAdapterForTypes=[wx.CheckBox],
                     instancesProvide=[IBindableValue])

    evt_type = wx.EVT_CHECKBOX

    @property
    def value(self):
        return self.model.Value
