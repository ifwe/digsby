import util.pyppmd as ppmd
from tests import TestCase, test_main

class TestPpmd(TestCase):
    def test_encode_decode(self):
        s = 'foo foo bar foo meep meep meep foo'
        self.assertRaises(WindowsError, ppmd.pack, s)

if __name__ == '__main__':
    test_main()
