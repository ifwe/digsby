from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
from jabber.jabber_util import xpath_eval

X_EVENT_NS = "jabber:x:event"

class X_Event(StanzaPayloadObject):
    xml_element_name = "x"
    xml_element_namespace = X_EVENT_NS

    def __init__(self, xmlnode=None, offline=False, delivered=False,
                       displayed=False, composing=False, id=None):
        if xmlnode is not None:
            self.from_xml(xmlnode)
        else:
            self.offline = offline
            self.delivered = delivered
            self.displayed = displayed
            self.composing = composing
            self.id = id

    def complete_xml_element(self, xmlnode, _doc):
        xmlnode.newChild(None, 'offline', None) if self.offline else None
        xmlnode.newChild(None, 'delivered', None) if self.delivered else None
        xmlnode.newChild(None, 'displayed', None) if self.displayed else None
        xmlnode.newChild(None, 'composing', None) if self.composing else None
        xmlnode.newTextChild(None, "id", self.id ) if self.id else None

    def from_xml(self, xmlnode):
        if xmlnode.type!="element":
            raise ValueError,"XML node is not a photo (not en element)"
        ns=get_node_ns_uri(xmlnode)
        if ns and ns!=self.xml_element_namespace or xmlnode.name!=self.xml_element_name:
            raise ValueError,"XML node is not a %s descriptor" % self.xml_element_name

        self.offline   = bool(xpath_eval(xmlnode, 'x:offline',  {'x':X_EVENT_NS}))
        self.delivered = bool(xpath_eval(xmlnode, 'x:delivered',{'x':X_EVENT_NS}))
        self.displayed = bool(xpath_eval(xmlnode, 'x:displayed',{'x':X_EVENT_NS}))
        self.composing = bool(xpath_eval(xmlnode, 'x:composing',{'x':X_EVENT_NS}))

        ids = xpath_eval(xmlnode, 'x:id',{'x':X_EVENT_NS})

        self.id = ids[0].getContent() if ids else None

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r