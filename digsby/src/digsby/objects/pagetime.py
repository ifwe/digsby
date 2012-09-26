import libxml2
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
from pyxmpp.utils import to_utf8, from_utf8
from datetime import datetime

PAGETIME_NS = 'digsby:pagetime'

class PageTime(StanzaPayloadObject):
    xml_element_name = 'pagetime'
    xml_element_namespace = PAGETIME_NS

    def __init__(self, xmlnode_or_pagetime):
        if isinstance(xmlnode_or_pagetime,libxml2.xmlNode):
            self.from_xml(xmlnode_or_pagetime)
        else:
            self.pagetime = xmlnode_or_pagetime

    def from_xml(self,node):
        if node.type!="element":
            raise ValueError,"XML node is not a pagetime (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not a %s descriptor" % self.xml_element_name
        self.pagetime = int(from_utf8(node.getContent()))

    def complete_xml_element(self, xmlnode, _unused):
        xmlnode.addContent(to_utf8(self.pagetime))

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r