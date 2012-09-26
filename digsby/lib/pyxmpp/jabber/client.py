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
"""Basic Jabber client functionality implementation.

Extends `pyxmpp.client` interface with legacy authentication
and basic Service Discovery handling.

Normative reference:
  - `JEP 78 <http://www.jabber.org/jeps/jep-0078.html>`__
  - `JEP 30 <http://www.jabber.org/jeps/jep-0030.html>`__
"""

__revision__="$Id: client.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import logging

from pyxmpp.jabber.clientstream import LegacyClientStream
from pyxmpp.jabber.disco import DISCO_ITEMS_NS,DISCO_INFO_NS
from pyxmpp.jabber.disco import DiscoInfo,DiscoItems,DiscoIdentity
from pyxmpp.jabber import disco
from pyxmpp.client import Client
from pyxmpp.stanza import Stanza
from pyxmpp.cache import CacheSuite
from pyxmpp.utils import from_utf8
from pyxmpp.interfaces import IFeaturesProvider

class JabberClient(Client):
    """Base class for a Jabber client.

    :Ivariables:
        - `disco_items`: default Disco#items reply for a query to an empty node.
        - `disco_info`: default Disco#info reply for a query to an empty node --
          provides information about the client and its supported fetures.
        - `disco_identity`: default identity of the default `disco_info`.
        - `register`: when `True` than registration will be started instead of authentication.
    :Types:
        - `disco_items`: `DiscoItems`
        - `disco_info`: `DiscoInfo`
        - `register`: `bool`
    """
    def __init__(self,jid=None, password=None, server=None, port=5222,
            auth_methods=("sasl:DIGEST-MD5","digest"),
            tls_settings=None, keepalive=0,
            disco_name=u"pyxmpp based Jabber client", disco_category=u"client",
            disco_type=u"pc"):
        """Initialize a JabberClient object.

        :Parameters:
            - `jid`: user full JID for the connection.
            - `password`: user password.
            - `server`: server to use. If not given then address will be derived form the JID.
            - `port`: port number to use. If not given then address will be derived form the JID.
            - `auth_methods`: sallowed authentication methods. SASL authentication mechanisms
              in the list should be prefixed with "sasl:" string.
            - `tls_settings`: settings for StartTLS -- `TLSSettings` instance.
            - `keepalive`: keepalive output interval. 0 to disable.
            - `disco_name`: name of the client identity in the disco#info
              replies.
            - `disco_category`: category of the client identity in the disco#info
              replies. The default of u'client' should be the right choice in
              most cases.
            - `disco_type`: type of the client identity in the disco#info
              replies. Use `the types registered by Jabber Registrar <http://www.jabber.org/registrar/disco-categories.html>`__
        :Types:
            - `jid`: `pyxmpp.JID`
            - `password`: `unicode`
            - `server`: `unicode`
            - `port`: `int`
            - `auth_methods`: sequence of `str`
            - `tls_settings`: `pyxmpp.TLSSettings`
            - `keepalive`: `int`
            - `disco_name`: `unicode`
            - `disco_category`: `unicode`
            - `disco_type`: `unicode`
        """

        Client.__init__(self,jid,password,server,port,auth_methods,tls_settings,keepalive)
        self.stream_class = LegacyClientStream
        self.disco_items=DiscoItems()
        self.disco_info=DiscoInfo()
        self.disco_identity=DiscoIdentity(self.disco_info,
                            disco_name, disco_category, disco_type)
        self.register_feature(u"dnssrv")
        self.register_feature(u"stringprep")
        self.register_feature(u"urn:ietf:params:xml:ns:xmpp-sasl#c2s")
        self.cache = CacheSuite(max_items = 1000)
        self.__logger = logging.getLogger("pyxmpp.jabber.JabberClient")

# public methods

    def connect(self, register = False):
        """Connect to the server and set up the stream.

        Set `self.stream` and notify `self.state_changed` when connection
        succeeds. Additionally, initialize Disco items and info of the client.
        """
        Client.connect(self, register)
        if register:
            self.stream.registration_callback = self.process_registration_form

    def register_feature(self, feature_name):
        """Register a feature to be announced by Service Discovery.

        :Parameters:
            - `feature_name`: feature namespace or name.
        :Types:
            - `feature_name`: `unicode`"""
        self.disco_info.add_feature(feature_name)

    def unregister_feature(self, feature_name):
        """Unregister a feature to be announced by Service Discovery.

        :Parameters:
            - `feature_name`: feature namespace or name.
        :Types:
            - `feature_name`: `unicode`"""
        self.disco_info.remove_feature(feature_name)

    def submit_registration_form(self, form):
        """Submit a registration form

        :Parameters:
            - `form`: the form to submit
        :Types:
            - `form`: `pyxmpp.jabber.dataforms.Form`"""
        self.stream.submit_registration_form(form)

# private methods
    def __disco_info(self,iq):
        """Handle a disco#info request.

        `self.disco_get_info` method will be used to prepare the query response.

        :Parameters:
            - `iq`: the IQ stanza received.
        :Types:
            - `iq`: `pyxmpp.iq.Iq`"""
        q=iq.get_query()
        if q.hasProp("node"):
            node=from_utf8(q.prop("node"))
        else:
            node=None
        info=self.disco_get_info(node,iq)
        if isinstance(info,DiscoInfo):
            resp=iq.make_result_response()
            self.__logger.debug("Disco-info query: %s preparing response: %s with reply: %s"
                % (iq.serialize(),resp.serialize(),info.xmlnode.serialize()))
            resp.set_content(info.xmlnode.copyNode(1))
        elif isinstance(info,Stanza):
            resp=info
        else:
            resp=iq.make_error_response("item-not-found")
        self.__logger.debug("Disco-info response: %s" % (resp.serialize(),))
        self.stream.send(resp)

    def __disco_items(self,iq):
        """Handle a disco#items request.

        `self.disco_get_items` method will be used to prepare the query response.

        :Parameters:
            - `iq`: the IQ stanza received.
        :Types:
            - `iq`: `pyxmpp.iq.Iq`"""
        q=iq.get_query()
        if q.hasProp("node"):
            node=from_utf8(q.prop("node"))
        else:
            node=None
        items=self.disco_get_items(node,iq)
        if isinstance(items,DiscoItems):
            resp=iq.make_result_response()
            self.__logger.debug("Disco-items query: %s preparing response: %s with reply: %s"
                % (iq.serialize(),resp.serialize(),items.xmlnode.serialize()))
            resp.set_content(items.xmlnode.copyNode(1))
        elif isinstance(items,Stanza):
            resp=items
        else:
            resp=iq.make_error_response("item-not-found")
        self.__logger.debug("Disco-items response: %s" % (resp.serialize(),))
        self.stream.send(resp)

    def _session_started(self):
        """Called when session is started.
        
        Activates objects from `self.interface_provides` by installing
        their disco features."""
        Client._session_started(self)
        for ob in self.interface_providers:
            if IFeaturesProvider.providedBy(ob):
                for ns in ob.get_features():
                    self.register_feature(ns)

# methods to override

    def authorized(self):
        """Handle "authorized" event. May be overriden in derived classes.
        By default: request an IM session and setup Disco handlers."""
        Client.authorized(self)
        self.stream.set_iq_get_handler("query",DISCO_ITEMS_NS,self.__disco_items)
        self.stream.set_iq_get_handler("query",DISCO_INFO_NS,self.__disco_info)
        disco.register_disco_cache_fetchers(self.cache,self.stream)

    def disco_get_info(self,node,iq):
        """Return Disco#info data for a node.

        :Parameters:
            - `node`: the node queried.
            - `iq`: the request stanza received.
        :Types:
            - `node`: `unicode`
            - `iq`: `pyxmpp.iq.Iq`

        :return: self.disco_info if `node` is empty or `None` otherwise.
        :returntype: `DiscoInfo`"""
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_info:
            return self.disco_info
        return None

    def disco_get_items(self,node,iq):
        """Return Disco#items data for a node.

        :Parameters:
            - `node`: the node queried.
            - `iq`: the request stanza received.
        :Types:
            - `node`: `unicode`
            - `iq`: `pyxmpp.iq.Iq`

        :return: self.disco_info if `node` is empty or `None` otherwise.
        :returntype: `DiscoInfo`"""
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_items:
            return self.disco_items
        return None

    def process_registration_form(self, stanza, form):
        """Fill-in the registration form provided by the server.

        This default implementation fills-in "username" and "passwords"
        fields only and instantly submits the form.

        :Parameters:
            - `stanza`: the stanza received.
            - `form`: the registration form.
        :Types:
            - `stanza`: `pyxmpp.iq.Iq`
            - `form`: `pyxmpp.jabber.dataforms.Form`
        """
        _unused = stanza
        self.__logger.debug(u"default registration callback started. auto-filling-in the form...")
        if not 'FORM_TYPE' in form or 'jabber:iq:register' not in form['FORM_TYPE'].values:
            raise RuntimeError, "Unknown form type: %r %r" % (form, form['FORM_TYPE'])
        for field in form:
            if field.name == u"username":
                self.__logger.debug(u"Setting username to %r" % (self.jid.node,))
                field.value = self.jid.node
            elif field.name == u"password":
                self.__logger.debug_s(u"Setting password to %r.decode('rot13')" % (self.password.encode('rot13'),))
                field.value = self.password
            elif field.required:
                self.__logger.debug(u"Unknown required field: %r" % (field.name,))
                raise RuntimeError, "Unsupported required registration form field %r" % (field.name,)
            else:
                self.__logger.debug(u"Unknown field: %r" % (field.name,))
        self.submit_registration_form(form)

# vi: sts=4 et sw=4
