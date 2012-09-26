
from util.observe import Observable, ObservableList, ObservableDict
from tests.mock.mockbuddy import MockBuddy
from util import Storage

from Queue import Queue

__metaclass__ = type



class MockConversation(Observable):
    def __init__(self):
        Observable.__init__(self)

        bud = MockBuddy('fakebuddy')

        self.name          = 'fakebuddy'
        self.me            = MockBuddy('digsby007')

        self.room_list     = ObservableList([bud, self.me])
        self.typing_status = ObservableDict()
        self.buddy         = bud
        self.messages      = Queue()
        self.protocol      = Storage(self_buddy = self.me, buddies = {'digsby007': self.me})
        self.ischat        = False


    def send_typing_status(self, *a):
        pass

    def _send_message(self, msg):
        self.sent_message(msg)

    def exit(self): pass
