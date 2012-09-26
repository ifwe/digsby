import time
import gc
import types
import sys
import util
import util.threads.threadpool as threadpool

def is_match(x):
    try:
        return isinstance(x, types.TracebackType)
    except:
        return False

def do_something_good():
    return 3 + 4

def do_something_bad():
    id()

def main():
    threadpool.ThreadPool(15)

    for i in range(50):
        util.threaded(do_something_bad)()

    time.sleep(1)
    gc.collect()

    for i in range(50):
        util.threaded(do_something_good)()

    for i in xrange(50):
        util.threaded(sys.exc_clear)()

    time.sleep(1)
    gc.collect()

    print len(filter(is_match, gc.get_objects()))

if __name__ == '__main__':
    main()
