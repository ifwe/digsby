from __future__ import with_statement

import sys, time, threading, string, logging, re, keyword, \
       types, inspect
import primitives
import primitives.funcs
from weakref import ref
from types import GeneratorType
from path import path
from collections import defaultdict
from traceback import print_exc
import warnings
import gc
import operator

log = logging.getLogger('util.introspect')

oldvars = vars

def uncollectable(clz):
    '''
    Returns all active objects of the given class.

    Calls gc.collect() first.
    '''

    import gc
    gc.collect()

    return [a for a in gc.get_objects() if isinstance(a, clz)]

class debug_property(object):
    '''
    Doesn't squash AttributeError.
    '''

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.__get = fget
        self.__set = fset
        self.__del = fdel
        self.__doc__ = doc

    def __get__(self, inst, type=None):
        if inst is None:
            return self
        if self.__get is None:
            raise AttributeError, "unreadable attribute"
        try:
            return self.__get(inst)
        except AttributeError, e:
            # don't allow attribute errors to be squashed
            print_exc()
            raise AssertionError('attribute error during __get__')

    def __set__(self, inst, value):
        if self.__set is None:
            raise AttributeError, "can't set attribute"

        try:
            return self.__set(inst, value)
        except AttributeError, e:
            print_exc()
            raise AssertionError('attribute error during __set__')

    def __delete__(self, inst):
        if self.__del is None:
            raise AttributeError, "can't delete attribute"

        try:
            return self.__del(inst)
        except AttributeError, e:
            print_exc()
            raise AssertionError('attribute error during __del__')


def vars(obj=None):
    res = {}

    if hasattr(obj, '__dict__'):
        return oldvars(obj)
    elif hasattr(obj, '__slots__'):
        return dict((attr, getattr(obj,attr,sentinel)) for attr in obj.__slots__)
    else:
        assert not (hasattr(obj, '__slots__') and hasattr(obj, '__dict__'))
        if hasattr(obj, 'keys'):
            return obj
        else:
            assert primitives.funcs.isiterable(obj)
            return dict((x, sentinel) for x in obj)

version_23 = sys.version_info < (2,4)
def this_list():
    '''
    From the Python Cookbook
    '''
    d = inspect.currentframe(1).f_locals
    nestlevel =1
    while '_[%d]' % nestlevel in d: nestlevel +=1
    result = d['_[%d]' %(nestlevel-1)]

    if version_23: return result.__self__
    else:          return result


def cannotcompile(f):
    return f

def stack_trace(level=1, frame=None):
    try:
        if frame is None:
            f = sys._getframe(level)
        else:
            f = frame
        frames = []
        while f is not None:
            c = f.f_code
            frames.insert(0,(c.co_filename, c.co_firstlineno, c.co_name))
            f = f.f_back
        return frames
    finally:
        del f, frame

def print_stack_trace(frame=None):
    trace = stack_trace(2,frame)
    for frame in trace:

        print '  File "%s", line %d, in %s' % frame

def print_stack_traces():
    '''
    Prints stack trace of all frames in sys._current_frames.
    No promises of threadsafety are made!!
    '''
    frames = sys._current_frames().items()
    for id,frame in frames:
        print 'Frame %d:' % id
        print_stack_trace(frame)

def is_all(seq, my_types = None):
    """
    Returns True if all elements in seq are of type my_type.

    If True, also returns the type.
    """

    #TODO: technically, return val for an empty sequence is undefined...what do we do?
    if not seq:
        try:     iter(my_types)
        except:  t = my_types
        else:    t = my_types[0]
        finally: return True, t

    if type( my_types ) == type:
        my_types = [my_types]

    if my_types == None:
        my_types = [type(seq[0])]

    all = True
    for elem in seq:
        if type(elem) not in my_types:
            all = False
            break

    if all:
        return all, my_types[0]
    else:
        return all, None

def get_func_name(level=1):
    return sys._getframe(level).f_code.co_name


def get_func(obj, command, *params):
    """
    get_func(obj, command, *params)
    Returns a function object named command from obj. If a function is
    not found, logs a critical message with the command name and parameters
    it was attempted to be called with.
    """
    try:
        func = getattr(obj, command.lower())
        log.debug('Finding %s.%s%s',
                   obj.__class__.__name__,
                   command.lower(),
                   params)
    except AttributeError:
        log.critical('%s has no function to handle: %s(%s)',
                      obj.__class__.__name__,
                      command.lower(),
                      ", ".join([repr(x) for x in params]))
        func = None

    return func

def decormethod(decorator):
    """
    Returns a method decorator. See observable.py for an example, or
    U{http://miscoranda.com/136} for an explanation.
    """
    def wrapper(method):
        return (lambda self, *args, **kw:
                decorator(self, method, *args, **kw))
    return wrapper

def funcToMethod(func,clas,method_name=None):
    """Adds func to class so it is an accessible method; use method_name to specify the name to be used for calling the method.
    The new method is accessible to any instance immediately.

    Thanks U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/81732} (yet again)
    """
    func.im_class=clas
    func.im_func=func
    func.im_self=None
    if not method_name: method_name=func.__name__
    clas.__dict__[method_name]=func

def attach_method(obj, func, name=None):
    'Attaches a function to an object as a method.'

    name = name or func.__name__
    cls = obj.__class__
    cls.temp_foo = func
    obj.__setattr__(name, cls.temp_foo)
    del cls.temp_foo

def isgeneratormethod(object):
    'Return true if the object is a method of a generator object.'

    return isinstance(getattr(object, '__self__', None), GeneratorType)

CO_VARARGS     = 0x0004
CO_VARKEYWORDS = 0x0008

def callany(func, *args):
    '''
    Calls a callable with the number args it is expecting.
    '''
    if not callable(func): raise TypeError, "callany's first argument must be callable"

    from util.callbacks import CallLater, CallLaterDelegate, CallbackSequence

    c = func
    while isinstance(c, CallLater):
        c = c.cb

    if isinstance(c, CallbackSequence):
        c = c.__call__

    if isinstance(c, CallLaterDelegate):
        return [callany(child, *args) for child in c]

    if hasattr(c, 'im_func'):
        code = c.im_func.func_code
        nargs = code.co_argcount - 1
        codeflags = code.co_flags
    elif hasattr(c, 'func_code'):
        code = c.func_code
        nargs = code.co_argcount
        codeflags = code.co_flags
    else:
        # Last resort: call it simply as func(*args)
        code = None
        codeflags = 0
        nargs = len(args)

    hasargs   = codeflags & CO_VARARGS
    haskwargs = codeflags & CO_VARKEYWORDS

    if haskwargs:
        args = []
        msg = 'callany given a kwarg function (%r): no arguments will be passed!' % funcinfo(c)

        warnings.warn(msg)

        if getattr(sys, 'DEV', False):
            # Keep the warning above, in case this exception is squashed.
            raise AssertionError(msg)

    if not hasargs:
        args  = list(args)[:nargs]
        args += [None] * (nargs - len(args))
    return func(*args)

def pythonize(s, lower=True):
    'Return a valid python variable name'

    if not isinstance(s, basestring):
        raise TypeError, 'Only string/unicode types can be pythonized!'

    allowed = string.letters + string.digits + '_'

    s = str(s).strip()

    if s.startswith('__') and s.endswith('__'):
        # only special words are allowed to be like __this__
        s = s[2:-2]

    if not s:
        return s

    s = ('_' if s[0] in string.digits else '')+ s
    s = ('_' if keyword.iskeyword(s) else '') + s

    new_s = ''
    for ch in s:
        new_s += ch if ch in allowed else '_'

    if lower:
        new_s = new_s.lower()

    return new_s

attached_functions = {}

def dyn_dispatch(obj, func_name, *args, **kwargs):
    func_name = pythonize(str(func_name))
    if not hasattr(obj, func_name):
        fn = sys._getframe(1).f_code.co_filename

        d = dict(name=func_name)
        d.update(kwargs)
        code = str(obj.func_templ % d)
        f = open(fn, 'a')
        f.write(code)
        f.close()

        newcode = ''
        code = code.replace('\n    ', '\n')

        exec(code)
        attach_method(obj, locals()[func_name])
        l = attached_functions.setdefault(obj.__class__, [])
        l.append(func_name)

    if func_name in attached_functions.setdefault(obj.__class__, []):
        args = [obj] + list(args)

    return getattr(obj, func_name)(*args, **kwargs)

class CallTemplate(string.Template):
    '''
    Like string.Template, but matches unnamed arguments and is callable.

    Useful as a quick replacement for defining short "return a string"
    functions.

    >>> nick = CallTemplate('NICK $username $realname')
    >>> print nick('digsby05', 'Digsby Dragon')
    NICK digsby05 Digsby Dragon
    '''

    def __init__(self, templ):
        string.Template.__init__(self,templ)

        # grab placeholder names from the string using the Template regex
        self.placeholders = [m[1] for m in
                             re.findall(self.pattern, self.template)]

    def __call__(self, *args, **kws):
        # match placeholders to args, and override with keyword args
        return self.substitute(**primitives.dictadd
                               (zip(self.placeholders, args), kws))



_profilers_enabled = False
def set_profilers_enabled(val):
    global _profilers_enabled
    _profilers_enabled = val

def use_profiler(target, callable):
    '''
    Use a disabled profiler to run callable.

    Profile object will be stored in target.profiler and can be .enable()d later.
    '''
    target.profiler = EnableDisableProfiler()

    def cb():
        #print 'starting profiler on %s' % threading.currentThread().getName()
        global _profilers_enabled
        if not _profilers_enabled:
            target.profiler.disable()  # start disabled to avoid performance cost
        callable()

    if sys.platform == 'win32':
        from wx import SEHGuard
    else:
        SEHGuard = lambda c: c()

    def run_with_sehguard():
        return SEHGuard(cb)

    target.profiler.runcall(run_with_sehguard)

def all_profilers():
    'Returns a sequence of all the profilers in the system.'

    return dict((thread, thread.profiler) for thread in threading.enumerate() if hasattr(thread, 'profiler'))

def get_profile_report(profiler):
    from pstats import Stats
    from cStringIO import StringIO

    io = StringIO()
    stats = Stats(profiler, stream = io)

    io.write('\nby cumulative time:\n\n')
    stats.sort_stats('cumulative').print_stats(25)

    io.write('\nby number of calls:\n\n')
    stats.sort_stats('time').print_stats(25)

    return io.getvalue()

from cProfile import Profile
Profile.report = get_profile_report

def profilereport():
    s = []
    for thread, profiler in all_profilers().iteritems():
        s.extend([repr(thread), profiler.report()])

    return '\n'.join(s)

class Memoize(object):
    __slots__ = ['func', 'cache']

    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __repr__(self):
        return '<Memoize for %r (%d items)>' % (funcinfo(self.func), len(self.cache))

    def __call__(self, *args, **kwargs):
        key   = (args, tuple(kwargs.items()))
        cache = self.cache

        try:
            return cache[key]
        except KeyError:
            return cache.setdefault(key, self.func(*args, **kwargs))

memoize = Memoize

# A read-once property.
memoizedprop = lambda getter: property(memoize(getter))

# timing decorator

def print_timing(num_runs=1):
    def wrapper1(func):
        def wrapper(*arg, **kwargs):
            t1 = time.clock()
            for i in range(num_runs):
                res = func(*arg, **kwargs)
            t2 = time.clock()
            print '%s took %0.3fms.' % (func.func_name, (((t2-t1)*1000.)/float(num_runs)))
            return res
        return wrapper
    return wrapper1

class i(int):
    '''
    Iterable integers.

    >>> for x in i(5): print x,
    0 1 2 3 4
    '''
    def __iter__(self): return iter(xrange(self))

def reload_(obj):
    '''
    Gets the latest code from disk and swaps it into the object.

    Returns the newly reloaded module.
    '''
    # Reload the object's bases class module
#    def bases(klas):
#        if klas == object:
#            return
#        for klass in klas.__bases__:
#            bases(klass)
#        for klass in klas.__bases__:
#            reload(sys.modules[klass.__module__])
#    bases(obj.__class__)
    for klass in reversed(obj.__class__.__mro__):
        if klass not in __builtins__:
            reload(sys.modules[klass.__module__])
    return reload2_(obj)

def reload2_(obj):
    '''
    Gets the latest code from disk and swaps it into the object.

    Returns the newly reloaded module.
    '''
    # Reload the object's class's module.
    m = sys.modules[obj.__class__.__module__]
    m = reload(m)

    # Grab the new class object.
    cl = getattr(m, obj.__class__.__name__)

    # Replace the object's __class__ attribute with the new class.
    obj.__class__ = cl

    return sys.modules[obj.__class__.__module__]

def bitflags_enabled(map, flags):
    bits = [f for f in map.iterkeys() if isinstance(f, int)]
    return [map[f] for f in sorted(bits) if f & flags != 0]

def import_module(modulePath):
    aMod = sys.modules.get(modulePath, False)
    if aMod is False or not isinstance(aMod, types.ModuleType):
        if isinstance(modulePath, unicode):
            modulePath = modulePath.encode('filesys')
        # The last [''] is very important so that the 'fromlist' is non-empty, thus returning the
        # module specified by modulePath, and not the top-level package. (i.e. when importing a.b.c
        # with no fromlist, the module 'a' is returned. with a non-empty fromlist, a.b.c is returned.
        # See http://docs.python.org/library/functions.html#__import__
        aMod = __import__(modulePath, globals(), locals(), [''])
        sys.modules[modulePath] = aMod
    return aMod

def import_function(fullFuncName):
    'Retrieve a function object from a full dotted-package name.'

    if not isinstance(fullFuncName, basestring):
        raise TypeError('import_function needs a string, you gave a %s' % type(fullFuncName))


    # Parse out the path, module, and function
    lastDot = fullFuncName.rfind(u".")
    funcName = fullFuncName[lastDot + 1:]
    modPath = fullFuncName[:lastDot]

    aMod = import_module(modPath)
    try:
        aFunc = getattr(aMod, funcName)
    except AttributeError, e:
        log.error('%r. Module contents = %r', e, aMod.__dict__)
        raise e

    # Assert that the function is a *callable* attribute.
    assert callable(aFunc), u"%s is not callable." % fullFuncName

    # Return a reference to the function itself,
    # not the results of the function.
    return aFunc

@memoize
def base_classes(clazz):
    '''
    Returns the list of classes above a class in the inheritance tree.

    Classes only appear once in the list, even in a diamond inheritance pattern.

    >>> class Foo(object): pass
    >>> class Bar(Foo): pass
    >>> class Boop(Bar): pass
    >>> [c.__name__ for c in base_classes(Boop)]
    ['Bar', 'Foo', 'object']
    '''
    classes = []
    for cl in clazz.__bases__:
        classes += [cl] + base_classes(cl)
    return list(set(classes))

# thanks Python Cookbook
def wrapfunc(obj, name, processor, avoid_doublewrap = True):
    call = getattr(obj, name)
    if avoid_doublewrap and getattr(call, 'processor', None) is processor:
        return

    original_callable = getattr(call, 'im_func', call)
    def wrappedfunc(*args, **kwargs):
        return processor(original_callable, *args, **kwargs)

    wrappedfunc.original = call
    wrappedfunc.processor = processor

    wrappedfunc.__name__ = getattr(call, '__name__', name)
    if inspect.isclass(obj):
        if hasattr(call, 'im_self'):
            if call.im_self:
                wrappedfunc = classmethod(wrappedfunc)
        else:
            wrappedfunc = staticmethod(wrappedfunc)

    setattr(obj, name, wrappedfunc)

def unwrapfunc(obj, name):
    setattr(obj, name, getattr(obj, name).original)

def tracing_processor(original_callable, *args, **kwargs):
    r_name = getattr(original_callable, '__name__', '<unknown>')
    r_args = [primitives.try_this((lambda: repr(a)), '<%s at %s>' % (type(a), id(a)))
              for a in args]
    r_args.extend(['%s-%r' % x for x in kwargs.iteritems()])

    print '-> %s(%s)' % (r_name, ', '.join(r_args))
    return original_callable(*args, **kwargs)

def add_tracing(class_object, method_name):
    wrapfunc(class_object, method_name, tracing_processor)

def trace(clz):
    'Adds tracing print statements for entering and exiting all methods of a class.'

    for meth, v in inspect.getmembers(clz, inspect.ismethod):
        if not meth.startswith('__'):
            add_tracing(clz, meth)

def typecounts(contains = None, objs=None):
    import gc

    if objs is None:
        objs = gc.get_objects()

    counts = defaultdict(int)

    for obj in objs:
        counts[type(obj).__name__] += 1

    if contains is not None:
        contains = lambda s, ss = contains: s[0].find(ss) != -1

    return filter(contains, sorted(counts.iteritems(), key = lambda a: a[1], reverse = True))


def funcinfo(func):
    """
    Returns a simple readable string describing a function's name and location
    in the codebase.

    >>> from util import strip_html
    >>> funcinfo(strip_html)
    '<strip_html (primitives.py:710)>'
    """
    if not hasattr(func, 'func_code'):
        return repr(func)

    name = getattr(func, '__name__', getattr(getattr(func, '__class__', None), '__name__', '<UNKNOWN OBJECT>'))
    c = func.func_code

    filename = c.co_filename
    if not isinstance(filename, str):
        filename = '??'
    else:
        try:
            try:
                filepath = path(c.co_filename)
            except UnicodeDecodeError:
                pass
            else:
                if filepath.name == '__init__.py':
                    filename = filepath.parent.name + '/' + filepath.name
                else:
                    filename = filepath.name
        except Exception:
            print_exc()

    return '<%s (%s:%s)>' % (name, filename, c.co_firstlineno)

def leakfinder():
    import wx
    from pprint import pprint
    from util import typecounts
    import gc

    f = wx.Frame(None, pos=(30,30),
                 style = wx.DEFAULT_FRAME_STYLE|wx.FRAME_TOOL_WINDOW | wx.STAY_ON_TOP)

    b = wx.Button(f, -1, 'memory stats')
    b2 = wx.Button(f, -1, 'all functions')
    b3 = wx.Button(f, -1, 'all unnamed lambdas')

    sz = f.Sizer = wx.BoxSizer(wx.VERTICAL);
    sz.AddMany([b,b2,b3])


    f.stats = {}
    def onstats(e):
        new = typecounts()
        news = dict(new)

        for cname in news.keys():
            if cname in f.stats:
                diff = news[cname] - f.stats[cname][0]
                f.stats[cname] = (news[cname], diff)
            else:
                f.stats[cname] = (news[cname], 0)

        print '****' * 10
        pprint(sorted(f.stats.iteritems(), key = lambda a: a[1]))

    def on2(e, filterName = None):
        funcs = [o for o in gc.get_objects() if type(o).__name__ == 'function']
        counts = defaultdict(int)

        for name, f in [(f.__name__, f) for f in funcs]:
            if filterName is not None and name != filterName: continue
            t = path(f.func_code.co_filename).name, f.func_code.co_firstlineno
            counts[t] += 1

        print '((Filename, Line Number), Count)'
        pprint(sorted(list(counts.iteritems()), key= lambda i: i[1]))

        #for name in [f.__name__ for f in funcs]:
        #    counts[name]+=1

        #pprint(sorted(list(counts.iteritems()), key= lambda i: i[1]))

    b.Bind(wx.EVT_BUTTON, onstats)
    b2.Bind(wx.EVT_BUTTON, on2)
    b3.Bind(wx.EVT_BUTTON, lambda e: on2(e, '<lambda>'))
    f.Sizer.Layout()
    f.Fit()
    f.Show()


def counts(seq, groupby):
    # accumulate counts
    counts = defaultdict(int)
    for obj in seq:
        counts[groupby(obj)] += 1

    # return descending [(count, group), ...]
    return sorted(((count, val) for val, count in counts.iteritems()), reverse = True)


class InstanceTracker(object):
    '''
    Mixin to track all instances of a class through a class variable "_instances"

    Provides cls.CallAll(func, *a, **k) as well.

    If you're not using CallAll, beware--the references in _instances are weakref.ref
    objects--i.e., to get the real instances:

    filter(None, (r() for r in cls._instances))
    '''

    def track(self):
        # store a weak reference to the instance in the
        # class's "_instances" list
        try:
            _instances = self.__class__._instances
        except AttributeError:
            self.__class__._instances = [ref(self)]
        else:
            # Make sure we don't already have a reference to this object.
            for wref in _instances:
                if wref() is self:
                    break
            else:
                # Keep a weak reference in self.__class__._instances
                _instances.append(ref(self))

    @classmethod
    def all(cls):
        objs = []

        try:
            wrefs = cls._instances
        except AttributeError:
            # an instance hasn't been __new__ed yet.
            return []

        import wx
        for wref in wrefs[:]:
            obj = wref()
            if obj is not None:
                if wx.IsDestroyed(obj):
                    wrefs.remove(wref)
                else:
                    objs.append(obj)

        return objs

    @classmethod
    def CallAll(cls, func, *args, **kwargs):
        'Calls func(obj, *a, **k) on all live instances of this class.'

        import wx

        try:
            instances = cls._instances
        except AttributeError:
            return # no instances were created yet.

        removeList = []

        for wref in instances:
            obj = wref()
            if obj is not None and not wx.IsDestroyed(obj):
                try:
                    func(obj, *args, **kwargs)
                except TypeError:
                    print type(obj), repr(obj)
                    raise
            else:
                removeList.append(wref)

        for wref in removeList:
            try:
                instances.remove(wref)
            except ValueError:
                pass # weakrefs can go away


class DeadObjectError(AttributeError):
    pass

class DeadObject(object):
    reprStr = "Placeholder for DELETED %s object! Please unhook all callbacks, observers, and event handlers PROPERLY."
    attrStr = "Attribute access no longer allowed - This object has signaled that it is no longer valid!"

    def __repr__(self):
        if not hasattr(self, "_name"):
            self._name = "[unknown]"
        return self.reprStr % self._name

    def __getattr__(self, *args):
        if not hasattr(self, "_name"):
            self._name = "[unknown]"
        raise DeadObjectError(self.attrStr % self._name)

    def __nonzero__(self):
        return 0

def generator_repr(g):
    '''
    A nicer __repr__ for generator instances.
    '''
    frame = g.gi_frame
    code = frame.f_code
    return '<generator %s (%s:%d) at 0x%08x>' % \
            (code.co_name, code.co_filename, frame.f_lineno, id(g))

def gc_diagnostics(stream = None):
    '''
    prints a detailed GC report to stream (or stdout) about "interesting"
    objects in gc.get_objects(), based on things like __len__,
    sys.getreferents, etc.
    '''
    import gc, sys, linecache
    import locale
    from operator import itemgetter
    from itertools import ifilterfalse, imap
    getrefcount = sys.getrefcount

    if stream is None:
        stream = sys.stdout

    # Collect garbage first.
    linecache.clearcache()
    gc.collect()

    def w(s): stream.write(s + '\n')

    filter_objects = ((), '', )
    filter_types   = (type,)
    objs = [(getrefcount(o), o) for o in gc.get_objects()    # gather (refcount, object) if
            if not isinstance(o, filter_types) and           # not is any of the types above
            not any(o is a for a in filter_objects)]         # and is not any of the objects above

    itemgetter0 = itemgetter(0)
    itemgetter1 = itemgetter(1)
    objs.sort(key=itemgetter0)
    num_objs = len(objs)

    # Print the total number of objects
    w('%d objects' % num_objs)

    ##
    # find objects with len() returning obscenely large numbers
    ##
    N = 600 # threshold
    notallowed = (basestring, ) # don't care about long strings...
    # ...or module dictionaries

    import __builtin__
    blacklist = set()
    oldlen = 0
    modlen = len(sys.modules)
    while modlen != oldlen:
        blacklist |= set(id(m.__dict__) for m in sys.modules.itervalues() if m)
        for m in sys.modules.values():
            if m and hasattr(m, '__docfilter__'):
                blacklist.add(id(m.__docfilter__._globals))
        oldlen = modlen
        modlen = len(sys.modules)
    blacklist.add(id(__builtin__))
    blacklist.add(id(__builtin__.__dict__))
    blacklist.add(id(sys.modules)) # also exclude sys.modules
    blacklist.add(id(locale.locale_alias))
    if sys.modules.get('stringprep', None) is not None:
        import stringprep
        blacklist.add(id(stringprep.b3_exceptions))
    blacklist.add(id(objs))        # and the gc.get_objects() list itself

    def blacklisted(z):
        return (isinstance(z, notallowed) or id(z) in blacklist or z is blacklist)

    def blacklisted_1(z):
        z = z[-1]
        return blacklisted(z)

    def large_sequence(z):
        try:
            return len(z) > 300 and not blacklisted(z)
        except:
            pass

    def saferepr(obj):
        try:
            # use generator_repr if necessary
            if hasattr(obj, 'gi_frame'):
                try:
                    return generator_repr(obj)
                except Exception, e:
                    pass
            return repr(obj)
        except Exception, e:
            try: return '<%s>' % type(obj).__name__
            except: return '<??>'

    ##
    # Print the most referenced objects

    num_most_reffed = min(int(num_objs * .05), 20)
    most_reffed = ifilterfalse(blacklisted_1, reversed(objs))

    w('\n\n')
    w('*** top %d referenced objects' % num_most_reffed)
    w('sys.getrefcount(obj), id, repr(obj)[:1000]')

    for nil in xrange(num_most_reffed):
        try:
            rcount, obj = most_reffed.next()
        except StopIteration:
            break

        w('%d %d: %s' % (rcount, id(obj), saferepr(obj)[:1000]))
#        referrers = [foo for foo in [(getrefcount(o), o) for o in gc.get_referrers(obj)    # gather (refcount, object) if
#                    if not isinstance(o, filter_types) and           # not is any of the types above
#                    not any(o is a for a in filter_objects) and not blacklisted(o) and isinstance(o, dict)]
#                    if foo[0]>10]
#        for ref in referrers:
#            w('\t%d %d: %s' % (ref[0], id(ref[1]), saferepr(ref[1])[:1000]))



    #
    ##

    import util.gcutil as gcutil
    def safe_nameof(o):
        try:
            return gcutil.nameof(o)[:200]
        except:
            return '[?]'

    ##
    # print the first thousand characters of each objects repr
    w('\n\n')
    w('*** objects with __len__ more than %d' % N)
    w('__len__(obj), repr(obj)[:1000]')

    large_objs = sorted([(len(a), id(a), safe_nameof(a), saferepr(a)[:2000])
                         for (obj_refcount, a) in objs if large_sequence(a)],
                        key = itemgetter0, reverse = True)

    for count, _id, nameof, s in large_objs:
        if _id != id(objs):
            w('count %d id %d: %s %s' % (count, _id, nameof, s))
    #
    ##

    ##
    # Print "count: 'typename'" for the top 20 most instantiated types
    # that aren't builtin types.
    w('\n\n')
    _typecounts = typecounts(objs = imap(itemgetter1, objs))

    num_types = 20
    w('*** top %d instantiated types' % num_types)
    builtin_names = set(__builtins__.keys())
    tc_iter = ifilterfalse(lambda _x: builtin_names.__contains__(itemgetter0(_x)), _typecounts)
    for nil in range(num_types):
        try:
            tname, tcount = tc_iter.next()
        except StopIteration:
            break

        w('%d: %r' % (tcount, tname))

    funcinfos = defaultdict(int)
    for refcount, obj in objs:
        if callable(obj):
            try:
                finfo = funcinfo(obj)
            except:
                continue
            funcinfos[finfo] += refcount

    num_infos = min(len(funcinfos), 20)
    funcinfos = funcinfos.items()
    funcinfos.sort(key=itemgetter1, reverse=True)
    w('\n\n')
    w('*** %d most referenced callables' %  num_infos)
    for i in range(num_infos):
        finfo, frcount = funcinfos[i]
        w('%d: %r' % (frcount, finfo))

    #
    # show all top level WX objects
    #
    try:
        import wx
    except ImportError:
        pass
    else:
        w('\n\n*** top level windows')
        for tlw in wx.GetTopLevelWindows():
            w(' - '.join((saferepr(tlw), saferepr(tlw.Name))))

    ##
    # Print out anything in gc.garbage
    #

    w('\n\n*** gc.garbage')
    if not gc.garbage:
        w('(none)')
    else:
        for obj in gc.garbage:
            w(saferepr(obj))


    ##
    # Print out objects with refcounts >>> len(referrers)
    #
    w('\n\n*** high refcounts w/out referrers')
    for refcount, obj in find_high_refcounts():
        w('%d: %s' % (refcount, repr(obj)[:100]))

HIGH_REFCOUNT = 500

def _high_refcounts(getrefcount=sys.getrefcount):
    for obj in gc.get_objects():
        refcount = getrefcount(obj)
        if refcount > HIGH_REFCOUNT:
            yield refcount, obj

def find_high_refcounts(limit = 10,
                        # localize hack
                        key=operator.itemgetter(0),
                        getrefcount=sys.getrefcount,
                        get_referrers=gc.get_referrers,
                        get_objects=gc.get_objects):
    '''
    returns a sorted list of [(refcount, object), ...] for objects who
    have a higher refcount than number of referrers.
    '''

    blacklist = set(
        [id(tuple())],
    )

    l = []
    for refcount, obj in _high_refcounts():
        if id(obj) not in blacklist:
            delta = refcount - len(get_referrers(obj))
            if delta:
                l.append((delta, obj))
                l.sort(reverse=True, key=key)
                del l[limit:]

    return l



import cProfile, _lsprof
class EnableDisableProfiler(cProfile.Profile):
    '''
    Subclasses cProfile.Profile to add enable and disable methods.
    '''

    def __init__(self, *a, **k):
        self.enabled = False
        _lsprof.Profiler.__init__(self, *a, **k)

    def enable(self):
        self.enabled = True
        return _lsprof.Profiler.enable(self)

    def disable(self):
        self.enabled = False
        return _lsprof.Profiler.disable(self)

    def print_stats(self, sort=-1):
        import pstats
        pstats.Stats(self, stream = sys.stderr).strip_dirs().sort_stats(sort).print_stats()

if __name__ == '__main__':
    from pprint import pprint
    pprint(typecounts('Graphics'))
