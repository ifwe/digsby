'''
Classes for observing property changes on objects.
'''

from __future__ import with_statement
from contextlib import contextmanager
from collections import defaultdict
from util.introspect import funcinfo
from util.primitives.refs import better_ref as ref
from weakref import ref as weakref_ref
from peak.util.imports import whenImported
import sys
import traceback
from threading import currentThread

try:
    sentinel
except NameError:
    class Sentinel(object):
        def __repr__(self):
            return "<Sentinel (%r backup) %#x>" % (__file__, id(self))
    sentinel = Sentinel()

import logging
log = logging.getLogger('observable')


# with wx present, there will be extra event functionality
# CAS: it never would work properly w/o wx, but now it might not work properly
# if wx isn't used somewhere else first.
_usingWX = False
def _setup_usingWX(_mod):
    try:
        import wx
        globals()['wx'] = wx
        from wx import EvtHandler #@UnusedImport
        globals()['EvtHandler'] = EvtHandler
        from wx import PyDeadObjectError #@UnusedImport
        globals()['PyDeadObjectError'] = PyDeadObjectError
    except ImportError:
        pass
    else:
        globals()['_usingWX'] = True

class PyDeadObjectError(object):
    #must be before whenImported('wx', _setup_usingWX)
    pass
whenImported('wx', _setup_usingWX)

class mydefaultdict(defaultdict):
    pass

class ObservableBase(object):
    '''
    Provides plumbing for the observable pattern. You probably don't want to
    subclass this--try Observable instead.
    '''

    observable_attrs = 'observers _observable_frozen class_names _freezecount guimap _flags'.split()

    _observable_frozen = False
    _freezecount = False

    def __init__(self):
        # attribute -> [callbacks]
        s = object.__setattr__

        s(self, 'observers', mydefaultdict(list))
        s(self, '_flags', {})

    def add_observer_callnow(self, callback, *attrs, **options):
        'Like add_observer, except invokes "callback" immediately.'

        self.add_observer(callback, *attrs, **options)

        for attr in attrs:
            val = getattr(self, attr)
            callback(self, attr, val, val)

    def add_observer(self, callback, *attrs, **options):
        '''
        Listen for changes on an object.

        Callback should be a callable with the following signature:

          callback(obj, attr, old, new)

        obj is this object (self), attr is the name of what has changed,
        old is the old value (None if there was no value), and new is
        the new value.
        '''
        assert all(isinstance(a, basestring) for a in attrs)

        if isinstance(getattr(callback, 'im_self', None), EvtHandler) \
            or 'gui_target' in options:

            if not hasattr(self, 'guimap'): object.__setattr__(self, 'guimap', {})

            callback = _wrap_gui_callback(self.guimap,
                                          options.get('gui_target', callback))

        obj = options.get('obj')
        if obj is None:
            obj = getattr(callback, 'im_self', None)

        # when a weakref dies, make sure it is removed from our .observers list.

        try:
            obs = self.observers
        except AttributeError, err:
            raise AttributeError('did you forget to call Observable.__init__ in a subclass? ' + str(err))

        weak_obs = weakref_ref(obs)
        def on_weakref_dead(wref):
            _obs = weak_obs()
            if _obs is not None:
                for a in (attrs or [None]):
                    live = []
                    for r in _obs[a]:
                        if getattr(r, 'object', None) is wref:
                            r.destroy()
                        else:
                            live.append(r)
                    _obs[a] = live

        _cb = ref(callback, on_weakref_dead, obj = obj)

        for a in (attrs or [None]):
            if _cb not in obs[a]:
                obs[a].append(_cb)

    def add_gui_observer(self, callback, *attrs, **_kws):
        cb = lambda *a, **k: wx.CallAfter(callback, *a, **k)
        obj = _kws.get('obj', None)
        if obj is None:
            obj = callback.im_self
        cb._observer_cb = callback
        return self.add_observer(cb, *attrs, **dict(obj=obj))



    def notifyall(self, attrs, olds, vals):
        if self._observable_frozen: return

        kw = {'doNone': False}
        obs     = self.observers
        notify  = self.notify
        livecbs = self._live_callbacks

        for (attr, old, new) in zip(attrs, olds, vals):
            if old != new: #XXX: temp removed
                notify(attr, old, new, **kw)

                for cb, wref in livecbs(None):
                    try: cb(self, None, None, None)
                    except Exception, e:
                        traceback.print_exc()
                        try: obs[None].remove(wref)
                        except ValueError: log.info('notifyall: weak reference (%s) already collected', wref)

    def notify(self, attr = None, old = None, val = None, doNone = True):
        'Subclasses call notify to inform observers of changes to the object.'
        obs     = self.observers
        notify  = self.notify
        livecbs = self._live_callbacks

        if self._observable_frozen or attr == 'observers': return

        checkList = obs.keys() if attr is None else ( [None, attr] if doNone else [attr] )

        # Notify regular object observers (both attribute specific and not)
        for a in checkList:
            for cb, wref in livecbs(a):
                try:
                    cb(self, attr, old, val)
                except PyDeadObjectError, _deade:
                    try:
                        obs[a].remove(wref)
                    except ValueError:
                        log.info('weak reference already collected')
                except Exception, e:
                    print >> sys.stderr, "Error notifying %s" % funcinfo(cb)
                    traceback.print_exc()

                    try:
                        obs[a].remove(wref) # remove the listener
                    except ValueError:
                        # the listener was already removed somehow.
                        log.info('weak reference already collected')

        # Observable property notification
        for obsprop in getattr(self, '_oprops', {}).get(attr, []):
            notify(obsprop, old, val)

    #TODO: remove_observer will not complain if there are no callbacks to
    # remove. perhaps have an optional "strict" flag argument that asserts that
    # the number of observers removed is correct? (assuming of course that
    # nothing was garbage collected.
    def remove_observer(self, callback, *attrs):
        try:
            callback = self.guimap.pop(callback)
        except (AttributeError, KeyError):
            pass

        obs = self.observers

        for a in attrs or [None]:
            for wref in obs[a]:
                ref = wref()
                ref = getattr(ref, '_observer_cb', ref)
                if ref == callback: # b.bar == b.bar, however: b.bar is not b.bar
                    try:
                        obs[a].remove(wref)
                    except ValueError:
                        # this is okay: the weak reference may be invalid by naow
                        # (but log since this should only happen very occasionally and randomly)
                        log.info('weak reference already collected')
                    else:
                        # unbound_ref leaks in some situations; destroy alleviates it
                        if hasattr(wref, 'destroy'):
                            wref.destroy()

    remove_gui_observer = remove_observer

    def _live_callbacks(self, attr):
        "Returns all callback objects which haven't been garbage collected."

        try:
            obs = self.observers
        except AttributeError, err:
            raise AttributeError('Did you forget to call an Observable init? ' + err)

        live = []
        retval = []
        for wref in obs[attr]:
            obj = wref()
            if obj is not None:
                live.append(wref)
                retval.append((obj, wref))

        # don't keep references to dead weakrefs
        obs[attr][:] = live

        return retval

    @contextmanager
    def change_group(self):
        self.freeze()
        try:
            yield self
        finally:
            self.thaw()

    frozen = change_group

    def freeze(self):
        if self._freezecount == 0:
            assert self._observable_frozen == False
            object.__setattr__(self, '_observable_frozen', True)
        self._freezecount += 1

        assert self._freezecount >= 0

    def thaw(self):
        self._freezecount -= 1

        if self._freezecount == 0:
            assert self._observable_frozen != False
            self._observable_frozen = False

            self.notify()

        assert self._freezecount >= 0

    def thaw_silent(self):
        self._freezecount -= 1

        if self._freezecount == 0:
            assert self._observable_frozen != False
            self._observable_frozen = False

        assert self._freezecount >= 0

    @contextmanager
    def silent(self):
        self.freeze()
        try:
            yield self
        finally:
            self.thaw_silent()

    @contextmanager
    def flagged(self, flags):
        '''flags will be passed as the value of attr in any notify calls
           in this context and on this thread.'''
        t = currentThread()
        self._flags[t] = flags
        yield
        self._flags.pop(t, None)

    def isflagged(self, flags):
        t = currentThread()
        curflags = self._flags.get(t, sentinel)
        return (curflags is not sentinel and curflags == flags)


class Observable(ObservableBase):
    '''
    Notifies observers of any attribute changes.

    >>> foo = Observable()
    >>> def observer(attr, old, new): print '%s: %s -> %s' % (attr, old, new)
    >>> foo.add_observer(observer)
    >>> foo.bar = 'kelp'
    bar: None -> kelp
    '''
    _osentinel = Sentinel()

    def setnotify(self, attr, val):
        'Sets an attribute on this object, and notifies any observers.'

        old = getattr(self, attr, None)
        object.__setattr__(self, attr, val)
        self.notify(attr, old, val)

    def setnotifyif(self, attr, val):
        '''
        If val is different than this object's current value for attr, then
        the attribute is set and any observers are notified.
        '''

        if getattr(self, attr, self._osentinel) == attr:
            return False
        else:
            self.setnotify(attr, val)
            return True

    def link(self, attrname, callback, callnow = True):
        """
        Link an attribute's value to a simple callback, which is called with new
        values when the attributes' value changes.
        """
        options = {}
        if _usingWX and isinstance(getattr(callback, 'im_self', None), EvtHandler):
            options['gui_target'] = callback

        self.add_observer(lambda src, attr, old, new: callback(new), attrname,
                          **options)

        if callnow:
            callback(getattr(self, attrname))

class notifyprop(object):
    def __init__(self, name):
        self.name = name
        self.privname = '_autoprop_' + name

    def __get__(self, obj, objtype = None):
        try:
            return getattr(obj, self.privname)
        except:
            import sys, pprint
            print >>sys.stderr, pprint.pformat(vars(obj))
            raise

    def __set__(self, obj, val):
        n = self.privname
        old = getattr(obj, n, None)
        object.__setattr__(obj, n, val)
        obj.notify(self.name, old, val)



def _wrap_gui_callback(guimap, func):
    'Uses "AddPendingEvent" to call a function later on the GUI thread.'

    try:
        return guimap[func]
    except KeyError:
        pass

    evtH = func.im_self

    def wrap(*a, **kws):
        try:
            # getting any attribute on a dead WX object raises PyDeadObjectError
            getattr(evtH, '__bogusattributeXYZ123__', None)
        except PyDeadObjectError:
            # if its dead, remove this callback
            guimap.pop(func, None)
        else:
            # otherwise call it on the GUI thread.
            wx.CallAfter(func, *a, **kws)

    wrap.im_self = func.im_self

    guimap[func] = wrap
    return wrap

if __name__ == '__main__':
    #import doctest
    #doctest.testmod(verbose=True)

    class A(Observable):
        state = notifyprop('state')

    a = A()

    def foo(self, *a): print a
    a >> "state" >> foo

    a.state = 'online'
