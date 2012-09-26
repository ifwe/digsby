from digsby.abstract_blob import *
from digsby.DigsbyProtocol import DigsbyProtocol as protocol
from digsby.digsbybuddy import DigsbyBuddy as dbuddy
from digsby.widgets.widget import iswidget
import loginutil
import blobs
import accounts
import widgets
import web
from loginutil import DigsbyLoginError

def make_get(self, digsby_protocol):
    iq = Iq(stanza_type="get")
    iq.set_to(digsby_protocol.jid.domain)
    self.as_xml(parent=iq.get_node())
    return iq

import digsbysasl
import pyxmpp.sasl

pyxmpp.sasl.safe_mechanisms_dict["DIGSBY-SHA256-RSA-CERT-AES"] = (digsbysasl.DigsbyAESClientAuthenticator,None)
pyxmpp.sasl.all_mechanisms_dict["DIGSBY-SHA256-RSA-CERT-AES"] = (digsbysasl.DigsbyAESClientAuthenticator,None)
