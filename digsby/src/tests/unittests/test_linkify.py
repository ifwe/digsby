from tests import TestCase, test_main
from tests.testnet import linkify_test_strings
import util

class TestLinkify(TestCase):
    def test_linkify(self):
        '''
        Test all the linkify strings in src/tests/testnet.py
        '''

        for url, result in linkify_test_strings:
            self.expect_equal(util.linkify(url), result)


if __name__ == '__main__':
    test_main()
