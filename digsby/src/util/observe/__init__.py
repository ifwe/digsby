from observable import *
from observabledict import *
from observablelist import *
from observableproperty import *

def clear_all():
    import gc

    count = 0
    for obj in gc.get_objects():
        try:
            observers = getattr(obj, 'observers', None)
            clear     = getattr(observers, 'clear', None)
            if clear is not None:
                clear()
                count += 1
        except:
            pass

    return count

import logging
def add_observers(obj, argslist):
    for func, attr in argslist:
        if not hasattr(obj, attr):
            logging.critical('%s has no attribute %s to observe!',
                             obj.__class__.__name__, attr)
        else:
            obj.add_observer(func, attr)


if __name__ == '__main__':
    import doctest, unittest

    import observable

    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(observable))
    unittest.TextTestRunner().run(suite)
