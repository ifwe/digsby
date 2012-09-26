from __future__ import with_statement
from tests import TestCase, test_main

from util.merge import merge_values, merge

class TestMerge(TestCase):
    def test_merge(self):
        d = {1: 2}
        merge_values(d, 3, 4); assert d == {1: 2, 3: 4}

        d = {1: 2}
        merge_values(d, 1, 3); assert d == {1: 3}

        d, d2 = {1: {2: 3}}, {1: {2: 4}}
        res = merge(d, d2)
        assert res == {1: {2: 4}}, repr(res)

        d, d2 = {1: {2: 3}}, [(1, {2: 4})]
        res = merge(d, d2)
        assert res == {1: {2: 4}}, repr(res)

if __name__ == '__main__':
    test_main()
