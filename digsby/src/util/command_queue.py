from util import Timer, threaded
from util.primitives.funcs import do
from Queue import Queue
from threading import RLock
from functools import wraps
from util import callsback, callany
from Queue import Empty

import logging
log = logging.getLogger('cmdq')

class SerialCommandQueue(object):
    '''When multiple threads are not allowed'''
    #needs to be merged with CommandQueue, careful of threads.
    def __init__(self, start_hooks=None, end_hooks=None, retry_time=2):
        self.start_hooks = start_hooks
        self.end_hooks = end_hooks
        self.retry_time = retry_time
        self.do_queue = Queue()
        self.state_lock = RLock()
        self.loop_running = False

    def add_new(self, (func, instance, a, k)):
        with self.state_lock:
            self.do_queue.put((func, instance, a, k))
            if not self.loop_running:
                self.loop_running = True
                self.flush()

    @threaded
    def flush(self):
        try:
            do(f() for f in self.start_hooks)
        except Exception, e:
            import traceback
            traceback.print_exc()
            with self.state_lock:
                self.do_queue = Queue()
                self.loop_running = False
                return

        self.state_lock.acquire()

        while True: #have stuff
            try:
                #get an item
                (func, instance, a, k) = self.do_queue.get(False)
            except Empty:
                break
            else:
                #do item
                self.state_lock.release()
                func(instance, *a, **k)
                self.state_lock.acquire()

        self.state_lock.release()

        do(f() for f in self.end_hooks)

        with self.state_lock:
            if self.do_queue.empty():
                self.loop_running = False
            else:
                self.flush()

class CommandQueue(object):
    def __init__(self, start_hooks, end_hooks, shutdown_interval=30,
                 retry_time=2):
        self.start_hooks = start_hooks
        self.end_hooks = end_hooks
        self.shutdown_interval = shutdown_interval
        self.retry_time = retry_time
        self.do_queue = Queue()
        self.state_lock = RLock()
        self.timer = Timer(shutdown_interval, self.finish)
        self.loop_running = False
        self.initialized = False
        self.initializing = False
        self.shutting_down = False
        self.timer_valid = False

    def add_new(self, (func, instance, a, k) ):
#        print "add_new"
        with self.state_lock:
            self.timer_valid = False
            self.timer.cancel()
            self.do_queue.put((func, instance, a, k))
            if not self.loop_running:
                #initialize if necessary, callback is start timer, flush
                self.loop_running = True
                if self.initialized:
                    self.flush()
                elif not self.initializing:
                    self.initializing = True
                    threaded(self.initialize)()

    def initialize(self):
#        print "initialize"
        with self.state_lock:
            if self.shutting_down:
                t = Timer(self.retry_time, threaded(self.initialize))
                t.start()
                return

        try:
            do(f() for f in self.start_hooks)
        except Exception, e:

            import traceback
            traceback.print_exc()

            #log.error('Error initializing cmdq: %s', str(e))
            with self.state_lock:
                self.do_queue = Queue()
                self.loop_running = False
                self.initialized = False
                self.initializing = False
                return

        with self.state_lock:
            self.initialized = True
            self.initializing = False
        self.flush()

    @threaded
    def flush(self):
#        print "flush"
        self.state_lock.acquire()

        while True: #have stuff
            self.state_lock.release()
            try:
                #get an item
                (func, instance, a, k) = self.do_queue.get(False)
            except Empty:
                break
            else:
                #do item
                func(instance, *a, **k)
            finally:
                self.state_lock.acquire()

#        print "end of flush1"
        self.loop_running = False
        self.timer_valid = True
        self.timer.start()
        self.state_lock.release()
#        print "end of flush2"

    @threaded
    def finish(self):
#        print "finish"
        with self.state_lock:
            if not self.timer_valid:
                return
            self.initialized = False
            self.shutting_down = True

        do(f() for f in self.end_hooks)

        with self.state_lock:
            self.shutting_down = False

def cmdqueue(qname='cmdq'):
    def wrapper2(func):
        def wrapper1(instance, *args, **kws):
#            print instance, args, kws
            cmdq = getattr(instance, qname)
            cmdq.add_new((func, instance, args, kws))
        return wrapper1
    return wrapper2

def callback_cmdqueue(qname='cmdq'):
    def wrapper2(func):
        @wraps(func)
        @callsback
        def wrapper(instance, callback = None, *args,  **kws):
#            callback=kws.pop('callback')
            requestID=kws.pop('requestID', None)
            cmdq = getattr(instance, qname)

            def do_thing(*a, **k):
                try:
                    result = func(instance, *args, **kws)
                    exception = None
                except Exception, e:
                    exception = e
                    result = None

                    import traceback, sys
                    sys.stderr.write('The following exception occurred in callback_cmdqueue:\n')
                    traceback.print_exc()

                if exception:
                    callany(callback.error, e)
                else:
                    callany(callback.success, result)

            cmdq.add_new((do_thing, None, (), {}))
        return wrapper
    return wrapper2

__all__ = ['callback_cmdqueue', 'cmdqueue', 'CommandQueue']
