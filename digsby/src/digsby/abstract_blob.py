import binascii
from pyxmpp.xmlextra import get_node_ns_uri
from pyxmpp.utils import to_utf8
import libxml2 #@UnresolvedImport
from pyxmpp.iq import Iq
from pyxmpp.xmlextra import common_doc
import base64
from pyxmpp.objects import StanzaPayloadObject

MAX_BLOB_SIZE = int(65536 * 3/5) # b/c of base 64
MAX_VARBINARY = 255


class AbstractBlob(StanzaPayloadObject):
    xml_element_name = 'query'

    def __init__(self, xmlnode_or_time=None, data=None, rawdata=sentinel):
        self._data = None
        self.tstamp = None
        self.update_needed = False
        if isinstance(xmlnode_or_time,libxml2.xmlNode):
            self.__from_xml(xmlnode_or_time)
        elif rawdata is not sentinel:
            self.tstamp = xmlnode_or_time
            self._data = rawdata
        else:
            self.tstamp = xmlnode_or_time
            self.data = data

    def __from_xml(self, node):
        self.tstamp = None
        AbstractBlob.set_data(self, None)
        if node.type!="element":
            raise ValueError,"XML node is not a %s (not en element)" % self.xml_element_namespace
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not a %s" % self.xml_element_namespace

        n=node.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=self.xml_element_namespace:
                n=n.next
                continue
            if n.name=="data":
                AbstractBlob.set_data(self, base64.decodestring(n.getContent()))
            elif n.name=="time":
                self.tstamp=n.getContent()
            elif n.name=="update-needed":
                self.update_needed = True
            n=n.next

    def complete_xml_element(self, xmlnode, _unused):
        xmlnode.newTextChild(None, "time", to_utf8(self.tstamp)) if self.tstamp is not None else None

        bytes = self._data
        if bytes is not None:
            xmlnode.newTextChild(None, "data", binascii.b2a_base64(bytes))

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

    def set_data(self, data):
        datalen = len(data) if data is not None else 0
        if datalen > MAX_BLOB_SIZE:
            raise ValueError("Blob Size %d out of range 0 - %d." %
                             (datalen, MAX_BLOB_SIZE))
        self._data = data

    def get_data(self):
        return self._data

    def del_data(self):
        self._data = None

    data = property(get_data, set_data, del_data)

    def make_push(self, digsby_protocol):
        'Creates a set stanza.'

        iq=Iq(stanza_type="set")
        iq.set_to(digsby_protocol.jid.domain)
        self.as_xml(parent=iq.get_node())
        return iq

    def make_get(self, digsby_protocol):
        iq = Iq(stanza_type="get")
        iq.set_to(digsby_protocol.jid.domain)
        self.as_xml(parent=iq.get_node())
        return iq

class AbstractVarBinary(AbstractBlob):
    def set_data(self, data):
        datalen = len(data) if data is not None else 0
        if datalen > MAX_VARBINARY:
            raise ValueError("VarBinary Size %d out of range 0 - %d." %
                             (datalen, MAX_VARBINARY))
        self._data = data

    data = property(AbstractBlob.get_data, set_data, AbstractBlob.del_data)
