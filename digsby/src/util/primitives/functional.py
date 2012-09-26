
from cStringIO import StringIO

class chained_files(object):
    '''
    Makes a .read able object from several .readable objects.

    >>> from cStringIO import StringIO
    >>> chained = chained_files(StringIO(s) for s in 'one two three'.split())
    >>> print chained.read(8)
    onetwth
    >>> print chained.read(8)
    ree
    '''

    def __init__(self, fileobjs):
        # make any non readable strings StringIOs
        self._bytecount = 0
        self.fileobjs = []

        for obj in fileobjs:
            if not hasattr(obj, 'read') and isinstance(obj, str):
                self.fileobjs.append(StringIO(obj))
            else:
                self.fileobjs.append(obj)

            if not hasattr(self.fileobjs[-1], 'read'):
                raise TypeError('chained_files makes a .read object out of .read objects only. got a %r', obj)

            if hasattr(obj, 'tell'):
                self._bytecount += obj.tell()
            else:
                print '%s object %r has no attribute tell' % (type(obj), obj)

        self.obj      = self.fileobjs.pop(0)

    def read(self, blocksize = -1):
        if blocksize < 0:
            val = ''.join(obj.read() for obj in [self.obj] + self.fileobjs)
            self._bytecount += len(val)
            return val
        else:
            chunk = StringIO()
            chunkstr = self.obj.read(blocksize) if self.obj is not None else ''
            chunksize = len(chunkstr)
            chunk.write(chunkstr)

            diff = blocksize - chunksize
            while diff and self.obj is not None:
                subchunk = self.obj.read(diff)
                if not subchunk:
                    if self.fileobjs:
                        self.obj = self.fileobjs.pop(0)
                    else:
                        self.read = lambda self: ''
                        self.obj = None


                chunk.write(subchunk)
                chunksize += len(subchunk)
                diff = blocksize - chunksize

            val = chunk.getvalue()
            self._bytecount += len(val)
            return val

    def tell(self):
        return self._bytecount

class AttrChain(object):
    __name = None
    __target = None

    def __init__(self, name=None, target=None, *_a, **_k):
        self.__name = name
        self.__target = target

    def __getattr__(self, attr, sep='.'):
        if attr == "_getAttributeNames":
            return False
        return AttrChain((self.__name + sep if self.__name is not None else '') + attr, self.__get_target())

    def __truediv__(self, other):
        return self.__getattr__(other, sep='/')

    __div__ = __truediv__

    def __call__(self, *a, **k):
        return self.__get_target()(self.__name, *a, **k)

    def __get_target(self):
        if self.__target is not None:
            return self.__target
        try:
            return super(AttrChain, self).__call__
        except AttributeError:
            if getattr(type(self), '__call__') != AttrChain.__call__:
                return self.__call__
        raise AttributeError("%s object has no target, no __call__ and no super class with __call__" % type(self).__name__)

    def __repr__(self):
        return '<AttrChain ' + str(self.__name) + '>'


class ObjectList(list):

    def __init__(self, *a, **k):
        self.__dict__['strict'] = k.pop('strict', True)
        list.__init__(self, *a, **k)

    def __setattr__(self, attr, val):
        for o in self: setattr(o, attr, val)

    def __getattr__(self, attr):
        try:
            return list.__getattr__(self, attr)
        except AttributeError:
            try:
                return self.__dict__[attr]
            except KeyError:

                if self.__dict__.get('strict', True):
                    default = sentinel
                else:
                    default = lambda *a, **k: None

                res = ObjectList(getattr(x, attr, sentinel) for x in self)

                if self.__dict__.get('strict', True) and sentinel in res:
                    raise AttributeError("Not all objects in %r have attribute %r" % (self, attr))

                try:
                    res = FunctionList(res)
                except AssertionError:
                    pass

                return res

    def __repr__(self):
        return '<%s: %r>' % (type(self).__name__, list.__repr__(self))

class FunctionList(ObjectList):
    def __init__(self, *a, **k):
        ObjectList.__init__(self, *a, **k)
        if not all(callable(x) for x in self):
            raise AssertionError

    def __call__(self, *a, **k):
        return [f(*a, **k) for f in self]

def compose(funcs):
    '''
    Returns a function which is the composition of all functions in "funcs."

    Each function must take and return one argument.
    '''

    def composed(res):
        for f in funcs:
            res = f(res)
        return res

    return composed

def chain(*iterables):
    '''
    Replacement for itertools.chain, you get back a normal generator, complete with
    next, close, send, and throws methods.
    '''
    for it in iterables:
        for element in it:
            yield element

def main():
    chained = chained_files(StringIO(s) for s in 'one two three'.split())
    print chained.read(8)
    print chained.read(8)

if __name__ == '__main__':
    main()
