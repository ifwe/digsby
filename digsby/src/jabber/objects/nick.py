import libxml2
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
from pyxmpp.utils import to_utf8, from_utf8

NICK_NS = 'http://jabber.org/protocol/nick'

class Nick(StanzaPayloadObject):
    xml_element_name = 'nick'
    xml_element_namespace = NICK_NS

    def __init__(self, xmlnode_or_nick):
        if isinstance(xmlnode_or_nick,libxml2.xmlNode):
            self.from_xml(xmlnode_or_nick)
        else:
            self.nick = xmlnode_or_nick

    def from_xml(self,node):
        if node.type!="element":
            raise ValueError,"XML node is not a nick (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not a %s descriptor" % self.xml_element_name
        self.nick = from_utf8(node.getContent())

    def complete_xml_element(self, xmlnode, _unused):
        xmlnode.addContent(to_utf8(self.nick))

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r