from threading import Thread, currentThread
from random import choice, randint
from weakref import ref
from time import sleep
from Queue import Queue
import gc

import wx


num_threads = 20
num_labels = 10
num_repeats = 500


class _forallobj(object):
    def __init__(self, obj):
        object.__setattr__(self, 'obj', obj)

    def __setattr__(self, attr, val):
        for elem in self.obj:
            setattr(elem, attr, val)

def forall(seq):
    return _forallobj(seq)


def test_threads():
    f = wx.Frame(None)


    s = f.Sizer = wx.BoxSizer(wx.VERTICAL)

    labels = []
    for x in xrange(num_labels):
        l = wx.StaticText(f, -1)
        s.Add(l)
        labels.append(l)

    funcs = []
    def foo1():
        while True:
            bar = [meep**2 for meep in xrange(randint(1, 10000))]
            sleep(randint(1, 200) / 200.0)
            #print 'foo1', currentThread().getName()

    def foo2():
        while True:
            objects = []
            for x in xrange(20000):
                objects.append(object())

            sleep(randint(1, 200) / 200.0)
            if randint(1,5) == 5:
                gc.collect()

    q = Queue()

    def foo3():
        while True:
            item = q.get()
            weakitem  = ref(item)
            del item
            q.task_done()
            #print 'foo3', currentThread().getName(), q.qsize()
            sleep(.001)

    def on_timer():
        for x in xrange(randint(1,5)):
            item = choice((wx.EvtHandler, wx.Rect))()
            q.put(item)


    funcs = [foo1, foo2, foo3]

    def wrapper(func):
        def inner(*a, **k):
            gc.set_debug(gc.DEBUG_STATS)
            return func(*a, **k)

        return inner


    def make_thread():
        t = Thread(target = wrapper(choice(funcs)))
        t.setDaemon(True)
        return t

    threads = [make_thread() for x in xrange(num_threads)]

    f.Show()

    @wx.CallAfter
    def later():
        for t in threads:
            t.start()

    b = wx.Button(f, -1, 'gc')
    b.Bind(wx.EVT_BUTTON, lambda e: gc.collect())

    a = wx.GetApp()
    a.timer = wx.PyTimer(on_timer)
    a.timer.Start(15, False)

    a.other_timer = wx.PyTimer(wx.StressTest)
    a.other_timer.Start(1000, False)

def main():
    import gc
    gc.set_debug(gc.DEBUG_STATS)

    a = wx.PySimpleApp()
    test_threads()
    a.MainLoop()

if __name__ == '__main__':
    main()