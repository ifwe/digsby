import logging
log = logging.getLogger('facebook.sasl')
from pyxmpp.sasl.core import ClientAuthenticator
from pyxmpp.sasl.core import Success, Response
from util.net import WebFormData

class XFacebookPlatformClientAuthenticator(ClientAuthenticator):
    def __init__(self, password_manager, fbapi=None):
        ClientAuthenticator.__init__(self, password_manager)
        self.api = password_manager.owner.api

    def start(self, ignored_username, ignored_authzid):
        return Response()

    def challenge(self, challenge):
        in_params = WebFormData.parse(challenge, utf8=True)
        out_params = {'nonce': in_params['nonce'].encode('utf-8')}
        out_params = self.api.prepare_call(in_params['method'].encode('utf-8'), **out_params)
        return Response(out_params)

    def finish(self,data):
        return Success(None)
