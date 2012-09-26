import sys
import lxml.html
import lxml.etree
from tests import TestCase, test_main

def parse_test_doc():
    parser = lxml.html.HTMLParser(encoding='utf-8')
    doc = lxml.html.document_fromstring('''
            <b></i>
    ''', parser = parser)

class TestLxml(TestCase):
    def test_error_log_leak(self):
        if not hasattr(sys, 'gettotalrefcount'):
            return

        before = sys.gettotalrefcount()
        for x in xrange(50):
            parse_test_doc()
        after = sys.gettotalrefcount()

        self.assert_equal(before, after)


if __name__ == '__main__':
    test_main()
