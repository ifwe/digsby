'''
Observable Tests
'''
from __future__ import with_statement

from tests import TestCase, test_main
from tests.testutil.findleaks import check_collected

import wx
import util.observe as observe
import weakref, gc

ObservableBase = observe.ObservableBase
Observable = observe.Observable
base_classes = observe.Observable

class Car(Observable): pass
class Chevy(Car): pass
class Cav(Chevy): pass

class TestObserver(object):
    def observer(self, source, attr, old, new):
        self.attr, self.old, self.new = attr, old, new

    def class_observer(self, obj, attr, old, new):
        self.obj, self.attr, self.old, self.new = obj, attr, old, new

    def __call__(self):
        attrs = (['obj'] if hasattr(self, 'obj') else []) + 'attr old new'.split()
        return tuple(getattr(self, a) for a in attrs)

class EventHandlerObserver(wx.EvtHandler):
    def on_change(self, src, attr, old, new):
        pass

class TestObservableFunctions(TestCase):

    def setUp(self):
        self.t = TestObserver()

    def testObserving(self):
        a = Observable()
        a.add_observer(self.t.observer)

        a.setnotify('foo', 'bar')
        self.assertEqual(('foo', None, 'bar'), self.t())

        a.remove_observer(self.t.observer)
        a.setnotify('foo', 'meep')
        self.assertEqual(('foo', None, 'bar'), self.t())

    def testAttrObserving(self):
        # Add an observer that's only interested in foo changes
        a = Observable()
        a.add_observer(self.t.observer, 'foo')

        result = ('foo', None, 'bar')

        a.setnotify('foo', 'bar')
        self.assertEqual(result, self.t())

        a.setnotify('other_attribute', 5)
        self.assertEqual(result, self.t())

        a.remove_observer(self.t.observer, 'foo')
        a.setnotify('foo', 'done')
        self.assertEqual(result, self.t())

    def testWeakRefs(self):
        'Make sure observable objects can be garbage collected.'

        # To see if Observable causes memory leaks, first keep a weak reference
        # to an Observable object, then add an observer to it
        obj = Observable()
        obj.add_observer(self.t.observer)
        obj_ref = weakref.ref(obj)
        self.assertEqual(obj_ref(), obj)

        obj.setnotify('color', 'red')
        self.assertEqual(self.t(), ('color', None,'red'))

        # Now delete the object, and force a garbage collect.
        del obj
        gc.collect()

        # Our weak reference should be none--meaning the object was successfully
        # garbage collected.
        self.assertEqual(obj_ref(), None)

    def test_check_collected(self):
        'Make sure the @check_collected decorator reports a leak'

        class myobject(object): pass

        # should raise AssertionError
        def foo():
            lst = []
            @check_collected
            def fail():
                o = myobject()
                lst.append(o)
                return o

        self.assertRaises(AssertionError, foo)

        # should not raise AssertionError
        def bar():
            @check_collected
            def succeed():
                return myobject()

        bar()

    def testWeakRefGui(self):
        'Ensure GUI object observers do not leak'

        eh = EventHandlerObserver()
        foo = TestObserver()

        @check_collected
        def check_evthandler_method():
            o = Observable()
            o.add_observer(eh.on_change)
            return o

        @check_collected
        def check_normal_method():
            o = Observable()
            o.add_observer(foo.observer)
            return o

        @check_collected
        def check_lambda_with_obj():
            o = Observable()
            o.add_observer(lambda *a: eh.on_change(*a), obj = eh)
            return o


    def testFreezing(self):
        car = Car()
        car.add_observer(self.t.observer)

        with car.frozen():
            car.setnotify('fuel', 500)
            car.setnotify('miles', 12000)
            car.setnotify('another', 'afdafas')
        print self.t()


if __name__ == '__main__':
    test_main()
