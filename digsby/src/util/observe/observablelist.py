from .observable import ObservableBase
from util.introspect import decormethod
import sys
from logging import getLogger; log = getLogger('observablelist')

try:
    sentinel
except NameError:
    class Sentinel(object):
        def __repr__(self):
            return "<Sentinel (%r backup) %#x>" % (__file__, id(self))
    sentinel = Sentinel()

def list_notify(f):
    def wrapper1(self, *args, **kw):
        old_list = self[:]
        val = f(self, *args,**kw)
        self.notify('list', old_list, self)
        return val
    return wrapper1

class ObservableList(list, ObservableBase):
    "A list you can register observers on."

    def __init__(self, *args):
        ObservableBase.__init__(self)
        list.__init__(self, *args)
        self._observable_frozen = False
        self._freezecount = 0

    @decormethod
    def notify_wrap(self, func, *args, **kw):
        """
        Methods decorated with notify_wrap make a copy of the list before the
        operation, then notify observers of the change after. The list itself,
        the old list, and the new list are sent as arguments.
        """
        val = func(self, *args,**kw)
        if not self._observable_frozen:
            self.notify('list', None, self)
        return val

    def add_list_observer(self, list_changed, child_changed, *attrs, **kwargs):
        ch = kwargs.get('childfunc', lambda child: child)


        # Sanity check -- this list must be holding Observable children
        if getattr(sys, 'DEV', False):
            for child in [ch(c) for c in self]:
                if not hasattr(child, 'add_observer'):
                    raise TypeError("This list has non observable children")

        class ListWatcher(object):
            def __init__(self, srclist, list_callback, child_callback, *attrs, **kwargs):
                self.srclist = srclist
                self.listcopy = set(srclist)
                srclist.add_observer(self.on_list_changed, **kwargs)

                self.list_callback = list_callback
                self.child_args = [child_callback] + list(attrs)
                self.child_kwargs = dict(kwargs)

                # Initial observations.
                for child in [ch(c) for c in srclist]:
                    child.add_observer(*self.child_args, **self.child_kwargs)

            def on_list_changed(self, src, attr, old, new):
#                if not hasattr(src, 'srclist'):
#                    print >> sys.stderr, 'WARNING: observablelist.on_list_change not unlinked'
#                    return

                assert src is self.srclist

                new = set(src)
                old = self.listcopy

                chargs = self.child_args
                kwargs = self.child_kwargs
                for newchild in (new - old):
                    ch(newchild).add_observer(*chargs, **kwargs)

                for oldchild in (old - new):
                    ch(oldchild).remove_observer(*chargs, **kwargs)

                self.listcopy = new

            def disconnect(self):
                chargs, kwargs = self.child_args, self.child_kwargs
                for child in self.srclist:
                    child.remove_observer(*chargs)

                self.srclist.remove_observer(self.on_list_changed)
                self.srclist.remove_observer(self.list_callback)
                self.__dict__.clear()

                self.disconnect = self.disconnect_warning

            def disconnect_warning(self):
                log.critical('calling ListWatcher.disconnect more than once')

        # Inform of list structure changes
        if list_changed is not None:
            self.add_observer(list_changed, **kwargs)

        # Inform of list children changes
        # call .disconnect on this object when finished.
        return ListWatcher(self, list_changed, child_changed, *attrs, **kwargs)

    def remove_list_observer(self, list_changed, child_changed, *attrs):
        if list_changed is not None:
            self.remove_observer(list_changed)

    #TODO: uncruft this with some metaclass magic

    @notify_wrap
    def __setitem__(self, i, v): return list.__setitem__(self, i, v)
    @notify_wrap
    def __delitem__ (self,key): return list.__delitem__(self, key)
    @notify_wrap
    def __setslice__ (self, i, j, seq): return list.__setslice__(self, i, j, seq)
    @notify_wrap
    def __delslice__(self, i, j): return list.__delslice__(self, i, j)
    @notify_wrap
    def append(self, elem): return list.append(self, elem)

    @notify_wrap
    def pop(self, i = sentinel):
        if i is not sentinel:
            return list.pop(self, i)
        else:
            return list.pop(self)

    @notify_wrap
    def extend(self, seq): return list.extend(self, seq)
    @notify_wrap
    def insert(self, i, elem): return list.insert(self, i, elem)
    @notify_wrap
    def remove(self, elem): return list.remove(self, elem)
    @notify_wrap
    def reverse(self): return list.reverse(self)
    @notify_wrap
    def sort(self, *a, **k): return list.sort(self, *a, **k)
    @notify_wrap
    def __iadd__(self, item): return list.__iadd__(self, item)

observable_list = ObservableList

if __name__ == '__main__':
    from util.observe.observable import Observable
    class Buddy(Observable):
        def __init__(self, name, status = 'online'):
            Observable.__init__(self)
            self.name = name; self.status = status

        def __repr__(self): return '<Buddy %s (%s)>' % (self.name, self.status)

    buddies = ObservableList([Buddy(n) for n in 'Bobby Barbera Betty Ben'.split()])

    def buddy_list_changed(src, attr, old, new):
        print 'The buddylist changed. New list is %r' % new

    def buddy_attr_changed(src, attr, old, new):
        print 'Buddy %r changed %s from %s to %s' % (src, attr, old, new)

    buddies.add_list_observer(buddy_list_changed, buddy_attr_changed)

    print 'Original list', buddies
    b = buddies[2]
    b.setnotify('status', 'away')
    del buddies[2]

    b.setnotify('status', 'online') # should not notify
