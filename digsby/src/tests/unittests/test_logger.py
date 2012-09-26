'''
tests the common.logger.Logger class, which is responsible for logging messages
to disk, and for reading them back
'''

from common.logger import Logger
from common.message import Message
from contextlib import contextmanager
from tests import TestCase, test_main
import os
import shutil
from datetime import datetime

__all__ = ['TestLogger']

test_logdir = os.path.join(os.path.dirname(__file__), 'data', 'logs', 'kevin')

class MockAccount(object):
    def __init__(self, service, username):
        self.name = service
        self.username = username

class MockBuddy(object):
    def __init__(self, name, protocol):
        self.name = name
        self.protocol = protocol
        self.service = protocol.name

    def increase_log_size(self, bytes):
        pass

class MockProtocol(object):
    def __init__(self, name, username):
        self.name = name
        self.username = username
    
    def should_log(self, msg):
        return True

class MockConversation(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class TestLogger(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.logger = Logger(output_dir = test_logdir)
        self.protocol = MockProtocol('aim', 'digsby03')
        self.account = MockAccount('aim', 'digsby03')
        self.self_buddy = MockBuddy('digsby03', self.protocol)
        self.buddy = MockBuddy('digsby01', self.protocol)
        self.convo = MockConversation(buddy = self.buddy, ischat=False, protocol=self.protocol)

    def test_log_dir_exists(self):
        log_path = self.logger.pathfor(self.account, self.buddy)
        self.assert_(os.path.isdir(log_path), 'directory does not exist: %r' % log_path)

    def test_read_messages(self):
        history = list(self.logger.history_for(self.account, self.buddy))
        self.assert_equal(10, len(history))
        self.assert_(bool(msg) for msg in history)

    @contextmanager
    def scratch_logger(self):
        SCRATCH = 'scratch' # directory to store temp logs
        if os.path.isdir(SCRATCH):
            self.assert_(False, 'scratch directory should not exist already')

        os.makedirs(SCRATCH)
        self.assert_(os.path.isdir(SCRATCH))
        try:
            logger = Logger(output_dir = SCRATCH)
            yield logger
        finally:
            shutil.rmtree(SCRATCH)

    def test_write_read_unicode(self):
        with self.scratch_logger() as logger:
            unicode_msg = u'\xd0\xb9\xd1\x86\xd1\x83\xd0\xba\xd0\xb5'

            # log a message with unicode
            msg = Message(buddy = self.buddy,
                message = unicode_msg,
                type = 'incoming',
                conversation = self.convo,
                timestamp = datetime(month=12, day=25, year=2000, hour=12))

            logger.on_message(msg)

            # check that the file is on disk
            logfile = os.path.join(logger.OutputDir, r'aim\digsby03\digsby01_aim\2000-12-25.html')
            self.assert_(os.path.isfile(logfile), logfile)

            history = logger.history_for(self.account, self.buddy)

            # assert that unicode was encoded and decoded properly
            logmsg = list(history)[0]
            self.assert_(logmsg.message == unicode_msg)

    def test_html_entities(self):
        with self.scratch_logger() as logger:

            message = u'foo bar <b>meep</b>'.encode('xml')

            msg = Message(buddy = self.buddy,
                message = message,
                type = 'incoming',
                conversation = self.convo,
                timestamp = datetime(month=12, day=25, year=2000, hour=12))

            logger.on_message(msg)

            # check that the file is on disk
            logfile = os.path.join(logger.OutputDir, r'aim\digsby03\digsby01_aim\2000-12-25.html')
            self.assert_(os.path.isfile(logfile), logfile)
            print open(logfile,'rb').read()

            history = list(logger.history_for(self.account, self.buddy))
            self.assert_equal(1, len(history))
            self.assert_('<' not in history[0].message)


if __name__ == '__main__':
    test_main()
