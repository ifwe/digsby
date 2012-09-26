#
# (C) Copyright 2003-2006 Jacek Konieczny <jajcus@jajcus.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License Version
# 2.1 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# pylint: disable-msg=W0201

"""TLS support for XMPP streams.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: streamtls.py 681 2008-12-05 07:18:41Z jajcus $"
__docformat__="restructuredtext en"

import socket
import sys
import errno
import logging

from pyxmpp.streambase import StreamBase,STREAM_NS
from pyxmpp.streambase import FatalStreamError,StreamEncryptionRequired
from pyxmpp.exceptions import TLSNegotiationFailed, TLSError, TLSNegotiatedButNotAvailableError

try:
    import M2Crypto
    if M2Crypto.version_info < (0, 16):
        tls_available = 0
    else:
        from M2Crypto import SSL
        from M2Crypto.SSL import SSLError
        import M2Crypto.SSL.cb
        tls_available = 1
except ImportError:
    tls_available = 0

if not tls_available:
    class SSLError(Exception):
        "dummy"
        pass

TLS_NS="urn:ietf:params:xml:ns:xmpp-tls"

class TLSSettings:
    """Storage for TLS-related settings of an XMPP stream.

       :Ivariables:
            - `require`: is TLS required
            - `verify_peer`: should the peer's certificate be verified
            - `cert_file`: path to own X.509 certificate
            - `key_file`: path to the private key for own X.509 certificate
            - `cacert_file`: path to a file with trusted CA certificates
            - `verify_callback`: callback function for certificate
              verification. See M2Crypto documentation for details."""

    def __init__(self,
            require=False,verify_peer=True,
            cert_file=None,key_file=None,cacert_file=None,
            verify_callback=None,ctx=None):
        """Initialize the TLSSettings object.

        :Parameters:
            - `require`:  is TLS required
            - `verify_peer`: should the peer's certificate be verified
            - `cert_file`: path to own X.509 certificate
            - `key_file`: path to the private key for own X.509 certificate
            - `cacert_file`: path to a file with trusted CA certificates
            - `verify_callback`: callback function for certificate
              verification. The callback function must accept two arguments:
              'ok' and 'store_context' and return True if a certificate is accepted.
              The verification callback should call Stream.tls_is_certificate_valid()
              to check if certificate subject name matches stream peer JID.
              See M2Crypto documentation for details. If no verify_callback is provided,
              then default `Stream.tls_default_verify_callback` will be used."""
        self.require=require
        self.ctx=ctx
        self.verify_peer=verify_peer
        self.cert_file=cert_file
        self.cacert_file=cacert_file
        self.key_file=key_file
        self.verify_callback=verify_callback

class StreamTLSMixIn:
    tls_available = tls_available
    """Mix-in class providing TLS support for an XMPP stream.

    :Ivariables:
        - `tls`: TLS connection object.
    """
    def __init__(self,tls_settings=None):
        """Initialize TLS support of a Stream object

        :Parameters:
          - `tls_settings`: settings for StartTLS.
        :Types:
          - `tls_settings`: `TLSSettings`
        """
        self.tls_settings=tls_settings
        self.__logger=logging.getLogger("pyxmpp.StreamTLSMixIn")

    def _reset_tls(self):
        """Reset `StreamTLSMixIn` object state making it ready to handle new
        connections."""
        self.tls=None
        self.tls_requested=False

    def _make_stream_tls_features(self,features):
        """Update the <features/> with StartTLS feature.

        [receving entity only]

        :Parameters:
            - `features`: the <features/> element of the stream.
        :Types:
            - `features`: `libxml2.xmlNode`

        :returns: updated <features/> element node.
        :returntype: `libxml2.xmlNode`"""
        if self.tls_settings and not self.tls:
            tls=features.newChild(None,"starttls",None)
            ns=tls.newNs(TLS_NS,None)
            tls.setNs(ns)
            if self.tls_settings.require:
                tls.newChild(None,"required",None)
        return features

    def _write_raw(self,data):
        """Same as `Stream.write_raw` but assume `self.lock` is acquired."""
        logging.getLogger("pyxmpp.Stream.out").debug("OUT: %r",data)
        try:
            if self.tls:
                self.tls.setblocking(True)
            if self.socket:
                self.socket.send(data)
            if self.tls:
                self.tls.setblocking(False)
        except (IOError,OSError,socket.error),e:
            raise FatalStreamError("IO Error: "+str(e))
        except SSLError,e:
            raise TLSError("TLS Error: "+str(e))

    def _read_tls(self):
        """Read data pending on the stream socket and pass it to the parser."""
        if self.eof:
            return
        while self.socket:
            try:
                r=self.socket.read()
                if r is None:
                    return
            except socket.error,e:
                if e.args[0]!=errno.EINTR:
                    raise
                return
            self._feed_reader(r)

    def _read(self):
        """Read data pending on the stream socket and pass it to the parser."""
        self.__logger.debug("StreamTLSMixIn._read(), socket: %r",self.socket)
        if self.tls:
            self._read_tls()
        else:
            StreamBase._read(self)

    def _process(self):
        """Same as `Stream.process` but assume `self.lock` is acquired."""
        try:
            StreamBase._process(self)
        except SSLError,e:
            self.close()
            raise TLSError("TLS Error: "+str(e))

    def _process_node_tls(self,xmlnode):
        """Process incoming stream element. Pass it to _process_tls_node
        if it is in TLS namespace.

        :raise StreamEncryptionRequired: if encryption is required by current
          configuration, it is not active and the element is not in the TLS
          namespace nor in the stream namespace.

        :return: `True` when the node was recognized as TLS element.
        :returntype: `bool`"""
        ns_uri=xmlnode.ns().getContent()
        if ns_uri==STREAM_NS:
            return False
        elif ns_uri==TLS_NS:
            self._process_tls_node(xmlnode)
            return True
        if self.tls_settings and self.tls_settings.require and not self.tls:
            raise StreamEncryptionRequired,"TLS encryption required and not started yet"
        return False

    def _handle_tls_features(self):
        """Process incoming StartTLS related element of <stream:features/>.

        [initiating entity only]

        The received features node is available in `self.features`."""
        ctxt = self.doc_in.xpathNewContext()
        ctxt.setContextNode(self.features)
        ctxt.xpathRegisterNs("tls",TLS_NS)
        try:
            tls_n=ctxt.xpathEval("tls:starttls")
            tls_required_n=ctxt.xpathEval("tls:starttls/tls:required")
        finally:
            ctxt.xpathFreeContext()

        if not self.tls:
            if tls_required_n and not self.tls_settings:
                raise FatalStreamError,"StartTLS support disabled, but required by peer"
            if self.tls_settings and self.tls_settings.require and not tls_n:
                raise FatalStreamError,"StartTLS required, but not supported by peer"
            if self.tls_settings and tls_n:
                self.__logger.debug("StartTLS negotiated")
                if not self.tls_available:
                    raise TLSNegotiatedButNotAvailableError,("StartTLS negotiated, but not available"
                            " (M2Crypto >= 0.16 module required)")
                if self.initiator:
                    self._request_tls()
            else:
                self.__logger.debug("StartTLS not negotiated")

    def _request_tls(self):
        """Request a TLS-encrypted connection.

        [initiating entity only]"""
        self.tls_requested=1
        self.features=None
        root=self.doc_out.getRootElement()
        xmlnode=root.newChild(None,"starttls",None)
        ns=xmlnode.newNs(TLS_NS,None)
        xmlnode.setNs(ns)
        self._write_raw(xmlnode.serialize(encoding="UTF-8"))
        xmlnode.unlinkNode()
        xmlnode.freeNode()

    def _process_tls_node(self,xmlnode):
        """Process stream element in the TLS namespace.

        :Parameters:
            - `xmlnode`: the XML node received
        """
        if not self.tls_settings or not tls_available:
            self.__logger.debug("Unexpected TLS node: %r" % (xmlnode.serialize()))
            return False
        if self.initiator:
            if xmlnode.name=="failure":
                raise TLSNegotiationFailed,"Peer failed to initialize TLS connection"
            elif xmlnode.name!="proceed" or not self.tls_requested:
                self.__logger.debug("Unexpected TLS node: %r" % (xmlnode.serialize()))
                return False
            try:
                self.tls_requested=0
                self._make_tls_connection()
                self.socket=self.tls
            except SSLError,e:
                self.tls=None
                raise TLSError("TLS Error: "+str(e))
            self.__logger.debug("Restarting XMPP stream")
            self._restart_stream()
            return True
        else:
            raise FatalStreamError,"TLS not implemented for the receiving side yet"

    def _make_tls_connection(self):
        """Initiate TLS connection.

        [initiating entity only]"""
        if not tls_available or not self.tls_settings:
            raise TLSError,"TLS is not available"

        self.state_change("tls connecting",self.peer)
        self.__logger.debug("Creating TLS context")
        if self.tls_settings.ctx:
            ctx=self.tls_settings.ctx
        else:
            ctx=SSL.Context('tlsv1')

        verify_callback = self.tls_settings.verify_callback
        if not verify_callback:
            verify_callback = self.tls_default_verify_callback


        if self.tls_settings.verify_peer:
            self.__logger.debug("verify_peer, verify_callback: %r", verify_callback)
            ctx.set_verify(SSL.verify_peer, 10, verify_callback)
        else:
            ctx.set_verify(SSL.verify_none, 10)

        if self.tls_settings.cert_file:
            ctx.use_certificate_chain_file(self.tls_settings.cert_file)
            if self.tls_settings.key_file:
                ctx.use_PrivateKey_file(self.tls_settings.key_file)
            else:
                ctx.use_PrivateKey_file(self.tls_settings.cert_file)
            ctx.check_private_key()
        if self.tls_settings.cacert_file:
            try:
                ctx.load_verify_location(self.tls_settings.cacert_file)
            except AttributeError:
                ctx.load_verify_locations(self.tls_settings.cacert_file)
        self.__logger.debug("Creating TLS connection")
        self.tls=SSL.Connection(ctx,self.socket)
        self.socket=None
        self.__logger.debug("Setting up TLS connection")
        self.tls.setup_ssl()
        self.__logger.debug("Setting TLS connect state")
        self.tls.set_connect_state()
        self.__logger.debug("Starting TLS handshake")
        self.tls.connect_ssl()
        self.state_change("tls connected",self.peer)
        self.tls.setblocking(0)

        # clear any exception state left by some M2Crypto broken code
        try:
            raise Exception
        except:
            pass

    def tls_is_certificate_valid(self, store_context):
        """Check subject name of the certificate and return True when
        it is valid.

        Only the certificate at depth 0 in the certificate chain (peer
        certificate) is checked.

        Currently only the Common Name is checked and certificate is considered
        valid if CN is the same as the peer JID.

        :Parameters:
            - `store_context`: certificate store context, as passed to the
              verification callback.

        :returns: verification result. `True` if certificate subject name is valid.
        """
        depth = store_context.get_error_depth()
        if depth > 0:
            return True
        cert = store_context.get_current_cert()
        cn = cert.get_subject().CN
        if str(cn) != self.peer.as_utf8():
            return False
        return True

    def tls_default_verify_callback(self, ok, store_context):
        """Default certificate verification callback for TLS connections.

        Will reject connection (return `False`) if M2Crypto finds any error
        or when certificate CommonName doesn't match peer JID.

        TODO: check otherName/idOnXMPP (or what it is called)

        :Parameters:
            - `ok`: current verification result (as decided by OpenSSL).
            - `store_context`: certificate store context

        :return: computed verification result."""
        try:
            self.__logger.debug("tls_default_verify_callback(ok=%i, store=%r)" % (ok, store_context))
            from M2Crypto import X509,m2

            depth = store_context.get_error_depth()
            cert = store_context.get_current_cert()
            cn = cert.get_subject().CN

            self.__logger.debug("  depth: %i cert CN: %r" % (depth, cn))
            if ok and not self.tls_is_certificate_valid(store_context):
                self.__logger.debug(u"Common name does not match peer name (%s != %s)" % (cn, self.peer.as_utf8))
                return False
            return ok
        except:
            self.__logger.exception("Exception caught")
            raise

    def get_tls_connection(self):
        """Get the TLS connection object for the stream.

        :return: `self.tls`"""
        return self.tls

# vi: sts=4 et sw=4
