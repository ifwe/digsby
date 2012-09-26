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
# pylint: disable-msg=W0201

"""Core XMPP stream functionality.

Normative reference:
  - `RFC 3920 <http://www.ietf.org/rfc/rfc3920.txt>`__
"""

__revision__="$Id: streambase.py 700 2010-04-03 15:34:59Z jajcus $"
__docformat__="restructuredtext en"

import libxml2
import socket
import os
import time
import random
import threading
import errno
import logging


from pyxmpp import xmlextra
from pyxmpp.expdict import ExpiringDictionary
from pyxmpp.utils import to_utf8
from pyxmpp.stanza import Stanza
from pyxmpp.error import StreamErrorNode
from pyxmpp.iq import Iq
from pyxmpp.presence import Presence
from pyxmpp.message import Message
from pyxmpp.jid import JID
from pyxmpp import resolver
from pyxmpp.stanzaprocessor import StanzaProcessor
from pyxmpp.exceptions import StreamError, StreamEncryptionRequired, HostMismatch, ProtocolError
from pyxmpp.exceptions import FatalStreamError, StreamParseError, StreamAuthenticationError

STREAM_NS="http://etherx.jabber.org/streams"
BIND_NS="urn:ietf:params:xml:ns:xmpp-bind"

def stanza_factory(xmlnode, stream = None):
    """Creates Iq, Message or Presence object for XML stanza `xmlnode`"""
    if xmlnode.name=="iq":
        return Iq(xmlnode, stream = stream)
    if xmlnode.name=="message":
        return Message(xmlnode, stream = stream)
    if xmlnode.name=="presence":
        return Presence(xmlnode, stream = stream)
    else:
        return Stanza(xmlnode, stream = stream)

class StreamBase(StanzaProcessor,xmlextra.StreamHandler):
    """Base class for a generic XMPP stream.

    Responsible for establishing connection, parsing the stream, dispatching
    received stanzas to apopriate handlers and sending application's stanzas.
    This doesn't provide any authentication or encryption (both required by
    the XMPP specification) and is not usable on its own.

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
        - `initiator`: `True` if local stream endpoint is the initiating entity.
        - `owner`: `Client`, `Component` or similar object "owning" this stream.
        - `_reader`: the stream reader object (push parser) for the stream.
    """
    def __init__(self, default_ns, extra_ns = (), keepalive = 0, owner = None):
        """Initialize Stream object

        :Parameters:
          - `default_ns`: stream's default namespace ("jabber:client" for
            client, "jabber:server" for server, etc.)
          - `extra_ns`: sequence of extra namespace URIs to be defined for
            the stream.
          - `keepalive`: keepalive output interval. 0 to disable.
          - `owner`: `Client`, `Component` or similar object "owning" this stream.
        """
        StanzaProcessor.__init__(self)
        xmlextra.StreamHandler.__init__(self)
        self.default_ns_uri=default_ns
        if extra_ns:
            self.extra_ns_uris=extra_ns
        else:
            self.extra_ns_uris=[]
        self.keepalive=keepalive
        self._reader_lock=threading.Lock()
        self.process_all_stanzas=False
        self.port=None
        self._reset()
        self.owner = owner
        self.__logger=logging.getLogger("pyxmpp.Stream")

    def _reset(self):
        """Reset `Stream` object state making it ready to handle new
        connections."""
        self.doc_in=None
        self.doc_out=None
        self.socket=None
        self._reader=None
        self.addr=None
        self.default_ns=None
        self.extra_ns={}
        self.stream_ns=None
        self._reader=None
        self.ioreader=None
        self.me=None
        self.peer=None
        self.skip=False
        self.stream_id=None
        self._iq_response_handlers=ExpiringDictionary()
        self._iq_get_handlers={}
        self._iq_set_handlers={}
        self._message_handlers=[]
        self._presence_handlers=[]
        self.eof=False
        self.initiator=None
        self.features=None
        self.authenticated=False
        self.peer_authenticated=False
        self.auth_method_used=None
        self.version=None
        self.last_keepalive=False

    def _connect_socket(self,sock,to=None):
        """Initialize stream on outgoing connection.

        :Parameters:
          - `sock`: connected socket for the stream
          - `to`: name of the remote host
        """
        self.eof=0
        self.socket=sock
        if to:
            self.peer=JID(to)
        else:
            self.peer=None
        self.initiator=1
        self._send_stream_start()
        self._make_reader()

    def connect(self,addr,port,service=None,to=None):
        """Establish XMPP connection with given address.

        [initiating entity only]

        :Parameters:
            - `addr`: peer name or IP address
            - `port`: port number to connect to
            - `service`: service name (to be resolved using SRV DNS records)
            - `to`: peer name if different than `addr`
        """
        self.lock.acquire()
        try:
            return self._connect(addr,port,service,to)
        finally:
            self.lock.release()

    def _connect(self,addr,port,service=None,to=None):
        """Same as `Stream.connect` but assume `self.lock` is acquired."""
        if to is None:
            to=str(addr)
        if service is not None:
            self.state_change("resolving srv",(addr,service))
            addrs=resolver.resolve_srv(addr,service)
            if not addrs:
                addrs=[(addr,port)]
        else:
            addrs=[(addr,port)]
        msg=None
        for addr,port in addrs:
            if type(addr) in (str, unicode):
                self.state_change("resolving",addr)
            s=None
            for res in resolver.getaddrinfo(addr,port,0,socket.SOCK_STREAM):
                family, socktype, proto, _unused, sockaddr = res
                try:
                    s=socket.socket(family,socktype,proto)
                    self.state_change("connecting",sockaddr)
                    s.connect(sockaddr)
                    self.state_change("connected",sockaddr)
                except socket.error, msg:
                    self.__logger.debug("Connect to %r failed" % (sockaddr,))
                    if s:
                        s.close()
                        s=None
                    continue
                break
            if s:
                break
        if not s:
            if msg:
                raise socket.error, msg
            else:
                raise FatalStreamError,"Cannot connect"

        self.addr=addr
        self.port=port
        self._connect_socket(s,to)
        self.last_keepalive=time.time()

    def accept(self,sock,myname):
        """Accept incoming connection.

        [receiving entity only]

        :Parameters:
            - `sock`: a listening socket.
            - `myname`: local stream endpoint name."""
        self.lock.acquire()
        try:
            return self._accept(sock,myname)
        finally:
            self.lock.release()

    def _accept(self,sock,myname):
        """Same as `Stream.accept` but assume `self.lock` is acquired."""
        self.eof=0
        self.socket,addr=sock.accept()
        self.__logger.debug("Connection from: %r" % (addr,))
        self.addr,self.port=addr
        if myname:
            self.me=JID(myname)
        else:
            self.me=None
        self.initiator=0
        self._make_reader()
        self.last_keepalive=time.time()

    def disconnect(self):
        """Gracefully close the connection."""
        self.lock.acquire()
        try:
            return self._disconnect()
        finally:
            self.lock.release()

    def _disconnect(self):
        """Same as `Stream.disconnect` but assume `self.lock` is acquired."""
        if self.doc_out:
            self._send_stream_end()

    def _post_connect(self):
        """Called when connection is established.

        This method is supposed to be overriden in derived classes."""
        pass

    def _post_auth(self):
        """Called when connection is authenticated.

        This method is supposed to be overriden in derived classes."""
        pass

    def state_change(self,state,arg):
        """Called when connection state is changed.

        This method is supposed to be overriden in derived classes
        or replaced by an application.

        It may be used to display the connection progress."""
        self.__logger.debug("State: %s: %r" % (state,arg))

    def close(self):
        """Forcibly close the connection and clear the stream state."""
        self.lock.acquire()
        try:
            return self._close()
        finally:
            self.lock.release()

    def _close(self):
        """Same as `Stream.close` but assume `self.lock` is acquired."""
        self._disconnect()
        if self.doc_in:
            self.doc_in=None
        if self.features:
            self.features=None
        self._reader=None
        self.stream_id=None
        if self.socket:
            self.socket.close()
        self._reset()

    def _make_reader(self):
        """Create ne `xmlextra.StreamReader` instace as `self._reader`."""
        self._reader=xmlextra.StreamReader(self)

    def stream_start(self,doc):
        """Process <stream:stream> (stream start) tag received from peer.

        :Parameters:
            - `doc`: document created by the parser"""
        self.doc_in=doc
        self.__logger.debug("input document: %r" % (self.doc_in.serialize(),))

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

        to_from_mismatch=0
        if self.initiator:
            self.stream_id=r.prop("id")
            peer=r.prop("from")
            if peer:
                peer=JID(peer)
            if self.peer:
                if peer and peer!=self.peer:
                    self.__logger.debug("peer hostname mismatch:"
                        " %r != %r" % (peer,self.peer))
                    to_from_mismatch=1
            else:
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

        if to_from_mismatch:
            raise HostMismatch

    def stream_end(self, _unused):
        """Process </stream:stream> (stream end) tag received from peer.

        :Parameters:
            - `_unused`: document created by the parser"""
        self.__logger.debug("Stream ended")
        self.eof=1
        if self.doc_out:
            self._send_stream_end()
        if self.doc_in:
            self.doc_in=None
            self._reader=None
            if self.features:
                self.features=None
        self.state_change("disconnected",self.peer)

    def stanza_start(self,doc,node):
        """Process stanza (first level child element of the stream) start tag
        -- do nothing.

        :Parameters:
            - `doc`: parsed document
            - `node`: stanza's full XML
        """
        pass

    def stanza(self, _unused, node):
        """Process stanza (first level child element of the stream).

        :Parameters:
            - `_unused`: parsed document
            - `node`: stanza's full XML
        """
        self._process_node(node)

    def error(self,descr):
        """Handle stream XML parse error.

        :Parameters:
            - `descr`: error description
        """
        raise StreamParseError,descr

    def _send_stream_end(self):
        """Send stream end tag."""
        self.doc_out.getRootElement().addContent(" ")
        s=self.doc_out.getRootElement().serialize(encoding="UTF-8")
        end=s.rindex("<")
        try:
            self._write_raw(s[end:])
        except (IOError,SystemError,socket.error),e:
            self.__logger.debug("Sending stream closing tag failed:"+str(e))
        self.doc_out.freeDoc()
        self.doc_out=None
        if self.features:
            self.features=None

    def _send_stream_start(self,sid=None):
        """Send stream start tag."""
        if self.doc_out:
            raise StreamError,"Stream start already sent"
        self.doc_out=libxml2.newDoc("1.0")
        root=self.doc_out.newChild(None, "stream", None)
        self.stream_ns=root.newNs(STREAM_NS,"stream")
        root.setNs(self.stream_ns)
        self.default_ns=root.newNs(self.default_ns_uri,None)
        for prefix,uri in self.extra_ns:
            self.extra_ns[uri]=root.newNs(uri,prefix)
        if self.peer and self.initiator:
            root.setProp("to",self.peer.as_utf8())
        if self.me and not self.initiator:
            root.setProp("from",self.me.as_utf8())
        root.setProp("version","1.0")
        if sid:
            root.setProp("id",sid)
            self.stream_id=sid
        sr=self.doc_out.serialize(encoding="UTF-8")
        self._write_raw(sr[:sr.find("/>")]+">")

    def _send_stream_error(self,condition):
        """Send stream error element.

        :Parameters:
            - `condition`: stream error condition name, as defined in the
              XMPP specification."""
        if not self.doc_out:
            self._send_stream_start()
        e=StreamErrorNode(condition)
        e.xmlnode.setNs(self.stream_ns)
        self._write_raw(e.serialize())
        e.free()
        self._send_stream_end()

    def _restart_stream(self):
        """Restart the stream as needed after SASL and StartTLS negotiation."""
        self._reader=None
        #self.doc_out.freeDoc()
        self.doc_out=None
        #self.doc_in.freeDoc() # memleak, but the node which caused the restart
                    # will be freed after this function returns
        self.doc_in=None
        self.features=None
        if self.initiator:
            self._send_stream_start(self.stream_id)
        self._make_reader()

    def _make_stream_features(self):
        """Create the <features/> element for the stream.

        [receving entity only]

        :returns: new <features/> element node."""
        root=self.doc_out.getRootElement()
        features=root.newChild(root.ns(),"features",None)
        return features

    def _send_stream_features(self):
        """Send stream <features/>.

        [receiving entity only]"""
        self.features=self._make_stream_features()
        self._write_raw(self.features.serialize(encoding="UTF-8"))

    def write_raw(self,data):
        """Write raw data to the stream socket.

        :Parameters:
            - `data`: data to send"""
        self.lock.acquire()
        try:
            return self._write_raw(data)
        finally:
            self.lock.release()

    def _write_raw(self,data):
        """Same as `Stream.write_raw` but assume `self.lock` is acquired."""
        logging.getLogger("pyxmpp.Stream.out").debug("OUT: %r",data)
        try:
            self.socket.send(data)
        except (IOError,OSError,socket.error),e:
            raise FatalStreamError("IO Error: "+str(e))

    def _write_node(self,xmlnode):
        """Write XML `xmlnode` to the stream.

        :Parameters:
            - `xmlnode`: XML node to send."""
        if self.eof or not self.socket or not self.doc_out:
            self.__logger.debug("Dropping stanza: %r" % (xmlnode,))
            return
        xmlnode=xmlnode.docCopyNode(self.doc_out,1)
        self.doc_out.addChild(xmlnode)
        try:
            ns = xmlnode.ns()
        except libxml2.treeError:
            ns = None
        if ns and ns.content == xmlextra.COMMON_NS:
            xmlextra.replace_ns(xmlnode, ns, self.default_ns)
        s = xmlextra.safe_serialize(xmlnode)
        self._write_raw(s)
        xmlnode.unlinkNode()
        xmlnode.freeNode()

    def send(self,stanza):
        """Write stanza to the stream.

        :Parameters:
            - `stanza`: XMPP stanza to send."""
        self.lock.acquire()
        try:
            return self._send(stanza)
        finally:
            self.lock.release()

    def _send(self,stanza):
        """Same as `Stream.send` but assume `self.lock` is acquired."""
        if not self.version:
            try:
                err = stanza.get_error()
            except ProtocolError:
                err = None
            if err:
                err.downgrade()
        self.fix_out_stanza(stanza)
        self._write_node(stanza.xmlnode)

    def idle(self):
        """Do some housekeeping (cache expiration, timeout handling).

        This method should be called periodically from the application's
        main loop."""
        self.lock.acquire()
        try:
            return self._idle()
        finally:
            self.lock.release()

    def _idle(self):
        """Same as `Stream.idle` but assume `self.lock` is acquired."""
        self._iq_response_handlers.expire()
        if not self.socket or self.eof:
            return
        now=time.time()
        if self.keepalive and now-self.last_keepalive>=self.keepalive:
            self._write_raw(" ")
            self.last_keepalive=now

    def fileno(self):
        """Return filedescriptor of the stream socket."""
        self.lock.acquire()
        try:
            return self.socket.fileno()
        finally:
            self.lock.release()

    def loop(self,timeout):
        """Simple "main loop" for the stream."""
        self.lock.acquire()
        try:
            while not self.eof and self.socket is not None:
                act=self._loop_iter(timeout)
                if not act:
                    self._idle()
        finally:
            self.lock.release()

    def loop_iter(self,timeout):
        """Single iteration of a simple "main loop" for the stream."""
        self.lock.acquire()
        try:
            return self._loop_iter(timeout)
        finally:
            self.lock.release()

    def _loop_iter(self,timeout):
        """Same as `Stream.loop_iter` but assume `self.lock` is acquired."""
        import select
        self.lock.release()
        try:
            if not self.socket:
                time.sleep(timeout)
                return False
            try:
                ifd, _unused, efd = select.select( [self.socket], [], [self.socket], timeout )
            except select.error,e:
                if e.args[0]!=errno.EINTR:
                    raise
                ifd, _unused, efd=[], [], []
        finally:
            self.lock.acquire()
        if self.socket in ifd or self.socket in efd:
            self._process()
            return True
        else:
            return False

    def process(self):
        """Process stream's pending events.

        Should be called whenever there is input available
        on `self.fileno()` socket descriptor. Is called by
        `self.loop_iter`."""
        self.lock.acquire()
        try:
            self._process()
        finally:
            self.lock.release()

    def _process(self):
        """Same as `Stream.process` but assume `self.lock` is acquired."""
        try:
            try:
                self._read()
            except (xmlextra.error,),e:
                self.__logger.exception("Exception during read()")
                raise StreamParseError(unicode(e))
            except:
                raise
        except (IOError,OSError,socket.error),e:
            self.close()
            raise FatalStreamError("IO Error: "+str(e))
        except (FatalStreamError,KeyboardInterrupt,SystemExit),e:
            self.close()
            raise

    def _read(self):
        """Read data pending on the stream socket and pass it to the parser."""
        self.__logger.debug("StreamBase._read(), socket: %r",self.socket)
        if self.eof:
            return
        try:
            r=self.socket.recv(1024)
        except socket.error,e:
            if e.args[0]!=errno.EINTR:
                raise
            return
        self._feed_reader(r)

    def _feed_reader(self,data):
        """Feed the stream reader with data received.

        If `data` is None or empty, then stream end (peer disconnected) is
        assumed and the stream is closed.

        :Parameters:
            - `data`: data received from the stream socket.
        :Types:
            - `data`: `unicode`
        """
        logging.getLogger("pyxmpp.Stream.in").debug("IN: %r",data)
        if data:
            try:
                r=self._reader.feed(data)
                while r:
                    r=self._reader.feed("")
                if r is None:
                    self.eof=1
                    self.disconnect()
            except StreamParseError:
                self._send_stream_error("xml-not-well-formed")
                raise
        else:
            self.eof=1
            self.disconnect()
        if self.eof:
            self.stream_end(None)

    def _process_node(self,xmlnode):
        """Process first level element of the stream.

        The element may be stream error or features, StartTLS
        request/response, SASL request/response or a stanza.

        :Parameters:
            - `xmlnode`: XML node describing the element
        """
        ns_uri=xmlnode.ns().getContent()
        if ns_uri=="http://etherx.jabber.org/streams":
            self._process_stream_node(xmlnode)
            return

        if ns_uri==self.default_ns_uri:
            stanza=stanza_factory(xmlnode, self)
            self.lock.release()
            try:
                self.process_stanza(stanza)
            finally:
                self.lock.acquire()
                stanza.free()
        else:
            self.__logger.debug("Unhandled node: %r" % (xmlnode.serialize(),))

    def _process_stream_node(self,xmlnode):
        """Process first level stream-namespaced element of the stream.

        The element may be stream error or stream features.

        :Parameters:
            - `xmlnode`: XML node describing the element
        """
        if xmlnode.name=="error":
            e=StreamErrorNode(xmlnode)
            self.lock.release()
            try:
                self.process_stream_error(e)
            finally:
                self.lock.acquire()
                e.free()
            return
        elif xmlnode.name=="features":
            self.__logger.debug("Got stream features")
            self.__logger.debug("Node: %r" % (xmlnode,))
            self.features=xmlnode.copyNode(1)
            self.doc_in.addChild(self.features)
            self._got_features()
            return

        self.__logger.debug("Unhandled stream node: %r" % (xmlnode.serialize(),))

    def process_stream_error(self,err):
        """Process stream error element received.

        :Types:
            - `err`: `StreamErrorNode`

        :Parameters:
            - `err`: error received
        """

        self.__logger.debug("Unhandled stream error: condition: %s %r"
                % (err.get_condition().name,err.serialize()))

    def check_to(self,to):
        """Check "to" attribute of received stream header.

        :return: `to` if it is equal to `self.me`, None otherwise.

        Should be overriden in derived classes which require other logic
        for handling that attribute."""
        if to!=self.me:
            return None
        return to

    def generate_id(self):
        """Generate a random and unique stream ID.

        :return: the id string generated."""
        return "%i-%i-%s" % (os.getpid(),time.time(),str(random.random())[2:])

    def _got_features(self):
        """Process incoming <stream:features/> element.

        [initiating entity only]

        The received features node is available in `self.features`."""
        ctxt = self.doc_in.xpathNewContext()
        ctxt.setContextNode(self.features)
        ctxt.xpathRegisterNs("stream",STREAM_NS)
        ctxt.xpathRegisterNs("bind",BIND_NS)
        bind_n=None
        try:
            bind_n=ctxt.xpathEval("bind:bind")
        finally:
            ctxt.xpathFreeContext()

        if self.authenticated:
            if bind_n:
                self.bind(self.me.resource)
            else:
                self.state_change("authorized",self.me)

    def bind(self,resource):
        """Bind to a resource.

        [initiating entity only]

        :Parameters:
            - `resource`: the resource name to bind to.

        XMPP stream is authenticated for bare JID only. To use
        the full JID it must be bound to a resource.
        """
        iq=Iq(stanza_type="set")
        q=iq.new_query(BIND_NS, u"bind")
        if resource:
            q.newTextChild(None,"resource",to_utf8(resource))
        self.state_change("binding",resource)
        self.set_response_handlers(iq,self._bind_success,self._bind_error)
        self.send(iq)
        iq.free()

    def _bind_success(self,stanza):
        """Handle resource binding success.

        [initiating entity only]

        :Parameters:
            - `stanza`: <iq type="result"/> stanza received.

        Set `self.me` to the full JID negotiated."""
        jid_n=stanza.xpath_eval("bind:bind/bind:jid",{"bind":BIND_NS})
        if jid_n:
            self.me=JID(jid_n[0].getContent().decode("utf-8"))
        self.state_change("authorized",self.me)

    def _bind_error(self,stanza):
        """Handle resource binding success.

        [initiating entity only]

        :raise FatalStreamError:"""
        raise FatalStreamError,"Resource binding failed"

    def connected(self):
        """Check if stream is connected.

        :return: True if stream connection is active."""
        if self.doc_in and self.doc_out and not self.eof:
            return True
        else:
            return False

# vi: sts=4 et sw=4
