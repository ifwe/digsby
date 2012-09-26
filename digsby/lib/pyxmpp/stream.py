#
# (C) Copyright 2003-2010 Jacek Konieczny <jajcus@jajcus.net>
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

"""Generic XMPP stream implementation.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: stream.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import logging

from pyxmpp.streambase import StreamBase
from pyxmpp.streamtls import StreamTLSMixIn
from pyxmpp.streamsasl import StreamSASLMixIn

class Stream(StreamTLSMixIn,StreamSASLMixIn,StreamBase):
    """Generic XMPP stream class.

    Responsible for establishing connection, parsing the stream,
    StartTLS encryption and SASL authentication negotiation
    and usage, dispatching received stanzas to apopriate handlers
    and sending application's stanzas.

    Whenever we say "stream" here we actually mean two streams
    (incoming and outgoing) of one connections, as defined by the XMPP
    specification.

    :Ivariables:
        - `lock`: RLock object used to synchronize access to Stream object.
        - `features`: stream features as annouced by the initiator.
        - `me`: local stream endpoint JID.
        - `peer`: remote stream endpoint JID.
        - `process_all_stanzas`: when `True` then all stanzas received are
          considered local.
        - `tls`: TLS connection object.
        - `initiator`: `True` if local stream endpoint is the initiating entity.
        - `_reader`: the stream reader object (push parser) for the stream.
    """
    def __init__(self, default_ns, extra_ns = (), sasl_mechanisms = (),
                    tls_settings = None, keepalive = 0, owner = None):
        """Initialize Stream object

        :Parameters:
          - `default_ns`: stream's default namespace ("jabber:client" for
            client, "jabber:server" for server, etc.)
          - `extra_ns`: sequence of extra namespace URIs to be defined for
            the stream.
          - `sasl_mechanisms`: sequence of SASL mechanisms allowed for
            authentication. Currently "PLAIN", "DIGEST-MD5" and "GSSAPI" are supported.
          - `tls_settings`: settings for StartTLS -- `TLSSettings` instance.
          - `keepalive`: keepalive output interval. 0 to disable.
          - `owner`: `Client`, `Component` or similar object "owning" this stream.
        """
        StreamBase.__init__(self, default_ns, extra_ns, keepalive, owner)
        StreamTLSMixIn.__init__(self, tls_settings)
        StreamSASLMixIn.__init__(self, sasl_mechanisms)
        self.__logger = logging.getLogger("pyxmpp.Stream")

    def _reset(self):
        """Reset `Stream` object state making it ready to handle new
        connections."""
        StreamBase._reset(self)
        self._reset_tls()
        self._reset_sasl()

    def _make_stream_features(self):
        """Create the <features/> element for the stream.

        [receving entity only]

        :returns: new <features/> element node."""
        features=StreamBase._make_stream_features(self)
        self._make_stream_tls_features(features)
        self._make_stream_sasl_features(features)
        return features

    def _process_node(self,xmlnode):
        """Process first level element of the stream.

        The element may be stream error or features, StartTLS
        request/response, SASL request/response or a stanza.

        :Parameters:
            - `xmlnode`: XML node describing the element
        """
        if self._process_node_tls(xmlnode):
            return
        if self._process_node_sasl(xmlnode):
            return
        StreamBase._process_node(self,xmlnode)

    def _got_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        self._handle_tls_features()
        self._handle_sasl_features()
        StreamBase._got_features(self)
        if not self.tls_requested and not self.authenticated:
            self.state_change("fully connected",self.peer)
            self._post_connect()

# vi: sts=4 et sw=4
