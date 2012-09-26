from __future__ import with_statement
import itertools
import functools
import logging
import os, sys, traceback
import threading
import time

log = logging.getLogger('util.primitives.synch')

def lock(f):
    @functools.wraps(f)
    def wrapper1(instance, *args, **kw):
        if not hasattr(instance, '_lock'):
            try:
                instance._lock = threading.RLock()
            except AttributeError:
                raise NotImplementedError, '%s needs a _lock slot' % instance.__class__.__name__
        with instance._lock:
            val = f(instance, *args, **kw)
        return val
    return wrapper1

class RepeatCheck(object):
    '''
    A callable object that returns True if you call
    it with the same object, or the same list of objects.
    '''

    def __init__(self, idfunc = None):
        self.ids = sentinel

        if idfunc is None: idfunc = id
        self.id = idfunc

    def __call__(self, *x):
        if x == tuple():
            # clear
            self.ids = sentinel
            return
        elif len(x) != 1:
            raise TypeError('takes one argument')

        try:
            newids = [self.id(a) for a in x]
        except TypeError:
            newids = [self.id(a)]

        changed = newids != self.ids
        self.ids = newids

        return changed

def repeat_guard(func):
    'Useful for observer callbacks to elimanate redunant updates.'

    guard = RepeatCheck()

    def wrapper(src, attr, old, new):
        if guard(src): return
        return func(src, attr, old, new)

    return wrapper

class HangingThreadDaemon(threading.Thread):
    '''
    Create one, and start() it when you are closing the program.

    If the program is not exiting because of non-daemon Threads
    sticking around, it will tell you which ones are still running.
    '''
    ids = itertools.count()
    def __init__(self, wait = 3, sysexit = False):
        threading.Thread.__init__(self, name="HangingThreadDaemon %d" %
                                  self.ids.next())
        self.wait = wait
        self.sysexit = sysexit

        # the presence of this thread should not prevent normal program shutdown
        self.setDaemon(True)

    def run(self):
        time.sleep(self.wait)

        threads = list(threading.enumerate())
        if threads:
            print 'Remaining non-daemon threads:'
            for thread in threads:
                if not thread.isDaemon():
                    print ' ', thread

        collect_garbage_and_report()

        if self.sysexit:
            try:
                import common.commandline as cc
                cc.where()
            except Exception:
                traceback.print_exc()
            print >>sys.stderr, 'forcing shutdown...'
            os._exit(1)

def collect_garbage_and_report():
    import gc
    garbage_count = gc.collect()
    if garbage_count > 0:
        log.info("Garbage collected. " + str(garbage_count) + " unreachable objects")
        if garbage_count:
            log.info("Garbage left (only first 20 listed): %r", gc.garbage[:20])

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True)
