from pyxmpp.utils import from_utf8
from pyxmpp.iq import Iq
from pyxmpp.objects import StanzaPayloadObject
from pyxmpp.utils import to_utf8
from pyxmpp.xmlextra import common_doc
from pyxmpp.xmlextra import get_node_ns_uri
import base64
import cPickle
import pickletools
import binascii
import digsby.accounts
import digsbyprofile
import common
from digsby.accounts import DIGSBY_ACCOUNTS_NS
import libxml2


def fix_truncated(short):
    from common.protocolmeta import fix_shortname
    return fix_shortname.get(short, short)

class Account(StanzaPayloadObject, common.HashedAccount):
    xml_element_name = 'account'
    xml_element_namespace = DIGSBY_ACCOUNTS_NS

    def __init__(self, xmlnode_or_acct_or_id=None, protocol=None, username=None,
                 password=None, data=None, action=None):

        # from an incoming XML node
        if isinstance(xmlnode_or_acct_or_id, libxml2.xmlNode):
            self.__from_xml(xmlnode_or_acct_or_id)

        # from an account object
        elif isinstance(xmlnode_or_acct_or_id, common.AccountBase):
            acct = xmlnode_or_acct_or_id
            self.id       = acct.id
            self.protocol = acct.protocol_info().get('name_truncated', acct.protocol)
            self.username = acct.name
            self.password = acct.password
            try:
                self.data     = cPickle.dumps(acct.get_options())
            except:
                print 'acct.get_options()', repr(acct.get_options())
                raise
            else:
                if hasattr(pickletools, 'optimize'):
                    self.data = pickletools.optimize(self.data)
            self.action   = action

        # id
        else:
            self.id       = xmlnode_or_acct_or_id
            self.protocol = protocol
            self.username = username
            self.password = password
            self.data     = data
            self.action   = action

        if not isinstance(self.id, int) or not self.id >= 0:
            raise ValueError("positive int id is required! (got %r)" % self.id)


    def __repr__(self):
        return '<Digsby.Account %s (%s)>' % (self.protocol, self.username)

    def __from_xml(self, node):
        '''A libxml2 node to a digsby.account'''

        if node.type!="element":
            raise ValueError,"XML node is not an account element (not en element)"
        ns = get_node_ns_uri(node)
        if ns and ns != DIGSBY_ACCOUNTS_NS or node.name != "account":
            raise ValueError,"XML node is not an account element"
        id = node.prop("id")
        self.id = int(from_utf8(id)) if id else None

        username = node.prop("username")
        self.username = from_utf8(username) if username else None

        protocol = node.prop("protocol")
        self.protocol = from_utf8(protocol) if protocol else None

        self.protocol = fix_truncated(self.protocol)

        password = node.prop("password")
        self.password = base64.b64decode(password) if password else None

        action = node.prop("action")
        self.action = from_utf8(action) if action else None

        self.data = None
        n=node.children
        while n:
            if n.type!="element":
                n = n.next
                continue
            ns = get_node_ns_uri(n)
            if ns and ns!=DIGSBY_ACCOUNTS_NS:
                n=n.next
                continue
            if n.name=="data":
                self.data=base64.decodestring(n.getContent())
            n = n.next

    def complete_xml_element(self, xmlnode, _unused):
        'to xml'

        if isinstance(self.id, int) and self.id >=0:
            xmlnode.setProp("id",  to_utf8(str(self.id)))
        else:
            raise ValueError, "self.id must be int"
        xmlnode.setProp("protocol", to_utf8(self.protocol)) if self.protocol else None
        xmlnode.setProp("username", to_utf8(self.username)) if self.username else None
        xmlnode.setProp("password", base64.b64encode(self.password)) if self.password else None
        xmlnode.setProp("action",   to_utf8(self.action)) if self.action else None
        xmlnode.newTextChild(None, "data", binascii.b2a_base64(self.data)) if self.data is not None else None

    def make_push(self, digsby_protocol):
        return digsby.accounts.Accounts([self]).make_push(digsby_protocol)

    def __str__(self):
        n=self.as_xml(doc=common_doc)
        r=n.serialize()
        n.unlinkNode()
        n.freeNode()
        return r

    def get_options(self):
        return cPickle.loads(self.data)
