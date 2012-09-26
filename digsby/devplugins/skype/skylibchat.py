#__LICENSE_GOES_HERE__

'''
http://developer.skype.com/skypekit/development-guide/conversation-class-overview
'''


import common
import skylibprotocol
from util.callbacks import callsback
from util.primitives.fmtstr import fmtstr

class SkyLibConversation(common.Conversation):
    ischat = False

    def __init__(self, protocol, buddy):
        buddies = [buddy]
        if not buddies or not all(isinstance(buddy, skylibprotocol.SkypeBuddy)
                                  for buddy in buddies):
            raise TypeError
        super(SkyLibConversation, self).__init__(protocol)
        self.c = buddy.skycontact.OpenConversation()
        self.c.OnMessage = self.OnMessage
        self.buddy_to = buddy

    def OnMessage(self, message):
        self.message = message
        if message.type == 'POSTED_TEXT':
            if message.author != self.protocol.self_buddy.name:
                self.buddy_says(self.protocol.get_buddy(message.author),
                                message.body_xml,
                                content_type='text/xml')

    @property
    def name(self):
        return self.buddy.name

    @property
    def self_buddy(self):
        return self.protocol.self_buddy

    @property
    def buddy(self):
        return self.buddy_to

    @callsback
    def _send_message(self, message, auto = False, callback=None, **opts):
        assert isinstance(message, fmtstr)
        self.c.PostText(message.format_as('xhtml'), True)

    def send_typing_status(self, status):
        return

    def buddy_join(self, buddy):
        if buddy not in self.room_list:
            self.room_list.append(buddy)
        self.typing_status[buddy] = None

    @property
    def id(self):
        return self.buddy_to

    def exit(self):
        self.c.RemoveFromInbox()
        self.protocol.conversations.pop(self.id, None)
        super(SkyLibConversation, self).exit()
