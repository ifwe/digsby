from digsby.accounts.account import Account
from pyxmpp.iq import Iq
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.xmlextra import common_doc, get_node_ns_uri
from common.hashacct import HashedAccounts
import base64
import binascii
from digsby.accounts import DIGSBY_ACCOUNTS_NS
import libxml2

from jabber.jabber_util import xpath_eval


class Accounts(StanzaPayloadObject, list, HashedAccounts):
    xml_element_name = 'query'
    xml_element_namespace = DIGSBY_ACCOUNTS_NS

    def __init__(self, xmlelem_or_accounts=[], order=sentinel):
        if isinstance(xmlelem_or_accounts, libxml2.xmlNode):
            self.__from_xml(xmlelem_or_accounts)
        else:
            self.order = order
            self.extend(xmlelem_or_accounts)

    def __from_xml(self, node):
        if node.type!="element":
            raise ValueError,"XML node is not an Accounts element (not en element)"
        ns=get_node_ns_uri(node)
        if ns and ns!=DIGSBY_ACCOUNTS_NS or node.name!="query":
            raise ValueError,"XML node is not an Accounts element"
        accts = xpath_eval(node, 'a:account',{'a':DIGSBY_ACCOUNTS_NS})
        orders = xpath_eval(node, 'a:order',{'a':DIGSBY_ACCOUNTS_NS})
        self.order = [ord(c) for c in
                 base64.decodestring(orders[0].getContent())] if orders else []
        self.extend(Account(acct) for acct in accts)

    def complete_xml_element(self, xmlnode, doc):
        if self.order is not sentinel:
            xmlnode.newTextChild(None, "order",
                                 binascii.b2a_base64(''.join(chr(c)
                                                     for c in self.order)))

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

    @staticmethod
    def from_local_store(local_info):
        '''
        Create an Accounts object filled with Account objects from a dictionary
        of primitives (usually from the local accounts store).
        '''
        accts = Accounts(order=local_info['order'])
        
        for a in local_info['accts']:
            # TODO: from_net always calls cPickle.loads on it's .data -- we have a case
            # where that shouldn't happen
            import cPickle
            data = cPickle.dumps(a['data'])
            
            accts.append(Account(a['id'], a['protocol'], a['username'], a['password'], data))
            
        return accts
