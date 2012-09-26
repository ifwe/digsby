from pyxmpp.iq import Iq
import libxml2
import util
from pyxmpp.utils import to_utf8
from pyxmpp.xmlextra import get_node_ns_uri
from pyxmpp.xmlextra import common_doc
from pyxmpp.objects import StanzaPayloadObject

PRIVACY_NS = "jabber:iq:privacy"
PRIVACY_TYPES = ("message", "presence-in", "presence-out", "iq")
PRIVACY_ATTRS = ("type", "value", "action","order")

class ListItem(StanzaPayloadObject):
    xml_element_name = "item"
    xml_element_namespace = PRIVACY_NS

    def __init__(self, xmlnode=None,       type=None, value=None,
                       action=None,        order=0,
                       message=False,      presence_in=False,
                       presence_out=False, iq=False):

        self.type         = type
        self.value        = value

        self.action       = action
        self.order        = order

        self.message      = message
        self.presence_in  = presence_in
        self.presence_out = presence_out
        self.iq           = iq

        self.__from_xml(xmlnode) if xmlnode else None
        assert self.action in ("allow", "deny")
        assert self.order
        if self.type is not None: assert self.type in ('group', 'jid', 'subscription')

#    @property
#    def messages_blocked(self):
#        return self.message or self.all_blocked()
    def __from_xml(self, xmlnode):
        """Initialize ListItem from XML node."""
        if xmlnode.type!="element":
            raise ValueError,"XML node is not a list item (not en element)"
        ns=get_node_ns_uri(xmlnode)
        if ns and ns!=PRIVACY_NS or xmlnode.name!="item":
            raise ValueError,"XML node is not a list item"

        [setattr(self, x, xmlnode.prop(x)) for x in PRIVACY_ATTRS]
        self.order = int(self.order) if self.order else 0

        n=xmlnode.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=PRIVACY_NS or n.name not in PRIVACY_TYPES:
                n=n.next
                continue
            setattr(self, util.pythonize(n.name), True)
            n=n.next

    def all_blocked(self):
        return all(self.message,self.presence_in,self.presence_out,self.iq) or \
            not any(self.message,self.presence_in,self.presence_out,self.iq)

    def complete_xml_element(self, xmlnode, doc):
        xmlnode.setProp("type", self.type) if self.type else None
        xmlnode.setProp("value", self.value) if self.value else None
        xmlnode.setProp("action", self.action)
        xmlnode.setProp("order", to_utf8(self.order))

        [xmlnode.newChild(None, child, None)
         for child in PRIVACY_TYPES
         if getattr(self, util.pythonize(child))]

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

class List(StanzaPayloadObject, list):
    xml_element_name = "list"
    xml_element_namespace = PRIVACY_NS

    def __init__(self, xmlnode_or_name):
        list.__init__(self)
        if isinstance(xmlnode_or_name,libxml2.xmlNode):
            self.__from_xml(xmlnode_or_name)
        else:
            self.name = xmlnode_or_name

    def __from_xml(self, xmlnode):
        """Initialize List from XML node."""
        if xmlnode.type!="element":
            raise ValueError,"XML node is not a list (not en element)"
        ns=get_node_ns_uri(xmlnode)
        if ns and ns!=PRIVACY_NS or xmlnode.name!="list":
            raise ValueError,"XML node is not a list"
        self.name = xmlnode.prop("name")
        n=xmlnode.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=PRIVACY_NS or n.name != "item":
                n=n.next
                continue
            self.append(ListItem(n))
            n=n.next

    def complete_xml_element(self, xmlnode, doc):
        xmlnode.setProp("name", self.name)
        [item.as_xml(xmlnode, doc) for item in self]

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

class Privacy(StanzaPayloadObject, list):
    xml_element_name = 'query'
    xml_element_namespace = PRIVACY_NS

    def __init__(self, xmlnode=None):
        self.active  = None
        self.default = None

        if xmlnode is not None:
            self.__from_xml(xmlnode)

    def __from_xml(self, xmlnode):
        if xmlnode.type!="element":
            raise ValueError,"XML node is not a Privacy (not en element)"
        ns=get_node_ns_uri(xmlnode)
        if ns and ns!=PRIVACY_NS or xmlnode.name!="query":
            raise ValueError,"XML node is not a query"
        n=xmlnode.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=PRIVACY_NS or n.name not in ("active", "default", "list"):
                n=n.next
                continue
            if n.name == "active":
                self.active = n.prop("name")if libxml2.xmlNode.hasProp("name") else None
            elif n.name == "default":
                self.default = n.prop("default")if libxml2.xmlNode.hasProp("default") else None
            else:
                self.append(List(n))
            n = n.next


    def complete_xml_element(self, xmlnode, doc):
        if self.active is not None:
            active = xmlnode.newChild(None, "active", None)
            if self.active: active.setProp("name", self.active)
        if self.default is not None:
            default = xmlnode.newChild(None, "default", None)
            if self.default: default.setProp("name", self.default)
        for list_ in self:
            list_.as_xml(xmlnode, doc)

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r




