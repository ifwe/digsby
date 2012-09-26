import wx
import unittest

try:
    _
except NameError:
    import gettext
    gettext.install('Digsby')

if getattr(wx, 'WXPY', False):
    wx.WindowClass = wx._Window
else:
    wx.WindowClass = wx.Window

try:
    sentinel
except NameError:
    import bootstrap
    bootstrap.install_sentinel()

class TestCase(unittest.TestCase):
    def setUp(self):
        if wx.GetApp() is None:
            self._init_once()

    def _init_once(self):
        global app
        from tests.testapp import testapp
        app = testapp()


    def run(self, result=None):
        if result is None:
            self.result = self.defaultTestResult()
        else:
            self.result = result

        return unittest.TestCase.run(self, result)

    def expect(self, val, msg=None):
        '''
        Like TestCase.assert_, but doesn't halt the test.
        '''
        try:
            self.assert_(val, msg)
        except:
            self.result.addFailure(self, self._exc_info())

    def expectEqual(self, first, second, msg=None):
        try:
            self.failUnlessEqual(first, second, msg)
        except:
            self.result.addFailure(self, self._exc_info())

    expect_equal = expectEqual

    assert_equal = unittest.TestCase.assertEqual
    assert_raises = unittest.TestCase.assertRaises


test_main = unittest.main
