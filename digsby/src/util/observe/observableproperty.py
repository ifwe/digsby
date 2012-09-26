'''
Properties that notify observers when one of the attributes they depend on
changes.

todo:
 should ObservableProperty just catch attribute accesss? or is explicit better


thanks U{http://users.rcn.com/python/download/Descriptor.htm}
'''
from pprint import pprint
from collections import defaultdict

try:
    sentinel
except NameError:
    class Sentinel(object):
        def __repr__(self):
            return "<Sentinel (%r backup) %#x>" % (__file__, id(self))
    sentinel = Sentinel()

class ObservableMeta(type):
    'Hooks properties up to dependents.'

    def __new__(mcl, name, bases, cdict):
        # Collect all all observable properties
        obsprops = [(k,v) for k,v in cdict.iteritems()
                    if isinstance(v, ObservableProperty)]

        props = cdict['_oprops'] = defaultdict(list)

        for propname, prop in obsprops:
            for hidden_attr in prop.observe:
                props[hidden_attr].append(propname)

        return super(ObservableMeta, mcl).__new__(mcl, name, bases, cdict)

class ObservableProperty(object):
    def __init__(self, fget = None, fset = None, fdel = None, doc = None,
                 observe = sentinel):
        if not all(callable(c) for c in filter(None, [fget, fset, fdel])):
            raise AssertionError('%s %s %s' % (repr(fget), repr(fset), repr(fdel)))
        self.fget, self.fset, self.fdel = fget, fset, fdel
        self.__doc__ = doc

        if observe is sentinel:
            raise ValueError("'observe' keyword argument is required")

        if isinstance(observe, basestring):
            observe = tuple([observe])
        self.observe = observe

    def __get__(self, obj, objtype):
        return self.fget(obj)

    def __set__(self, obj, value):
        self.fset(obj, value)

    def __delete__(self, obj):
        self.fdel(obj)

    def __repr__(self):
        return '<ObservableProperty (%r)>' % self.observe

def main():
    from util.observe import Observable

    class foo(Observable):
        __metaclass__ = ObservableMeta

        def __init__(self):
            Observable.__init__(self)
            self._hidden = 'Hello world'


        def _wikized(self):
            return self._hidden.title().replace(' ','')

        def transmutate(self):
            self.setnotify('_hidden', 'Observable properties sure are fun')

        wikiword = ObservableProperty(_wikized, observe = ('_hidden'))

    f = foo()
    assert hasattr(f, '_oprops')

    def observer(instance, attr, old, new):
        print '%s: %s -> %s' % (attr, old, new)

    f.add_observer(observer, 'wikiword')
    f.transmutate()
    f.setnotify('_hidden','another test')

if __name__ == '__main__':
    main()


'''
the pure python equivalent of 'property'


class Property(object):
    "Emulate PyProperty_Type() in Objects/descrobject.c"

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError, "unreadable attribute"
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError, "can't set attribute"
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError, "can't delete attribute"
        self.fdel(obj)
'''

