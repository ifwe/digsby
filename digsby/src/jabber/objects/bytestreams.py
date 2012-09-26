from pprint import pprint
from pyxmpp.utils import from_utf8
from pyxmpp.utils import to_utf8
import libxml2
from pyxmpp.jid import JID
from pyxmpp.jabber.disco import DiscoCacheFetcherBase
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri

BYTESTREAMS_NS="http://jabber.org/protocol/bytestreams"
BYTESTREAMS_UDP_NS=BYTESTREAMS_NS+"#udp"

class StreamHost(StanzaPayloadObject):
    """A <streamhost/> element of bytestreams reply.

    :Ivariables:
        - `jid`: the JID of the StreamHost.
        - `host`: the hostname or IP address of the StreamHost.
        - `port`: the port associated with the host
        - `zeroconf`: the zeroconf identifier (should be `_jabber.bytestreams`)
        - `xmlnode`: XML element describing the StreamHost.
    :Types:
        - `jid`: `JID`
        - `host`: `unicode`
        - `port`: `int`
        - `zeroconf`: `unicode`
        - `xmlnode`: `libxml2.xmlNode`
    """
    xml_element_name = 'streamhost'
    xml_element_namespace = BYTESTREAMS_NS
    def __init__(self, xmlnode_or_jid, host=None, port=None, zeroconf=None):
        """Initialize an `StreamHost` object.

        Wrap an existing streamhost XML element or create a new one.

        :Parameters:
            - `xmlnode_or_jid`: XML element describing the StreamHost or the JID of
              the StreamHost.
            - `host`: the hostname or IP address of the StreamHost.
            - `port`: the port of the StreamHost
            - `zeroconf`: the zeroconf identifier of the StreamHost.
        :Types:
            - `xmlnode_or_node`: `libxml2.xmlNode` or `unicode`
            - `host`: `unicode`
            - `port`: `int`
            - `zeroconf`: `unicode`
            """
        if isinstance(xmlnode_or_jid,libxml2.xmlNode):
            self.from_xml(xmlnode_or_jid)
        else:
            self.jid      = JID(xmlnode_or_jid)
            self.host     = host
            self.port     = port
            self.zeroconf = zeroconf
        if not (bool(self.port) ^ bool(self.zeroconf)):
            raise ValueError, 'StreamHost element requires one of [port, zeroconf]'

    def from_xml(self,node):
        #need jid, host, port, zeroconf
        """Initialize StreamHost from XML node."""
        if node.type!="element":
            raise ValueError,"XML node is not a streamhost (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=self.xml_element_namespace or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not a %s descriptor" % self.xml_element_name
        jid=JID(node.prop("jid").decode("utf-8"))
        self.jid=jid

        host=node.prop("host").decode("utf-8")
        self.host=host

        port=node.prop("port")
        #py2.5:
        self.port = int(port.decode("utf-8")) if port else None
        #py2.4:
#        if port:
#            self.port = int(port.decode("utf-8"))
#        else:
#            self.port = None
        zeroconf=node.prop("zeroconf")
        #py2.5:
        self.zeroconf = zeroconf.decode("utf-8") if zeroconf else None
        #py2.4
#        if zeroconf:
#            self.zeroconf=zeroconf.decode("utf-8")
#        else:
#            self.zeroconf=None
    def __eq__(self, other):
        if other is self:
            return True
        if not isinstance(other, self.__class__):
            return False
        return self.jid == other.jid and self.host == other.host and \
               self.port == other.port and self.zeroconf == other.zeroconf

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.jid, self.host, self.port, self.zeroconf))

    def complete_xml_element(self, xmlnode, _unused):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `_unused`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `_unused`: `libxml2.xmlDoc`"""
        xmlnode.setProp("jid",JID(self.jid).as_utf8())
        xmlnode.setProp("host", unicode(self.host).encode("utf-8"))
        if self.port:
            xmlnode.setProp("port", unicode(self.port).encode("utf-8"))
        if self.zeroconf:
            xmlnode.setProp("zeroconf", unicode(self.zeroconf).encode("utf-8"))

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

class ByteStreams(StanzaPayloadObject):
    """A bytestreams response object.

    :Ivariables:
        - `node`: node name of the bytestreams element (cached).
        - `hosts`: streamhosts in the bytestreams object.
        - `xmlnode`: XML element listing the items.
    :Types:
        - `node`: `unicode`
        - `hosts`: `list` of `StreamHost`
        - `xmlnode`: `libxml2.xmlNode`
    """
    xml_element_name = 'query'
    xml_element_namespace = BYTESTREAMS_NS
    #CAS: bytestreams#udp not implemented
    def __init__(self,xmlnode_or_node=None, sid=None, mode=None):
        """Initialize an `ByteStreams` object.

        Wrap an existing bytestreams XML element or create a new one.

        :Parameters:
            - `xmlnode_or_node`: XML node to be wrapped into `self` or an item
              node name.
        :Types:
            - `xmlnode_or_node`: `libxml2.xmlNode` or `unicode`
            """
        self.hosts = []
        self.sid   = sid
        self.mode  = mode
        self.activate  = None
        self.host_used = None
        if isinstance(xmlnode_or_node, libxml2.xmlNode):
            self.from_xml(xmlnode_or_node)
        else:
            self.node      = xmlnode_or_node

    def from_xml(self,node,strict=True):
        """
        Initialize Roster object from XML node.

        If `strict` is False, than invalid items in the XML will be ignored.
        """
        node_=node.prop("node")
        sid=node.prop("sid")
        self.sid = from_utf8(sid) if sid else None
        mode=node.prop("mode")
        self.mode = from_utf8(mode) if mode else None
        self.mode = self.mode if self.mode != 'tcp' else None
        if node_:
            self.node = node_.decode("utf-8")
        else:
            self.node = None
        if node.type!="element":
            raise ValueError,"XML node is not a bytestreams (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=BYTESTREAMS_NS or node.name!="query":
            raise ValueError,"XML node is not a bytestreams query"
        n=node.children
        while n:
            if n.type!="element":
                n=n.next
                continue
            ns=get_node_ns_uri(n)
            if ns and ns!=BYTESTREAMS_NS:
                n=n.next
                continue
            if n.name=="streamhost":
                try:
                    self.add_host(n)
                except ValueError:
                    if strict:
                        raise
            elif n.name=="streamhost-used":
                host_used=JID(n.prop("jid").decode("utf-8"))
                self.host_used=host_used
            elif n.name=="activate":
                activate=JID(n.getContent())
                self.activate=activate
            n=n.next

    def complete_xml_element(self, xmlnode, _unused):
        """Complete the XML node with `self` content.

        Should be overriden in classes derived from `StanzaPayloadObject`.

        :Parameters:
            - `xmlnode`: XML node with the element being built. It has already
              right name and namespace, but no attributes or content.
            - `_unused`: document to which the element belongs.
        :Types:
            - `xmlnode`: `libxml2.xmlNode`
            - `_unused`: `libxml2.xmlDoc`"""
        if self.node:
            xmlnode.setProp("node", to_utf8(self.node))
        if self.sid:
            xmlnode.setProp("sid", to_utf8(self.sid))
        if self.mode and self.mode != 'tcp':
            xmlnode.setProp("mode", to_utf8(self.mode))
        for host in self.hosts:
            try:
                host.as_xml(xmlnode, _unused)
            except:
                pprint(host)
                raise
        if self.activate:
            xmlnode.newChild(None, "activate", JID(self.activate).as_utf8())
        if self.host_used:
            h = xmlnode.newChild(None, "streamhost-used", None)
            h.setProp("jid",JID(self.host_used).as_utf8())

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

    def add_host(self,streamhost_jid, host=None, port=None, zeroconf=None):
        """Add a StreamHost to the `ByteStreams` object.

        :Parameters:
            - `streamhost_jid`: jid of the streamhost.
            - `host`: hostname of the streamhost.
            - `port`: the port associated with the host
            - `zeroconf`: the zeroconf identifier (should be `_jabber.bytestreams`)
        :Types:
            - `streamhost_jid`: `JID`
            - `host`: `unicode`
            - `port`: `int`
            - `zeroconf`: `unicode`

        :returns: the streamhost created.
        :returntype: `StreamHost`"""
        sh = StreamHost(streamhost_jid, host, port, zeroconf)
        self.hosts.append(sh)
        return sh

def register_streamhost_cache_fetchers(cache_suite,stream):
    tmp=stream
    class ByteStreamsCacheFetcher(DiscoCacheFetcherBase):
        stream=tmp
        disco_class=ByteStreams
        __response = DiscoCacheFetcherBase._DiscoCacheFetcherBase__response #@UndefinedVariable
        __error = DiscoCacheFetcherBase._DiscoCacheFetcherBase__error #@UndefinedVariable
        __timeout = DiscoCacheFetcherBase._DiscoCacheFetcherBase__timeout #@UndefinedVariable
        def fetch(self):
            """Initialize the Service Discovery process."""
            from pyxmpp.iq import Iq
            jid,node = self.address
            iq = Iq(to_jid = jid, stanza_type = "get")
            disco = self.disco_class(node)
            disco.as_xml(iq.xmlnode) #only line that was changed
            self.stream.set_response_handlers(iq,self.__response, self.__error,
                    self.__timeout)
            self.stream.send(iq)
            """Cache fetcher for ByteStreams."""
    cache_suite.register_fetcher(ByteStreams,ByteStreamsCacheFetcher)
