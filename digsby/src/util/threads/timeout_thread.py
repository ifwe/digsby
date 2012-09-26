'''
Timers which run on a background thread, and execute your callback function on that background thread.

Timer intervals are in seconds!
'''

from __future__ import with_statement
from itertools import count
from operator import attrgetter
from threading import Condition
from peak.util.imports import whenImported
import sys
from util import default_timer
from logging import getLogger; log = getLogger('timeout_thread')
from traceback import print_exc
from os.path import split as pathsplit
from functools import wraps

TR = None
CV = Condition()

from heapq import heappush, heapify, heappop

from .bgthread import BackgroundThread

__all__ = ['TimeOut', 'Timer', 'call_later', 'ResetTimer', 'RepeatTimer', 'delayed_call']

class TimeRouter(BackgroundThread):
    '''
    A thread to run Timers and occasional repetetive actions.
    This implements a single thread for all of them.
    '''

    ids = count()

    def __init__(self, cv):
        BackgroundThread.__init__(self, name = 'TimeRouter')

        self.count = self.ids.next()
        self.done  = False
        self.cv    = cv

        self.timeouts = []

    def add(self, timeout):
        '''
        Adds a TimeOut object to the internal queue

        @param timeout: an instance of TimeOut
        @type timeout: TimeOut
        '''
        with self.cv:
            timeout.compute_timeout()
            if timeout not in self.timeouts:
                heappush(self.timeouts, timeout)

            self.cv.notifyAll()

    def stop(self):
        with self.cv:
            self.done = True
            del TR.timeouts[:]
            TimeRouter.add = Null
            TimeOut.start = Null
            self.cv.notifyAll()

    join = stop # WARNING: DOES NOT ACTUALLY JOIN

    def resort(self):
        '''
        Cause the heap to resort itself.
        '''
        with self.cv:
            heapify(self.timeouts)
            self.cv.notifyAll()


    def run(self):
        from util.introspect import use_profiler
        self.BeforeRun()
        try:
            res = use_profiler(self, self._run)
        finally:
            self.AfterRun()
        return res

    def _run(self):
        with self.cv:
            while not self.done:
                setattr(self, 'loopcount', getattr(self, 'loopcount', 0) + 1)
                timeouts = self.timeouts
                if not timeouts: #this is so we can start the thread and
                                      #then add stuff to it
                    self.cv.wait()
                    if self.done: break

                if len(timeouts) > 1000:
                    log.warning('um thats a lot of timeouts: %d', len(timeouts))

                for x in timeouts: x.compute_timeout()

                heapify(timeouts) # timeouts are maintained in a sorted order in a heap
                while timeouts and timeouts[0].finished():
                    setattr(self, 'loopcount', getattr(self, 'loopcount', 0) + 1)
                    heappop(timeouts)

                if not timeouts:
                    t = None
                    break

                t = timeouts[0].compute_timeout()

                while t <= 0:
                    setattr(self, 'loopcount', getattr(self, 'loopcount', 0) + 1)
                    front = heappop(timeouts)

                    if not front.finished():
                        self.cv.release()
                        try:
                            front.process()
                        except Exception, e:
                            front.finished = lambda *a, **k: True
                            print_exc()
                            log.log(100, "caught exception in process, FIX this NOW!: %r, %r", front, e)
                            del e
                        finally:
                            self.cv.acquire()
                        if self.done: break

                    if not front.finished():
                        front.compute_timeout()
                        heappush(timeouts, front)

                    if not timeouts:
                        t = None
                        break

                    t = timeouts[0].compute_timeout()
                if self.done: break
                if t is None:
                    break

                self.cv.wait(t + t/100)
                if self.done: break

                # clear any tracebacks
                sys.exc_clear()

            #we're done, so take us out of action,
            #and then release the lock
            global TR
            log.info('TimeRouter %r id(0x%x) is done', TR, id(TR))
            TR = None

def join():
    'Ends the timeout thread.'

    global TR, CV
    with CV:
        if TR is not None:
            TR.join()

class TimeOut(object):
    '''
    The base class that is used by TimeRouter.
    in a nutshell: if TimeRouter is a queue, everything in the queue should be
    a TimeOut
    '''

    def __init__(self):
        global CV
        self._cv = CV
        self._started  = False
        self._finished = False

    def __hash__(self):
        return hash(id(self))

    def start(self):
        global TR
        with self._cv:
            if TR is None:
                TR = TimeRouter(self._cv)
                TR.start()
            self._started  = True
            self._finished = False
            TR.add(self)
            self._cv.notifyAll()

    def stop(self):
        with self._cv:
            self._finished = True
            self._cv.notifyAll()
        if getattr(self, '_verbose', True):
            log.debug("%r done.", self)

    def compute_timeout(self):
        '''
        Returns the amount of time from now after which process should be called

        Implementing classes must set self._last_computed to this value before
        the method returns
        '''
        raise NotImplementedError

    last_computed = property(attrgetter('_last_computed'))

    def started(self):
        return self._started

    def finished(self):
        return self._finished

    def process(self):
        '''
        The method where things happen

        Implementing classes which are done after this call should
        call self.stop() before this method exits
        '''
        raise NotImplementedError

    def __cmp__(self, other):
        ret = self.last_computed - other.last_computed
        if   ret > 0: ret =  1
        elif ret < 0: ret = -1
        else:         ret =  cmp(hash(self), hash(other))
        return ret

class Timer(TimeOut):
    def __init__(self, interval, function, *args, **kwargs):
        assert callable(function)
        int(interval)
        self._interval = interval
        self._func = function
        self._args = args
        self._kwargs = kwargs

        self._called_from = self._getcaller()
        TimeOut.__init__(self)

    def _getcaller(self):
        '''
        Grab the name, filename, and line number of the function that created
        this Timer.
        '''

        f = sys._getframe(2)
        caller_name = f.f_code.co_name
        filename = pathsplit(f.f_code.co_filename)[-1]
        linenumber = f.f_code.co_firstlineno
        self.called_from = '%s:%s:%s' % (filename, caller_name, linenumber)


    def __repr__(self):
        from util import funcinfo
        return '<%s (from %s), callable is %s>' % (self.__class__.__name__, self.called_from, funcinfo(self._func))

    def start(self):
        self.done_at = default_timer() + self._interval
        TimeOut.start(self)

    def compute_timeout(self):
        self._last_computed = self.done_at - default_timer()
        return self._last_computed

    def cancel(self):
        self.stop()

    def process(self):
        self.stop()
        self._func(*self._args, **self._kwargs)

    def isAlive(self):
        return self.started() and not self.finished()

    def stop(self):
        with self._cv:
            self.done_at = default_timer()
            self.compute_timeout()
            TimeOut.stop(self)

    @property
    def remaining(self):
        return self.done_at - default_timer()


def call_later(interval, function, *a, **k):
    t = Timer(interval, function, *a, **k)
    t.start()
    return t


class ResetTimer(Timer):
    '''
    A timer that can be reset
    '''
    def __init__(self, *a, **k):
        Timer.__init__(self, *a, **k)
        self.waiting = False

    def compute_timeout(self):
        if self.waiting:
            self._last_computed = default_timer() + 5
            return self._last_computed
        else:
            return Timer.compute_timeout(self)

    def process(self):
        self._func(*self._args, **self._kwargs)
        self.waiting = True

    def temp_override(self, new_time):
        with self._cv:
            self.done_at = default_timer() + new_time
            self._cv.notifyAll()

    def reset(self, new_time = None):
        with self._cv:
            if new_time is not None:
                self._interval = new_time

            self.waiting = False
            self.done_at = default_timer() + self._interval

            if self.finished():
                self.start()
            else:
                self._cv.notifyAll()
#        else:
#            global TR, CV
#            with CV:
#                if TR is None:
#                    self.start()
#                else:
#                    TR.resort()

class RepeatTimer(Timer):

    def __init__(self, *a, **k):
        Timer.__init__(self, *a, **k)
        self.paused = None

    #def __repr__(self):
        #if hasattr(self, 'done_at'):
        #    return '<RepeatTimer (%.2f)>' % self.compute_timeout()
        #else:
        #    return '<RepeatTimer %s>' % id(self)

    def compute_timeout(self):
        if self.paused is not None:
            self._last_computed = self.paused
            return self._last_computed
        else:
            self._last_computed = self.done_at - default_timer()
            return self._last_computed

    def pause(self):
        'pause the countdown'
        with self._cv:
            self.paused = self.compute_timeout() or .01

    def unpause(self):
        'resume the countdown'
        with self._cv:
            assert self.paused is not None, 'must be paused to unpause'
            self.done_at = self.paused + default_timer()
            self.paused = None

    def temp_override(self, new_time):
        'set the time remaining to new_time'
        with self._cv:
            self.done_at = default_timer() + new_time
            self._cv.notifyAll()

    def temp_reset(self, new_time):
        'set the time remaining to new_time, start/unpause the timer if stopped/paused'
        with self._cv:
            self.paused = None
            self.done_at = default_timer() + new_time

            if not self.isAlive():
                TimeOut.start(self)
            else:
                self._cv.notifyAll()

    def process(self):
        self._func(*self._args, **self._kwargs)
        self.done_at = default_timer() + self._interval

    def reset(self, new_time = None):
        '''
        reset, timer will go off in new_time or current interval
        starts the timer if stopped/paused
        '''
        with self._cv:
            if new_time is not None:
                self._interval = new_time

            self.paused = None
            self.done_at = default_timer() + self._interval

            if self.finished():
                self.start()
            else:
                self._cv.notifyAll()
#        else:
#            global TR, CV
#            with CV:
#                if TR is None:
#                    self.start()
#                else:
#                    TR.resort()
    def stop(self):
        '''
        turns the timer off
        '''
        with self._cv:
            self.paused = None
            Timer.stop(self)

def delayed_call(func, seconds, wxonly = False):
    '''
    Function wrapper to make function invocation only happen after so many seconds.

    Recalling the function will set the timer back to the original "seconds" value.
    '''

    assert callable(func)

    def ontimer(*a, **k):
        func._rtimer.stop()
        func(*a, **k)

    @wraps(func)
    def wrapper(*a, **k):
        try:
            timer = func._rtimer
        except AttributeError:
            # timer is being created for the first time.
            if wxonly:
                import wx
                timer = func._rtimer = wx.PyTimer(lambda: ontimer(*a, **k))
                timer.start = timer.reset = lambda s=seconds*1000, timer=timer: timer.Start(s)
                timer.stop  = timer.Stop
            else:
                timer = func._rtimer = ResetTimer(seconds, lambda: ontimer(*a, **k))

            timer.start()
        else:
            # timer already exists.
            timer.reset()

            if wxonly:
                timer.notify = lambda: ontimer(*a, **k)

    return wrapper

def TimeRouterCallLater(*a, **k):
    t = Timer(0, *a, **k)
    t._verbose = False
    t.start()

def wakeup():
    TimeRouterCallLater(lambda: None)

def _register_call_later(callbacks):
    callbacks.register_call_later('TimeRouter', TimeRouterCallLater)
whenImported('util.callbacks', _register_call_later)

if __name__ == "__main__":
    from util import CallCounter
    class WaitNSeconds(TimeOut):

        def __init__(self, seconds, name):
            TimeOut.__init__(self)
            self._finished = False
            self.seconds = seconds
            self.name    = name
            self.totaltime = 0
            self.cc = CallCounter(4, self.stop)
            self.done_at = default_timer() + seconds

        def compute_timeout(self):
            self._last_computed = self.done_at - default_timer()
            return self._last_computed

        def process(self):
            x = default_timer() - self.done_at + self.seconds
            self.totaltime += x
            print "%s done, waited %f, total:%f" % (self.name, x, self.totaltime)
            self.done_at = default_timer() + self.seconds
            self.cc()



    one = WaitNSeconds(1, "one")
    two = WaitNSeconds(3, "two")
    three = WaitNSeconds(3, "three")
    two.done_at = three.done_at
    one.start()
    two.start()
    three.start()
    TR.join()

    def cb():
        print 'the time is now:',default_timer()
    _5sec = ResetTimer(5, cb)
    _2sec = ResetTimer(2, cb)
    _5sec.start()
    _2sec.start()
    from time import sleep
    for i in range(5):
        sleep(2)
        _2sec.reset()
        print 'reset 2'

    _5sec.reset()
    print 'reset 5'
    sleep(6)
    _5sec.stop()
    _2sec.stop()
    TR.join()
