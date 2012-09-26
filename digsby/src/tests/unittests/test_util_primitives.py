from __future__ import with_statement

import sys
from tests import TestCase, test_main
from contextlib import contextmanager
from util.primitives.error_handling import try_this, with_traceback
from util.primitives.funcs import isint
from util.primitives.mapping import odict
from util.primitives.strings import preserve_whitespace
import traceback

def rabbithole():
    rabbithole()

python_debug_build = hasattr(sys, 'gettotalrefcount')

class TestUtilPrimitives(TestCase):
    def test_try_this(self):
        'Ensure try_this squashes exceptions'

        def raise_it(e):
            raise e

        self.assert_equal(5, try_this(lambda: 1/0, 5))
        self.assert_equal('foo', try_this(lambda: raise_it(AssertionError), 'foo'))

        if not python_debug_build:
            self.assert_raises(RuntimeError, rabbithole)
            self.assert_equal('bar', try_this(rabbithole, 'bar'))

    def test_with_traceback(self):
        'Test with_traceback'

        def test_prints_traceback(func):
            def test_print_exc():
                test_print_exc.succeed = True
            test_print_exc.succeed = False


            with replace_function(traceback, 'print_exc', test_print_exc):
                with_traceback(func)

            self.assert_(test_print_exc.succeed, '%r did not call traceback.print_exc()' % func)

        if not python_debug_build:
            test_prints_traceback(rabbithole)
        test_prints_traceback(lambda: 1/0)

    def test_isint(self):
        self.assert_(isint('5'))
        self.assert_(isint('123'))
        self.assert_(isint('-2321'))
        self.assert_(not isint('1.5'))
        self.assert_(not isint('.'))
        self.assert_(not isint(''))
        self.assert_(not isint(' '))
        self.assert_(not isint('foo'))
        self.assert_(not isint('5 foo'))
        self.assert_(not isint('foo 5'))

    def test_odict(self):
        d = odict()
        d['foo'] = 'bar'
        d['meep'] = 'baz'
        d[321] = 123
        d[None] = None

        self.assert_equal(['foo', 'meep', 321, None], d.keys())
        self.assert_equal(['bar', 'baz', 123, None], d.values())
        self.assert_equal([('foo', 'bar'), ('meep', 'baz'), (321, 123), (None, None)],
                          d.items())

        d.pop(321)

        self.assert_equal(['foo', 'meep', None], d.keys())
        self.assert_equal(['bar', 'baz', None], d.values())
        self.assert_equal([('foo', 'bar'), ('meep', 'baz'), (None, None)],
                          d.items())

        self.assert_raises(KeyError, lambda: d.pop(456))

    def test_preserve_whitespace(self):
        cases = [
            ('', ''),
            ('test', 'test'),
            ('<b>test</b>', '<b>test</b>'),
            (' ', ' '),
            ('  ', '&nbsp;&nbsp;'),
            ('   ', '&nbsp;&nbsp;&nbsp;'),
            ('test abc\ndef', 'test abc<br />def'),
        ]

        for inp, expected in cases:
            self.expect_equal(expected, preserve_whitespace(inp))

@contextmanager
def replace_function(module, function_name, replfunc):
    assert hasattr(replfunc, '__call__')
    assert isinstance(function_name, basestring)

    oldfunc = getattr(module, function_name)
    try:
        setattr(module, function_name, replfunc)
        yield
    finally:
        setattr(module, function_name, oldfunc)



if __name__ == '__main__':
    test_main()
