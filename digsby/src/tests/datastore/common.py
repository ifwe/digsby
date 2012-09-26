# if __name__ == '__main__':
import sys
import textwrap
import path
import unittest

import digsbysite

from datastore.common import DictDatastore, NestedDictDatastore, YAMLDatastore

class DictDatastoreTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            'emptystring': '',
            'string': 'here\'s a string',
            'zero': 0,
            'int': 1,
            'none': None,
            'empty tuple': (),
            'tuple': (1, 'foo', None),
            'empty list': [],
            'list': ['a', 'b', 'c'],
            'empty dict': {},
            'dict': {'foo': 'bar'},
        }
        self.datastore = DictDatastore(self.data)

    def tearDown(self):
        del self.datastore
        del self.data

    def test_keys(self):
        self.assertEqual(set(self.datastore.keys()), set(self.data.keys()))

    def test_items(self):
        self.assertEqual(sorted(list(self.datastore.items())), sorted(list(self.data.items())))

    def test_get_success(self):
        for key in self.datastore.keys():
            try:
                val = self.datastore.get(key)
            except Exception:
                pass
            if isinstance(val, type(self.datastore)):
                val = val.data
            self.assertEqual(val, self.data.get(key), key)

    def test_get_fail(self):
        self.assertRaises(KeyError, lambda: self.datastore.get('bad key'))

    def test_get_default(self):
        for k, v in self.datastore.items():
            default = v
            val = self.datastore.get('bad key', default = default)
            val = getattr(val, 'data', val)
            self.assertEqual(default, val)

    def test_set_new(self):
        for k, v in self.datastore.items():
            new_k = 'new ' + k
            self.datastore.set(new_k, v)
            new_v = self.datastore.get(new_k)
            if isinstance(new_v, type(self.datastore)):
                new_v = new_v.data
            self.assertEqual(v, new_v)

    def test_set_existing(self):
        new_value = 'previously nonexistent value'
        for k in sorted(self.datastore.keys()):
            self.datastore.set(k, new_value)
            self.assertEqual(self.datastore.get(k), new_value)

    def test_set_empty(self):
        for k, v in sorted(self.datastore.items()):
            self.datastore.set(k)
            self.assertRaises(KeyError, lambda: self.datastore.get(k))

    def test_clear(self):
        for k, v in self.datastore.items():
            self.datastore.clear(k)
            self.assertRaises(KeyError, lambda: self.datastore.get(k))

class NestedDictDatastoreTests(DictDatastoreTests):
    def setUp(self):
        self.data = {
            'a': {'b': {'c': 0},
                  'd': {'e': 'f'},
                  'g': 'h',
                  },
            'i': 'j',
        }
        key = lambda x: tuple(x.split('.'))
        self.flat_data = dict([(key('a.b.c'), 0),
                               (key('a.d.e'), 'f'),
                               (key('a.g'), 'h'),
                               (key('i'), 'j')])

        self.datastore = NestedDictDatastore(data = self.data)

    def tearDown(self):
        del self.data
        del self.flat_data
        del self.datastore

    def test_set_new(self):
        for k, v in sorted(self.datastore.items(), reverse=True):
            new_k0 = (('new ' + k[0]),)
            new_k = new_k0 + k[1:]
            self.datastore.set(new_k, v)
            new_v = self.datastore.get(new_k)

            if isinstance(new_v, type(self.datastore)):
                new_v = new_v.data
            self.assertEqual(v, new_v)

    def test_items(self):
        items = sorted(list(self.datastore.items()))
        for k, v in items:
            self.assertEqual(type(k), tuple)
        self.assertEqual(items, sorted(list(self.flat_data.items())))

    def test_get_success(self):
        for key in self.datastore.keys():
            try:
                val = self.datastore.get(key)
            except Exception:
                pass
            if isinstance(val, type(self.datastore)):
                val = val.data
            self.assertEqual(val, self.flat_data[key], (key, val, self.flat_data[key]))

        for key in self.flat_data.keys():
            if not all(isinstance(x, basestring) for x in key):
                continue
            string_key = '.'.join(key)
            self.assertEqual(self.flat_data[key], self.datastore.get(key))
            self.assertEqual(self.flat_data[key], self.datastore.get(string_key))

    def test_keys(self):
        self.assertEqual(set(self.datastore.keys()), set(self.flat_data.keys()))


class YAMLDatastoreTests(NestedDictDatastoreTests):
    def create_datastore(self):
        filepath = path.path(__file__).parent / 'test.yaml'
        with filepath.open('wb') as f:
            f.write(textwrap.dedent(
                '''
                ---
                a:
                  b:
                    c: 0
                  d:
                    e: f
                  g: h
                i: j
                '''
            ))
        return YAMLDatastore(filepath = filepath)

    def setUp(self):
        self.datastore = self.create_datastore()
        key = lambda x: tuple(x.split('.'))
        self.flat_data = dict([(key('a.b.c'), 0),
                               (key('a.d.e'), 'f'),
                               (key('a.g'), 'h'),
                               (key('i'), 'j')])

    def tearDown(self):
        del self.datastore
        del self.flat_data
        (path.path(__file__).parent / 'test.yaml').remove()

    def test_file_write(self):
        new_dstore = self.create_datastore()
        self.test_set_new()
        self.test_set_existing()
        new_items = set(new_dstore.items())
        my_items = set(self.datastore.items())
        self.assertEqual(my_items, new_items)

def suite():
    s = unittest.TestSuite()
    loader = unittest.TestLoader()
    tests = map(loader.loadTestsFromTestCase, [
        DictDatastoreTests,
        NestedDictDatastoreTests,
        YAMLDatastoreTests,
    ])

    s.addTests(
        tests
    )
    return s

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
    #unittest.main()
