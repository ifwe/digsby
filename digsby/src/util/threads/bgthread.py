from __future__ import with_statement
import util.primitives.funcs as funcs
import threading
from Queue import Queue
from functools import wraps
from traceback import print_exc

__all__ = ['BackgroundThread', 'add_before_cb', 'add_before_cb']

class DelegateThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        threading.Thread.__init__(self, group, target, name, args, kwargs,
                                  verbose)

        self.BeforeRun = funcs.Delegate()
        self.AfterRun  = funcs.Delegate()

class BackgroundThread(DelegateThread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):

        DelegateThread.__init__(self, group, target, name, args, kwargs,
                                verbose)

        self.setDaemon(True)

        global _before_run, _after_run

        self.BeforeRun[:] = _before_run
        self.AfterRun[:] = _after_run


_before_run = []
_after_run  = []

def add_before_cb(cb):
    assert callable(cb)
    global _before_run
    _before_run.append(cb)

def add_after_cb(cb):
    assert callable(cb)
    global _after_run
    _after_run.append(cb)

from thread import get_ident

class on_thread(object):
    '''
    Used as a decorator:

      @on_thread('foo')
      def do_foo_stuff():
          this_executes_on_thread_named_foo()

    And with calling a function directly:

      on_thread('foo').call(my_func, *args, **kwargs)
    '''

    threads = {}
    lock = threading.RLock()

    def __init__(self, name, daemon = True):
        self.name = name
        self.daemon = daemon

        try:
            self._id = self.threads[self.name].ident
        except KeyError:
            self._id = -1

    @property
    def thread(self):
        # should already be locked.

        try:
            return self._thread
        except AttributeError:
            with self.lock:
                try:
                    self._thread = self.threads[self.name]
                except KeyError:
                    self._thread = self.threads[self.name] = on_thread_thread(self.name, daemon=self.daemon)
                    self._thread.start()
                    self._id = self._thread.ident

            return self._thread

    def _done(self, thread_name):
        # called internally by the thread
        with self.lock:
            self.threads.pop(thread_name)

    @property
    def now(self):
        "True if the current thread is this on_thread object's thread."

        return self._id == get_ident()

    def call(self, func, *a, **k):
        assert hasattr(func, '__call__')
        self.thread.queue(func, *a, **k)

    def __call__(self, func):
        # So it acts as a decorator.

        @wraps(func)
        def wrapper(*a, **k):
            self.call(func, *a, **k)

        wrapper.on_thread = self
        return wrapper

try:
    from wx import SEHGuard
except ImportError:
    SEHGuard = lambda c: c()

class on_thread_thread(BackgroundThread):
    'yet another consumer thread'

    def __init__(self, name, daemon=True):
        BackgroundThread.__init__(self, name=name)
        self.setDaemon(daemon)
        self.work = Queue()
        self.done = False

    def run(self):
        self.BeforeRun()
        try:
            SEHGuard(self._consumer_loop)
        finally:
            self.AfterRun()

    def _consumer_loop(self):
        while not self.done:
            setattr(self, 'loopcount', getattr(self, 'loopcount', 0) + 1)
            func, args, kwargs = self.work.get()
            try:
                func(*args, **kwargs)
            except Exception:
                print_exc()
            self.work.task_done()

        on_thread(self.name)._done()

    def queue(self, func, *a, **k):
        if __debug__:
            import traceback
            self.last_stack = traceback.format_stack()
        self.work.put((func, a, k))

    def join(self):
        self.done = True
        self.work.join()

