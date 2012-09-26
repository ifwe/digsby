from util.primitives.safeeval import safe_eval, SafeEvalException, unallowed_ast_nodes
import unittest
import time

should_raise = [
'import sys',
'__import__("sys")',
"(lambda: None).func_globals['__builtins__'].quit()",
]

class TestSafeEval(unittest.TestCase):
    def test_should_raise(self):
        for expr in should_raise:
            self.assertRaises(SafeEvalException,
                safe_eval, expr)

    def test_builtin(self):
        # attempt to access a unsafe builtin
        self.assertRaises(SafeEvalException,
            safe_eval, "open('test.txt', 'w')")

    def test_getattr(self):
        # attempt to get arround direct attr access
        self.assertRaises(SafeEvalException, \
            safe_eval, "getattr(int, '__abs__')")

    def test_func_globals(self):
        # attempt to access global enviroment where fun was defined
        self.assertRaises(SafeEvalException, \
            safe_eval, "def x(): pass; print x.func_globals")

    def test_lowlevel(self):
        # lowlevel tricks to access 'object'
        self.assertRaises(SafeEvalException, \
            safe_eval, "().__class__.mro()[1].__subclasses__()")

    def test_timeout_ok(self):
        if 'CallFunc' in unallowed_ast_nodes:
            return # disabled since function calls are disabled

        # attempt to exectute 'slow' code which finishes within timelimit
        def test(): time.sleep(2)
        env = {'test':test}
        safe_eval("test()", env, timeout_secs = 5)

    def test_timeout_exceed(self):
        # attempt to exectute code which never teminates
        self.assertRaises(SafeEvalException, \
            safe_eval, "while 1: pass")

    def test_invalid_context(self):
        # can't pass an enviroment with modules or builtins
        import __builtin__
        env = {'f' : __builtin__.open, 'g' : time}
        self.assertRaises(SafeEvalException, \
            safe_eval, "print 1", env)

    def test_callback(self):
        if 'CallFunc' in unallowed_ast_nodes:
            return # disabled since function calls are disabled

        # modify local variable via callback
        self.value = 0
        def test(): self.value = 1
        env = {'test':test}
        safe_eval("test()", env)
        self.assertEqual(self.value, 1)

if __name__ == "__main__":
    unittest.main()

