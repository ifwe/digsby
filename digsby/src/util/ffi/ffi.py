'''

Foreign function interface utility.

'''

import ctypes, sys
from ctypes import Structure, byref, sizeof

__all__ = ['Struct', 'cimport']

class Struct(Structure):
    '''
    Like ctypes.Structure but with
     - an __init__ that accepts both args and kwargs
     - a __repr__ showing all fields and their values
     - a ptr property returning a ctypes.byref
     - a __len__ returning ctypes.sizeof
    '''

    def __init__(self, *a, **k):
        cls = type(self)
        fields = getattr(cls, '_fields_', None)

        if fields is None:
            raise AssertionError('ctypes.Structure must have _fields_')

        a = a + (0,) * (len(fields) - len(a))

        # initialize all elements with 0, *args, or **kwargs
        for i, (name, native_type) in enumerate(fields):
            setattr(self, name, k.pop(name, a[i]))

        if k:
            raise ValueError('not defined in _fields_: %s' % ', '.join(k))

    def __repr__(self):
        vals = ' '.join('%s=%s' % (name, getattr(self, name)) for name, t in self._fields_)
        return '<%s %s>' % (type(self).__name__, vals)

    @property
    def ptr(self):
        return byref(self)

    def __len__(self):
        return sum(sizeof(t) for name, t in self._fields_)


import os

def cimport(**k):
    '''
    Imports functions from DLLs.

    >>> cimport(user32 = ['ShowWindow', 'SetWindowPos'])
    >>> ShowWindow(hwnd)
    '''
    
    if os.name == 'nt':
        platform_dlls = ctypes.windll
        G = sys._getframe(1).f_globals
        for name, funcs in k.iteritems():
            dll = getattr(platform_dlls, name)
            G.update((func, getattr(dll, func)) for func in funcs)
    else:
        import gui.native
        gui.native.notImplemented()
