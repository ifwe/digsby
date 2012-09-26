'''
multithreaded logging performance test
'''
import sys
import wx
from logging import getLogger; log = getLogger('test_logging')
from threading import Thread
from contextlib import contextmanager

class LogThread(Thread):
    def __init__(self, n):
        Thread.__init__(self)
        self.n = n
        self.profiler = None

    def run(self):
        def foo():
            n = self.n
            for x in xrange(n):
                log.info('test %r %d', self.name, n)

        foo()


def main():
    from tests.testapp import testapp
    with testapp(release_logging=True, plugins=False):
        threads = []

        for x in xrange(10):
            threads.append(LogThread(10000))

        def foo():
            print sys.LOGFILE_NAME
            with timed(logtofile=r'c:\log.txt'):
                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

        foo()

        import os
        os._exit(0)

@contextmanager
def timed(name='', logtofile=None):
    'Shows the time something takes.'

    from time import time

    before = time()
    try:
        yield
    except:
        raise
    else:
        diff = time() - before
        msg = 'took %s secs' % diff
        if name:
            msg = name + ' ' + msg
        print msg

        if logtofile is not None:
            open(logtofile, 'a').write('%f\n' % diff)



if __name__ == '__main__':
    main()
