'''
Easy network callbacks.

    >> @callsback
       def longNetworkOperation(callback = None):
           if socket.performOp():
               callback.success()
           else:
               callback.error()

    >> longNetworkOperation(success = lambda: log('yay'), error = on_fail)


Inspiration from pyxmpp
'''
from __future__ import with_statement
from introspect import funcinfo
from primitives.funcs import Delegate
from functools import wraps
from logging import getLogger
from traceback import print_exc
import sys
import threading

log = getLogger('callbacks')

CALLBACKS = ('success', 'error', 'timeout')

call_later_lock = threading.Lock() #not reentrant, there should be no side-effects when using this lock.
call_laters = dict()

def register_call_later(threadname, call_later):
    with call_later_lock:
        call_laters[threadname] = call_later

def unregister_call_later(threadname):
    with call_later_lock:
        call_laters.pop(threadname)

DO_NOTHING = lambda *a, **k: None

class CallLater(object):
    def __init__(self, cb, threadname=None):
        assert callable(cb)
        self.threadname = threadname or threading.currentThread().getName()
        if self.threadname not in call_laters:

            try:
                cb_dbg_str = ', '. join(str(s) for s in [funcinfo(cb), cb.func_code.co_filename, cb.func_code.co_firstlineno])
            except Exception:
                cb_dbg_str = 'Error making debug string. Repr is: {%s}' % funcinfo(cb)
            if cb is not DO_NOTHING:
                pass
#                log.warning("WARNING: %s is supposed to be called later, but thread %s does not have a call later mechanism!",
#                            cb_dbg_str, self.threadname)
        self.cb = cb

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, funcinfo(self.cb))

    def __call__(self, *a, **k):
        if threading.currentThread().getName() != self.threadname \
            and self.threadname in call_laters:

            try:
                return call_laters[self.threadname](lambda: self.cb(*a, **k))
            except Exception:
                print >> sys.stderr, "callback is %s" % funcinfo(self.cb)
                raise

        else:
            try:
                return self.cb(*a, **k)
            except Exception:
                print >>sys.stderr, '%s in %s (%s). args/kwargs are: %r,%r' % (getattr(self.cb, '__name__', funcinfo(self.cb)), self.cb.__module__,
                                                       funcinfo(self.cb), a,k)
                raise

class CallLaterDelegate(Delegate):
    def __init__(self, *a):
        Delegate.__init__(self, (CallLater(x) for x in a))

    def __iadd__(self, f):
        if isinstance(f, list):
            for thing in f:
                self += thing
        else:
            self.append(CallLater(f))
        return self

    def remove(self, x):
        for y in self:
            if y.cb == x:
                return super(CallLaterDelegate, self).remove(y)
        else:
            return super(CallLaterDelegate, self).remove(x)

class Callback(object):

    _callback_names = CALLBACKS

    def __init__(self, _cbnames = None, **cbs):
        #self.inited = False
        if _cbnames is not None:
            self._callback_names = _cbnames
#        def printhey(*a, **k):
#            print 'hey!'

        for name, callback in cbs.iteritems():
            if not callable(callback):
                raise TypeError('keyword args to Callback must be callable: %s' % name)
            setattr(self, name, CallLaterDelegate(callback))
            attr = getattr(self, name)

#            attr += printhey

        #self.inited = True


    def __getattr__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            if attr in self._callback_names:
                return CallLaterDelegate() #CallLater(DO_NOTHING)
            else:
                raise

    def __setattr__(self, attr, val):
        #assert not self.inited
        object.__setattr__(self, attr, val)

    def __call__(self, *a, **k):
        return self.success(*a,**k)

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, ' '.join('%s=%s'% item for item in self.__dict__.items()))

EMPTY_CALLBACK = Callback()
DefaultCallback = EMPTY_CALLBACK
CALLBACK_ATTR = "_iscallback"

def callback_adapter(f, do_return=True):
    @callsback
    def wrapped(*a, **k):
        cb = k.pop('callback')
        try:
            retval = f(*a, **k)
        except Exception, e:
            cb.error(e)
        else:
            cb.success(retval)
            if do_return:
                return retval
    return wrapped

def callsback(func, callbacks_ = CALLBACKS):
#    if 'callback' not in func.func_code.co_varnames:
#        raise AssertionError('function with callsback decorator (%s(%d) - %s) must '
#                             'have callback argument' %
#                             (func.func_code.co_filename, func.func_code.co_firstlineno,
#                              func.func_name))

    @wraps(func)
    def wrapper(*secret_a, **secret_kws):
        # Check that the original function has a callback argument

        cb = None
        # User can optionally can pass a Callback object
        if 'callback' in secret_kws:
            if any((cbname in secret_kws) for cbname in callbacks_):
                raise AssertionError('use callback or individual callbacks')
            cb = secret_kws['callback']
        else:

            # Otherwise calllables like "success = lambda: ..." can be passed
            for cbname in callbacks_:
                if cbname in secret_kws:
                    if cb is None:
                        cb = Callback(_cbnames = None if callbacks_ is CALLBACKS else callbacks_)
                    if not callable(secret_kws[cbname]):
                        raise TypeError('%s must be callable' % cbname)

                    mycb = CallLaterDelegate(secret_kws[cbname])

                    setattr(cb, cbname, mycb)
                    del secret_kws[cbname]
            secret_kws['callback'] = cb

        # No callbacks were specified. Use the empty one.
        if cb is None:
            _cbnames = None if callbacks_ is CALLBACKS else callbacks_
            secret_kws['callback'] = cb = Callback(_cbnames = _cbnames)


        '''

        Details of semantics of return values:

        If an exception is raised during the function:
            cb.error      returns a false value: exception is re-raised.
                          returns a true  value: exception is not raised -- has been handled

        If execution completes normally:
            func          returns a false value: no added effect, value is returned
                          returns True (NOTE: must be the value True!):
                                      cb.success is called, value is returned

        These conditions are to guarantee that old callbacks still function the same
        way and future functionality is present.

        '''

        try:
            val = func(*secret_a, **secret_kws)
        except Exception, e:
            print_exc()
            from util import callany
            if not callany(cb.error, e):
                raise
            val = None
        else:
            if val is True:
                cb.success()

        return val
    setattr(wrapper, CALLBACK_ATTR, True)
    return wrapper

def is_callsback(f):
    return bool(getattr(f, CALLBACK_ATTR, False))

def named_callbacks(names = ()):
    def wrapper(func):
        return callsback(func, names)
    return wrapper

@callsback
def do_cb(seq, callback = None):
    CallbackSequence(seq, callback=callback)()

class CallbackSequence(object):
    #
    #TODO: add a "simultaneous" mode
    #
    def __init__(self, sequence, callback):
        self.iter = iter(sequence)
        self.callback = callback
        self.n = 0

    def __call__(self, *a):
        self.n = self.n + 1
        try:
            next = self.iter.next()
        except StopIteration:
            log.debug('stop iteration, calling success: %r',
                     funcinfo(self.callback.success))
            self.callback.success()
        else:
            log.debug('%s #%d: %r',
                     funcinfo(self.callback), self.n, funcinfo(next))

            next(*a, **dict(success = self, error = self.callback.error))


@callsback
def do_cb_na(seq, callback = None):
    CallbackSequenceNoArgs(seq, callback=callback)()

class CallbackSequenceNoArgs(object):
    #
    #TODO: add a "simultaneous" mode
    #
    def __init__(self, sequence, callback):
        self.iter = iter(sequence)
        self.callback = callback
        self.n = 0

    def __call__(self, *a):
        self.n = self.n + 1
        try:
            next = self.iter.next()
        except StopIteration:
            log.debug('stop iteration, calling success: %r',
                     funcinfo(self.callback.success))
            self.callback.success()
        else:
            log.debug('%s #%d: %r',
                     funcinfo(self.callback), self.n, funcinfo(next))

            next(**dict(success = self, error = self.callback.error))

def wxcall(func):
    @wraps(func)
    def wrapper(*a, **k):
        CallLater(func, threadname='MainThread')(*a, **k)
    return wrapper

class CallbackStream(object):
    '''
    a wrapper for a file like object that notifies a progress callback and a
    finished callback.

    also can be cancelled via .cancel() -- will raise CallbackSteram.Cancel
    '''
    class Cancel(Exception):
        pass

    def __init__(self, stream, progress, finished):
        self._progress = progress or Null
        self._finished = finished or Null
        self.cancelled = False

        self.stream = stream

    def read(self, bytes = -1):
        if self.cancelled:
            raise CallbackStream.Cancel

        try:
            data = self.stream.read(bytes)
            self.on_progress(self.stream.tell())
        except ValueError:
            data = ''

        if data == '':
            self.stream.close()
            if not self.cancelled:
                self.on_finished()
        return data

    def cancel(self):
        self.stream.close()
        self.cancelled = True

    def tell(self):
        return self.stream.tell()

    def seek(self, *a, **k):
        return self.stream.seek(*a, **k)

    def on_progress(self, num_bytes):
        self._progress(num_bytes)

    def on_finished(self):
        self._finished()
        self._progress = self._finished = Null

    def fileno(self):
        return self.stream.fileno()

    @property
    def name(self):
        return self.stream.name

if __name__ == '__main__':

    class MyProtocol(object):

        @callsback
        def networkOperation(self, someArg, callback = None):
            callback.success()

    def good():
        print 'success'

    def bad():
        print 'bad'

    c = Callback(success = good)

    MyProtocol().networkOperation(5, callback = c)    # should print 'success'
    MyProtocol().networkOperation(5, success = good)  # should print 'success'
    MyProtocol().networkOperation(5)                  # should print nothing
