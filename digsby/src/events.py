'''
events.py

Provides a way for method calls to happen through wxEvent notifications.
'''
from __future__ import with_statement
import wx, pprint, traceback, sys
from threading import currentThread
from weakref import ref

MAINTHREAD_NAME = 'MainThread'

class ThreadsafeGUIProxy(object):
    '''
    Uses wxCallAfter to proxy all method calls to a GUI target if called from
    any thread but the main one.
    '''

    def __init__(self, target):
        self.target = target

    def __getattr__(self, attr):
        '''
        Intercept all undefined method calls, and proxy them via a thread-safe
        InvokeEvent to the GUI.
        '''

        method = getattr(self.target, attr)
        if currentThread().getName() == MAINTHREAD_NAME:
            return lambda *a, **k: method(*a, **k)
        else:
            return lambda *a, **k: wx.CallAfter(method, *a, **k)

from traceback import print_exc

def callevent(e):
    e.ref = None
    try:
        for callAfterCallback, a, k in e._callables:
            try: callAfterCallback(*a, **k)
            except Exception, e:        # no "with traceguard:" for performance
                print_exc()

    except AttributeError:
        e.callable(*e.args, **e.kw)

from wx import GetApp, NewEventType, PyEvent


def CallAfterCombining(callable, *args, **kw):
    'a call after tuned to be a bit faster'

    assert(hasattr(callable, '__call__'))

    app = GetApp()

    try:
        r = app._last
    except AttributeError:
        pass
    else:
        e = r()
        if e is not None and e.ref is r:
            return e._callables.append((callable, args, kw))

    try:
        evt = PyEvent(0, app._CallAfterId)
    except AttributeError:
        id = app._CallAfterId = NewEventType()
        app.Connect(-1, -1, id, callevent)
        evt = PyEvent(0, id)

    evt._callables = [(callable, args, kw)]
    evt.ref = app._last = ref(evt)

    app.AddPendingEvent(evt)
