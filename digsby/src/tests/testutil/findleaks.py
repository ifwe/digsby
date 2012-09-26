import gc
import sys
import weakref

def _enable_gc(val):
    if val: gc.enable()
    else:   gc.disable()

class gc_enabled(object):
    '''
    a context manager that temporarily enables or disables garbage collection
    '''

    def __init__(self, enabled=True):
        self.enabled = enabled

    def __enter__(self):
        self.originally_enabled = gc.isenabled()
        _enable_gc(self.enabled)

    def __exit__(self, *a):
        _enable_gc(self.originally_enabled)

def check_collected(func):
    '''
    Decorates func, and checks that the return value of func is collected.
    '''

    obj = func()
    assert obj is not None, "function given to check_collected must return a value"

    if isinstance(obj, tuple):
        # don't use [a for a ...] syntax here, since it leaks a "magic" local
        # like _[1] and the last item in the list won't be collected
        weakobjs = list(weakref.ref(o) for o in obj)
    else:
        weakobjs = [weakref.ref(obj)]

    del obj

    gc.collect()

    for weakobj in weakobjs:
        if weakobj() is not None:
            refs = '\n'.join('    %r' % r for r in gc.get_referrers(weakobj()))
            raise AssertionError('In function %r, %s has %d references:\n%s' %
                                 (func.__name__, repr(weakobj()), sys.getrefcount(weakobj()), refs))

