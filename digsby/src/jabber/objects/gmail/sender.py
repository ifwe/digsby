from jabber.objects.gmail import GOOGLE_MAIL_NOTIFY_NS
from pyxmpp.utils import from_utf8
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import get_node_ns_uri

#address     The email address of the sender.
#name     The display name of the sender.
#originator     A number indicating whether this sender originated this thread: 1 means that this person originated this thread; 0 or omitted means that another person originated this thread.
#unread     A number indicating whether or not the thread includes an unread message: 1 means yes; 0 or omitted means no.


class Sender(StanzaPayloadObject):
    xml_element_name = 'sender'
    xml_element_namespace = GOOGLE_MAIL_NOTIFY_NS

    def __init__(self, xmlnode):
        self.__from_xml(xmlnode)

    def __from_xml(self,node):
        if node.type!="element":
            raise ValueError,"XML node is not a %s element (not en element)" % self.xml_element_name
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not an %s element" % self.xml_element_name

        self.name = from_utf8(node.prop("name"))
        self.address = from_utf8(node.prop("address"))

        originator = node.prop("originator")
        self.originator = int(from_utf8(originator)) if originator else 0

        unread = node.prop("unread")
        self.unread = int(from_utf8(unread)) if unread else 0

