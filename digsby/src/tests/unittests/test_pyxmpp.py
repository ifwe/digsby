from tests import TestCase, test_main
from tests.debugxmlhandler import DebugXMLHandler
from pyxmpp.xmlextra import StreamReader
from jabber.threadstream import ignore_xml_error

class TestPyxmpp(TestCase):
    def test_undefined_namespace(self):
        'Make sure we ignore undefined namespace errors.'

        s = '''<roster blah='.datagate.net.uk/Home' name='Vlada' gr:t='B' subscription='none' />'''

        handler = DebugXMLHandler()

        try:
            return StreamReader(handler).feed(s)
        except Exception, e:
            if not ignore_xml_error(e.message):
                raise

if __name__ == '__main__':
    test_main()

