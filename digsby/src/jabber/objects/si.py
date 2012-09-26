from pyxmpp.xmlextra import get_node_ns_uri
from pyxmpp.utils import to_utf8
import libxml2
from pyxmpp.objects import StanzaPayloadObject

SI_NS     = 'http://jabber.org/protocol/si'


class SI(StanzaPayloadObject):
    xml_element_name = 'si'
    xml_element_namespace = SI_NS

    def __init__(self, xmlnode_or_id=None, mime_type=None, profile_ns=None):
        if isinstance(xmlnode_or_id,libxml2.xmlNode):
            self.__from_xml(xmlnode_or_id)
        else:
            self.sid = xmlnode_or_id
            self.mime_type = mime_type
            self.profile_ns = profile_ns

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not an si (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=SI_NS or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not an si"
        sid       = node.prop("id")
        self.sid  = to_utf8(sid) if sid else None
        mime_type = node.prop("mime-type")
        self.mime_type  = to_utf8(mime_type) if mime_type else None
        profile_ns   = node.prop("profile")
        self.profile_ns  = to_utf8(profile_ns) if profile_ns else None

    def complete_xml_element(self, xmlnode, _unused):
        xmlnode.setProp("id",to_utf8(self.sid))
        xmlnode.setProp("mime-type",to_utf8(str(self.mime_type))) if self.mime_type else None
        xmlnode.setProp("profile",to_utf8(self.profile_ns)) if self.profile_ns else None

    @classmethod
    def from_iq(cls, iq):
        return cls(iq.xpath_eval('si:si',{'si':SI_NS})[0])
