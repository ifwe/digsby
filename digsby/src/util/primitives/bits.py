import mapping
import itertools
import random

def hex2bin(s):
    return ''.join(chr(int(x,16)) for x in s.split())

def rand32():
    return random.randint(1, (1 << 32) - 1)

def getrandbytes(n):
    return ''.join(chr(random.getrandbits(8)) for _i in range(n))

def rol(i, n, bits=32):
    '''
    ROtate Left.
    '''
    div, mod = divmod(i << n, (2**bits)-1)
    return mod | (div >> bits)

def ror(i, n, bits=32):
    '''
    ROtate Right.
    '''
    return ((i % 2**n) << (bits - n)) + (i >> n)

def bitfields(*names):
    '''
    >>> bitfields('zero','one','two','three').three
    8
    '''
    bits = [2**i for i in xrange(len(names))]
    return mapping.Storage(itertools.izip(names, bits))

class BitFlags(object):
    def __init__(self, names):
        self._field = bitfields(*names)
        self.__dict__.update(dict.fromkeys(names, False))

    def Pack(self):
        return reduce(lambda a, b: a | b,
                      map(lambda x: getattr(self._field,x)*getattr(self,x), self._field))

    def Unpack(self, val):
        [setattr(self, field, True) for (field, i) in self._field.items() if val&i==i]

def leftrotate(s, shift, size=32):
    max = pow(2, size)
    s = (s % max) << shift
    wrap, s = divmod(s, max)
    return s | wrap

def utf7_to_int(databuf):
    total = i = 0
    more_bytes = True
    while more_bytes:
        byte = ord(databuf[i])
        more_bytes = bool(byte & 0x80)
        total |= (byte & 0x7f) * (1 << (7*i))
        i += 1

    return total, i

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
