'''

test abc def

'''
from __future__ import with_statement

import asyncore
import errno
import select
import time
import traceback
import sys

from select import error as select_error
from Queue import Queue, Empty
from sys import exc_clear
from threading import RLock, currentThread
from traceback import print_exc
from asyncore import ExitNow

from logging import getLogger
log = getLogger('asyncore.thread')

INTERRUPT_sentinel = 0xDEAD

# when there are no readable/writable sockets, or asyncorethread
# callbacks, we just spin by sleeping with this value
NO_SOCKET_SLEEP = .2

def read(obj):
    try:
        obj.handle_read_event()
    except ExitNow:
        raise
    except Exception, e:
        obj.handle_error(e)

def write(obj):
    try:
        obj.handle_write_event()
    except ExitNow:
        raise
    except Exception, e:
        obj.handle_error(e)

def exc (obj):
    try:
        obj.handle_expt_event()
    except ExitNow:
        raise
    except Exception, e:
        obj.handle_error(e)

def readwrite(obj, flags):
    try:
        if flags & (select.POLLIN | select.POLLPRI):
            obj.handle_read_event()
        if flags & select.POLLOUT:
            obj.handle_write_event()
        if flags & (select.POLLERR | select.POLLHUP | select.POLLNVAL):
            obj.handle_expt_event()
    except ExitNow:
        raise
    except Exception, e:
        obj.handle_error(e)

def kpoll(timeout=0.0, map=None, amap = asyncore.socket_map, do_log=False):
    if map is None:
        map = amap

    if map:
        mapget = map.get
        r = []; w = []; e = []

        for fd, obj in map.items():
            is_r = obj.readable()
            is_w = obj.writable()

            if is_r: r.append(fd)
            if is_w: w.append(fd)
            if is_r or is_w: e.append(fd)

        if [] == r == w == e:
            time.sleep(max(timeout, NO_SOCKET_SLEEP)) # no sockets to select on
            return

        try:
            _r, _w, _e = r, w, e
            r, w, e = select.select(r, w, e, timeout)
        except select_error, err:
            if err[0] == errno.EINTR:
                return INTERRUPT_sentinel
            elif err[0] == errno.ENOTSOCK:
                BAD = None
                for _list in (r,w,e):
                    if BAD is not None:
                        break
                    for _fd in _list:
                        try:
                            real_fn = mapget(_fd).fileno()
                            if real_fn != _fd: raise Exception
                        except:
                            BAD = _fd
                            break
                del _fd, _list
                if BAD is None:
                    # wtf? do the old behavior.
                    raise err
                else:
                    bad_obj = mapget(BAD)
                    log.fatal("Removing the following item from the socket map because it is not a socket: %r", bad_obj)
                    try:    del map[BAD]
                    except KeyError: pass
                    for _list in (r,w,e):
                        if BAD in _list:
                            _list.remove(BAD)
                    del _list
            else:
                raise err
        else:
            if do_log:
                log.critical("_r, _w, _e = %r, %r, %r", _r, _w, _e)
                log.critical("r, w, e = %r, %r, %r", r, w, e)

        for fd in r:
            obj = mapget(fd)
            if obj is None: continue
            read(obj)

        for fd in w:
            obj = mapget(fd)
            if obj is None: continue
            write(obj)

        for fd in e:
            obj = mapget(fd)
            if obj is None: continue
            exc(obj)

        if r == []: return True

def callback_call(callable, callback):
    try: callable()
    except Exception, e:
        print_exc()

        # pass the exception to callback.error
        try: callback.error(e)
        except: print_exc()
    else:
        try: callback.success()
        except: print_exc()

import util.threads.bgthread

class AsyncoreThread(util.threads.bgthread.BackgroundThread):
    "Asyncore thread class."

    def __init__(self, timeout=.1, use_poll=0,map=None):
        self.flag     = True
        self.timeout  = timeout
        self.use_poll = use_poll
        self.map      = map
        self.timeouts = {}
        self.hooks    = []

        util.threads.bgthread.BackgroundThread.__init__(self, None, None, 'AsyncoreThread')

    def run(self):
        self.BeforeRun()
        try:
            util.use_profiler(self, self.loop)
        except:
            traceback.print_exc()
            raise
        finally:
            self.AfterRun()

    def join(self, timeout = None):
        self.flag = False
        util.threads.bgthread.BackgroundThread.join(self, timeout)

    def loop(self):
        global to_call

        if self.map is None:
            self.map = asyncore.socket_map
        last = 0
        fastcount = 0
        while self.flag:
            now = time.clock()
            if now - last < .1: #self.timeout, but I want a hardcoded value in case self.timeout changes to something bad.
                fastcount += 1
            else:
                fastcount = 0
            last = now
            if not getattr(self, 'loopcount', 0) % 5000:
                log.debug("Asyncorethread socket map is: %r", self.map)
            do_log = False
            if fastcount and not (fastcount % 5000):
                try:
                    log.critical("Asyncorethread may be spinning, fastcount %r socket map is: %r", fastcount, self.map)
                except Exception:
                    try:
                        log.critical("Asyncorethread may be spinning, failed to print socket map")
                    except Exception:
                        pass
                do_log = True
            setattr(self, 'loopcount', getattr(self, 'loopcount', 0) + 1)
            try:
                tocall, callback = to_call.get_nowait()
            except Empty, e:
                tocall, callback = None, None
                exc_clear()

            if tocall:
                callback_call(tocall, callback)

            empty = to_call.empty()
            timeout = self.timeout * empty

            if self.map or not empty:
                try:
                    kret = kpoll(timeout, self.map, do_log=do_log)
                except :
                    print repr(self.map)
                    raise
                else:
                    if kret == INTERRUPT_sentinel:
                        setattr(self, 'interrupt_count', getattr(self, 'interrupt_count', 0) + 1)
                        if not (self.interrupt_count % 5000):
                            log.critical('interrupt count is high: %r', self.interrupt_count)
                    else:
                        setattr(self, 'interrupt_count', 0)
            else:
                # sleep for a little longer if we've got nothing to do.
                time.sleep(.3)

            # clear any tracebacks
            exc_clear()

        if self.map:
            for sock in self.map.values():
                log.info('closing socket %r', sock)
                sock.close_when_done()

        log.info( "Asyncore Thread is done." )

    def end(self):
        log.info('stopping the network thread. obtaining lock...')

        with net_lock:
            log.info( 'Ending asyncore loop...' )
            self.flag = False
            for sock in self.map.values():
                log.info('closing socket %r', sock)
                sock.close_when_done()

    def force_exit(self):
        with net_lock:
            if self.map is None: return
            for sock in self.map.values():
                try:
                    peername = sock.getpeername()
                except:
                    peername = None
                log.critical('socket %s connected to %s', str(sock), peername)
                sock.close()
            self.map.clear()
            self.map = None
            self.flag = False
            del self.hooks

    def add_hook(self, cb):
        self.hooks.append( cb )

ref_count = 0
net_thread = None
net_lock = RLock()
running = False
to_call = Queue()

def __start():
    global net_thread, ref_count

    try:
        net_thread
    except NameError:
        # Not defined, this means it was del'd in join
        return
    else:
        if ref_count <= 1 or not(net_thread and net_thread.isAlive()):
            net_thread = AsyncoreThread()
            log.info("AsyncoreThread.start %s", ref_count)
            net_thread.start()

def start():
    global ref_count, net_thread, net_lock, running
    running = True
    with net_lock:
        ref_count += 1
        __start()


def end():
    log.critical("AsyncoreThread.end called!")
    traceback.print_stack()

def end_thread():
    global ref_count, net_thread, net_lock, running

    with net_lock:
        log.info("AsyncoreThread.end %s", ref_count)
        if net_thread:
            net_thread.end()

def join(timeout = 1.5):
    global net_thread, to_call
    if net_thread:
        log.critical("Joining with network thread, timeout is %s...", timeout)
        net_thread.join(timeout)
        if net_thread.isAlive():
            log.critical('  forcing critical exit.')

            net_thread.force_exit()
            net_thread.join()
            del net_thread

        log.critical('...done joining.')
        global call_later
        call_later = lambda call, callback=None: (call(), callback.success() if callback else None)

def call_later(call, callback = None, callnow = True, verbose = True):
    if not callable(call):
        raise TypeError, "argument must be callable"

    if callback is None:
        import util.callbacks
        callback = util.callbacks.EMPTY_CALLBACK

    if callnow and currentThread().getName() == 'AsyncoreThread' or 'net_thread' not in globals():
        import util
        try:
            call()
        except Exception, e:
            if verbose:
                traceback.print_exc()

            with util.traceguard:
                callback.error(e)
        else:
            with util.traceguard:
                callback.success()

        return
    else:
        global to_call
        to_call.put((call, callback))
        start()

import util.callbacks
util.callbacks.register_call_later('AsyncoreThread', call_later)

