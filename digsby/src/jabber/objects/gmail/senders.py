from jabber.objects.gmail.sender import Sender
from jabber.jabber_util.functions import xpath_eval
from pyxmpp.xmlextra import get_node_ns_uri
from jabber.objects.gmail import GOOGLE_MAIL_NOTIFY_NS
from pyxmpp.objects import StanzaPayloadObject

#senders

#contains n    sender


class Senders(StanzaPayloadObject, list):
    xml_element_name = 'senders'
    xml_element_namespace = GOOGLE_MAIL_NOTIFY_NS

    def __init__(self, xmlnode):
        self.__from_xml(xmlnode)

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not a %s element (not en element)" % self.xml_element_name
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not an %s element" % self.xml_element_name
        senders = xpath_eval(node, 's:sender',{'s':GOOGLE_MAIL_NOTIFY_NS})
        self.extend(Sender(sender) for sender in senders)
