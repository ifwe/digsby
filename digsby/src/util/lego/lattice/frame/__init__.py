import protocols
from peak.events import trellis
from ...blocks import IBindableValue
from ..blocks import IValueListener

class BindingValueListener(protocols.Adapter, trellis.Component):
    protocols.advise(asAdapterForProtocols=[IBindableValue],
                     instancesProvide=[IValueListener])

    def __init__(self, subject):
        protocols.Adapter.__init__(self, subject)
        trellis.Component.__init__(self)
#        self.value_changed()
        self.subject.bind(self.value_changed)

    def value_changed(self):
        self.value = self.get_value()

    def get_value(self):
        return self.subject.value

    value = trellis.make(rule=get_value, writable=True, optional=True, name='value')

class ObservableChangeBindable(trellis.Component):
    def __init__(self, model, *attrs):
        self.model = model
        self.attrs = attrs

    def bind(self, func):
        assert func
        self.func = func
        self.model.add_gui_observer(self.on_change, *self.attrs)

    def unbind(self):
        self.model.remove_gui_observer(self.on_change, *self.attrs)
        del self.func

    def on_change(self, *a, **k):
        self.func()

class ObservableAttrBindable(ObservableChangeBindable):
    protocols.advise(instancesProvide=[IBindableValue])
    def __init__(self, model, attr):
        super(ObservableAttrBindable, self).__init__(model, attr)
        self.attr = attr
    @property
    def value(self):
        return getattr(self.model, self.attr, False)
