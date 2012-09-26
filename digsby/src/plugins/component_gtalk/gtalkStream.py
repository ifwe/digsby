from pyxmpp import sasl
from pyxmpp.exceptions import SASLNotAvailable, SASLMechanismNotAvailable, SASLAuthenticationFailed, \
                              FatalStreamError
from jabber.threadstream import ThreadStream
from pyxmpp.streamsasl import SASL_NS
from pyxmpp.streambase import STREAM_NS
from pyxmpp.jid import JID
import libxml2

from logging import getLogger
log = getLogger('gtalkStream')

GTALK_AUTH_NS = 'http://www.google.com/talk/protocol/auth'

class GoogleTalkStream(ThreadStream):
    def stream_start(self,doc):
        """Process <stream:stream> (stream start) tag received from peer.

        :Parameters:
            - `doc`: document created by the parser"""
        self.doc_in=doc
        log.debug("input document: %r" % (self.doc_in.serialize(),))

        try:
            r=self.doc_in.getRootElement()
            if r.ns().getContent() != STREAM_NS:
                self._send_stream_error("invalid-namespace")
                raise FatalStreamError,"Invalid namespace."
        except libxml2.treeError:
            self._send_stream_error("invalid-namespace")
            raise FatalStreamError,"Couldn't get the namespace."

        self.version=r.prop("version")
        if self.version and self.version!="1.0":
            self._send_stream_error("unsupported-version")
            raise FatalStreamError,"Unsupported protocol version."

#        to_from_mismatch=0
        assert self.initiator
        if self.initiator:
            self.stream_id=r.prop("id")
            peer=r.prop("from")
            if peer:
                peer=JID(peer)
#            if self.peer:
#                if peer and peer!=self.peer:
#                    self.__logger.debug("peer hostname mismatch:"
#                        " %r != %r" % (peer,self.peer))
#                    to_from_mismatch=1
#            else:
                self.peer=peer
        else:
            to=r.prop("to")
            if to:
                to=self.check_to(to)
                if not to:
                    self._send_stream_error("host-unknown")
                    raise FatalStreamError,'Bad "to"'
                self.me=JID(to)
            self._send_stream_start(self.generate_id())
            self._send_stream_features()
            self.state_change("fully connected",self.peer)
            self._post_connect()

        if not self.version:
            self.state_change("fully connected",self.peer)
            self._post_connect()

#        if to_from_mismatch:
#            raise HostMismatch

    def _sasl_authenticate(self,username,authzid,mechanism=None):
        """Start SASL authentication process.

        [initiating entity only]

        :Parameters:
            - `username`: user name.
            - `authzid`: authorization ID.
            - `mechanism`: SASL mechanism to use."""
        if not self.initiator:
            raise SASLAuthenticationFailed,"Only initiating entity start SASL authentication"
        while not self.features:
            self.__logger.debug("Waiting for features")
            self._read()
        if not self.peer_sasl_mechanisms:
            raise SASLNotAvailable,"Peer doesn't support SASL"

        if not mechanism:
            mechanism=None
            for m in self.sasl_mechanisms:
                if m in self.peer_sasl_mechanisms:
                    mechanism=m
                    break
            if not mechanism:
                raise SASLMechanismNotAvailable,"Peer doesn't support any of our SASL mechanisms"
            self.__logger.debug("Our mechanism: %r" % (mechanism,))
        else:
            if mechanism not in self.peer_sasl_mechanisms:
                raise SASLMechanismNotAvailable,"%s is not available" % (mechanism,)

        self.auth_method_used="sasl:"+mechanism

        self.authenticator=sasl.client_authenticator_factory(mechanism,self)

        initial_response=self.authenticator.start(username,authzid)
        if not isinstance(initial_response,sasl.Response):
            raise SASLAuthenticationFailed,"SASL initiation failed"

        root=self.doc_out.getRootElement()
        xmlnode=root.newChild(None,"auth",None)
        ns=xmlnode.newNs(SASL_NS,None)
        xmlnode.setNs(ns)
        xmlnode.setProp("mechanism",mechanism)

        ga=xmlnode.newNs(GTALK_AUTH_NS,'ga')
        xmlnode.newNsProp(ga, 'client-uses-full-bind-result', 'true')

        if initial_response.data:
            xmlnode.setContent(initial_response.base64())

        self._write_raw(xmlnode.serialize(encoding="UTF-8"))
        
        self.freeOutNode(xmlnode)
        