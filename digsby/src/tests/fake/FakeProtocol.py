import random

import common
from contacts import Group, Contact
from util.observe import ObservableDict
from util import Timer

class FakeBuddy(common.buddy):

    _renderer = 'Contact'

    def __init__(self, name, protocol):
        self.status = 'unknown'
        common.buddy.__init__(self, name, protocol)

    @property #required property
    def idle(self): return False
    @property
    def online(self): return self.status != 'offline'
    @property
    def mobile(self): return False
    @property
    def status_message(self): return "FooooooBAAAAAR!!!!"
    @property
    def away(self): return False
    @property
    def blocked(self): False

class FakeConversation(common.Conversation):
    ischat = False
    def __init__(self, protocol):
        common.Conversation.__init__(self, protocol)

    @property
    def self_buddy(self):
        return self.protocol.self_buddy

    @property
    def name(self):
        return self.self_buddy.name

    def send_typing_status(self, status):
        pass

    #really should be callsback
    def _send_message(self, message, success=None, error=None, *args, **kwargs):
        if message.startswith('msg'):
            try:
                how_long = int(message.split()[1])
                t = Timer(how_long, self.protocol.incomming_message, self.self_buddy, u"Here's your message %ds later" % how_long)
                t.start()
            except Exception:
                pass

    def exit(self):
        pass

class FakeProtocol(common.protocol):

    name = 'fake'
    NUM_BUDDIES = common.prefprop('fake.num_buddies', default=20)

    def __init__(self, username, password, hub, server=None, **options):
        common.protocol.__init__(self, username, password, hub)

        self.root_group = Group('Root', self, 'Root')
        self.buddies = ObservableDict()
        self.self_buddy = FakeBuddy('self', self)
        self.buddies['self'] = self.self_buddy
        self.conversations = {}

    def Connect(self, invisible=False):
        self.change_state(self.Statuses.ONLINE)
        g1 = Group('Foo', self, 'Foo')
        g2 = Group('Bar', self, 'Bar')
        self.buddies['foobar'] = FakeBuddy('foobar', self)
        #g1.append(Contact(self.buddies['foobar'], 'foobar'))
        self.root_group.append(g1)
        self.root_group.append(g2)

        for i in range(int(self.NUM_BUDDIES)):
            g = random.choice((g1, g2))
            buddy = FakeBuddy('FakeBuddy #%d'% (i % 3), self)
            buddy.status = random.choice(('away', 'available', 'offline'))
            g.append(buddy)

        self.root_group.notify()


    #needs to be added to Protocol NotImplemented
    def set_message(self, message, status, format = None, default_status='away'):
        pass

    #needs to be added to Protocol NotImplemented
    def set_buddy_icon(self, icondata):
        pass

    def Disconnect(self):
        self.change_state(self.Statuses.OFFLINE)

    @property
    def caps(self):
        return []

    def convo_for(self, contact):
        try:
            return self.conversations[contact.id]
        except KeyError:
            c = FakeConversation(self)
            self.conversations[contact.id] = c
            return c

    def incomming_message(self, buddy, message):
        self.conversations.values()[0].received_message(buddy, message)
