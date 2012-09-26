import unittest

class bar(object):
    def bar(self):
        print 'bar'


class AddRemoveTests(unittest.TestCase):

    def test_add_remove(self):
        from util.observe import ObservableList
        l = ObservableList()
        b = bar()
        l.add_observer(b.bar)
        l.remove_observer(b.bar)
        self.failIf(any(l.observers.values()), 'still have observers')


def main():
    unittest.main()

if __name__ == '__main__':
    main()
