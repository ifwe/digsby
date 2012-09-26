import unittest
_tests = unittest.TestSuite()
from .common import *
_tests.addTests(suite())
from .v0 import *
_tests.addTests(suite())

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())


