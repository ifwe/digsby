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

"""Jabberd external component interface (jabber:component:accept).

Normative reference:
  - `JEP 114 <http://www.jabber.org/jeps/jep-0114.html>`__
"""

__revision__="$Id: component.py 714 2010-04-05 10:20:10Z jajcus $"
__docformat__="restructuredtext en"

import threading
import logging

from pyxmpp.jabberd.componentstream import ComponentStream
from pyxmpp.utils import from_utf8
from pyxmpp.jabber.disco import DiscoItems,DiscoInfo,DiscoIdentity
from pyxmpp.stanza import Stanza

class Component:
    """Jabber external component ("jabber:component:accept" protocol) interface
    implementation.

    Override this class to build your components.

    :Ivariables:
        - `jid`: component JID (should contain only the domain part).
        - `secret`: the authentication secret.
        - `server`: server to which the commonent will connect.
        - `port`: port number on the server to which the commonent will
          connect.
        - `keepalive`: keepalive interval for the stream.
        - `stream`: the XMPP stream object for the active connection
          or `None` if no connection is active.
        - `disco_items`: disco items announced by the component. Created
          when a stream is connected.
        - `disco_info`: disco info announced by the component. Created
          when a stream is connected.
        - `disco_identity`: disco identity (part of disco info) announced by
          the component. Created when a stream is connected.
        - `disco_category`: disco category to be used to create
          `disco_identity`.
        - `disco_type`: disco type to be used to create `disco_identity`.

    :Types:
        - `jid`:  `pyxmpp.JID`
        - `secret`: `unicode`
        - `server`: `unicode`
        - `port`: `int`
        - `keepalive`: `int`
        - `stream`: `pyxmpp.jabberd.ComponentStream`
        - `disco_items`: `pyxmpp.jabber.DiscoItems`
        - `disco_info`: `pyxmpp.jabber.DiscoInfo`
        - `disco_identity`: `pyxmpp.jabber.DiscoIdentity`
        - `disco_category`: `str`
        - `disco_type`: `str`"""
    def __init__(self, jid=None, secret=None, server=None, port=5347,
            disco_name=u"PyXMPP based component", disco_category=u"x-service",
            disco_type=u"x-unknown", keepalive=0):
        """Initialize a `Component` object.

        :Parameters:
            - `jid`: component JID (should contain only the domain part).
            - `secret`: the authentication secret.
            - `server`: server name or address the component should connect.
            - `port`: port number on the server where the component should connect.
            - `disco_name`: disco identity name to be used in the
              disco#info responses.
            - `disco_category`: disco identity category to be used in the
              disco#info responses.  Use `the categories registered by Jabber Registrar <http://www.jabber.org/registrar/disco-categories.html>`__
            - `disco_type`: disco identity type to be used in the component's
              disco#info responses.  Use `the types registered by Jabber Registrar <http://www.jabber.org/registrar/disco-categories.html>`__
            - `keepalive`: keepalive interval for the stream.

        :Types:
            - `jid`:  `pyxmpp.JID`
            - `secret`: `unicode`
            - `server`: `str` or `unicode`
            - `port`: `int`
            - `disco_name`: `unicode`
            - `disco_category`: `unicode`
            - `disco_type`: `unicode`
            - `keepalive`: `int`"""
        self.jid=jid
        self.secret=secret
        self.server=server
        self.port=port
        self.keepalive=keepalive
        self.stream=None
        self.lock=threading.RLock()
        self.state_changed=threading.Condition(self.lock)
        self.stream_class=ComponentStream
        self.disco_items=DiscoItems()
        self.disco_info=DiscoInfo()
        self.disco_identity=DiscoIdentity(self.disco_info,
                            disco_name, disco_category, disco_type)
        self.register_feature("stringprep")
        self.__logger=logging.getLogger("pyxmpp.jabberd.Component")

# public methods

    def connect(self):
        """Establish a connection with the server.

        Set `self.stream` to the `pyxmpp.jabberd.ComponentStream` when
        initial connection succeeds.

        :raise ValueError: when some of the component properties
          (`self.jid`, `self.secret`,`self.server` or `self.port`) are wrong."""
        if not self.jid or self.jid.node or self.jid.resource:
            raise ValueError,"Cannot connect: no or bad JID given"
        if not self.secret:
            raise ValueError,"Cannot connect: no secret given"
        if not self.server:
            raise ValueError,"Cannot connect: no server given"
        if not self.port:
            raise ValueError,"Cannot connect: no port given"

        self.lock.acquire()
        try:
            stream=self.stream
            self.stream=None
            if stream:
                stream.close()

            self.__logger.debug("Creating component stream: %r" % (self.stream_class,))
            stream=self.stream_class(jid = self.jid,
                    secret = self.secret,
                    server = self.server,
                    port = self.port,
                    keepalive = self.keepalive,
                    owner = self)
            stream.process_stream_error=self.stream_error
            self.stream_created(stream)
            stream.state_change=self.__stream_state_change
            stream.connect()
            self.stream=stream
            self.state_changed.notify()
            self.state_changed.release()
        except:
            self.stream=None
            self.state_changed.release()
            raise

    def get_stream(self):
        """Get the stream of the component in a safe way.

        :return: Stream object for the component or `None` if no connection is
            active.
        :returntype: `pyxmpp.jabberd.ComponentStream`"""
        self.lock.acquire()
        stream=self.stream
        self.lock.release()
        return stream

    def disconnect(self):
        """Disconnect from the server."""
        stream=self.get_stream()
        if stream:
            stream.disconnect()

    def socket(self):
        """Get the socket of the connection to the server.

        :return: the socket.
        :returntype: `socket.socket`"""
        return self.stream.socket

    def loop(self,timeout=1):
        """Simple 'main loop' for a component.

        This usually will be replaced by something more sophisticated. E.g.
        handling of other input sources."""
        self.stream.loop(timeout)

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


# private methods
    def __stream_state_change(self,state,arg):
        """Handle various stream state changes and call right
        methods of `self`.

        :Parameters:
            - `state`: state name.
            - `arg`: state parameter.
        :Types:
            - `state`: `string`
            - `arg`: any object"""
        self.stream_state_changed(state,arg)
        if state=="fully connected":
            self.connected()
        elif state=="authenticated":
            self.authenticated()
        elif state=="authorized":
            self.authorized()
        elif state=="disconnected":
            self.state_changed.acquire()
            try:
                if self.stream:
                    self.stream.close()
                self.stream_closed(self.stream)
                self.stream=None
                self.state_changed.notify()
            finally:
                self.state_changed.release()
            self.disconnected()

    def __disco_info(self,iq):
        """Handle a disco-info query.

        :Parameters:
            - `iq`: the stanza received.

        Types:
            - `iq`: `pyxmpp.Iq`"""
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
        """Handle a disco-items query.

        :Parameters:
            - `iq`: the stanza received.

        Types:
            - `iq`: `pyxmpp.Iq`"""
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

# Method to override
    def idle(self):
        """Do some "housekeeping" work like <iq/> result expiration. Should be
        called on a regular basis, usually when the component is idle."""
        stream=self.get_stream()
        if stream:
            stream.idle()

    def stream_created(self,stream):
        """Handle stream creation event.

        [may be overriden in derived classes]

        By default: do nothing.

        :Parameters:
            - `stream`: the stream just created.
        :Types:
            - `stream`: `pyxmpp.jabberd.ComponentStream`"""
        pass

    def stream_closed(self,stream):
        """Handle stream closure event.

        [may be overriden in derived classes]

        By default: do nothing.

        :Parameters:
            - `stream`: the stream just created.
        :Types:
            - `stream`: `pyxmpp.jabberd.ComponentStream`"""
        pass

    def stream_error(self,err):
        """Handle a stream error received.

        [may be overriden in derived classes]

        By default: just log it. The stream will be closed anyway.

        :Parameters:
            - `err`: the error element received.
        :Types:
            - `err`: `pyxmpp.error.StreamErrorNode`"""
        self.__logger.debug("Stream error: condition: %s %r"
                % (err.get_condition().name,err.serialize()))

    def stream_state_changed(self,state,arg):
        """Handle a stream state change.

        [may be overriden in derived classes]

        By default: do nothing.

        :Parameters:
            - `state`: state name.
            - `arg`: state parameter.
        :Types:
            - `state`: `string`
            - `arg`: any object"""
        pass

    def connected(self):
        """Handle stream connection event.

        [may be overriden in derived classes]

        By default: do nothing."""
        pass

    def authenticated(self):
        """Handle successful authentication event.

        A good place to register stanza handlers and disco features.

        [should be overriden in derived classes]

        By default: set disco#info and disco#items handlers."""
        self.__logger.debug("Setting up Disco handlers...")
        self.stream.set_iq_get_handler("query","http://jabber.org/protocol/disco#items",
                                    self.__disco_items)
        self.stream.set_iq_get_handler("query","http://jabber.org/protocol/disco#info",
                                    self.__disco_info)

    def authorized(self):
        """Handle successful authorization event."""
        pass

    def disco_get_info(self,node,iq):
        """Get disco#info data for a node.

        [may be overriden in derived classes]

        By default: return `self.disco_info` if no specific node name
        is provided.

        :Parameters:
            - `node`: name of the node queried.
            - `iq`: the stanza received.
        :Types:
            - `node`: `unicode`
            - `iq`: `pyxmpp.Iq`"""
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_info:
            return self.disco_info
        return None

    def disco_get_items(self,node,iq):
        """Get disco#items data for a node.

        [may be overriden in derived classes]

        By default: return `self.disco_items` if no specific node name
        is provided.

        :Parameters:
            - `node`: name of the node queried.
            - `iq`: the stanza received.
        :Types:
            - `node`: `unicode`
            - `iq`: `pyxmpp.Iq`"""
        to=iq.get_to()
        if to and to!=self.jid:
            return iq.make_error_response("recipient-unavailable")
        if not node and self.disco_items:
            return self.disco_items
        return None

    def disconnected(self):
        """Handle stream disconnection (connection closed by peer) event.

        [may be overriden in derived classes]

        By default: do nothing."""
        pass

# vi: sts=4 et sw=4
