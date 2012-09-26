import unittest
from stats_counters.stanzas.action import Action

class TestData(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass

    def testEmptyInput(self):
        'explicit call with no args is invalid'
        self.assertRaises(ValueError, lambda: Action())

    def testBadInput(self):
        'whitelist'
        self.assertRaises(TypeError, lambda: Action(type='foo'))

    def testEmpty(self):
        self.assertEqual(str(Action('im_sent')), '<action xmlns="digsby:stats:counter" type="im_sent"/>')

    def testValue(self):
        self.assertEqual(str(Action('im_sent', value=1)), '<action xmlns="digsby:stats:counter" type="im_sent" value="1"/>')

    def testValue2(self):
        self.assertEqual(str(Action('im_sent', value=None)), '<action xmlns="digsby:stats:counter" type="im_sent"/>')

    def testInitialResult(self):
        self.assertEqual(str(Action('im_sent', initial=5, value=2, result=7)),
                         '<action xmlns="digsby:stats:counter" type="im_sent" initial="5" value="2" result="7"/>')

    def testRoundtrip(self):
        self.assertEqual(str(Action('im_sent', value=None)),
                         str(Action(Action('im_sent', value=None).as_xml().children)))

    def testRoundtrip2(self):
        self.assertEqual(str(Action('im_sent', initial=5, value=2, result=7)),
                         str(Action(Action('im_sent', initial=5, value=2, result=7).as_xml().children)))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
