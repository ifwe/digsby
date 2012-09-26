try:
    from researchdriver.driver import *
except ImportError:
    from plugins.researchdriver.driver import *
import unittest

try:
    _
except NameError:
    import gettext
    gettext.install('digsby')

class DriverTests(unittest.TestCase):
    class profile(object):
        username = 'digsby'

    def setUp(self):
        try:
            Driver.stop()
        except Exception:
            pass

    def tearDown(self):
        try:
            Driver.stop()
        except Exception:
            pass

    def testStart(self):
        self.failUnlessEqual(Driver.start(self.profile), STARTED, "driver failed to start")
        self.failUnless(Driver.running(), "driver failed to start")

    def testAlreadyStarted(self):
        self.failUnlessEqual(Driver.start(self.profile), STARTED, "driver failed to start")
        self.failUnless(Driver.running(), "driver failed to start")
        self.failUnlessEqual(Driver.start(self.profile), ALREADY_RUNNING, "driver did not recognize it was already started")
        self.failUnless(Driver.running(), "driver failed to start")

    def testStop(self):
        self.failUnlessEqual(Driver.start(self.profile), STARTED, "driver failed to start")
        self.failUnless(Driver.running(), "driver failed to start")
        Driver.stop()
        self.failIf(Driver.running())

def main():
    unittest.main()

def testrun():
    class profile(object):
        username = '12/16/2008 test1'
    print Driver.start(profile)
    print Driver.proc.kill.__doc__
    time.sleep(30)
    Driver.stop()

def testmemory():
    class profile(object):
        username = 'testsecurity1'
    for i in xrange(60000):
        Driver.start(profile)
        if ((i / 100) * 100) == i:
            print i
        Driver.stop()

if __name__ == '__main__':
    main()
