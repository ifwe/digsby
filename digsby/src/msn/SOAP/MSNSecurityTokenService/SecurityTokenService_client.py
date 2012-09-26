##################################################
# file: SecurityTokenService_client.py
#
# client stubs generated by "ZSI.generate.wsdl2python.WriteServiceModule"
#     D:\workspace\digsby\Digsby.py --no-traceback-dialog --multi --server=api5.digsby.org
#
##################################################

from SecurityTokenService_types import *
import urlparse, types
from ZSI.TCcompound import ComplexType, Struct
from ZSI import client
from ZSI.schema import GED, GTD
import ZSI

import ZSI.wstools.Namespaces as NS
from msn.SOAP import Namespaces as MSNS, MSNBindingSOAP

import util.callbacks as callbacks
import util.network.soap as soap

# Locator
class SecurityTokenServiceLocator:
    SecurityTokenServicePort_address = "https://login.live.com/RST2.srf"
    def getRequestSecurityTokenPortAddress(self):
        return SecurityTokenServiceLocator.SecurityTokenServicePort_address
    def getRequestSecurityTokenPort(self, url=None, **kw):
        return SecurityTokenServicePortBindingSOAP(url or SecurityTokenServiceLocator.SecurityTokenServicePort_address, **kw)
    def getRequestMultipleSecurityTokensPortAddress(self):
        return SecurityTokenServiceLocator.SecurityTokenServicePort_address
    def getRequestMultipleSecurityTokensPort(self, url=None, **kw):
        return SecurityTokenServicePortBindingSOAP(url or SecurityTokenServiceLocator.SecurityTokenServicePort_address, **kw)

# Methods
class SecurityTokenServicePortBindingSOAP(MSNBindingSOAP):

    # op: RequestMultipleSecurityTokens
    @callbacks.callsback
    def RequestMultipleSecurityTokens(self, request, soapheaders=(), callback = None, **kw):
        if isinstance(request, RequestMultipleSecurityTokensMessage) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        # TODO: Check soapheaders
        self.binding.RPC(None, None, request, soapaction=kw.get('soapaction', ''), soapheaders=soapheaders,
                         callback = callback,
                         **kw)

    # op: RequestSecurityToken
    @callbacks.callsback
    def RequestSecurityToken(self, request, soapheaders=(), callback = None, **kw):
        if isinstance(request, RequestSingleSecurityTokenMessage) is False:
            raise TypeError, "%s incorrect request type" % (request.__class__)
        # no input wsaction
        # TODO: Check soapheaders
        self.binding.RPC(None, None, request, soapaction=kw.get('soapaction', ''), soapheaders=soapheaders,
                         callback = callback,
                         **kw)

RequestMultipleSecurityTokensMessage            = GED(MSNS.PPCRL.BASE, "RequestMultipleSecurityTokens").pyclass
RequestSecurityTokenResponseCollectionMessage   = GED(NS.WSTRUST.BASE, "RequestSecurityTokenResponseCollection").pyclass
RequestSingleSecurityTokenMessage               = GED(NS.WSTRUST.BASE, "RequestSecurityToken").pyclass
RequestSingleSecurityTokenResponseMessage       = GED(NS.WSTRUST.BASE, "RequestSecurityTokenResponse").pyclass