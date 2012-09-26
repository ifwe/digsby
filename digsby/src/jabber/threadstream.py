from __future__ import with_statement
import pyxmpp.error
from pyxmpp.exceptions import ClientStreamError#, FatalClientError, ClientError
from util.threads.threadpool2 import threaded
from util.callbacks import callsback
from util import GetSocketType
from util.primitives.funcs import Delegate
from pyxmpp.exceptions import LegacyAuthenticationError, TLSNegotiationFailed
from pyxmpp.streambase import STREAM_NS
import pyxmpp.xmlextra as xmlextra
from util.diagnostic import Diagnostic
import libxml2
import time

import Queue
import logging
import socket
from jabber.threadstreamsocket import ThreadStreamSocket #@UnresolvedImport

from pyxmpp.jabber.clientstream import LegacyClientStream
from pyxmpp.exceptions import StreamError, StreamEncryptionRequired, HostMismatch, ProtocolError, TLSError
from pyxmpp.exceptions import FatalStreamError, StreamParseError, StreamAuthenticationError, SASLAuthenticationFailed
from pyxmpp.jid import JID
from pyxmpp import resolver

from common import netcall
from threading import currentThread
import traceback
import sys

log = logging.getLogger("ThreadStream")

outdebug = logging.getLogger("ThreadStream.out").debug
outdebug_s = getattr(logging.getLogger("ThreadStream.out"), 'debug_s', outdebug)

indebug = logging.getLogger("ThreadStream.in").debug
indebug_s = getattr(logging.getLogger("ThreadStream.in"), 'debug_s', outdebug)

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

def ignore_xml_error(descr):
    # ignore undefined namespace errors
    if descr == 'Parser error #201.':
        return True

class ThreadStream(LegacyClientStream):
    killonce = False
    def __init__(self, *a, **k):
        LegacyClientStream.__init__(self, *a, **k)
        self.__logger = logging.getLogger("ThreadStream")
        self.__shutdown = False

        # Debugging hooks for incoming and outgoing XML nodes.
        self.on_incoming_node = Delegate()
        self.on_outgoing_node = Delegate()


#        self._to_call = Queue.Queue()

#    def call_later(self, call, *a, **k):
#        if not callable(call): raise TypeError
#        self._to_call.put((call, a, k))
#
#    def _idle(self):
#        LegacyClientStream._idle(self)
#        while not self._to_call.empty():
#            try:
#                c, a, k = self._to_call.get_nowait()
#                c(*a, **k)
#            except Queue.Empty:
#                pass

    def stanza(self, _unused, node):
        'All incoming stanzas.'

        self.on_incoming_node(node)
        LegacyClientStream.stanza(self, _unused, node)

    def _write_node(self, xmlnode):
        'Write an outgoing node.'

        self.on_outgoing_node(xmlnode)

        ### Copied from streambase.py
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
        ###

        ###
        # Changed from streambase.py implementation, now we use a subroutine that grabs the lock
        # and checks if the doc is not None first.
        self.freeOutNode(xmlnode)
        ###

    def freeOutNode(self, xmlnode):
        with self.lock:
            if self.doc_out is not None:
                xmlnode.unlinkNode()
                xmlnode.freeNode()

    def write_raw(self, data):
        netcall(lambda: LegacyClientStream.write_raw(self, data))

    def idle(self):
        netcall(lambda: LegacyClientStream.idle(self))

    def send(self, stanza):
        netcall(lambda: LegacyClientStream.send(self, stanza))

    def _write_raw(self,data):
        """Same as `Stream.write_raw` but assume `self.lock` is acquired."""
        if sys.DEV and currentThread().getName() != 'AsyncoreThread':
            try:
                raise AssertionError, 'bad thread for _write_raw: %r' % currentThread().getName()
            except AssertionError:
#                from hub import Hub
#                Hub.on_error()
                traceback.print_exc()
                traceback.print_stack()
                import wx
                def do_submit():
                    d = Diagnostic(description = "Automated: Woah, bad thread")
                    d.prepare_data()
                    d.do_post()
                    from common import profile
                    uname = profile.username
                    del profile
                    wx.MessageBox("Hey %s! Something crazy just happened!\n"
                                  "I submitted a bug report for you. - Chris" % uname)
                wx.CallLater(3000, do_submit)
                raise
        outdebug_s("OUT: %r", data)
#        try:
        self.socket.push(data)
#        except Exception, e:
#            self.handle_error(e)
        outdebug("OUT: done")


    def fileno(self):
        "Return filedescriptor of the stream socket."

        with self.lock:
            return self.socket._fileno

    def connect(self, server = None, port = None):
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

        outdebug('connect')
        with self.lock:
            self._connect1(server,port)

    def _connect1(self,server=None,port=None):
        "Same as `ClientStream.connect` but assume `self.lock` is acquired."

        outdebug('_connect1')

        if not self.my_jid.node or not self.my_jid.resource:
            raise ClientStreamError("Client JID must have username and resource",self.my_jid)
        if not server:
            server=self.server
        if not port:
            port=self.port
        if server:
            self.__logger.debug("server: %r", (server,port))
            service=None
        else:
            service="xmpp-client"
        if port is None:
            port=5222
        if server is None:
            self.__logger.debug("server: %r", (server,port))
            server=self.my_jid.domain
        self.me=self.my_jid

        def connect_failed():
            self.owner.set_offline(self.owner.Reasons.CONN_FAIL)
        self._connect2(server,port,service,self.my_jid.domain, sck_cls = GetSocketType())#, error=connect_failed)

    #@threaded
    def _connect2(self,addr1,port1,service=None,to=None, sck_cls=socket.SocketType):
        """Same as `Stream.connect` but assume `self.lock` is acquired."""

        outdebug('_connect2')
        self.__logger.debug("server: %r", (addr1,port1))

        if to is None:
            to=str(addr1)
        if service is not None:
            self.state_change("resolving srv",(addr1,service))
            try:
                addrs=resolver.resolve_srv(addr1,service)
            except Exception:
                traceback.print_exc()
                addrs = []
            if not addrs:
                addrs=[(addr1, port1)]
            else:
                addrs.append((addr1, port1))
        else:
            addrs=[(addr1, port1)]
        msg=None

        self.__logger.debug("addrs: %r", addrs)

        for addr,port in addrs:
            if type(addr) in (str, unicode):
                self.state_change("resolving",addr)
            s=None
            try:
                resolved = resolver.getaddrinfo(addr,port,0,socket.SOCK_STREAM)
            except Exception:
                self.__logger.debug('an attempt to resolve %r failed', (addr, port))
                resolved = []
            else:
                self.__logger.debug('an attempt to resolve %r succeeded', (addr, port))
            resolved.append((2, 1, 0, '_unused', (addr,port)))

            for res in resolved:
                family, socktype, proto, _unused, sockaddr = res
                self.__logger.debug('res: %r', res)
                try:
                    s=sck_cls(family,socktype,proto)
                    s.settimeout(10)
                    self.state_change("connecting",sockaddr)
                    s.connect(sockaddr)
                    if ThreadStream.killonce:
                        ThreadStream.killonce = False
                        raise socket.error
                    if self.owner.do_ssl:
                        ctx=SSL.Context()
                        ctx.set_verify(SSL.verify_none, 10)
                        s.setblocking(True)
                        ssl = SSL.Connection(ctx, s)
                        ssl.setup_ssl()
                        ssl.set_connect_state()
                        ssl.connect_ssl()
                        s.setblocking(False)
                        s = ssl
                        s.setblocking(False)
                    self.state_change("connected",sockaddr)
                except (socket.error, SSLError), msg:
                    self.__logger.debug("Connect to %r failed: %r", sockaddr,msg)
                    traceback.print_exc()
                    if s:
                        s.close()
                        s=None
                    continue
                break
            if s:
                self.__logger.debug('connected to: %r', (addr, port))
                break
        if not s:
            if msg:
                self.__logger.debug('failed to connect to %r: %r', (addr,port), msg)
                raise socket.error, msg
            else:
                self.__logger.debug('failed to connect to %r: unknown reason', (addr,port))
                raise FatalStreamError,"Cannot connect"

        self.addr=addr
        self.port=port
        with self.owner.lock:
            if self.owner.connect_killed == True:
                raise FatalStreamError, "Connect Killed"
        self._connect_socket(s,to)
        self.last_keepalive=time.time()

    def closed(self):
        logging.getLogger("ThreadStream").debug("closed")
        self._do_closed()

    def closed_dead(self):
        logging.getLogger("ThreadStream").debug("closed_dead")
        self._do_closed()

    def _do_closed(self):
        want_try_again = self.owner.fatal_error()
        self.owner.stream = None
        self.close(False)
        self.owner.disconnected(want_try_again)
#        self.state_change("disconnected", self.peer)

    def __connect_error(self):
        pass

    def _connect_socket(self,sock,to=None):
        """Initialize stream on outgoing connection.

        :Parameters:
          - `sock`: connected socket for the stream
          - `to`: name of the remote host
        """
        logging.getLogger("ThreadStream").debug("connecting")
        def asyncore_stuff():
            logging.getLogger("ThreadStream").debug("creating ThreadStreamSocket")
            new_sock = ThreadStreamSocket(sock, self._feed_reader, 0, self.closed, self.closed_dead, ssl=self.owner.do_ssl)
            LegacyClientStream._connect_socket(self, new_sock, to)
        netcall(asyncore_stuff)

    def _loop_iter(self,timeout):
        assert False

    def _process(self):
        assert False

    def _read(self):
        assert False

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
            self.tls_requested=0
            self._make_tls_connection(success=self.finish_process,
                                      error=self.fail_process)
        return True

    def fail_process(self):
        self.owner.fatal_error()
        self.close()

    def finish_process(self):
        self.socket=self.tls
        self.__logger.debug("Restarting XMPP stream")
        self._restart_stream()
        return True

    def _restart_stream(self):
        self.stream_id=None
        LegacyClientStream._restart_stream(self)

    @callsback
    def _make_tls_connection(self, callback = None):
        """Initiate TLS connection.

        [initiating entity only]"""
        ctx = None
        try:
            if not tls_available or not self.tls_settings:
                raise TLSError,"TLS is not available"

            tlssettings = self.tls_settings

            self.state_change("tls connecting", self.peer)
            self.__logger.debug("Creating TLS context")

            ctx = getattr(tlssettings, 'ctx', None)
            if ctx is None:
                ctx = SSL.Context('tlsv1')

            verify_callback = tlssettings.verify_callback

            if not verify_callback:
                verify_callback = getattr(self, 'tls_default_verify_callback', None)

            if tlssettings.verify_peer:
                self.__logger.debug("verify_peer, verify_callback: %r", verify_callback)
                ctx.set_verify(SSL.verify_peer, 10, verify_callback)
            else:
                ctx.set_verify(SSL.verify_none, 10)

            if tlssettings.cert_file:
                ctx.use_certificate_chain_file(tlssettings.cert_file)
                if tlssettings.key_file:
                    ctx.use_PrivateKey_file(tlssettings.key_file)
                else:
                    ctx.use_PrivateKey_file(tlssettings.cert_file)
                ctx.check_private_key()

            if tlssettings.cacert_file:
                try:
                    ctx.load_verify_location(tlssettings.cacert_file)
                except AttributeError:
                    ctx.load_verify_locations(tlssettings.cacert_file)
        except Exception, e:
            self.__logger.error('Error with TLS stuff: %r', e)
            import traceback; traceback.print_exc()
            callback.error()
            return
        #so, if we do a callback/threaded here, how do we ensure that the socket
        #is eventually shut down?  the error callback? a try except?
        #I'm worried that if we go off to another thread, we won't be able
        #to get back on asyncore in non-blocking mode.
        #not that the way it is is particularly useful.
        #
        self.callback = callback
        self.socket.make_tls(ctx, success=self.tls_done, error=self.tls_fail)

    tls_fail = fail_process

    def tls_done(self):
        self.tls = self.socket

        self.state_change("tls connected", self.peer)

        # clear any exception state left by some M2Crypto broken code
        try:
            raise Exception
        except:
            pass
        self.callback.success()

    def _got_features(self):
        try:
            return LegacyClientStream._got_features(self)
        except FatalStreamError, e:
            if e.__class__ == FatalStreamError:
                self.owner.auth_failed(e.message)
            else:
                raise

    def registration_error(self, stanza):
        with self.lock:
            ae = None
            err = stanza.get_error()
            ae  = err.xpath_eval("e:*",{"e":"jabber:iq:auth:error"})
            if ae:
                ae = ae[0].name
            else:
                ae = err.get_condition().name

        if self.registration_error_callback is not None:
            self.registration_error_callback((ae,) + pyxmpp.error.stanza_errors[ae])
        self.registration_error_callback = None
        self.registration_success_callback = None

    def registration_success(self, stanza):
        if self.registration_success_callback is not None:
            self.registration_success_callback()

        self.registration_success_callback = None
        self.registration_error_callback   = None
        _unused = stanza

        with self.lock:
            self.state_change("registered", self.registration_form)
            if ('FORM_TYPE' in self.registration_form
                    and self.registration_form['FORM_TYPE'].value == 'jabber:iq:register'):
                if 'username' in self.registration_form:
                    self.my_jid = JID(self.registration_form['username'].value,
                            self.my_jid.domain, self.my_jid.resource)
                if 'password' in self.registration_form:
                    self.password = self.registration_form['password']
            self.registration_callback = None

    def disconnect(self):
        """Disconnect from the server."""
        LegacyClientStream.disconnect(self)
        self.state_change("disconnected",self.peer)

    def stream_end(self, _unused):
        LegacyClientStream.stream_end(self, _unused)
        self.shutdown()

    def _send_stream_end(self):
        LegacyClientStream._send_stream_end(self)
        self.shutdown()

    def shutdown(self):
        if not self.__shutdown:
            outdebug("non-Force shutdown")
            self.__shutdown = True
            if self.socket:
                outdebug("non-Force close_when_done")
                self.socket.close_when_done()
        else:
            outdebug("Force shutdown")
            self.close(False)

    def close(self, do_disconnect=True):
        "Forcibly close the connection and clear the stream state."

        with self.lock:
            return self._close(do_disconnect)

    def _close(self, do_disconnect=True):
        "Same as `Stream.close` but assume `self.lock` is acquired."

        if do_disconnect:
            self._disconnect()
        if self.doc_in:
            self.doc_in = None
        if self.features:
            self.features = None
        self._reader = None
        self.stream_id = None
        if self.socket:
            self.socket.close()
        self._reset()

    def _process_node(self, stanza):
        try:
            LegacyClientStream._process_node(self, stanza)
        except SASLAuthenticationFailed, e:
            self.owner.auth_failed(reason = getattr(e, 'reason', e.message))
            self.__logger.critical("SASLAuthenticationFailed: %r, %r", e.message, getattr(e, 'reason', 'unknown-reason'))
        except LegacyAuthenticationError, e:
            self.owner.auth_failed(reason = e.message)
            self.__logger.critical("LegacyAuthenticationError")
        except FatalStreamError, e:
            import hub
            hub.get_instance().on_error(e)
            self.__logger.critical("Stream blew up")
            self.owner.fatal_error()
            self.close()
#        except FatalClientError, e:
#            raise e
#        except ClientError, e:
#            traceback.print_exc()
#            raise e
#        except Exception, e:
#            import hub
#            hub.get_instance().on_error(e)
#            raise

    def _process_sasl_failure(self, xmlnode):
        try:
            LegacyClientStream._process_sasl_failure(self, xmlnode)
        except SASLAuthenticationFailed, e:
            e.reason = getattr(xmlnode.get_children(), 'name', 'unknown-reason')
            raise e


    def error(self, descr):
        if ignore_xml_error(descr):
            return

        self.__logger.critical("XML parse error: " + descr)
        self.owner.fatal_error()
        self.close()

    def fix_in_stanza(self,stanza):
        LegacyClientStream.fix_in_stanza(self,stanza)
        if self.initiator:
            to=stanza.get_to()
            if to is not None:
                p = self.peer
                pb = p.bare() if p else None
                tob = to.bare() if to else None
                if tob == pb or to == p or to == pb or tob == p:
                    stanza.set_to(False)

    def _feed_reader(self, data):
        with self.lock:
            if self._reader is not None:
                self._super_feed_reader(data)
            else:
                self.close(False)

    def _super_feed_reader(self,data): #feed reader copied from superclass
        """Feed the stream reader with data received.

        If `data` is None or empty, then stream end (peer disconnected) is
        assumed and the stream is closed.

        :Parameters:
            - `data`: data received from the stream socket.
        :Types:
            - `data`: `unicode`
        """
        indebug_s("IN: %r",data)

        if data:
            try:
                r=self._reader.feed(data)
                while r:
                    r=self._reader.feed("")
                if r is None:
                    indebug('r was None, setting eof + disconnect')
                    self.eof=1
                    self.disconnect()
            except StreamParseError:
                self._send_stream_error("xml-not-well-formed")
                raise
        else:
            indebug('no data, setting eof + disconnect')
            self.eof=1
            self.disconnect()
        if self.eof:
            indebug('eof calling stream_end')
            self.stream_end(None)

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

        to_from_mismatch=0
        old_peer = None

        assert self.initiator
        if self.initiator:
            self.stream_id=r.prop("id")
            peer=r.prop("from")
            if peer:
                peer=JID(peer)
            if self.peer:
                if peer and peer != self.peer:# and not unicode(self.peer).endswith(unicode(peer)) \
                                                #and not unicode(peer).endswith(unicode(self.peer)):
                    self.__logger.debug("peer hostname mismatch:"
                        " %r != %r" % (peer,self.peer))
                    to_from_mismatch=1
                    #TODO: something here (?), to go along with 'on_host_mismatch' from end of this function
                    old_peer, self.peer = self.peer, peer
                elif peer:
                    self.peer = peer
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

        if to_from_mismatch:
            handler = getattr(self, 'on_host_mismatch', None)
            if handler is not None:
                handler(old_peer, peer)

        if not self.version:
            self.state_change("fully connected",self.peer)
            self._post_connect()

    def on_host_mismatch(self, mine, theirs):
        self._had_host_mismatch = True
        self._host_mismatch_info = (mine, theirs)

    def _make_reader(self):
        self._reader=IgnoreNSErrorReader(self)

class IgnoreNSErrorReader(xmlextra.StreamReader):
    def feed(self,s):
        try:
            return xmlextra.StreamReader.feed(self, s)
            #super doesn't work on old style classes
#            return super(IgnoreNSErrorReader, self).feed(s)
        except Exception as e:
            if ignore_xml_error(e.message):
                return 0
            raise
