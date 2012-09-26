from .observable import ObservableBase
from weakref import WeakValueDictionary
from collections import defaultdict
from traceback import print_exc
from util.primitives.refs import better_ref
from peak.util.imports import whenImported


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
        from wx import PyDeadObjectError
        globals()['PyDeadObjectError'] = PyDeadObjectError
    except ImportError:
        pass
    else:
        globals()['_usingWX'] = True

class PyDeadObjectError(object):
    #must be before whenImported('wx', _setup_usingWX)
    pass
whenImported('wx', _setup_usingWX)

class Linked(object):
    __slots__ = ('dict', 'thread', 'attr', 'ref')
    def __init__(self, dict, thread, attr, ref):
        self.dict  = dict
        self.thread = thread
        self.attr = attr
        self.ref = ref

    def unlink(self):
        links = self.dict._links[self.thread]
        if self.attr in links:
            try:
                links[self.attr].remove(self.ref)
            except ValueError:
                pass

class DictWatcher(object):
    def __init__(self, srcdict, child_callback, *attrs):
        srcdict.add_observer(self.on_dict_changed)
        self.srcdict = srcdict
        self.dictcopy = srcdict.copy()
        self.child_args = [child_callback] + list(attrs)

        # Initial observations.
        for key, child in srcdict.items():
            child.add_observer(*self.child_args)

    def unbind_children(self):
        # Initial observations.
        for key, child in self.srcdict.items():
            child.remove_observer(*self.child_args)

        self.srcdict.clear()
        del self.srcdict

    def on_dict_changed(self, src, attr, old, new):
        if src != getattr(self, 'srcdict', None):
            raise PyDeadObjectError

        new = set(src.keys())
        old = set(self.dictcopy.keys())

        for newkey in (new - old):
            src[newkey].add_observer(*self.child_args)

        for oldkey in (old - new):
            self.dictcopy[oldkey].remove_observer(*self.child_args)

        self.dictcopy = src.copy()


class ObservableDict(dict, ObservableBase):
    'Observable dictionaries inform their observers when their values change.'

    _dict_observers = WeakValueDictionary()

    def __init__(self, *args):
        ObservableBase.__init__(self)
        dict.__init__(self, *args)

    def __setitem__(self, key, val):
        """
        Notifies upon setting a dictionary item.

        >>> def observer(k, old, new): print "%s: %s -> %s" % (k, old, new)
        >>> ages = observable_dict({'john': 35, 'joe': 24, 'jenny': 63})
        >>> ages.add_observer(observer)
        >>> ages['joe'] += 1
        joe: 24 -> 25
        """
        old = self.get(key, None)
        retval = dict.__setitem__(self, key, val)
        self.notify(key, old, val)
        return retval

    def secret_set(self, key, val):
        return dict.__setitem__(self, key, val)

    def remove_dict_observer(self, dict_changed, child_changed):
        watcher = self._dict_observers.pop((dict_changed, child_changed), None)
        if watcher:
            watcher.unbind_children()
            del watcher

    def link(self, key, callback, callnow = True, obj = None, thread = 'gui'):
        """
        Link a key's value to a simple callback, which is called with new
        values when the key changes.
        """
        assert callnow is True or callnow is False

        try:
            links = self._links
        except AttributeError:
            links = self._setup_links()

        try:
            thread_links = links[thread]
        except KeyError:
            thread_links = links[thread] = defaultdict(list)

        if obj is None:
            obj = callback.im_self

        def on_weakref_dead(wref):
            live = []
            for r in thread_links[key]:
                if getattr(r, 'object', None) is wref:
                    r.destroy()
                else:
                    live.append(r)
            thread_links[key][:] = live

        ref = better_ref(callback, cb=on_weakref_dead, obj = obj)
        thread_links[key].append(ref)

        if callnow:
            callback(self[key])

        return Linked(self, thread, key, ref)

    def _setup_links(self):
        links = {}
        object.__setattr__(self, '_links', links)
        assert self._links is links
        self.add_observer(self._link_watcher)

        return links

    def _link_watcher(self, src, attr, old, new):
        for thread_name, callbacks in self._links.items():
            if attr in callbacks:
                def later(cbs=callbacks[attr]):
                    for cb_ref in list(cbs):
                        cb = cb_ref()

                        if cb is None:
                            try:
                                cbs.remove(cb)
                            except ValueError:
                                pass
                        else:
                            try:
                                cb(new)
                            except Exception:
                                print_exc()

                if thread_name == 'gui':
                    wx.CallAfter(later)
                else:
                    assert False


    def clear(self):
        """
        Observers are given a list of all the dictionaries keys, all of it's
        old values, and a list of Nones with length equal to it's previous
        keys.

        >>> def observer(k, old, new): print "%s: %s -> %s" % (k, old, new)
        >>> ages = observable_dict({'john': 35, 'joe': 24, 'jenny': 63})
        >>> ages.add_observer(observer)
        >>> ages.clear()
        ['john', 'joe', 'jenny']: [35, 24, 63] -> [None, None, None]
        """
        keys = self.keys()
        old_vals = [self[k] for k in keys]
        dict.clear(self)
        self.notify()

    def update(self, mapping):
        keys = mapping.keys()
        old_vals = [self.get(k, None) for k in keys]
        new_vals = [mapping.get(k) for k in keys]
        dict.update(self, mapping)
        self.notifyall(keys, old_vals, new_vals)

    def __delitem__(self, key):
        old_val = self[key]
        retval = dict.__delitem__(self, key)
        self.notify(key, old_val, None)
        return retval

    def setdefault(self, k, x=None):
        "a[k] if k in a, else x (also setting it)"
        if k not in self:
            retval = dict.setdefault(self, k, x)
            self.notify(k, None, x)
            return retval
        else:
            return self[k]

    def pop(self, k, x=None):
        "a[k] if k in a, else x (and remove k)"
        if k in self:
            val = self[k]
            dict.pop(self, k, x)
            self.notify(k, val, None)
            return val
        else:
            return x

    def popitem(self):
        "remove and return an arbitrary (key, value) pair"
        k, v = dict.popitem(self)
        self.notify(k, v, None)
        return k, v




observable_dict = ObservableDict
