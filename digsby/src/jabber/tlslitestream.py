from __future__ import with_statement

from pyxmpp import resolver
from pyxmpp.exceptions import TLSError as XMPPTLSError
from pyxmpp.jabber.clientstream import LegacyClientStream

import util
import util.primitives.funcs as funcs
import common
from common import netcall, profile
from threading import currentThread

import traceback
import sys
import time
import Queue
import logging
import socket
import threadstream

try:
    from tlslite.api import TLSError, TLSConnection, TLSAsyncDispatcherMixIn, TLSLocalAlert
    tls_available = 1
except ImportError:
    tls_available = 0

log = logging.getLogger("tlslitestream")

outdebug = logging.getLogger("tlslitestream.out").debug
outdebug_s = getattr(logging.getLogger("tlslitestream.out"), 'debug_s', outdebug)

indebug = logging.getLogger("tlslitestream.in").debug
indebug_s = getattr(logging.getLogger("tlslitestream.in"), 'debug_s', outdebug)

class AsyncStreamSocket(common.socket):
    def __init__(self, sock, collect, on_close, on_error, on_connect, **k):
        self.socket = None
        self.term = 0
        self.tls = None
        self._collector = collect
        self._logger = logging.getLogger(type(self).__name__)

        self.on_close = funcs.Delegate()
        self.on_close += on_close

        self.on_error = funcs.Delegate()
        self.on_error += on_error

        self.on_connect = funcs.Delegate()
        self.on_connect += on_connect

        self.lastbuffer = ''
        self._closed = False

        common.socket.__init__(self, sock)
        self.set_terminator(self.term)

        self.killed = False

    def collect_incoming_data(self, data):
        self._collector(data)

    def found_terminator(self):
        self.set_terminator(self.term)

    def handle_connect(self):
        self._logger.info('handle_connect')
        common.socket.handle_connect(self)
        self.on_connect[:], on_connect = funcs.Delegate([]), funcs.Delegate(self.on_connect[:])

        on_connect()

    def handle_error(self, e, force_close=False):
        self.killed = True
        if (not force_close) and self._closed:
            return

        self._closed = True
        self._logger.info('handle_error: %r', e)
        self.on_error[:], on_error = funcs.Delegate([]), funcs.Delegate(self.on_error[:])
        on_error()
        self.clear_delegates()

        if force_close:
            # Do it early in this case.
            self.close()

        common.socket.handle_error(self, e)

        if not force_close:
            self.close()

    def handle_expt(self):
        self.handle_error(Exception("OOB Data"), force_close = True)

    def handle_close(self):
        if self._closed:
            return

        self._closed = True
        self._logger.info('handle_close')
        self.close()

        common.socket.handle_close(self)
        on_close, self.on_close[:] = funcs.Delegate(self.on_close[:]), funcs.Delegate()

        self.clear_delegates()

        if not self.killed:
            # We don't want to run close callbacks *and* error callbacks - some of them perform similar tasks
            # or are mutually exclusive
            on_close()

    def clear_delegates(self):
        del self.on_close[:]
        del self.on_error[:]
        del self.on_connect[:]

        def should_not_be_called(*a, **k):
            raise AssertionError("This function should not have been called!")

        self.on_close   += should_not_be_called
        self.on_error   += should_not_be_called
        self.on_connect += should_not_be_called

    def fileno(self):
        if self.socket is not None:
            return self.socket.fileno()
        else:
            return -1

if tls_available:
    class TLSLiteStreamSocket(TLSAsyncDispatcherMixIn, AsyncStreamSocket):
        ac_in_buffer_size = 16384
        def __init__(self, sock, *a, **k):
            AsyncStreamSocket.__init__(self, sock, *a, **k)
            TLSAsyncDispatcherMixIn.__init__(self, sock)
            self._logger = logging.getLogger(type(self).__name__)

        @util.callsback
        def setup_ssl(self, callback = None):
            self._logger.info('Setting up SSL')
            self._set_tls_opts((3,0))
            self._start_tls()

        @util.callsback
        def setup_tls(self, callback = None):
            self._logger.info('Setting up TLS')
            self._set_tls_opts((3,1))
            self._start_tls()

        def _set_tls_opts(self, version):
            self.tlsConnection.version = version
            self.tlsConnection.ignoreAbruptClose = True
            self.tlsConnection.closeSocket = True

        def _start_tls(self):
            self.setHandshakeOp(self.tlsConnection.handshakeClientCert(async=True))

        def close(self):
            try:
                TLSAsyncDispatcherMixIn.close(self)
            except Exception, e:
                traceback.print_exc()
                log.error("Error trying to shut down TLSConnection. Un-cleanly closing socket. (the error was: %r)", e)
                AsyncStreamSocket.close(self)

        def handle_error(self, e, force_close = False):
            if self._closed:
                return

            try:
                raise e
            except TLSLocalAlert:
                if getattr(e, 'errorStr', None) is not None:
                    #sys.stderr.write(e.errorStr)
                    e.verbose = False
            except:
                # This is OK because we already have the exception and we're sending it somewhere else
                pass

            AsyncStreamSocket.handle_error(self, e, force_close = force_close)

else:
    log.error('Defining a stub for TLSLiteStreamSocket, but I really shouldn\'t be here...')
    class TLSLiteStreamSocket(AsyncStreamSocket):
        pass

class TLSLiteStream(threadstream.ThreadStream):

    tls_available = tls_available

    def __init__(self, *a, **k):
        threadstream.ThreadStream.__init__(self, *a, **k)
        self.do_ssl = self.owner.do_ssl and self.tls_available
        self.use_tls = self.tls_settings and any(self.tls_settings.__dict__.values()) and self.tls_available

        self._socket_class = AsyncStreamSocket

        log.info('using _socket_class %r', self._socket_class)

    def _determine_conn_info(self, server, port):
        if not server:
            server = self.server
        if not port:
            port = self.port

        if server:
            service = None
        else:
            service = 'xmpp-client'

        if port is None:
            port = 5222

        if server is None:
            server = self.my_jid.domain
        self.me = self.my_jid

        return server, port, service

    def endpoint_generator(self, server, port, service = None, to = None):
        if to is None:
            to = str(server)

        addrs = []
        if service is not None:
            try:
                self.state_change("resolving srv",(server,service))
                addrs = resolver.resolve_srv(server, service) or []
            except Exception, e:
                log.debug('Failed to resolve %r: %r', (server, service), e)

        addrs.append((server, port))

        for address, port in addrs:
            if type(address) not in (str, unicode):
                continue
            self.state_change("resolving", address)
            try:
                resolved = resolver.getaddrinfo(address, port, 0, socket.SOCK_STREAM)
            except Exception:
                resolved = []

            resolved.append((2, 1, 0, '_unused', (address, port)))

            for sock_info in resolved:
                yield sock_info

    def _connect1(self, server = None, port = None):
        "Same as `ClientStream.connect` but assume `self.lock` is acquired."
        outdebug('_connect1')
        server, port, service = self._determine_conn_info(server, port)
        if getattr(self, '_endpoints', None) is None:
            self._endpoints = self.endpoint_generator(server, port, service, self.my_jid.domain)
        elif getattr(self, '_endpoints', None) is False:
            return

        if getattr(self, 'socket', None) is not None:
            self.socket.close()
            self.socket = None

        try:
            endpoint = self._endpoints.next()
        except StopIteration:
            if self.socket is not None:
                self.socket.close()
                self.socket = None
            self._endpoints = None
            log.info('No more endpoints to try.')

            return self.owner.connect_attempt_failed()

        self.socket = self._socket_class(sock = False,  # Don't make one yet.
                                          collect = self._feed_reader,
                                          on_close = self.closed,
                                          on_error = self.closed_dead,
                                          on_connect = lambda *a: None,
                                          ssl = self.do_ssl)

        family, socktype, proto, _unused, sockaddr = endpoint
        addr, port = sockaddr
        self.socket.create_socket(family, socktype)
        self.socket.socket.settimeout(2)

        self.state_change("connecting",sockaddr)

        def setup_success():
            self.addr, self.port = addr, port
            self._connect_socket(self.socket, self.my_jid.domain)
            self._endpoints.close()
            self._endpoints = False
            self.last_keepalive = time.time()

            with self.owner.lock:
                if self.owner.connect_killed == True:
                    raise FatalStreamError("Cannot connect")

        def connect_fail(e=None):
            log.error('connection to %r failed: %r', (addr, port), e)
            self._connect1()

        def connect_success():
            log.info('connection to %r succeeded', (addr, port))
            self.state_change("connected",sockaddr)
            if self.do_ssl:
                log.debug('\tsetting up socket SSL')
                self.setup_ssl(success = setup_success, error = connect_fail)
            else:
                log.debug('\tinitializing stream connection')
                setup_success()

        self.socket.on_connect += connect_success
        self.socket.connect(sockaddr, error = connect_fail)

    def change_sock_type(self, new_cls):
        sck = self.socket.socket
        self.socket.del_channel()
        oldsck = self.socket
        oldsck.socket = None
        self.socket = new_cls(sock = sck, # the new asyncsocket will wrap the socket.socket from the old one.
                               collect  = oldsck._collector,
                               on_close = oldsck.on_close,
                               on_error = oldsck.on_error,
                               on_connect = oldsck.on_connect,
                               ssl = True)
        self.socket.on_connect.extend(oldsck.on_connect)
        self.socket.add_channel()

    @util.callsback
    def setup_ssl(self, callback = None):
        self.change_sock_type(TLSLiteStreamSocket)
        self.socket.on_connect += callback.success
        self.socket.on_error += callback.error
        self.socket.setup_ssl()

    @util.callsback
    def _make_tls_connection(self, callback = None):
        """Initiate TLS connection.

        [initiating entity only]"""
        self.change_sock_type(TLSLiteStreamSocket)

        self.socket.on_connect += callback.success
        self.socket.on_connect += lambda *a, **k: self.state_change("tls connected", self.peer)
        self.socket.on_error += callback.error

        self.tls = self.socket
        self.state_change("tls connecting", self.peer)
        self.socket.setup_tls()

    def _connect_socket(self,sock,to=None):
        """Initialize stream on outgoing connection.

        :Parameters:
          - `sock`: connected socket for the stream
          - `to`: name of the remote host
        """
        logging.getLogger("ThreadStream").debug("connecting")
        netcall(lambda: LegacyClientStream._connect_socket(self, sock, to))
