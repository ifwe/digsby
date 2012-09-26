from tests import TestCase, test_main
from weakref import ref

class myobj(object):
    pass

class TestRefs(TestCase):
    def test_weakref_subclass(self):

        root = myobj()
        def foo():
            b = myobj()
            b_ref = ref(b)
            b.root = root

            gui = myobj()
            gui.b = b

            class refsub(ref):
                __slots__ = ('strong_refs',)

            root.a = refsub(b)
            b.gui = refsub(gui)

            root.a.strong_refs = [b.gui]
            b.gui.strong_refs = [root.a]
            return b_ref

        assert foo()() is None

    def test_weakref_callback(self):

        f = myobj()
        ctx = myobj()

        def cb(wr):
            ctx.called_with_ref = wr

        w = ref(f, cb)

        del f
        assert w() is None

        assert ctx.called_with_ref is w

    def test_unbound_ref_callback(self):
        from util.primitives.refs import unbound_ref

        foo = myobj()
        ctx = myobj()

        def cb(wr):
            ctx.was_called = True


        theref = unbound_ref(foo, lambda: 42, cb=cb)
        del foo

        assert ctx.was_called and theref() is None

    def test_weakref_callback_cycle(self):
        '''check the assumption that a cycle involving a weakref callback keeps
        the object alive'''

        foo = myobj()
        def cb(f=foo):
            print 'deleting foo', f

        r = ref(foo, cb)
        del foo
        assert r() is not None

if __name__ == '__main__':
    test_main()
