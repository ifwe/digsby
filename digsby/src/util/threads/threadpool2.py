from .threadpool import ThreadPool, WorkRequest
from functools import wraps
from util.callbacks import callsback
from traceback import print_exc
from threading import Lock

from logging import getLogger; log = getLogger('threadpool2')

__all__ = ['threaded', 'threaded_exclusive']

def threaded(func):
    @wraps(func)
    @callsback
    def wrapper(*a, **kws):
        callback = kws.pop('callback')
        requestID = kws.pop('requestID', None)
        req = WorkRequest(func, args=a, kwds=kws, requestID=requestID,
                          callback=callback.success,
                          exc_callback=callback.error)
        req.verbose = wrapper.verbose

        ThreadPool().putRequest(req)

    wrapper.verbose = True
    return wrapper

def threaded_exclusive(func):
    '''
    Ensures that "func" is only running on one threadpool thread at a time.

    If you call "func" while it's running 5 times, it will run once more
    after it is finished -- there is not a 1-1 correspondence between
    the number of calls and the number of runs.
    '''
    assert hasattr(func, '__call__')

    func._exclusive_count = 0
    running_lock = Lock()
    count_lock = Lock()

    @wraps(func)
    def wrapper(*a, **k):
        count_lock.acquire(True)
        if not running_lock.acquire(False):
            # another thread is running -- increment the count so that
            # we know we need to run again
            func._exclusive_count += 1
            count_lock.release()
        else:
            try:
                old_count = func._exclusive_count
                count_lock.release()

                try:
                    func(*a, **k)
                except Exception:
                    print_exc()

                # compare old_count with the count now. if it's different,
                # execute the function again
                count_lock.acquire(True)
                if old_count != func._exclusive_count:
                    count_lock.release()

                    # thunk to threaded again to avoid any stack limits
                    threaded(wrapper)(*a, **k)
                else:
                    count_lock.release()
            finally:
                running_lock.release()

    return threaded(wrapper)

