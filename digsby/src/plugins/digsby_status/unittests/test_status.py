import unittest

URL = "http://digsby.com/"
_TAGLINE = " - I use "

MESSAGE_TAGLINE = _TAGLINE + URL
STATUS_TAGLINE = _TAGLINE + URL

TESTAPP = False

def fakeprefs():
#    from common import setfakeprefs
    global TESTAPP
    if not TESTAPP:
        TESTAPP = True
        from tests.testapp import testapp
        testapp(prefs={'digsby.status.promote_tag.upgrade_response':True},
                logging = False)
#    setfakeprefs({'digsby.status.promote_tag.upgrade_response':True})

class StatusTests(unittest.TestCase):
    def setUp(self):
        self.message = "Hi!"
        self.protocol = 'foo'
        self.protoname = 'foo'
        self.status = ''
        fakeprefs()

    def tearDown(self):
        pass

    def testTextAdd(self):
        import digsby_status
        status = self.message
        new_status = digsby_status.status_tag_urls.tag_status(status, self.protocol)
        self.assertEqual(new_status, status + MESSAGE_TAGLINE + self.protoname)

    def testRoundTrip(self):
        import digsby_status
        status = self.message
        new_status = digsby_status.status_tag_urls.tag_status(status, self.protocol)
        stripped_status = digsby_status.status_tag_urls.remove_tag_text(new_status, self.status)
        self.assertEqual(status, stripped_status)

class MyspaceIm(StatusTests):
    def setUp(self):
        super(MyspaceIm, self).setUp()
        self.protocol = 'msim'
        self.protoname = 'myspaceim'

class YahooIm(StatusTests):
    def setUp(self):
        super(YahooIm, self).setUp()
        self.protocol = 'yahoo'
        self.protoname = 'yahoo'

    def testTextAdd(self):
        import digsby_status
        status = self.message
        new_status = digsby_status.status_tag_urls.tag_status(status, self.protocol)
        self.assertEqual(new_status, status + MESSAGE_TAGLINE + self.protoname + ' ' + URL + self.protoname)

class OddMessage(StatusTests):
    def setUp(self):
        super(OddMessage, self).setUp()
        self.message = STATUS_TAGLINE

    def testRoundTrip(self):
        self.assertRaises(self.failureException,
                          super(OddMessage, self).testRoundTrip)

class OddMessage2(OddMessage):
    def setUp(self):
        super(OddMessage2, self).setUp()
        self.message = STATUS_TAGLINE + STATUS_TAGLINE

class RemoveAvailable(unittest.TestCase):

    def setUpMessage(self):
        self.message = self.status + STATUS_TAGLINE + 'asdkfjlskdljf'

    def setUpStatus(self):
        self.status = "Available"

    def setUp(self):
        self.setUpStatus()
        self.setUpMessage()
        fakeprefs()

    def testStripAvailable(self):
        import digsby_status
        stripped_status = digsby_status.status_tag_urls.remove_tag_text(self.message, self.status)
        self.assertEqual(stripped_status, '')

class RemoveAway(RemoveAvailable):
    def setUpStatus(self):
        super(RemoveAway, self).setUpStatus()
        self.status = "Away"

class DoNotRemoveMessage(unittest.TestCase):
    def setUpMessage(self):
        self.basemessage = "Foo"
        self.message = self.basemessage + MESSAGE_TAGLINE + 'alsdkfj;'

    def setUpStatus(self):
        self.status = "Available"

    def setUp(self):
        self.setUpStatus()
        self.setUpMessage()
        fakeprefs()

    def testStripMessage(self):
        import digsby_status
        stripped_status = digsby_status.status_tag_urls.remove_tag_text(self.message, self.status)
        self.assertEqual(stripped_status, self.basemessage)

class DoRemoveFoo(DoNotRemoveMessage):
    def setUpStatus(self):
        self.status = "Foo"

    def testStripMessage(self):
        self.assertRaises(self.failureException,
                          super(DoRemoveFoo, self).testStripMessage)

class DoNotRemoveMessageSpace(DoNotRemoveMessage):
    def setUpStatus(self):
        self.status = "Foo "

