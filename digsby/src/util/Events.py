from primitives.funcs import Delegate
from logging import getLogger
log = getLogger('events')

class Veto(object):
    pass

class BadEventException(Exception):
    pass

class EventMixin(object):
    events = set()

    def __init__(self):
        if not hasattr(self, 'handlers'):
            self.handlers = {}
            self.clear()

    def bind(self, ename, callback):
        assert callable(callback), ("%r is not callable!" % callback)
        #log.log(1, 'bind(%r, %r) to %r', ename, callback, self)
        self.handlers[ename] += (callback)

    bind_event = bind

    def event(self, ename, *args, **kw):
        if ename not in self.events:
            raise BadEventException(type(self).__name__, ename, self.events)

        if self.handlers[ename]:
            #log.log(1, 'event: calling %r%r. handlers are: %r', ename, args, self.handlers[ename])
            self.handlers[ename](*args, **kw)
        else:
            #log.log(1, 'event: %r%r has no handlers', ename, args)
            pass

    def unbind(self, ename, callback):
        #log.log(1, 'unbind(%r, %r) from %r', ename, callback, self)
        if self.handlers[ename]:
            try:
                self.handlers[ename] -= callback
            except ValueError:
                # Already gone from the list.
                pass

    unbind_event = unbind

    def clear(self):
        #log.log(1, 'clearing all event handlers from %r', self)
        for evtname in self.events:
            self.handlers[evtname] = Delegate()

    def __getattr__(self, attr):
        if attr in self.events:
            return self.handlers[attr]
        else:
            return object.__getattribute__(self, attr)

def event(f):
    import functools

    @functools.wraps(f)
    def wrapper(self, *a, **k):

        name = f.func_name
        retval = f(self, *a, **k)

        if retval is Veto or isinstance(retval, Veto):
            return
        elif isinstance(retval, tuple):
            self.event(name, *retval)
        elif retval not in (None, sentinel):
            self.event(name, retval)
        elif retval is None:
            self.event(name, *a, **k)

    return wrapper

