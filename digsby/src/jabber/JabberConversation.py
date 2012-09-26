from jabber.objects.x_event import X_Event, X_EVENT_NS
from jabber.objects.chatstates import ChatState, CHATSTATES_NS
from common.Conversation import Conversation
from pyxmpp.message import Message
from logging import getLogger
from jabber import JabberBuddy

from util import callsback
from pyxmpp.utils import from_utf8
from jabber.objects.x_delay import X_DELAY_NS, X_Delay
import libxml2
from common import pref
from util.primitives.fmtstr import fmtstr

log = getLogger('jabber.JabberConversation')

XHTML_IM_NS = 'http://jabber.org/protocol/xhtml-im'
XHTML_NS    = 'http://www.w3.org/1999/xhtml'

xdata_namespaces = {'xhtmlim': XHTML_IM_NS,
                    'xhtml'  : XHTML_NS}

typing_chatstates = dict(typing = 'composing',
                         typed  = 'paused')

class JabberConversation(Conversation):
#    def __init__(self, protocol, buddy, jid_to, jid_from,thread=None):
    def __init__(self, protocol, buddy, jid_to, thread=None):
        '''

        @param protocol:   a JabberProtocol Instance
        @param buddy:      the buddy you are talking to
        @param jid_to:     the jid you are talking to
        @param jid_from:   the jid you are talking from
        @param thread:     the thread id, if any (not yet used)
        '''

        if not isinstance(buddy, JabberBuddy.JabberBuddy):
            raise TypeError


        Conversation.__init__(self, protocol)
        self.buddy_to = buddy
        self.jid_to   = jid_to
#        self.jid_from = jid_from
        self.buddies  = protocol.buddies
        self.thread   = thread
        self.name     = buddy.alias

        self.reset_chat_states()

    ischat = False

    @property
    def self_buddy(self):
        return self.protocol.self_buddy

    @property
    def buddy(self): return self.buddy_to

    def reset_chat_states(self):
        self.chat_states_allowed = None
        self.x_events_allowed = None

    @callsback
    def _send_message(self, message, auto = False, callback=None, **opts):
        assert isinstance(message, fmtstr)

        if self.jid_to not in self.buddy.resources:
            self.reset_chat_states()
            self.jid_to = self.buddy.jid
        # PyXMPP will escape the message for us...
        m = Message(stanza_type = 'chat', to_jid = self.jid_to, body = message.format_as('plaintext'))

        #message = unicode(message.encode('xml'))

        #assert isinstance(message, unicode)

        append_formatted_html(m, message)

        if pref('privacy.send_typing_notifications', False):
            ChatState('active').as_xml(m.xmlnode)
            X_Event(composing = True).as_xml(m.xmlnode)

        try:
            self.protocol.send_message(m)
        except Exception, e:
            callback.error(e)
        else:
            callback.success()
        #self.sent_message(message.replace('\n', '<br />'), format)

    def send_typing_status(self, status):
        if not any((self.x_events_allowed, self.chat_states_allowed)):
            return
        m    = Message(to_jid = self.jid_to, stanza_type='chat')
        node = m.xmlnode
        if self.x_events_allowed:
            X_Event(composing = (status == 'typing')).as_xml(node)
        if self.chat_states_allowed:
            ChatState(typing_chatstates.get(status, 'active')).as_xml(node)

        self.protocol.send_message(m)

    def buddy_join(self, buddy):
        if buddy not in self.room_list:
            self.room_list.append(buddy)
        self.typing_status[buddy] = None

    def incoming_message(self, buddy, message):
        from_jid = message.get_from()
        if from_jid != self.jid_to:
            self.reset_chat_states()
        self.jid_to = from_jid
        #self.message = message
        body = get_message_body(message)

        if body:
            stamp = get_message_timestamp(message)

            if stamp:
                did_receive = self.received_message(buddy, body, timestamp = stamp, offline = True, content_type = 'text/html')
            else:
                did_receive = self.received_message(buddy, body, content_type = 'text/html')

            if did_receive:
                Conversation.incoming_message(self)

        chatstate = self.get_message_chatstate(message, body)
        if chatstate is False:
            chatstate = None
            if pref('jabber.system_message.show_gone', type=bool, default=False):
                self.system_message(_('{name} has left the conversation.').format(name=from_jid))
        self.typing_status[buddy] = chatstate

    def get_message_chatstate(self, message, body):
        'Returns "typing", "typed", or None for a <message> stanza.'
        retval = None
        xevents    = message.xpath_eval(u"jxe:x",{'jxe':X_EVENT_NS})
        chatstates = message.xpath_eval('cs:*', {'cs': CHATSTATES_NS})

        if chatstates:
            self.chat_states_allowed = True
            chatstate = ChatState(chatstates[0]).xml_element_name

            retval = {'composing':'typing',
             'paused'   :'typed',
             'gone'     : False, #left
             'inactive' : None,  #not typing or typed, not nearby?
             'active'   : None,  #not typing or typed, nearby?
             }.get(chatstate)
        if xevents:
            found_composing = X_Event(xevents[0]).composing
            if found_composing:
                self.x_events_allowed = True
            if not chatstates:
                retval = 'typing' if found_composing and not body else None

        return retval

    @property
    def id(self):
#        return (self.buddy_to, self.jid_to, self.jid_from, self.thread)
        return (self.buddy_to,)

    def exit(self):
        if self.chat_states_allowed and pref('privacy.send_typing_notifications', False):
            m    = Message(to_jid = self.jid_to, stanza_type='chat')
            node = m.xmlnode
            ChatState('gone').as_xml(node)
            self.protocol.send_message(m)
        self.protocol.conversations.pop(self.id, None)
        Conversation.exit(self)

def append_formatted_html(message_tag, message):
    '''
    Inserts an <html> node with formatted XHTML into a message tag.

      message_tag  a <message> stanza
      message      the message (a fmtstr object)

    After this method completes, the message stanza has an additional <html> child node.

    Also returns the <span> as a string.
    '''
    html = message_tag.xmlnode.newChild(None, 'html', None)
    xhtml_ns = html.newNs(XHTML_IM_NS, None)

    span_text = message.format_as('xhtml')
    body_text = '<body xmlns="%s">%s</body>' % (XHTML_NS, span_text)
    try:
        message_doc = libxml2.parseDoc(body_text.encode('utf-8'))
    except Exception:
        import traceback;traceback.print_exc()
        print 'This text failed: %r' % body_text
        raise
    message_node = message_doc.get_children()
    message_node_copy = message_node.docCopyNode(message_tag.xmlnode.doc, 1)
    html.addChild(message_node_copy)
    message_doc.freeDoc()

    return span_text

    #TODO: do I need to unlink or free nodes here?


def get_message_timestamp(message):
    'Returns a timestamp for a <message> stanza, or None.'

    xdelays = message.xpath_eval(u"jxd:x",{'jxd':X_DELAY_NS})
    if xdelays:
        delay = X_Delay(xdelays[0])
        if delay.timestamp is not None:
            return delay.timestamp


def get_message_body(message):
    'Returns the unicode message body from a <message> stanza.'

    jid  = message.get_from()

    xdata   = message.xpath_eval(u"xhtmlim:html/xhtml:body[1]/node()", xdata_namespaces)
    if xdata:
        # XHTML formatted message
        # TODO: Strip namespaces
        body = from_utf8(''.join(child.serialize() for child in xdata))
    else:
        # Old style <body> message
        body = message.get_body()
        body = unicode(body.encode('xml')) if body else None
        if body is not None:
            body = body.replace('\n', '<br />')

    return body
