import unittest
from simplejson import dumps, loads
from util.json import pydumps, pyloads

class JSON_SerializeTestingSuite(unittest.TestCase):

    def test_serialization(self):
        values = [5, 'foo', u'bar', (), (1,), (1,2), [], [1], [1,2],
                  set(), set('abc'), set((1,2,3)), set(((3,), (), '')),
                  {}, {1:2}, {'a':1}, {'1': 1}, {4.3: ''}, 4.3, {'4.3':5},
                  {u'234':54}, {1:u'342'}, {1:'abc'}, {1:2,3:4,5:6},
                  {'foo': set((1,2.3,'3', (), (1,2)))},
                  frozenset('123'),None, {None:None},
                  {True:False},u'__str__foo',
                  {u'__tuple__':u'foo'}, {u'__tuple__':'foo'},
                  {'__tuple__':u'foo'}, {'__tuple__':u'foo'},
                  ['__tuple__'],'__True__',u'__None__',
                  ]
        for value in values + [values]:
            dataout = pyloads(pydumps(value))
            self.assertEquals(value, dataout)
            self.assertEqual(type(value), type(dataout))

if __name__ == "__main__":
    unittest.main()
