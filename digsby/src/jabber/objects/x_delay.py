from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
from datetime import datetime
from pyxmpp.utils import to_utf8

X_DELAY_NS = "jabber:x:delay"

DELAY_TIME_FORMAT = '%Y%m%dT%H:%M:%S'

class X_Delay(StanzaPayloadObject):
    xml_element_name = "x"
    xml_element_namespace = X_DELAY_NS

    def __init__(self, xmlnode=None, from_=None, timestamp=None):
        if xmlnode is not None:
            self.from_xml(xmlnode)
        else:
            self.from_ = from_
            self.timestamp = timestamp

    def complete_xml_element(self, xmlnode, _doc):
        xmlnode.setProp('from', self.from_) if self.from_ else None
        if isinstance(self.timestamp, basestring):
            stamp = self.timestamp
        else:
            stamp = self.timestamp.strftime(DELAY_TIME_FORMAT)
        xmlnode.setProp('stamp', stamp)

    def from_xml(self, xmlnode):
        if xmlnode.type!="element":
            raise ValueError,"XML node is not a photo (not en element)"
        ns=get_node_ns_uri(xmlnode)
        if ns and ns!=self.xml_element_namespace or xmlnode.name!=self.xml_element_name:
            raise ValueError,"XML node is not a %s descriptor" % self.xml_element_name

        from_       = xmlnode.prop("from")
        self.from_  = to_utf8(from_) if from_ else None

        timestamp   = xmlnode.prop("stamp")
        try:
            self.timestamp = datetime.strptime(timestamp, DELAY_TIME_FORMAT)
        except Exception:
            self.timestamp = None

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r