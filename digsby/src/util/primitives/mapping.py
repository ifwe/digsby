import funcs
import functional
import itertools
from UserDict import DictMixin

try:
    sentinel
except NameError:
    class Sentinel(object):
        def __repr__(self):
            return "<Sentinel (%r backup) %#x>" % (__file__, id(self))
    sentinel = Sentinel()

def fmt_to_dict(delim1, delim2):
    class dictifier(dict):
        def __init__(self, *a, **k):
            if a and isinstance(a[0], basestring):
                dict.__init__(self, self.parse(a[0]), *a[1:],**k)
            else:
                dict.__init__(self, *a, **k)

        @classmethod
        def parse(cls, s):
            pairs = list(entry.strip().split(delim2,1) for entry in s.split(delim1))
            if len(pairs[-1]) == 1 and pairs[-1][0].strip() == '':
                pairs = pairs[:-1]

            return pairs

        def __str__(self):
            return delim1.join(delim2.join(i) for i in self.items())

    return dictifier

def dictreverse(mapping):
    """
        >>> dictreverse({1: 2, 3: 4})
        {2: 1, 4: 3}
    """
    return dict((value, key) for (key, value) in mapping.iteritems())

def dictadd(dict_a, dict_b):
    """
    Returns a dictionary consisting of the keys in `a` and `b`.
    If they share a key, the value from b is used.

        >>> dictadd({1: 0, 2: 0}, {2: 1, 3: 1})
        {1: 0, 2: 1, 3: 1}
    """
    result = dict(dict_a)
    result.update(dict_b)
    return result

def dictsub(a, b):
    '''
    >>> dictsub({3: 'three', 4: 'four', 5: 'five'}, {4: 'foo'})
    {3: 'three', 5: 'five'}
    '''
    a = a.copy()
    for key in b: a.pop(key, None)
    return a

def dictdiff(defaults, user):
    '''
    >>> dictdiff({3: 'three', 4: 'four', 5: 'five'}, {3: 'three', 4: 'foo', 5: 'five'})
    {4: 'foo'}
    '''
    diff = {}
    for k, v in user.iteritems():
        if k not in defaults or v != defaults[k]:
            diff[k] = v

    return diff

def intdictdiff(start, end):
    '''
    >>> intdictdiff({'a': 3, 'b': 4, 'c': 5}, {'a': 2, 'c': 6, 'd': 2})
    {'a': -1, 'c': 1, 'b': -4, 'd': 2}
    '''
    keys = set(start.keys()) | set(end.keys())
    out = {}
    for key in keys:
        startval = start.get(key, 0)
        endval   = end.get(key, 0)
        outval   = endval - startval
        if outval:
            out[key] = outval

    return out

class DictChain(functional.AttrChain,dict):
    def __init__(self,*args,**kwargs):
        dict.__init__(self,*args,**kwargs)
        functional.AttrChain.__init__(self,'base',self.__getattr2__)

    def __getattr2__(self, key):
        keys = key.split('.')[1:] if isinstance(key,basestring) else key

        next = self[keys[0]]
        if len(keys)>1 and isinstance(next,DictChain):
            return dict.__getattribute__(next,'__getattr2__')(keys[1:])
        else:
            if keys:
                try:
                    returner = next
                except:
                    return self['generic'][keys[0]]
                if isinstance(returner,DictChain):
                    return returner['value']
                else:
                    return returner
            else:
                return self['value']

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    instead of `obj['foo']`. Create one by doing `storage({'a':1})`.

    Setting attributes is like putting key-value pairs in too!

    (Thanks web.py)
    """
    def __getattr__(self, key, ga = dict.__getattribute__, gi = None):
        try:
            return ga(self, key)
        except AttributeError:
            try:
                if gi is not None:
                    return gi(self, key)
                else:
                    return self[key]
            except KeyError:
                msg = repr(key)
                if len(self) <= 20:
                    keys = sorted(self.keys())
                    msg += '\n  (%d existing keys: ' % len(keys) + str(keys) + ')'
                raise AttributeError, msg

    def __setattr__(self, key, value):
        self[key] = value

    def copy(self):
        return type(self)(self)

def dictrecurse(newtype):
    def recurser(_d, forbidden = ()):
        if not hasattr(_d, 'keys'):
            from pprint import pformat
            raise TypeError('what is?\n%s' % pformat(_d))

        for k in _d:
            if isinstance(_d[k], dict):
                _d[k] = recurser(_d[k])
            elif funcs.isiterable(_d[k]) and not isinstance(_d[k], forbidden + (basestring,)):
                if isinstance(_d[k], tuple):
                    t = tuple
                else:
                    t = list
                _d[k] = t((recurser(item) if isinstance(item, dict) else item)
                             for item in _d[k])
        if isinstance(newtype, type):
            return _d if type(_d) is newtype else newtype(_d)
        else:
            return newtype(_d)

    return recurser

to_storage = dictrecurse(Storage)

def from_storage(d):
    '''
    >>> s = Storage(wut = "boop", meep = Storage(yip = "pow"))
    >>> d = from_storage(s)
    >>> assert type(d) is dict and type(d['meep']) is dict
    >>> print d['meep']['yip']
    pow
    '''
    for k, v in d.items():
        if isinstance(v, Storage):
            d[k] = from_storage(v)
        elif isinstance(v, list):
            newlist = [(from_storage(e) if isinstance(e, Storage) else e) for e in d[k]]
            d[k] = newlist

    return d if type(d) is dict else dict(d)

def lookup_table(*a, **d):
    """
    Takes a dictionary, makes it a storage object, and stores all the reverse
    associations in it.
    """

    d = dict(*a, **d)
    d.update(dictreverse(d))
    return to_storage(d)

class get_change_dict(dict):
    def __init__(self, *a, **k):
        self.__dict__['_get_change_dict__get_change'] = k.pop('_get_change', None)
        super(get_change_dict, self).__init__(*a, **k)

    def __getitem__(self, key):
        if getattr(self, '_get_change_dict__get_change', None) is not None:
            key = self.__get_change(key)
        return super(get_change_dict, self).__getitem__(key)

    def __contains__(self, key):
        if self.__get_change is not None:
            key = self.__get_change(key)
        return super(get_change_dict, self).__contains__(key)

    def pop(self, key, x=None):
        'a.pop(k[, x])      a[k] if k in a, else x (and remove k)'
        key = self.__get_change(key)
        return super(get_change_dict, self).pop(key, x)

class set_change_dict(dict):
    def __init__(self, *a, **k):
        self.__dict__['_set_change_dict__set_change'] = k.pop('_set_change', None)
        super(set_change_dict, self).__init__(*a, **k)

    def __setitem__(self, key, val):
        if getattr(self, '_set_change_dict__set_change', None) is not None:
            key = self.__set_change(key)
        return super(set_change_dict, self).__setitem__(key, val)

    def setdefault(self, key, default):
        if self.__key_change is not None:
            key = self.__key_change(key)
        try:
            return super(set_change_dict, self).__getitem__(key.lower())
        except KeyError:
            super(set_change_dict, self).__setitem__(key.lower(), default)
            return default

class key_change_dict(set_change_dict, get_change_dict):
    def __init__(self, *a, **k):
        self.__dict__['_key_change_dict__key_change'] = _key_change = k.pop('_key_change', None)
        k['_set_change'] = _key_change
        k['_get_change'] = _key_change
        super(key_change_dict, self).__init__(*a, **k)

class lower_case_dict(key_change_dict):
    def __init__(self, *a, **k):
        self.__dict__['_lower_case_dict__key_change'] = k['_key_change'] = lambda key: key.lower()
        super(lower_case_dict, self).__init__(*a, **k)
        for key in list(self.keys()):
            self[key] = super(lower_case_dict, self).pop(key)

    def __delitem__(self, key):
        key = self.__key_change(key)
        return super(lower_case_dict, self).__delitem__(key)

class no_case_dict(set_change_dict, get_change_dict):
    '''
    >>> class Foo(no_case_dict, Storage):
    ...     pass
    ...
    >>> f = Foo({'Foo':'bar'})
    >>> f.foo
    'bar'
    >>> f.fOo
    'bar'
    >>> f
    {'Foo': 'bar'}
    '''
    def __init__(self, *a, **k):
        self.__dict__['_no_case_dict__mapping'] = {}
        k['_set_change'] = self.__set_change
        k['_get_change'] = self.__get_change
        super(no_case_dict, self).__init__(*a, **k)
        self.__dict__['_no_case_dict__inited'] = False
        for key in list(self.keys()):
            self[key] = self.pop(key)
        self.__dict__['_no_case_dict__inited'] = True

    def __set_change(self, key):
        self.__mapping[key.lower()] = key
        return key

    def __get_change(self, key):
        if self.__inited:
            key = self.__mapping[key.lower()]
        return key

def stringify_dict(dict):
    'Turn dict keys into strings for use as keyword args'
    new = {}
    for k,v in dict.items():
        if isinstance(k, basestring):
            new[str(k)] = v
        else:
            new[k] = v

    return new

class odict(dict):
    """
    an ordered dictionary
    """
    def __init__(self, d = None):
        if d is None: d = {}

        try:
            t = d.items()
            self._keys = [k for k, _v in t]
            dict.__init__(self, t)
        except:
            one, two, three = itertools.tee(d, 3)

            try:    self._keys = [k for k, _v in one]
            except: self._keys = [k for k in two]
            dict.__init__(self, d if isinstance(d, dict) else three)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        # a peculiar sharp edge from copy.deepcopy
        # we'll have our set item called without __init__

        if not hasattr(self, '_keys'):
            self._keys = [key,]
        if key not in self._keys:
            self._keys.append(key)

    __iter__ = property(lambda self: self._keys.__iter__)

    def clear(self):
        dict.clear(self)
        self._keys = []

    def pop(self, k, defval = sentinel):
        try:
            val = dict.pop(self, k)
        except KeyError:
            if defval is sentinel: raise
            else: return defval
        else:
            self._keys.remove(k)
            return val

    def iteritems(self):
        for i in self._keys:
            try:
                yield i, self[i]
            except KeyError:
                print 'fake keys', self._keys
                print 'real keys', self.keys()
                raise


    def items(self):
        return list(self.iteritems())

    def keys(self):
        return self._keys[:] #fast? copy

    def iterkeys(self): #iterator tied so that "changed size" etc...
        return iter(self._keys)

    def itervalues(self):
        for i in self._keys:
            yield self[i]

    def values(self):
        return list(self.itervalues())

    def popitem(self):
        if len(self._keys) == 0:
            raise KeyError('dictionary is empty')
        else:
            key = self._keys[-1]
            val = self[key]
            del self[key]
            return key, val

    def setdefault(self, key, failobj = None):
        ret = dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)
        return ret

    def update(self, d):
        try:
            for key in d.keys():
                if not self.has_key(key):
                    self._keys.append(key)
        except AttributeError:
            # might be an iterable of tuples
            for k,v in d:
                self[k] = v

            return
#                if not self.has_key(k):
#                    self._keys.append(k)
#                tmp[k] = v
#            d = tmp

        dict.update(self, d)

    def move(self, key, index):

        """ Move the specified to key to *before* the specified index. """

        try:
            cur = self._keys.index(key)
        except ValueError:
            raise KeyError(key)
        self._keys.insert(index, key)
        # this may have shifted the position of cur, if it is after index
        if cur >= index: cur = cur + 1
        del self._keys[cur]

    def index(self, key):
        if not self.has_key(key):
            raise KeyError(key)
        return self._keys.index(key)

    def get(self, key, default = None):
        return dict.get(self, key, default)

    def sort(self, cmp=None, key=None, reverse=False):
        return self._keys.sort(cmp=cmp, key=key, reverse=reverse)

    def sort_values(self, cmp=None, key=None, reverse=False):
        if key is None:
            key = lambda k: k
        value_key = lambda k: key(self.get(k))
        self.sort(cmp=cmp, key=value_key, reverse=reverse)

class OrderedDict(dict, DictMixin):
    '''
    Recipe 576693: Ordered Dictionary for Py2.4
    Drop-in substitute for Py2.7's new collections.OrderedDict. The recipe has big-oh performance that matches regular dictionaries (amortized O(1) insertion/deletion/lookup and O(n) iteration/repr/copy/equality_testing).
    http://code.activestate.com/recipes/576693/
    '''

    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__end
        except AttributeError:
            self.clear()
        self.update(*args, **kwds)

    def clear(self):
        self.__end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.__map = {}                 # key --> [key, prev, next]
        dict.clear(self)

    def __setitem__(self, key, value):
        if key not in self:
            end = self.__end
            curr = end[1]
            curr[2] = end[1] = self.__map[key] = [key, curr, end]
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        key, prev, next = self.__map.pop(key)
        prev[2] = next
        next[1] = prev

    def __iter__(self):
        end = self.__end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.__end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def popitem(self, last=True):
        if not self:
            raise KeyError('dictionary is empty')
        key = reversed(self).next() if last else iter(self).next()
        value = self.pop(key)
        return key, value

    def __reduce__(self):
        items = [[k, self[k]] for k in self]
        tmp = self.__map, self.__end
        del self.__map, self.__end
        inst_dict = vars(self).copy()
        self.__map, self.__end = tmp
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def keys(self):
        return list(self)

    setdefault = DictMixin.setdefault
    update = DictMixin.update
    pop = DictMixin.pop
    values = DictMixin.values
    items = DictMixin.items
    iterkeys = DictMixin.iterkeys
    itervalues = DictMixin.itervalues
    iteritems = DictMixin.iteritems

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, self.items())

    def copy(self):
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and \
                   all(p==q for p, q in  zip(self.items(), other.items()))
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other


class LazySortedDict(odict):
    '''
    dictionary which sorts it's keys when the internal _keys attribute is accessed/set
    note: this will not automatically sort in every instance
    if you want the dictionary to be sorted immediately, access the _keys
    such as the following as a one-liner
    dict._keys
    '''

    def _get_keys(self):
        try:
            self._real_keys = sorted(self._real_keys)
        except AttributeError:
            self._real_keys = []
        return self._real_keys

    def _set_keys(self, keys):
        self._real_keys = sorted(keys)

    def copy(self):
        return type(self)(self)

    _keys = property(_get_keys, _set_keys)

class ostorage(odict, Storage):
    '''
    >>> ostorage()
    {}
    >>> s = ostorage()
    >>> s.foo = 'bar'
    >>> s.bar = 'foo'
    >>> s
    {'foo': 'bar', 'bar': 'foo'}
    '''
    def __getattr__(self, attr):
        if attr == '_keys':
            return odict.__getattr__(self, attr)
        else:
            return Storage.__getattr__(self, attr)

    def __setattr__(self, attr, val):
        if attr == '_keys':
            return odict.__setattr__(self, attr, val)
        else:
            return Storage.__setattr__(self, attr, val)

#    def __delattr__(self, attr, val):
#        if attr == '_keys':
#            return odict.__delattr__(self, attr, val)
#        else:
#            return Storage.__delattr__(self, attr, val)

class Ostorage(OrderedDict, Storage):
    '''
    >>> Ostorage()
    Ostorage()
    >>> s = Ostorage()
    >>> s.foo = 'bar'
    >>> s.bar = 'foo'
    >>> s
    Ostorage([('foo', 'bar'), ('bar', 'foo')])
    >>> s.foo
    'bar'
    '''
    def __getattr__(self, attr):
        if attr in ('_OrderedDict__map', '_OrderedDict__end'):
            return OrderedDict.__getattr__(self, attr)
        else:
            return Storage.__getattr__(self, attr)

    def __setattr__(self, attr, val):
        if attr in ('_OrderedDict__map', '_OrderedDict__end'):
            return OrderedDict.__setattr__(self, attr, val)
        else:
            return Storage.__setattr__(self, attr, val)

def groupify(seq, keys = None, whitelist = True, mapclass=odict):
    '''
    converts sequential flattened dictionaries into dictionaries
    example [(1, 'a'), (2, 'b'), (1, 'c'), (2, 'd')] yields
    [{1: 'a', 2: 'b'}, {1: 'c', 2: 'd'}]
    '''
    retval = [mapclass()]
    idx = 0
    for k, v in seq:
        if keys and (whitelist ^ (k in keys)):
            continue
        if k in retval[idx]:
            retval.append(mapclass())
            idx += 1
        retval[idx][k] = v
    if not retval[0]:
        return []
    return retval

class FilterDict(dict):
    def __init__(self, filterfunc, d=None, **kw):
        if d is None: d = {}
        dict.__init__(self)

        d.update(kw)
        dict.__setattr__(self, 'ff', filterfunc)

        for k, v in d.iteritems():
            self.__setitem__(k,v)

    def __getitem__(self, key):
        return dict.__getitem__(self, self.ff(key))

    def __delitem__(self, key):
        return dict.__delitem__(self, self.ff(key))

    def __contains__(self, key):
        return dict.__contains__(self, self.ff(key))

    def __setitem__(self, key, newval):
        return dict.__setitem__(self, self.ff(key), newval)

class LowerDict(FilterDict):
    def __init__(self, *a, **k):
        def filterfunc(x):
            try: x = x.lower()
            except: pass
            return x

        FilterDict.__init__(self, filterfunc, *a, **k)

recurse_lower = dictrecurse(LowerDict)

class LowerStorage(LowerDict, Storage):
    def __init__(self, *a, **k):
        Storage.__init__(self)
        LowerDict.__init__(self, *a, **k)

recurse_lower_storage = dictrecurse(LowerStorage)

def odict_from_dictlist(seq):
    od = odict()
    for subdict in seq:
        key = subdict.keys()[0]
        od[key] = subdict[key]

    return od


if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
