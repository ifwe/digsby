from . import DIGSBY_STATS_COUNTER_NS
from .action import Action
from jabber.jabber_util.functions import xpath_eval
from pyxmpp.iq import Iq
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
import libxml2

class CounterQuery(StanzaPayloadObject, list):
    xml_element_name = 'query'
    xml_element_namespace = DIGSBY_STATS_COUNTER_NS

    def __init__(self, xmlelem_or_accounts=[], order=sentinel):
        if isinstance(xmlelem_or_accounts, libxml2.xmlNode):
            self.__from_xml(xmlelem_or_accounts)
        else:
            self.extend(xmlelem_or_accounts)

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not a Stats Counter element (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=DIGSBY_STATS_COUNTER_NS or node.name!="query":
            raise ValueError,"XML node is not a Stats Counter element"
        actions = xpath_eval(node, 'sc:action',{'sc':DIGSBY_STATS_COUNTER_NS})
        self.extend(Action(action) for action in actions)

    def complete_xml_element(self, xmlnode, doc):
        [item.as_xml(xmlnode, doc) for item in self]

    def make_push(self, digsby_protocol):
        iq=Iq(stanza_type="set")
        iq.set_to(digsby_protocol.jid.domain)
        self.as_xml(parent=iq.get_node())
        return iq

    def make_get(self, digsby_protocol):
        iq = Iq(stanza_type="get")
        iq.set_to(digsby_protocol.jid.domain)
        self.as_xml(parent=iq.get_node())
        return iq

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r