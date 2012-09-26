from decimal import Decimal
from logging import getLogger
from peak.util.addons import AddOn
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.utils import from_utf8
from pyxmpp.xmlextra import get_node_ns_uri
import hooks
import libxml2
import traceback

log = getLogger('plugins.digsby_geoip')

DIGSBY_GEOIP_NS = "digsby:geoip"
#===============================================================================
# jabber setup
#===============================================================================
class Digsby_GeoIP(AddOn):
    def __init__(self, subject):
        self.protocol = subject
        super(Digsby_GeoIP, self).__init__(subject)

    def setup(self, stream):
        self.stream = stream
        log.debug('setting up geoip')
        stream.set_iq_set_handler('query', DIGSBY_GEOIP_NS, self.geoip_set)

    def geoip_set(self, stanza):
        try:
            f = stanza.get_from()
            if f is not None and f.bare() != self.stream.peer.bare():
                return False
            node = stanza.xpath_eval('g:query/g:geoip',{'g':DIGSBY_GEOIP_NS})[0]
            geo = GeoIP(node)
        except Exception:
            traceback.print_exc()
            return False
        else:
            #===================================================================
            # push the information to anyone interested
            #===================================================================
            hooks.notify('digsby.geoip.received', geo.AsDict(), self.protocol, self.stream)
            return True

def setup(protocol, stream, *a, **k):
    Digsby_GeoIP(protocol).setup(stream)

#===============================================================================
# jabber class
#===============================================================================
class GeoIP(StanzaPayloadObject):
    xml_element_name = 'geoip'
    xml_element_namespace = DIGSBY_GEOIP_NS

    strfields = ['ip', 'city', 'country', 'region', 'state', 'postal']
    decfields = ['lat', 'lng']

    def __init__(self, xmlnode):
        if isinstance(xmlnode,libxml2.xmlNode):
            self.__from_xml(xmlnode)
        else:
            assert False

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not a geoip (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=DIGSBY_GEOIP_NS or node.name!=self.xml_element_name:
            raise ValueError,"XML node is not a geoip"

        for fields, convert in [(self.strfields, from_utf8), (self.decfields, Decimal)]:
            for field in fields:
                val = None
                try:
                    val2 = node.prop(field)
                    val = convert(val2) if val2 else None
                except Exception:
                    traceback.print_exc()
                setattr(self, field, val)

    def complete_xml_element(self, xmlnode, _unused):
        assert False

    def AsDict(self):
        d = dict((field, getattr(self, field)) for field in self.strfields)
        d.update((field, getattr(self, field)) for field in self.decfields)
        return d

def print_geoip(geoip, *a, **k):
    log.debug('got geoip information %r', geoip)
