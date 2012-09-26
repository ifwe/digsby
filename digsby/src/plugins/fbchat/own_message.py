import pyxmpp.message
import jabber
from common.Conversation import default_formatted_text

FACEBOOK_MESSAGES_NS = "http://www.facebook.com/xmpp/messages"

class OwnMessage(object):
    def __init__(self, iq):
        self.iq = iq
        self.message = pyxmpp.message.Message(iq.xpath_eval('f:own-message', {'f':FACEBOOK_MESSAGES_NS})[0])
        self.from_self = self.message.xmlnode.prop('self').lower() == 'true'

    def get_to(self):
        return self.message.get_to()

    def get_from(self):
        return self.iq.get_to()

    def get_body(self):
        return self.message.get_body()

def setup(protocol, stream, *a, **k):
    def handle_own_message(iq):
        om = OwnMessage(iq)
        if om.from_self:
            return
        assert om.get_from() == protocol.stream.me
        _to = om.get_to()
        buddy = protocol.buddies[_to]
        _from = om.get_from()
#        if _to.resource is None: #send from bare to bare
#            _from = _from.bare()
#        tup = (buddy, _from, _to, stanza.get_thread())
        tup = (buddy,)
        if tup in protocol.conversations:
            convo = protocol.conversations[tup]
        else:
#            convo = jabber.conversation(self, *tup)
            convo = jabber.conversation(protocol, buddy, _from)
            protocol.conversations[tup] = convo
            convo.buddy_join(protocol.self_buddy)
            convo.buddy_join(buddy)
#        message = Message(stanza.get_node())
        convo.sent_message(default_formatted_text(om.get_body()))
        return True

    stream.set_iq_set_handler("own-message", FACEBOOK_MESSAGES_NS, handle_own_message)

