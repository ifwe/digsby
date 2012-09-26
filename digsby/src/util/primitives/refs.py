from weakref import ref, ref as weakref_ref
import new
import traceback

def better_ref(method, cb = None, obj = None):
    if obj is None:
        return bound_ref(method, cb)
    else:
        return unbound_ref(obj, method, cb)

class ref_base(object):
    def maybe_call(self, *a, **k):
        try:
            o = self()
            if o is not None:
                return o(*a, **k)
        except Exception:
            traceback.print_exc()

class bound_ref(ref_base):
    def __init__(self, method, cb = None):
        from util.introspect import funcinfo
        assert hasattr(method, 'im_self'), 'no im_self: %s' % funcinfo(method)

        self.object = weakref_ref(method.im_self, cb)
        self.func   = weakref_ref(method.im_func)
        self.cls    = weakref_ref(method.im_class)

    def __call__(self):
        obj = self.object()
        if obj is None: return None

        func = self.func()
        if func is None: return None

        cls = self.cls()
        if cls is None: return None

        return new.instancemethod(func, obj, cls)

class unbound_ref(ref_base):
    def __init__(self, obj, method, cb = None):
        self.object = weakref_ref(obj, cb)
        self.func   = weakref_ref(method)

        try:
            unbound_cbs = obj._unbound_cbs
        except AttributeError:
            obj._unbound_cbs = unbound_cbs = {}

        unbound_cbs[self] = method

    def __call__(self):
        try:
            obj, func = self.object(), self.func()
        except AttributeError:
            pass
        else:
            if obj is not None and func is not None:
                return func

    def destroy(self):
        obj = self.object()
        if obj is not None:
            try:
                obj._unbound_cbs.pop(self, None)
            except AttributeError:
                pass

        del self.object
        del self.func

    def __repr__(self):
        try:
            from util import funcinfo
            f_info = funcinfo(self.func())
        except Exception, e:
            f_info = '(unknown)' 
        
        try:
            o_info = self.object()
        except Exception, e:
            o_info = '(unknown)'
        return '<unbound_ref to %s, obj is %r>' % (f_info, o_info)

better_ref_types = (bound_ref, unbound_ref)

class stupidref(ref):
    def __getattr__(self, attr):
        return getattr(self(), attr)

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
