import random
from tests import TestCase, test_main
import wx
import gc

def subthread_delete():
    app = wx.GetApp()
    from threading import Thread

    for x in xrange(10):
        if x % 100 == 0: print x

        num_timers = 100
        timers = []
        for x in xrange(num_timers):
            t = wx.Timer()
            timers.append(t)
            if x != 0:
                t.t = timers[x-1]

        timers[0].t = timers[-1]
        for x in xrange(100):
            timers[x].t2 = timers[random.randint(0, len(timers)-1)]



        def subthread():
            del timers[:]
            gc.collect()
            assert num_timers == len(app.pendingDelete)

        t = Thread(target=subthread)
        t.start()
        t.join()

        wx.flush_pending_delete()
        assert 0 == len(app.pendingDelete)

class TestSubthreadDelete(TestCase):
    def test_subthread_delete(self):
        return subthread_delete()

if __name__ == '__main__':
    from tests.testapp import testapp
    with testapp(plugins=False):
        subthread_delete()

    #test_main()

