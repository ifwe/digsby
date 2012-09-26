import libxml2
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
from pyxmpp.utils import to_utf8, from_utf8

VCARD_AVATAR_NS="vcard-temp:x:update"

class X_Update(StanzaPayloadObject):
    xml_element_name = "x"
    xml_element_namespace = VCARD_AVATAR_NS

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

class Photo(StanzaPayloadObject):
    xml_element_name = 'photo'
    xml_element_namespace = VCARD_AVATAR_NS

    def __init__(self, xmlnode_or_hash):
        if isinstance(xmlnode_or_hash,libxml2.xmlNode):
            self.from_xml(xmlnode_or_hash)
        else:
            self.hash = xmlnode_or_hash

    def from_xml(self,node):
        if node.type!="element":
            raise ValueError,"XML node is not a photo (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not a %s descriptor" % self.xml_element_name
        self.hash = from_utf8(node.getContent())

    def complete_xml_element(self, xmlnode, _unused):
        xmlnode.addContent(to_utf8(self.hash))

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r