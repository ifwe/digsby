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
# pylint: disable-msg=W0221

"""Client stream handling.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: clientstream.py 720 2010-04-20 10:31:35Z jajcus $"
__docformat__="restructuredtext en"

import logging

from pyxmpp.stream import Stream
from pyxmpp.streambase import BIND_NS
from pyxmpp.streamsasl import SASLNotAvailable,SASLMechanismNotAvailable
from pyxmpp.jid import JID
from pyxmpp.utils import to_utf8
from pyxmpp.exceptions import StreamError,StreamAuthenticationError,FatalStreamError
from pyxmpp.exceptions import ClientStreamError, FatalClientStreamError

class ClientStream(Stream):
    """Handles XMPP-IM client connection stream.

    Both client and server side of the connection is supported. This class handles
    client SASL authentication, authorisation and resource binding.

    This class is not ready for handling of legacy Jabber servers, as it doesn't
    provide legacy authentication.

    :Ivariables:
        - `my_jid`: requested local JID. Please notice that this may differ from
          `me`, which is actual authorized JID after the resource binding.
        - `server`: server to use.
        - `port`: port number to use.
        - `password`: user's password.
        - `auth_methods`: allowed authentication methods.
    :Types:
        - `my_jid`: `pyxmpp.JID`
        - `server`: `str`
        - `port`: `int`
        - `password`: `str`
        - `auth_methods`: `list` of `str`
    """
    def __init__(self, jid, password=None, server=None, port=None,
            auth_methods = ("sasl:DIGEST-MD5",),
            tls_settings = None, keepalive = 0, owner = None):
        """Initialize the ClientStream object.

        :Parameters:
            - `jid`: local JID.
            - `password`: user's password.
            - `server`: server to use. If not given then address will be derived form the JID.
            - `port`: port number to use. If not given then address will be derived form the JID.
            - `auth_methods`: sallowed authentication methods. SASL authentication mechanisms
              in the list should be prefixed with "sasl:" string.
            - `tls_settings`: settings for StartTLS -- `TLSSettings` instance.
            - `keepalive`: keepalive output interval. 0 to disable.
            - `owner`: `Client`, `Component` or similar object "owning" this stream.
        :Types:
            - `jid`: `pyxmpp.JID`
            - `password`: `unicode`
            - `server`: `unicode`
            - `port`: `int`
            - `auth_methods`: sequence of `str`
            - `tls_settings`: `pyxmpp.TLSSettings`
            - `keepalive`: `int`
        """
        sasl_mechanisms=[]
        for m in auth_methods:
            if not m.startswith("sasl:"):
                continue
            m=m[5:].upper()
            sasl_mechanisms.append(m)
        Stream.__init__(self, "jabber:client",
                    sasl_mechanisms = sasl_mechanisms,
                    tls_settings = tls_settings,
                    keepalive = keepalive,
                    owner = owner)
        self.server=server
        self.port=port
        self.password=password
        self.auth_methods=auth_methods
        self.my_jid=jid
        self.me = None
        self._auth_methods_left = None
        self.__logger=logging.getLogger("pyxmpp.ClientStream")

    def _reset(self):
        """Reset `ClientStream` object state, making the object ready to handle
        new connections."""
        Stream._reset(self)
        self._auth_methods_left=[]

    def connect(self,server=None,port=None):
        """Establish a client connection to a server.

        [client only]

        :Parameters:
            - `server`: name or address of the server to use. Not recommended -- proper value
              should be derived automatically from the JID.
            - `port`: port number of the server to use. Not recommended --
              proper value should be derived automatically from the JID.

        :Types:
            - `server`: `unicode`
            - `port`: `int`"""
        self.lock.acquire()
        try:
            self._connect(server,port)
        finally:
            self.lock.release()

    def _connect(self,server=None,port=None):
        """Same as `ClientStream.connect` but assume `self.lock` is acquired."""
        if not self.my_jid.node or not self.my_jid.resource:
            raise ClientStreamError,"Client JID must have username and resource"
        if not server:
            server=self.server
        if not port:
            port=self.port
        if server:
            self.__logger.debug("server: %r", (server,))
            service=None
        else:
            service="xmpp-client"
        if port is None:
            port=5222
        if server is None:
            server=self.my_jid.domain
        self.me=self.my_jid
        Stream._connect(self,server,port,service,self.my_jid.domain)

    def accept(self,sock):
        """Accept an incoming client connection.

        [server only]

        :Parameters:
            - `sock`: a listening socket."""
        Stream.accept(self,sock,self.my_jid)

    def _post_connect(self):
        """Initialize authentication when the connection is established
        and we are the initiator."""
        if self.initiator:
            self._auth_methods_left=list(self.auth_methods)
            self._try_auth()

    def _try_auth(self):
        """Try to authenticate using the first one of allowed authentication
        methods left.

        [client only]"""
        if not self.doc_out:
            self.__logger.debug("try_auth: disconnecting already?")
            return
        if self.authenticated:
            self.__logger.debug("try_auth: already authenticated")
            return
        self.__logger.debug("trying auth: %r", (self._auth_methods_left,))
        if not self._auth_methods_left:
            raise StreamAuthenticationError,"No allowed authentication methods available"
        method=self._auth_methods_left[0]
        if method.startswith("sasl:"):
            if self.version:
                self._auth_methods_left.pop(0)
                try:
                    mechanism = method[5:].upper()
                    # A bit hackish, but I'm not sure whether giving authzid won't mess something up
                    if mechanism != "EXTERNAL":
                        self._sasl_authenticate(self.my_jid.node, None,
                                mechanism=mechanism)
                    else:
                        self._sasl_authenticate(self.my_jid.node, self.my_jid.bare().as_utf8(),
                                mechanism=mechanism)
                except (SASLMechanismNotAvailable,SASLNotAvailable):
                    self.__logger.debug("Skipping unavailable auth method: %s", (method,) )
                    return self._try_auth()
            else:
                self._auth_methods_left.pop(0)
                self.__logger.debug("Skipping auth method %s as legacy protocol is in use",
                        (method,) )
                return self._try_auth()
        else:
            self._auth_methods_left.pop(0)
            self.__logger.debug("Skipping unknown auth method: %s", method)
            return self._try_auth()

    def _get_stream_features(self):
        """Include resource binding feature in the stream features list.

        [server only]"""
        features=Stream._get_stream_features(self)
        if self.peer_authenticated:
            bind=features.newChild(None,"bind",None)
            ns=bind.newNs(BIND_NS,None)
            bind.setNs(ns)
            self.set_iq_set_handler("bind",BIND_NS,self.do_bind)
        return features

    def do_bind(self,stanza):
        """Do the resource binding requested by a client connected.

        [server only]

        :Parameters:
            - `stanza`: resource binding request stanza.
        :Types:
            - `stanza`: `pyxmpp.Iq`"""
        fr=stanza.get_from()
        if fr and fr!=self.peer:
            r=stanza.make_error_response("forbidden")
            self.send(r)
            r.free()
            return
        resource_n=stanza.xpath_eval("bind:bind/bind:resource",{"bind":BIND_NS})
        if resource_n:
            resource=resource_n[0].getContent()
        else:
            resource="auto"
        if not resource:
            r=stanza.make_error_response("bad-request")
        else:
            self.unset_iq_set_handler("bind",BIND_NS)
            r=stanza.make_result_response()
            self.peer.set_resource(resource)
            q=r.new_query(BIND_NS,"bind")
            q.newTextChild(None,"jid",to_utf8(self.peer.as_unicode()))
            self.state_change("authorized",self.peer)
        r.set_to(None)
        self.send(r)
        r.free()

    def get_password(self, username, realm=None, acceptable_formats=("plain",)):
        """Get a user password for the SASL authentication.

        :Parameters:
            - `username`: username used for authentication.
            - `realm`: realm used for authentication.
            - `acceptable_formats`: acceptable password encoding formats requested.
        :Types:
            - `username`: `unicode`
            - `realm`: `unicode`
            - `acceptable_formats`: `list` of `str`

        :return: The password and the format name ('plain').
        :returntype: (`unicode`,`str`)"""
        _unused = realm
        if self.initiator and self.my_jid.node==username and "plain" in acceptable_formats:
            return self.password,"plain"
        else:
            return None,None

    def get_realms(self):
        """Get realms available for client authentication.

        [server only]

        :return: list of realms.
        :returntype: `list` of `unicode`"""
        return [self.my_jid.domain]

    def choose_realm(self,realm_list):
        """Choose authentication realm from the list provided by the server.

        [client only]

        Use domain of the own JID if no realm list was provided or the domain is on the list
        or the first realm on the list otherwise.

        :Parameters:
            - `realm_list`: realm list provided by the server.
        :Types:
            - `realm_list`: `list` of `unicode`

        :return: the realm chosen.
        :returntype: `unicode`"""
        if not realm_list:
            return self.my_jid.domain
        if self.my_jid.domain in realm_list:
            return self.my_jid.domain
        return realm_list[0]

    def check_authzid(self,authzid,extra_info=None):
        """Check authorization id provided by the client.

        [server only]

        :Parameters:
            - `authzid`: authorization id provided.
            - `extra_info`: additional information about the user
              from the authentication backend. This mapping will
              usually contain at least 'username' item.
        :Types:
            - `authzid`: unicode
            - `extra_info`: mapping

        :return: `True` if user is authorized to use that `authzid`.
        :returntype: `bool`"""
        if not extra_info:
            extra_info={}
        if not authzid:
            return 1
        if not self.initiator:
            jid=JID(authzid)
            if not extra_info.has_key("username"):
                ret=0
            elif jid.node!=extra_info["username"]:
                ret=0
            elif jid.domain!=self.my_jid.domain:
                ret=0
            elif not jid.resource:
                ret=0
            else:
                ret=1
        else:
            ret=0
        return ret

    def get_serv_type(self):
        """Get the server name for SASL authentication.

        :return: 'xmpp'."""
        return "xmpp"

    def get_serv_name(self):
        """Get the service name for SASL authentication.

        :return: domain of the own JID."""
        return self.my_jid.domain

    def get_serv_host(self):
        """Get the service host name for SASL authentication.

        :return: domain of the own JID."""
        # FIXME: that should be the hostname choosen from SRV records found.
        return self.my_jid.domain

    def fix_out_stanza(self,stanza):
        """Fix outgoing stanza.

        On a client clear the sender JID. On a server set the sender
        address to the own JID if the address is not set yet."""
        if self.initiator:
            stanza.set_from(None)
        else:
            if not stanza.get_from():
                stanza.set_from(self.my_jid)

    def fix_in_stanza(self,stanza):
        """Fix an incoming stanza.

        Ona server replace the sender address with authorized client JID."""
        if self.initiator:
            Stream.fix_in_stanza(self,stanza)
        else:
            stanza.set_from(self.peer)

# vi: sts=4 et sw=4
