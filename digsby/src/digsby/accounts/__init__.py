from pyxmpp.iq import Iq
DIGSBY_ACCOUNTS_NS     = 'digsby:accounts'
ADD = 'add'
UPDATE = 'update'
DELETE = 'delete'
ACC_ACTS = [ADD, UPDATE, DELETE]
import account
from account import Account
from accounts import Accounts


def make_push(acct, digsby_protocol):
    iq=Iq(stanza_type="set")
    iq.set_to(digsby_protocol.jid.domain)
    q = iq.new_query(DIGSBY_ACCOUNTS_NS)
    acct.as_xml(parent=q)
    return iq

def make_get(digsby_protocol):
    iq = Iq(stanza_type="get")
    iq.set_to(digsby_protocol.jid.domain)
    q = iq.new_query(DIGSBY_ACCOUNTS_NS)
    return iq