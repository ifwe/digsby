from tests import TestCase, test_main

import researchdriver.driver
STARTED = researchdriver.driver.STARTED
ALREADY_RUNNING = researchdriver.driver.ALREADY_RUNNING
Driver = researchdriver.driver.Driver

class DriverTests(TestCase):
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

if __name__ == '__main__':
    test_main()
