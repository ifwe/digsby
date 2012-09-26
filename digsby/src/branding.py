import hooks
import sys
import traceback

def get(hook_name, impl_default, default, *a, **k):
    impl = getattr(sys, 'BRAND', impl_default) or impl_default
    try:
        k.update(impl=impl)
        vals = list(hooks.each(hook_name, *a, **k))
    except Exception:
        traceback.print_exc()
    else:
        if vals:
            return vals[0]
    return default
