'''
Usage:

class Packet(Packable):
    fmt = (
        'version',    'H',
        'length',     'I',
        'flags',      'B',
    )

p = Packet(3,10,12)
assert Packet.unpack(p.pack()) == p

'''

from primitives import to_hex
from struct import Struct
from itertools import izip
from logging import getLogger; log = getLogger('packable')

__all__ = ['Packable']

def debugline(fc):
    return '  File "%s", line %d, in %s' % \
           (fc.co_filename, fc.co_firstlineno, fc.co_name)

class PackableMeta(type):
    #
    # For an example, see the __main__ method of this file.
    #

    def __new__(meta, classname, bases, newattrs):
        cls = super(PackableMeta, meta).__new__(meta, classname,
                                                bases, newattrs)

        # If there is no format description, don't do any class magic.
        if not 'fmt' in newattrs:
            return cls

        byteorder = newattrs.pop('byteorder', '!')
        fmt       = newattrs.pop('fmt')
        __slots__ = list(fmt[::2])
        _struct   = Struct(byteorder + ''.join(fmt[1::2]))
        _invars   = newattrs.pop('invars', [])
        if not isinstance(_invars, (list, tuple)): _invars = [_invars]

        fmts = ''.join('\t%s\t\t%s\n' % (i,j)
                       for i,j in izip(fmt[::2], fmt[1::2]))

        cls.__doc__ = \
'''Constructs a %s, taking sequential arguments in the order they were
specified by the format description (or named keyword arguments!):\n\n%s''' % (classname, fmts)

        def checkinvars(cls, o):
            for invar in cls._invars:
                if not invar(o):
                    fc = invar.func_code
                    raise AssertionError('Invariant failed after unpacking:'
                                         '\n%s' % debugline(fc))
        @classmethod
        def unpack(cls, data):
            sz = cls._struct.size
            o = cls(*cls._struct.unpack(data[:sz]))

            try:
                checkinvars(cls, o)
            except AssertionError:
                log.error('wrong data: %s', to_hex(data))
                raise
            return o, data[sz:]

        def pack(self):
            checkinvars(self.__class__, self)
            attrs = [getattr(self, field) for field in self.__slots__]
            return self._struct.pack(*attrs)

        def __eq__(self, other):
            for attr in self.__slots__:
                if getattr(other, attr, sentinel) != getattr(self, attr):
                    return False
            return True

        __len__ = lambda self: self.size
        __iter__ = lambda self: ((s, getattr(self, s)) for s in self.__slots__)
        __str__ = pack
        copy = lambda self: cls.unpack(self.pack())[0]
        size = _struct.size

        localdict = locals()
        classattrs = '''__slots__ _struct pack unpack __len__
                        _invars __iter__ __str__ __eq__ copy size'''.split()

        for a in classattrs: setattr(cls, a, localdict[a])
        return cls

class Packable(object):
    __metaclass__ = PackableMeta

    def __init__(self, *a, **kw):
        i = -1
        for i, d in enumerate(a): setattr(self, self.__slots__[i], d)
        for f in self.__slots__[i+1:]: setattr(self, f, 0)
        for k in kw: setattr(self, k, kw[k])

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, ' '.join('%s=%r' % i for i in self))

from math import log as _log, floor, ceil

def num_bits(i):
    return floor(_log(i,2))+1

def num_bytes(i):
    if i in (0,1): return 1
    else:          return int(ceil(pow(2, num_bits(num_bits(i)-1))/8))

def make_packable(info):
    names, values = zip(*sorted(info, key=lambda x: type(x[1])))

    type_size = {
                 str:     lambda s: len(s),
                 unicode: lambda u: 2*len(u),
                 int:     lambda i: pow(2, num_bits(num_bits(i)-1))/8,
                 bool:    lambda b: 0,
                 }

    get_size = lambda x: type_size[type(x)](x)
    sizes = [get_size(v) for v in values]
    ints = bools_to_ints(filter(lambda x: type(x) is bool, values))
    size_in_bytes = sum(sizes)+len(ints)*4


def bools_to_ints(bools):
    nums = []
    num_ints = ceil(len(bools)/32.0)
    for i in range(num_ints):
        num = 0
        for i in range(len(bools[i*32:(i+1)*32])):
            num |= bools[i] * pow(2, i%32)
        nums.append(num)
    return nums

def main():

    class Meep(Packable):
        fmt = ('version', '4s',
               'length',  'H',
               'name','3s')

        invars = [lambda o: o.version == 'OFT2']

    m = Meep('OFT2', 2, 'abc')
    print repr(str(Meep.unpack(m.pack())[0]))
    print m.__class__.__name__
    print m.__doc__
    print repr(m)

if __name__ == '__main__':
    main()
