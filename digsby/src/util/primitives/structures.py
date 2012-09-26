import mapping
import struct
import types

#import logging
#log = logging.getLogger('util.primitives.structures')

class enum(list):
    '''
    >>> suits = enum(*'spades hearts diamonds clubs'.split())
    >>> print suits.clubs
    3
    >>> print suits['hearts']
    1
    '''

    def __init__(self, *args):
        list.__init__(self, args)

    def __getattr__(self, elem):
        return self.index(elem)

    def __getitem__(self, i):
        if isinstance(i, basestring):
            return self.__getattr__(i)
        else:
            return list.__getitem__(self, i)

class EnumValue(object):
    def __init__(self, name, int, **kwds):
        self.str = name
        self.int = int

        for k,v in kwds.items():
            setattr(self, k, v)

    def __str__(self):
        return self.str
    def __int__(self):
        return self.int
    def __cmp__(self, other):
        try:
            other_int = int(other)
        except:
            return 1
        else:
            return cmp(int(self), other_int)
    def __repr__(self):
        return '<%s %s=%d>' % (type(self).__name__, str(self), int(self))

class _EnumType(type):
    def __new__(self, clsname, bases, vardict):
        clsdict = {}
        values = []
        ValueType = vardict.get('ValueType', EnumValue)
        for name, value in vardict.items():
            if name == 'ValueType' or name.startswith('_') or isinstance(value, types.FunctionType):
                clsdict[name] = value
                continue

            if isinstance(value, dict):
                EVal = ValueType(name, **value)
            elif isinstance(value, int):
                EVal = ValueType(name, value)
            elif isinstance(value, tuple):
                EVal = ValueType(name, *value)

            values.append(EVal)

        for val in values:
            clsdict[str(val)] = val

        _known = {}
        for val in values:
            values_dict = dict(vars(val))
            equiv = values_dict.values()
            for eq in equiv:
                try:
                    hash(eq)
                except TypeError:
                    continue
                _known[eq] = val

        clsdict['_known'] = _known

        return type.__new__(self, clsname, bases, clsdict)

class _Enum(object):
    __metaclass__ = _EnumType
    ValueType = EnumValue

    def __call__(self, something):
        if isinstance(something, self.ValueType):
            return something
        if isinstance(something, dict):
            something = something.get('int')

        return self._known.get(something, None)

def Enum(Name, Type = EnumValue, **kws):
    enum_dict = dict(vars(_Enum))
    enum_dict.update(ValueType = Type, **kws)
    return _EnumType(Name, (_Enum,), enum_dict)()

def new_packable(fmt, byteorder='!', invars=None):
    invars = invars or []
    slots = fmt[::2]
    fmtstring = byteorder + ''.join(fmt[1::2])

    class packable(object):
        __slots__, _fmt, invariants = slots, fmtstring, invars
        @classmethod
        def unpack(cls,data):
            o = cls(*struct.unpack(cls._fmt, data))
            assert all(invar(o) for invar in cls.invariants)
            return o
        def __init__(self, *a, **kw):
            i = -1
            for i, d in enumerate(a): setattr(self, self.__slots__[i], d)
            for field in self.__slots__[i+1:]: setattr(self, field, 0)
            for k in kw: setattr(self, k, kw[k])
        def pack(self):
            return struct.pack(self._fmt, *(getattr(self, field)
                                           for field in self.__slots__))
        def __iter__(self):
            return ((s, getattr(self, s)) for s in self.__slots__)
        def __len__(self): return struct.calcsize(self._fmt)
        __str__ = pack

        def __eq__(self, other):
            o = ()
            for slot in self.__slots__:
                sval = getattr(self, slot)
                oval = getattr(other, slot, o)
                if oval is o: return False
                if oval != sval: return False
            return True

        def __ne__(self, other):
            return not self.__eq__(other)

        def copy(self):
            return self.unpack(self.pack())

    return packable

def unpack_named(format, *args):
    """
    Like struct.unpack, but with names. Name/value pairs are put into a dictionary and
    returned.

    Usage:
    my_hash = unpack_named( data format, name1, name2, ..., nameN, data )

    In addition to all the normal pack/unpack keycodes like I, B, and H, you can also
    use an uppercase R to indicate the "rest" of the data. Logically, the R can only
    appear at the end of the format string.

    Example:

    >>> testdata = struct.pack("!HIB", 1,4000L,3) + "some extraneous data"
    >>> magic_hash = unpack_named("!HIBR", "one", "four thousand long", "three", "extra", testdata)
    >>> v = magic_hash.values()
    >>> v.sort()
    >>> print v
    [1, 3, 4000, 'some extraneous data']
    """
    data = args[-1]

    # if format has our special R character, make sure it's at end
    rest = None
    if 'R' in format:
        if format.find('R') != len(format) - 1:
            raise AssertionError("R character in format string to unpack_named can only appear at the end")
        else:
            format = format[:-1] # chop off the last character
            sz = struct.calcsize(format)

            # slice the "rest" off of the data
            rest = data[sz:]
            data = data[:sz]

    # unpack using the ever handy struct module
    tup = struct.unpack(format, data)

    # give names to our newly unpacked items
    magic_hash = {}
    for i in xrange(len(tup)):
        magic_hash[ args[i] ] = tup[i]
    if rest:
        magic_hash[ args[i+1] ] = rest

    return mapping.to_storage(magic_hash)

def remove_from_list(my_list, remove_these):
    my_list = my_list[:]
    remove_list = [e for e in my_list if e in remove_these]
    for e in remove_list: my_list.remove(e)
    return my_list

class oset(set):
    def __init__(self, iterable=None):
        self.data = []

        if iterable is None:
            iterable = []
        self.update(iterable, init=True)

    def add(self, val):
        '''
        >>> a = oset([1,2,3])
        >>> a.add(3)
        >>> a
        oset([1, 2, 3])
        >>> a = oset([1,2,3])
        >>> a.add(4)
        >>> a
        oset([1, 2, 3, 4])
        '''
        if val not in self.data:
            self.data.append(val)
            set.add(self, val)

    def __getitem__(self,n):
        '''
        >>> a = oset([8,4,6])
        >>> a[1]
        4
        >>> a[1:]
        oset([4, 6])
        '''
        if isinstance(n, slice):
            return type(self)(self.data[n])
        return self.data[n]

    def __iter__(self):
        return iter(self.data)

    def clear(self):
        del self.data[:]
        set.clear(self)

    def pop(self):
        ret = set.pop(self)
        self.data.remove(ret)
        return ret

    def remove(self, item):
        self.data.remove(item)
        set.remove(self, item)

    def discard(self, item):
        try:               self.remove(item)
        except ValueError: pass
        except KeyError:   pass

    def union(self, other):
        if not isinstance(other, oset):
            other = oset(other)
        return self | other

    def __or__(self, other):
        if not isinstance(other, set):
            raise ValueError, "other must be a set"
        ret = oset(self)
        ret.update(other)
        return ret

    def intersection(self, other):
        if not isinstance(other, oset):
            other = oset(other)
        return self & other

    def __and__(self, other):
        if not isinstance(other, set):
            raise ValueError, "other must be a set"
        a = oset(self)
        b = other
        return a - (a - b)

    def difference(self, other):
        other = oset(other)
        return self - other

    def __sub__(self, other):
        if not isinstance(other, set):
            raise ValueError, "other must be a set"
        first = oset(self)
        first -= other
        return first

    def symmetric_difference(self, other):
        if not isinstance(other, oset):
            other = oset(other)
        return self ^ other

    def __xor__(self, other):
        if not isinstance(other, set):
            raise ValueError, "other must be a set"
        return (self | other) - (self & other)

    def copy(self):
        return oset(self)

    def update(self, other, init=False):
        if not isinstance(other, oset) and not init:
            other = oset(other)
        self.__ior__(other, init=init)

    def __ior__(self, other, init=False):
        if not isinstance(other, set) and not init:
            raise ValueError, "other must be a set"
        for i in other:
            self.add(i)
        return self

    def intersection_update(self, other):
        if not isinstance(other, oset):
            other = oset(other)
        self &= other

    def __iand__(self, other):
        if not isinstance(other, set):
            raise ValueError, "other must be a set"
        self -= (self & other)

    def difference_update(self, other):
        if not isinstance(other, oset):
            other = oset(other)
        self -= other

    def __isub__(self, other):
        if not isinstance(other, set):
            raise ValueError, "other must be a set"
        for item in other:
            self.discard(item)
        return self

    def symmetric_difference_update(self, other):
        if not isinstance(other, oset):
            other = oset(other)
        self ^= other

    def __ixor__(self, other):
        if not isinstance(other, set):
            raise ValueError, "other must be a set"
        b = oset(other)
        b -= self
        self -= other
        self |= b
        return self

class roset(oset):
    def add(self,val):
        if val in self:
            self.data.remove(val)
            self.data.append(val)
        else:
            oset.add(self,val)

    def insert(self, idx, item):
        if item in self:
            self.data.remove(item)

        self.data.insert(idx, item)
        set.add(self, item)

class EmptyQueue(Exception): pass

class PriorityQueue(object):
    '''
    PriorityQueues sort their elements on insertion, using the heapq module.

    Not thread-safe!

    >>> pq = PriorityQueue('last')
    >>> pq += ('first', 0)
    >>> pq += ('third', 3)
    >>> pq += ('second', 2)
    >>> while len(pq): print pq.next()
    first
    second
    third
    last
    >>> len(pq)
    0
    '''
    default_priority = 5

    def __init__(self, *args):
        self.q = [(self.default_priority, arg) for arg in args]

        # Sort elements if we got them
        self.key = lambda a: a[0]
        self.q.sort(key=self.key)

    def __len__(self):
        return len(self.q)

    def count(self, x):
        return self.q.count(x)

    def peek(self):
        'Peek at the next element.'
        if not self.q: raise EmptyQueue

        __, item = self.q[0]
        return item

    def __iadd__(self, elemtuple):
        if isinstance(elemtuple, (tuple, list)):
            if len(elemtuple) != 2:
                raise TypeError('add to the PriorityQueue like += (item, priority) or just += item')
            self.append(*elemtuple)
        else:
            self.append(elemtuple)
        return self

    def __nonzero__(self):
        return self.q.__len__()

    def append(self, item, priority = default_priority):
        self.q.append((priority, item))
        self.q.sort(key=self.key)

    def next(self):
        __, item = self.q.pop(0)
        return item

    def __repr__(self):
        return "<PriorityQueue %r>" % self.q

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
