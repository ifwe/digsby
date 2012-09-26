from __future__ import with_statement

from peak.util.plugins import Hook
import traceback

__all__ = ['register', 'reduce']

def register(hook_identifier, cb, impl=None):
    return Hook(hook_identifier, impl).register(cb)

# XXX: isn't this actually foldl ?
def reduce(hook_identifier, arg, *args, **kwargs):
    '''
    Passes arg to the first Hook found for hook_identifier. The return value
    of that hook goes to the next hook, and so on. The return value of the
    last Hook becomes the return value of this function.
    '''
    raise_exceptions = kwargs.pop('raise_exceptions', False)
    impls = kwargs.pop('impls', [kwargs.pop('impl', None)])
    for impl in impls:
        for hook in Hook(hook_identifier, impl):
            if raise_exceptions:
                arg = hook(arg, *args, **kwargs)
            else:
                try:
                    arg = hook(arg, *args, **kwargs)
                except Exception:
                    traceback.print_exc()
    return arg

def notify(hook_identifier, *a, **k):
    for res in each(hook_identifier, *a, **k):
        pass

def each(hook_identifier, *a, **k):
    impls = k.pop('impls', [k.pop('impl', None)])
    for impl in impls:
        for hook in Hook(hook_identifier, impl):
            try:
                yield hook(*a, **k)
            except Exception:
                traceback.print_exc()

def first(hook_identifier, *a, **k):
    impls = k.pop('impls', [k.pop('impl', None)])
    raise_exceptions = k.pop('raise_hook_exceptions', False)

    for impl in impls:
        for hook in Hook(hook_identifier, impl = impl):
            try:
                v = hook(*a, **k)
                if v is not None:
                    return v
            except Exception:
                if raise_exceptions:
                    raise

                traceback.print_exc()

    return None

builtin_any = any
def any(hook_identifier, *a, **k):
    return builtin_any(each(hook_identifier, *a, **k))
