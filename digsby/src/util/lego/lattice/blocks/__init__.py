import protocols
from peak.events import trellis

class IValueListener(protocols.Interface):
    value = trellis.attr()
