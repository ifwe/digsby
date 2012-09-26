from __future__ import with_statement
from functional import ObjectList
from refs import stupidref, better_ref
from collections import defaultdict
from error_handling import traceguard
import functools
import operator
import pprint
import sys
import traceback

try:
    sentinel
except NameError:
    sentinel = object()

#import logging
#log = logging.getLogger('util.primitives.funcs')

def get(obj, key, default=sentinel):
    try:
        return obj[key]
    except (IndexError, KeyError):
        if default is sentinel:
            raise
        else:
            return default
    except TypeError:
        try:
            return getattr(obj, key)
        except AttributeError:
            if default is sentinel:
                raise
            else:
                return default

def ischeck(f):
    def checker(v):
        try:
            r = f(v)
        except Exception:
            return False
        else:
            if type(r) is bool:
                return r
            else:
                return True
    return checker

def itercheck(x, exclude=(basestring,)):
    try:
        iter(x)
    except:
        return False
    else:
        if not isinstance(x, exclude):
            return True
        else:
            return False

isint = ischeck(int)
isiterable = ischeck(itercheck)
isnumber = ischeck(float)

def make_first(seq, item):
    '''make item the first and only copy of item in seq'''

    seq[:] = [item] + [elem for elem in seq if elem != item]

def do(seq_or_func, seq=None):
    '''
    For use with generator expressions or where map would be used.
    More memory efficient than a list comprehension, and faster than map.

    Please note that you won't get your results back (if you want them, you shouldn't
    replace your list comprehension or map() with this).

    ex. [sock.close() for sock in self.sockets] becomes do(sock.close() for sock in self.sockets)
        map(lambda x: x.close(), self.sockets]  becomes do(lambda x: x.close(), self.sockets)
    '''

    if seq is None:
        for x in seq_or_func: pass
    else:
        for x in seq: seq_or_func(x)

def find(seq, item):
    '''
    Like list.index(item) but returns -1 instead of raising ValueError if the
    item cannot be found.
    '''

    try:
        return seq.index(item)
    except ValueError:
        return -1

def groupby(seq, key = lambda x: x):
    '''
    Like itertools.groupby, except all similar items throughout the sequence are grouped,
    not just consecutive ones.
    '''

    res = defaultdict(list)

    for item in seq:
        res[key(item)].append(item)

    for k in res:
        yield k, res[k]

class Delegate(ObjectList):
    VETO = object()

#    NOTE: better_ref didn't work: lambdas and inner functions
#    lose their references, and so they are garbage collected.
#    The code is being left here for reference, warning, and
#    example.

#    def __init__(self, sequence=()):
#        list.__init__(map(better_ref,sequence))

    def __init__(self, iterable = [], ignore_exceptions = None, collect_values=False):
        list.__init__(self, iterable)
        self.__dict__['collect_values'] = collect_values
        object.__setattr__(self, 'ignore_exceptions', ignore_exceptions if ignore_exceptions is not None else tuple())

    def __iadd__(self, f):
        if isinstance(f, list):
            for thing in f:
                self.__iadd__(thing)
        else:
            assert callable(f)
            self.append(f)
        return self

    def __isub__(self, f):
        #f = better_ref(f)
        if not isiterable(f): f = (f,)
        for x in f: self.remove(x)
        return self

    def __ipow__(self, d):
        assert operator.isMappingType(d)
        self(**d)
        return self

    def __imul__(self, a):
        assert operator.isSequenceType(a)
        self(*a)
        return self

    def __idiv__(self, tup):
        a,k = tup
        self(*a,**k)
        return self

    def __call__(self, *a, **k):
        result = [None]
        for call in self:
            try:
                result.append(call(*a, **k))
            except self.ignore_exceptions:
                self.remove(call)
            except Exception:
                traceback.print_exc()

            if result[-1] is self.VETO:
                break

            if not self.collect_values:
                # Since the likely case is that we are not collecting values for memory usage reasons,
                # we chop off the list to avoid wasting memory.
                result = result[-1:]

        if self.collect_values:
            # remove the None that we started with
            result.pop(0)
        else:
            # unwrap the result
            result = result[-1]

        return result

    def call_and_clear(self, *a, **k):
        copy = Delegate(self, self.ignore_exceptions, self.collect_values)
        del self[:]
        result = copy(*a, **k)
        return result

    def __repr__(self):
        from util import funcinfo
        return '<%s: [%s]>' % (type(self).__name__, ', '.join(funcinfo(f) for f in self))

    def add_unique(self, cb):
        if not cb in self: self.append(cb)

    def remove_maybe(self, cb):
        if cb in self: self.remove(cb)

objset = object.__setattr__

class PausableDelegate(Delegate):
    def __init__(self):
        Delegate.__init__(self)
        objset(self, 'paused', False)

    def __call__(self, *a, **k):
        if self.paused:
            self.paused_calls.append(lambda: Delegate.__call__(self, *a, **k))
            return None
        else:
            return Delegate.__call__(self, *a, **k)

    def pause(self):
        if not self.paused:
            objset(self, 'paused', True)
            objset(self, 'paused_calls', [])
            return True
        return False

    def unpause(self):
        if self.paused:
            objset(self, 'paused', False)
            if self.paused_calls:
                for call in self.paused_calls:
                    with traceguard: call()
                del self.paused_calls[:]
            return True
        return False

class WeakDelegate(object):
    def __init__(self):
        self.cbs = []

    def append(self, cb, obj = None):
        assert callable(cb)
        self.cbs.append(better_ref(cb, obj=obj))

    def __iadd__(self, cb):
        assert callable(cb)
        self.cbs.append(better_ref(cb))
        return self

    def __isub__(self, cb):
        assert callable(cb)
        assert cb is not None

        new_cbs = []
        for cbref in self.cbs:
            callback = cbref()
            if cb is not callback:
                new_cbs.append(cb)

        self.cbs = new_cbs
        return self

    def __call__(self, *a, **k):
        new_cbs = []
        cbs = self.cbs[:]
        self.cbs[:] = []

        for cbref in cbs:
            callback = cbref()
            if callback is not None:
                new_cbs.append(cbref)
                try:
                    callback(*a, **k)
                except Exception:
                    traceback.print_exc()

        self.cbs[:] = new_cbs

def autoassign(self, locals):
    '''
    Automatically assigns local variables to `self`.
    Generally used in `__init__` methods, as in:

        def __init__(self, foo, bar, baz=1): autoassign(self, locals())
    '''
    #locals = sys._getframe(1).f_locals
    #self = locals['self']
    for (key, value) in locals.iteritems():
        if key == 'self':
            continue
        setattr(self, key, value)

def flatten(seq):
    """
    Returns a list of the contents of seq with sublists and tuples "exploded".
    The resulting list does not contain any sequences, and all inner sequences
    are exploded.  For example:

    >>> flatten([7,(6,[5,4],3),2,1])
    [7, 6, 5, 4, 3, 2, 1]
    """
    lst = []
    for el in seq:
        if isinstance(el, (list, tuple)):
            lst.extend(flatten(el))
        else:
            lst.append(el)
    return lst

def dictargs(**argmap):
    'Magical dictionary splattage.'

    def decorator(func):
        @functools.wraps(func)
        def newf(self, response):
            try:
                args = [response[argmap[argname]]
                        for argname in
                        func.func_code.co_varnames[:func.func_code.co_argcount]
                        if argname != 'self']

            except KeyError:
                print >> sys.stderr, \
                    "Error matching argument for", func.__name__
                raise
            return func(self, *args)
        return newf
    return decorator

def dictargcall(func, argdict, argmapping):
    '''
    Calls a function, filling in arguments with the associations provided
    in argmapping.
    '''
    argdict = argdict.copy()
    args, kwargs = [], {}

    # grab some information about the function and its arguments
    code = func.func_code
    argcount = code.co_argcount
    argnames = code.co_varnames[:argcount]
    defaults = func.func_defaults or ()
    _takes_args, takes_kwargs = bool(code.co_flags & 4), bool(code.co_flags & 8)

    # skip over 'self' for bound methods
    if argnames and argnames[0] == 'self':
        argnames = argnames[1:]
        argcount -= 1

    # first, fill required arguments.
    for argname in argnames[:argcount - len(defaults)]:
        if argname not in argmapping:
            raise ValueError('required argument %s is not in mapping\n'
                             'given mapping: %s' % (argname, pprint.pformat(argmapping)))

        real_name = argmapping[argname]
        if real_name not in argdict:
            raise ValueError('required argument "%s" (%s) is not in argument '
                             'dictionary\ngiven arguments: %s' % (argname, real_name,
                                                          pprint.pformat(argdict)))

        args.append(argdict[real_name])
        del argdict[real_name]

    # second, fill in args with default values.
    default_index = 0
    for argname in argnames[argcount - len(defaults):]:
        if argname not in argmapping or argmapping[argname] not in argdict:
            args.append(defaults[default_index])
        else:
            args.append(argdict[argmapping[argname]])
            del argdict[argmapping[argname]]

        default_index += 1

    # if the function takes extra keyword arguments, fill them with the rest of
    # the values, using nice names if possible.
    if takes_kwargs:
        for k,v in argdict.iteritems():
            if k in argmapping: kwargs[argmapping[k]] = v
            else:               kwargs[str(k)] = v

    if not takes_kwargs: return func(*args)
    else:                return func(*args, **kwargs)

def funcToMethod(func,clas,method_name=None):
    """
    Adds func to class so it is an accessible method; use method_name to specify the name to be used for calling the method.
    The new method is accessible to any instance immediately.

    Thanks U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/81732} (yet again)
    """
    func.im_class=clas
    func.im_func=func
    func.im_self=None
    if not method_name: method_name=func.__name__
    clas.__dict__[method_name]=func

def attach_method(obj, func, name=None):
    "Attaches a function to an object as a method."

    name = name or func.__name__
    cls = obj.__class__
    cls.temp_foo = func
    obj.__setattr__(name, cls.temp_foo)
    del cls.temp_foo

class InheritableProperty(object):
    '''
    >>> class Foo(object):
    ...     def getter(self):
    ...        return getattr(self, '_foo', None) or "Foo"
    ...     def setter(self, value):
    ...        self._foo = value
    ...     foo = InheritableProperty('getter', setter)
    >>> class Bar(Foo):
    ...     def getter(self):
    ...         return "Bar"
    >>> f = Foo()
    >>> f.foo
    'Foo'
    >>> f.foo = "Baz"
    >>> f.foo
    'Baz'
    >>> b = Bar()
    >>> b.foo
    'Bar'
    >>> b.foo = "Baz"
    >>> b.foo
    'Bar'
    >>> b._foo
    'Baz'
    '''
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if callable(self.fget):
            return self.fget(obj)
        if isinstance(self.fget, basestring):
            return getattr(obj, self.fget)()
        raise AttributeError("unreadable attribute")

    def __set__(self, obj, value):
        if callable(self.fset):
            return self.fset(obj, value)
        if isinstance(self.fset, basestring):
            return getattr(obj, self.fset)(value)
        raise AttributeError("can't set attribute")

    def __delete__(self, obj):
        if callable(self.fdel):
            return self.fdel(obj)
        if isinstance(self.fdel, basestring):
            return getattr(obj, self.fdel)()
        raise AttributeError("can't delete attribute")

iproperty = InheritableProperty

def gen_sequence(func):
    from util.introspect import cannotcompile
    @cannotcompile
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        val = gen.next();
        try:
            gen.send(stupidref(gen))
        except StopIteration:
            pass
        return val
    return wrapper

def removedupes(seq, key = lambda x: x):
    '''
    >>> removedupes(['one','two','two','two','three','three'])
    ['one', 'two', 'three']
    '''
    #TODO: list(set(seq)).sort(cmp = lambda a, b: cmp(seq.index(a), seq.index(b)))
    #       does the same thing. Test it for speed diff
    s = set()
    uniqueseq = []
    for elem in seq:
        if key(elem) not in s:
            uniqueseq.append(elem)
            s.add(key(elem))
    return uniqueseq

def lispify(*args):
    '''
    returns a function which is the composition of the functions in
    args

    use at your own sanity's risk
    '''
    assert args
    try:     iter(args[0])
    except:  pass
    else:    args = args[0]

    return reduce(lambda x,y: lambda *a, **k: x(y(*a,**k)), args)

class CallCounter(object):
    def __init__(self, trigger, func, *args, **kwargs):
        assert trigger >= 0
        assert callable(func)
        self._count = -1
        self._trigger = trigger
        self._func = func
        self._args = args
        self._kwargs = kwargs

        self()

    def __call__(self):
        self._count += 1
        if self._count == self._trigger:
            self._func(*self._args, **self._kwargs)

    @property
    def func_code(self):
        return self._func.func_code

def readonly(attr):
    return property(operator.attrgetter(attr))

def takemany(n, iterable):
    while n > 0:
        yield iterable.next()
        n -= 1

def boolify(s):
    return s.lower() in ('yes', 'true', '1')

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
