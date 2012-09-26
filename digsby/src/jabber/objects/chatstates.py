import libxml2
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri

CHATSTATES_NS = "http://jabber.org/protocol/chatstates"

VALID_CHATSTATES = ["active", "composing", "gone", "inactive", "paused"]

class ChatState(StanzaPayloadObject):
    xml_element_namespace = CHATSTATES_NS

    def __init__(self, xmlnode_or_type):
        if isinstance(xmlnode_or_type,libxml2.xmlNode):
            self.from_xml(xmlnode_or_type)
        else:
            self.xml_element_name = xmlnode_or_type
            assert self.valid_state()

    def valid_state(self):
        return self.xml_element_name in VALID_CHATSTATES

    def from_xml(self, xmlnode):
        self.xml_element_name = xmlnode.name
        if xmlnode.type!="element":
            raise ValueError,"XML node is not a chat state (not en element)"
        ns=get_node_ns_uri(xmlnode)
        if ns and ns!=self.xml_element_namespace:
            raise ValueError,"XML node is not a chat state descriptor"
        if not self.valid_state():
            import warnings
            warnings.warn("XML node with name: %r is not a valid chat state" % self.xml_element_name)

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r
