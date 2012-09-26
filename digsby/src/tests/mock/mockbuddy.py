__metaclass__ = type
from util.observe import Observable
from util import Storage
S = Storage
from path import path
import random
from gui import skin
from tests.mock.mockprofiles import MockProfiles

protos = ['yahoo', 'aim', 'msn', 'jabber']
status_messages = '''
working on Digsby
out for lunch
homework
'''.strip().split('\n')

from common import caps

statuses = 'away available idle'.split()

class MockProtocol(object):
    def __init__(self, protocol):
        self.name = protocol
        self.self_buddy = S(name='digsby01')
        self.buddies = {'digsby01': self.self_buddy}
    
    def get_buddy(self, name):
        return MockBuddy(name)
    
    def group_for(self, s):
        return 'group'

class MockBuddy(Observable):

    _renderer = 'Contact'
    icon_path = path(r'file:///C:/windows/Blue Lace 16.bmp')

    def __init__(self, name, status = None, protocol = 'aim', capabilities=None):
        Observable.__init__(self)
        self.remote_alias = self.name = name

        self.mockprofile       = getattr(MockProfiles,name,'')
        self.buddy             = Storage()
        self.buddy.name        = name
        self.buddy.nice_name   = name
        self.buddy.profile     = self.mockprofile
        self.icon              = skin.get('BuddiesPanel.BuddyIcons.NoIcon')
        self.icon_path         = self.icon.path
        self.icon = self.icon.PIL
        self.id                = 5
        self.status_message    = random.choice(status_messages)
        self.sightly_status    = self.status_orb = self.status = status if status else random.choice(statuses)
        self.buddy.away        = self.status=='away'

        self.protocol          = MockProtocol(protocol)
        self.protocol.icq      = random.choice([True, False])
        self.protocol.username = self.protocol.name

        self.mockcaps          = capabilities if capabilities else [caps.BLOCKABLE, caps.EMAIL, caps.FILES, caps.IM, caps.PICTURES, caps.SMS]
        self.online_time       = None
        self.buddy.protocol    = self.protocol
        self.caps              = self.mockcaps

        #self.blocked           = False


    @property
    def service(self):
        return self.protocol.name

    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.service)

    @property
    def alias(self):
        return self.name

    @property
    def idle(self):
        return self.status == 'idle'

    @property
    def info_key(self):
        return self.service + '_' + self.name

    @property
    def stripped_msg(self):
        from util import strip_html2
        return strip_html2(self.status_message)

    def GetMockProfile(self):
        return self.htmlprofile

    def idstr(self):
        return u'/'.join([self.protocol.name,
                         self.protocol.username,
                         self.name])


    @property
    def online(self):
        return True

    @property
    def num_online(self):
        return int(self.online)

    def chat(self):
        print 'wut?'

from contacts.Contact import Contact
MockBuddy.__bases__ += (Contact,)
