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

"""Basic XMPP-IM client implementation.

Normative reference:
  - `RFC 3921 <http://www.ietf.org/rfc/rfc3921.txt>`__
"""

__revision__="$Id: client.py 717 2010-04-09 09:36:45Z jajcus $"
__docformat__="restructuredtext en"

import threading
import logging

from pyxmpp.clientstream import ClientStream
from pyxmpp.iq import Iq
from pyxmpp.presence import Presence
from pyxmpp.roster import Roster
from pyxmpp.exceptions import ClientError, FatalClientError
from pyxmpp.interfaces import IPresenceHandlersProvider, IMessageHandlersProvider
from pyxmpp.interfaces import IIqHandlersProvider, IStanzaHandlersProvider

class Client:
    """Base class for an XMPP-IM client.

    This class does not provide any JSF extensions to the XMPP protocol,
    including legacy authentication methods.

    :Ivariables:
        - `jid`: configured JID of the client (current actual JID
          is avialable as `self.stream.jid`).
        - `password`: authentication password.
        - `server`: server to use if non-standard and not discoverable
          by SRV lookups.
        - `port`: port number on the server to use if non-standard and not
          discoverable by SRV lookups.
        - `auth_methods`: methods allowed for stream authentication. SASL
          mechanism names should be preceded with "sasl:" prefix.
        - `keepalive`: keepalive interval for the stream or 0 when keepalive is
          disabled.
        - `stream`: current stream when the client is connected,
          `None` otherwise.
        - `roster`: user's roster or `None` if the roster is not yet retrieved.
        - `session_established`: `True` when an IM session is established.
        - `lock`: lock for synchronizing `Client` attributes access.
        - `state_changed`: condition notified the the object state changes
          (stream becomes connected, session established etc.).
        - `interface_providers`: list of object providing interfaces that
          could be used by the Client object. Initialized to [`self`] by
          the constructor if not set earlier. Put objects providing 
          `IPresenceHandlersProvider`, `IMessageHandlersProvider`,
          `IIqHandlersProvider` or `IStanzaHandlersProvider` into this list.
    :Types:
        - `jid`: `pyxmpp.JID`
        - `password`: `unicode`
        - `server`: `unicode`
        - `port`: `int`
        - `auth_methods`: `list` of `str`
        - `keepalive`: `int`
        - `stream`: `pyxmpp.ClientStream`
        - `roster`: `pyxmpp.Roster`
        - `session_established`: `bool`
        - `lock`: `threading.RLock`
        - `state_changed`: `threading.Condition`
        - `interface_providers`: `list`
    """
    def __init__(self,jid=None,password=None,server=None,port=5222,
            auth_methods=("sasl:DIGEST-MD5",),
            tls_settings=None,keepalive=0):
        """Initialize a Client object.

        :Parameters:
            - `jid`: user full JID for the connection.
            - `password`: user password.
            - `server`: server to use. If not given then address will be derived form the JID.
            - `port`: port number to use. If not given then address will be derived form the JID.
            - `auth_methods`: sallowed authentication methods. SASL authentication mechanisms
              in the list should be prefixed with "sasl:" string.
            - `tls_settings`: settings for StartTLS -- `TLSSettings` instance.
            - `keepalive`: keepalive output interval. 0 to disable.
        :Types:
            - `jid`: `pyxmpp.JID`
            - `password`: `unicode`
            - `server`: `unicode`
            - `port`: `int`
            - `auth_methods`: sequence of `str`
            - `tls_settings`: `pyxmpp.TLSSettings`
            - `keepalive`: `int`
        """
        self.jid=jid
        self.password=password
        self.server=server
        self.port=port
        self.auth_methods=list(auth_methods)
        self.tls_settings=tls_settings
        self.keepalive=keepalive
        self.stream=None
        self.lock=threading.RLock()
        self.state_changed=threading.Condition(self.lock)
        self.session_established=False
        self.roster=None
        self.stream_class=ClientStream
        if not hasattr(self, "interface_providers"):
            self.interface_providers = [self]
        self.__logger=logging.getLogger("pyxmpp.Client")

# public methods

    def connect(self, register = False):
        """Connect to the server and set up the stream.

        Set `self.stream` and notify `self.state_changed` when connection
        succeeds."""
        if not self.jid:
            raise ClientError, "Cannot connect: no or bad JID given"
        self.lock.acquire()
        try:
            stream = self.stream
            self.stream = None
            if stream:
                import common
                common.netcall(stream.close)

            self.__logger.debug("Creating client stream: %r, auth_methods=%r"
                    % (self.stream_class, self.auth_methods))
            stream=self.stream_class(jid = self.jid,
                    password = self.password,
                    server = self.server,
                    port = self.port,
                    auth_methods = self.auth_methods,
                    tls_settings = self.tls_settings,
                    keepalive = self.keepalive,
                    owner = self)
            stream.process_stream_error = self.stream_error
            self.stream_created(stream)
            stream.state_change = self.__stream_state_change
            stream.connect()
            self.stream = stream
            self.state_changed.notify()
            self.state_changed.release()
        except:
            self.stream = None
            self.state_changed.release()
            raise

    def get_stream(self):
        """Get the connected stream object.

        :return: stream object or `None` if the client is not connected.
        :returntype: `pyxmpp.ClientStream`"""
        self.lock.acquire()
        stream=self.stream
        self.lock.release()
        return stream

    def disconnect(self):
        """Disconnect from the server."""
        stream=self.get_stream()
        if stream:
            stream.disconnect()

    def request_session(self):
        """Request an IM session."""
        stream=self.get_stream()
        if not stream.version:
            need_session=False
        elif not stream.features:
            need_session=False
        else:
            ctxt = stream.doc_in.xpathNewContext()
            ctxt.setContextNode(stream.features)
            ctxt.xpathRegisterNs("sess","urn:ietf:params:xml:ns:xmpp-session")
            # jabberd2 hack
            ctxt.xpathRegisterNs("jsess","http://jabberd.jabberstudio.org/ns/session/1.0")
            sess_n=None
            try:
                sess_n=ctxt.xpathEval("sess:session or jsess:session")
            finally:
                ctxt.xpathFreeContext()
            if sess_n:
                need_session=True
            else:
                need_session=False

        if not need_session:
            self.state_changed.acquire()
            self.session_established=1
            self.state_changed.notify()
            self.state_changed.release()
            self._session_started()
        else:
            iq=Iq(stanza_type="set")
            iq.new_query("urn:ietf:params:xml:ns:xmpp-session","session")
            stream.set_response_handlers(iq,
                self.__session_result,self.__session_error,self.__session_timeout)
            stream.send(iq)

    def request_roster(self):
        """Request the user's roster."""
        stream=self.get_stream()
        iq=Iq(stanza_type="get")
        iq.new_query("jabber:iq:roster")
        stream.set_response_handlers(iq,
            self.__roster_result,self.__roster_error,self.__roster_timeout)
        stream.set_iq_set_handler("query","jabber:iq:roster",self.__roster_push)
        stream.send(iq)

    def get_socket(self):
        """Get the socket object of the active connection.

        :return: socket used by the stream.
        :returntype: `socket.socket`"""
        return self.stream.socket

    def loop(self,timeout=1):
        """Simple "main loop" for the client.

        By default just call the `pyxmpp.Stream.loop_iter` method of
        `self.stream`, which handles stream input and `self.idle` for some
        "housekeeping" work until the stream is closed.

        This usually will be replaced by something more sophisticated. E.g.
        handling of other input sources."""
        while 1:
            stream=self.get_stream()
            if not stream:
                break
            act=stream.loop_iter(timeout)
            if not act:
                self.idle()

# private methods

    def __session_timeout(self):
        """Process session request time out.

        :raise FatalClientError:"""
        raise FatalClientError("Timeout while tryin to establish a session")

    def __session_error(self,iq):
        """Process session request failure.

        :Parameters:
            - `iq`: IQ error stanza received as result of the session request.
        :Types:
            - `iq`: `pyxmpp.Iq`

        :raise FatalClientError:"""
        err=iq.get_error()
        msg=err.get_message()
        raise FatalClientError("Failed to establish a session: "+msg)

    def __session_result(self, _unused):
        """Process session request success.

        :Parameters:
            - `_unused`: IQ result stanza received in reply to the session request.
        :Types:
            - `_unused`: `pyxmpp.Iq`"""
        self.state_changed.acquire()
        self.session_established=True
        self.state_changed.notify()
        self.state_changed.release()
        self._session_started()

    def _session_started(self):
        """Called when session is started.
        
        Activates objects from `self.interface_provides` by installing
        their stanza handlers, etc."""
        for ob in self.interface_providers:
            if IPresenceHandlersProvider.providedBy(ob):
                for handler_data in ob.get_presence_handlers():
                    self.stream.set_presence_handler(*handler_data)
            if IMessageHandlersProvider.providedBy(ob):
                for handler_data in ob.get_message_handlers():
                    self.stream.set_message_handler(*handler_data)
            if IIqHandlersProvider.providedBy(ob):
                for handler_data in ob.get_iq_get_handlers():
                    self.stream.set_iq_get_handler(*handler_data)
                for handler_data in ob.get_iq_set_handlers():
                    self.stream.set_iq_set_handler(*handler_data)
        self.session_started()

    def __roster_timeout(self):
        """Process roster request time out.

        :raise ClientError:"""
        raise ClientError("Timeout while tryin to retrieve roster")

    def __roster_error(self,iq):
        """Process roster request failure.

        :Parameters:
            - `iq`: IQ error stanza received as result of the roster request.
        :Types:
            - `iq`: `pyxmpp.Iq`

        :raise ClientError:"""
        err=iq.get_error()
        msg=err.get_message()
        raise ClientError("Roster retrieval failed: "+msg)

    def __roster_result(self,iq):
        """Process roster request success.

        :Parameters:
            - `iq`: IQ result stanza received in reply to the roster request.
        :Types:
            - `iq`: `pyxmpp.Iq`"""
        q=iq.get_query()
        if q:
            self.state_changed.acquire()
            self.roster=Roster(q)
            self.state_changed.notify()
            self.state_changed.release()
            self.roster_updated()
        else:
            raise ClientError("Roster retrieval failed")

    def __roster_push(self,iq):
        """Process a "roster push" (change notification) received.

        :Parameters:
            - `iq`: IQ result stanza received.
        :Types:
            - `iq`: `pyxmpp.Iq`"""
        fr=iq.get_from()
        if fr and fr.bare() != self.jid.bare():
            resp=iq.make_error_response("forbidden")
            self.stream.send(resp)
            self.__logger.warning("Got roster update from wrong source")
            return
        if not self.roster:
            raise ClientError("Roster update, but no roster")
        q=iq.get_query()
        items=self.roster.update(q)
        for item in items:
            self.roster_updated(item)
        resp=iq.make_result_response()
        self.stream.send(resp)

    def __stream_state_change(self,state,arg):
        """Handle stream state changes.

        Call apopriate methods of self.

        :Parameters:
            - `state`: the new state.
            - `arg`: state change argument.
        :Types:
            - `state`: `str`"""
        self.stream_state_changed(state,arg)
        if state=="fully connected":
            self.connected()
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

# Method to override
    def idle(self):
        """Do some "housekeeping" work like cache expiration or timeout
        handling. Should be called periodically from the application main
        loop. May be overriden in derived classes."""
        stream=self.get_stream()
        if stream:
            stream.idle()

    def stream_created(self,stream):
        """Handle stream creation event. May be overriden in derived classes.
        This one does nothing.

        :Parameters:
            - `stream`: the new stream.
        :Types:
            - `stream`: `pyxmpp.ClientStream`"""
        pass

    def stream_closed(self,stream):
        """Handle stream closure event. May be overriden in derived classes.
        This one does nothing.

        :Parameters:
            - `stream`: the new stream.
        :Types:
            - `stream`: `pyxmpp.ClientStream`"""
        pass

    def session_started(self):
        """Handle session started event. May be overriden in derived classes.
        This one requests the user's roster and sends the initial presence."""
        self.request_roster()
        p=Presence()
        self.stream.send(p)

    def stream_error(self,err):
        """Handle stream error received. May be overriden in derived classes.
        This one passes an error messages to logging facilities.

        :Parameters:
            - `err`: the error element received.
        :Types:
            - `err`: `pyxmpp.error.StreamErrorNode`"""
        self.__logger.error("Stream error: condition: %s %r"
                % (err.get_condition().name,err.serialize()))

    def roster_updated(self,item=None):
        """Handle roster update event. May be overriden in derived classes.
        This one does nothing.

        :Parameters:
            - `item`: the roster item changed or `None` if whole roster was
              received.
        :Types:
            - `item`: `pyxmpp.RosterItem`"""
        pass

    def stream_state_changed(self,state,arg):
        """Handle any stream state change. May be overriden in derived classes.
        This one does nothing.

        :Parameters:
            - `state`: the new state.
            - `arg`: state change argument.
        :Types:
            - `state`: `str`"""
        pass

    def connected(self):
        """Handle "connected" event. May be overriden in derived classes.
        This one does nothing."""
        pass

    def authenticated(self):
        """Handle "authenticated" event. May be overriden in derived classes.
        This one does nothing."""
        pass

    def authorized(self):
        """Handle "authorized" event. May be overriden in derived classes.
        This one requests an IM session."""
        self.request_session()

    def disconnected(self):
        """Handle "disconnected" event. May be overriden in derived classes.
        This one does nothing."""
        pass

# vi: sts=4 et sw=4
