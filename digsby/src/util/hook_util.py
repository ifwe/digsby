from .primitives.error_handling import with_traceback
from .primitives.funcs import Delegate
from .primitives.synchronization import lock
from peak.util.addons import AddOn
from peak.util.plugins import Hook
import threading

class OneShotHook(AddOn):
    '''
    instantiates delegates bound to the constructor arguments, and will only
    call each function registered once, even if the hook is called again.
    This should mean a maximum of 1 delegate per hook per constructor argument,
    instead of endlessly registering more functions.  Upon creation of a more complete
    signaling system, this should get replaced.

    Intended to be used with the DigsbyProfile object, for hooks that we'd like to register
    for that object.
    '''

    def __init__(self, subject, group, impl=None):
        self.subject = subject
        self.group = group
        self.impl = impl
        self.delegate = Delegate()
        self._lock = threading.RLock()
        self.registered = False
        self.fired = False

    @lock
    def check_registered(self):
        if not self.registered:
            self.registered = True
            Hook(self.group, self.impl).register(self.call_and_clear)

    @lock
    def __call__(self, func, if_not_fired=False):
        if not (if_not_fired and self.fired):
            self.delegate += lambda *a, **k: with_traceback(func, *a, **k)
            self.check_registered()
            return True
        return False

    @lock
    def call_and_clear(self, *a, **k):
        self.delegate.call_and_clear(*a, **k)
        self.fired = True
