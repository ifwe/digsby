import struct
import common
import logging; _log = log = logging.getLogger('msn.p2p.dc')
import msn.MSNUtil as MSNU
import msn.P2P as P2P
import msn.P2P.P2PMessage as P2PMessage
import uuid
import util
import util.callbacks as callbacks
import util.Events as Events
import util.primitives.structures as structures

class DirectConnectionState(structures._Enum):
    Closed = 0
    Foo = 1
    Handshake = 2
    HandshakeReply = 3
    Established = 5

DCState = DirectConnectionState = DirectConnectionState()
DCState.NONE = DCState.Closed

class P2PDirectProcessor(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'DirectNegotiationTimedOut',
        'HandshakeCompleted',
        'P2PMessageReceived',

        'SendCompleted',
        'ConnectionClosed',
        'ConnectingException',
        'ConnectionException',
    ))

    StrictNonce = False

    Version = P2P.Version.V1
    Nonce = uuid.UUID(int = 0)
    needHash = False
    socketExpireTimer = None
    IsListener = False
    socketListener = None
    dcSocket = None
    startupSession = None
    nsMessageHandler = None
    dcState = DCState.Closed
    Reply = uuid.UUID(int=0)

    def DCState():
        def fget(self):
            return self.dcState
        def fset(self, value):
            if value != self.dcState:
                self.dcState = value
                if value == DirectConnectionState.Established:
                    self.OnHandshakeCompleted()

        return locals()
    DCState = property(**DCState())

    @property
    def Connected(self):
        return self.RemoteEndPoint is not None

    @property
    def RemoteEndPoint(self):
        if self.dcSocket is None:
            return None
        else:
            try:
                return self.dcSocket.getpeername()
            except Exception:
                return None

    @property
    def LocalEndPoint(self):
        if self.dcSocket is None:
            if self.socketListener is None:
                return None
            else:
                try:
                    return self.socketListener.getsockname()
                except Exception:
                    return None
        else:
            try:
                return self.dcSocket.getsockname()
            except AttributeError:
                return None

    @property
    def protocol(self):
        return self.nsMessageHandler

    def __init__(self, version, reply, authNonce, isNeedHash, session, nsMessageHandler):
        Events.EventMixin.__init__(self)

        self.Version = version
        self.Nonce = authNonce
        self.needHash = isNeedHash
        self.startupSession = session
        self.nsMessageHandler = nsMessageHandler
        self.Reply = reply

        # Handled by asyncore
        #self.MessagePool = P2PDCPool()

    def Listen(self, host, port):
        log.info("P2PDC.Listen(%r, %r)", host, port)
        # TODO: get prepared socket, listen, accept
        socket = MSNTcpServer()
        self.IsListener = True
        self.socketListener = socket

        # It says connect, but it's really accept! What a country.
        socket.connect(success = self.OnAccept, error = self.Disconnect)
        self.SetupTimer()

    @property
    def _timeout(self):
        from common import pref
        return pref('msn.direct.timeout', type=int, default=5)

    def Connect(self, endpoints):
        self.SetupTimer()
        self.dcSocket = MSNTcpClient(endpoints)
        self.dcSocket.connect(success = self.on_connected, error = self.Disconnect)

        log.info("P2PDC.Connect(endpoints = %r)", endpoints)

    def tryconnect(self):

        if self._ips:
            self.dcSocket.connect(self._ips.pop(0), use_proxy = False, success = self.on_connected, error = self.tryconnect)
        else:
            self.on_connect_error()

    def on_connected(self, sock):
        self._ips = []
        self.dcSocket.cleanup()

        #_log.info("Got socket with data: %r, %r", sock, sock._data)
        self.dcSocket = MSNDirectTcpSocket(sock, sock._data)
        self.dcSocket.bind_event('on_message', self.OnMessageReceived)
        self.dcSocket.bind_event('on_close', self.Disconnect)
        self.dcSocket.bind_event('on_error', self.ConnectionException)
        self.dcSocket.bind_event('on_send', self.SendCompleted)

        self.OnConnected()

    def on_connect_error(self):
        self._ips = []
        self.dcSocket.close()
        self.dcSocket = None
        self.ConnectingException()

    def SetupTimer(self):
        self.socketExpireTimer = util.Timer(15, self.SocketExpireTimer_elapsed)
        self.socketExpireTimer.start()

    def SocketExpireTimer_elapsed(self):
        self.OnDirectNegotiationTimedOut()

    def StopListening(self):
        if self.socketListener is not None:
            self.socketListener.close()

        self.socketListener = None

    def OnAccept(self, newsock):
        log.info("Socket accept! %r", newsock)
        self.dcSocket = MSNDirectTcpSocket(newsock)
        self.dcSocket.bind_event('on_message', self.OnMessageReceived)
        self.dcSocket.bind_event('on_close', self.Disconnect)
        self.dcSocket.bind_event('on_error', self.ConnectionException)
        self.dcSocket.bind_event('on_send', self.SendCompleted)

        self.DCState = DCState.Foo

        self.StopListening()
        #self.BeginDataReceive(self.dcSocket)
        self.OnConnected()

    def Disconnect(self):
        log.info("Disconnecting...")
        self.OnDisconnected()
        self.StopListening()
        if self.dcSocket is not None:
            socket, self.dcSocket = self.dcSocket, None
            if hasattr(socket, 'clear'):
                # Clear event handlers
                socket.clear()
            socket.close()

    def OnConnected(self):
        if (not self.IsListener) and self.DCState == DCState.Closed:
            log.info("Connected! Changing state to Foo, sending Foo, changing state to Handshake, sending handshake, changing state to HandshakeReply")
            self.DCState = DCState.Foo
            self.SendSocketData(self.dcSocket, '\x04\0\0\0foo\0')

            self.DCState = DCState.Handshake
            hm = P2PMessage.P2PDCHandshakeMessage(self.Version)
            hm.Guid = self.Reply
            log.info("Sending handshake reply message: %r", hm)

            if self.Version == P2P.Version.V1:
                hm.Header.Identifier = self.startupSession.NextLocalIdentifier(0)

            self.SendSocketData(self.dcSocket, hm.GetBytes())
            self.DCState = DCState.HandshakeReply

    def SendSocketData(self, socket, data, *a):
        #_log.info("SendSocketData(socket = %r, data = %r)", socket, data)
        return socket.send(data)

    def OnDisconnected(self):
        self.DCState = DCState.Closed
        self.event('ConnectionClosed')

    def VerifyHandshake(self, data):
        authVersion = P2P.Version.V1
        ret = None
        version1 = False
        version2 = False

        if len(data) == 48:
            authVersion = P2P.Version.V1
            version1 = True
        elif len(data) == 16:
            authVersion = P2P.Version.V2
            version2 = True
        else:
            return None

        if authVersion != self.Version:
            return None

        incomingHandshake = P2PMessage.P2PDCHandshakeMessage(self.Version)
        incomingHandshake.ParseBytes(data)

        incomingGuid = incomingHandshake.Guid
        if version1 and ((incomingHandshake.VHeader.Flags & P2P.Flags.DCHS) != P2P.Flags.DCHS):
            return None

        compareGuid = incomingGuid
        if self.needHash:
            compareGuid = MSNU.HashNonce(compareGuid)

        if self.Nonce == compareGuid or not self.StrictNonce:
            if self.Nonce != compareGuid:
                log.warning("nonces don't match! continuing anyway.")

            ret = P2PMessage.P2PDCHandshakeMessage(self.Version)
            ret.ParseBytes(data)
            ret.Guid = compareGuid
            ret.Header.Identifier = 0
            return ret

        return None

    def OnMessageReceived(self, data):
        #_log.info("%r got data: %r", self, data)
        #_log.info("\tDC state = %r", self.DCState)
        if self.DCState == DCState.Established:
            dcMessage = P2PMessage.P2PDCMessage(self.Version)
            dcMessage.ParseBytes(data)

            #_log.info("Got P2P message! %r", dcMessage)
            self.OnP2PMessageReceived(dcMessage)
        elif self.DCState == DCState.HandshakeReply:
            match = self.VerifyHandshake(data)
            if match is None:
                log.info("Bad handshake. Disconnecting")
                self.Disconnect()
                return
            else:
                log.info("Got valid handshake. Session Established")

            self.DCState = DCState.Established
        elif self.DCState == DCState.Handshake:

            match = self.VerifyHandshake(data)
            if match is None:
                log.info("Handshake didn't verify. Disconnecting...")
                self.Disconnect()
                return

            match.Guid = self.Reply
            if self.Version == P2P.Version.V1:
                match.Header.Identifier = self.startupSession.NextLocalIdentifier(0)

            log.info("Sending matching handshake and changing to 'Established'")
            self.SendSocketData(self.dcSocket, match.GetBytes())
            self.DCState = DCState.Established
        elif self.DCState == DCState.Foo:
            if len(data) == 4 and data == 'foo\0':
                log.info("Got FOO. State is now 'Handshake'")
                self.DCState = DCState.Handshake
            else:
                log.info("Got something besides foo. Disconnecting")
                self.Disconnect()
                return

        else:
            log.info("Don't know what to do with this data: %r", data)

    def SendMessage(self, session, message, callback = None):
        if not isinstance(message, P2PMessage.P2PDCMessage):
            #log.info("Making P2PDCMessage from %r, bytes = %r", message, message.GetBytes())
            message = P2PMessage.P2PDCMessage.Copy(message)

        if self.SendSocketData(self.dcSocket, message.GetBytes()):
            getattr(callback, 'after_send', lambda:None)()
        else:
            callback.error()

        self.event("SendCompleted", session, message)

    def OnDirectNegotiationTimedOut(self):
        self.event('DirectNegotiationTimedOut')

    def OnHandshakeCompleted(self):
        log.info("Handshake completed")
        if self.socketExpireTimer is not None:
            self.socketExpireTimer.stop()
            self.socketExpireTimer = None

        self.event('HandshakeCompleted')

    def OnP2PMessageReceived(self, message):
        self.event('P2PMessageReceived', message)

class MSNDCConnecter(Events.EventMixin):
    events = Events.EventMixin.events | set ((
        'timeout',
        'connected',

        'on_message',
        'on_close',
        'on_error',
        'on_send',
        'on_local_ip',
    ))

    def __init__(self, ips = ()):
        Events.EventMixin.__init__(self)
        self._ips = ips

        self.data = ''

    def connect(self):
        raise NotImplementedError

    def collect_incoming_data(self, data):
        self.data += data

    def bind(self, *a, **k):
        return Events.EventMixin.bind(self, *a, **k)

    @property
    def _timeout(self):
        from common import pref
        return pref('msn.direct.timeout', type=int, default=5)

    @property
    def localport(self):
        try:
            return self.socket.getsockname()[1]
        except:
            return 0

    def getsockname(self):
        return self.socket.getsockname()

class MSNTcpServer(common.TimeoutSocket, MSNDCConnecter):
    bind = MSNDCConnecter.bind

    def __init__(self):
        common.TimeoutSocket.__init__(self, False)
        MSNDCConnecter.__init__(self, ())
        self.set_terminator(0)

    @callbacks.callsback
    def connect(self, callback=None):
        self.tryaccept(('',0), callback.success, callback.error, self._timeout)

    def cleanup(self):
        self.del_channel()
        self.close()

    def set_ips(self, ips):
        pass

class MSNTcpClient(common.HydraSocket, MSNDCConnecter):
    def __init__(self, ips = ()):
        common.HydraSocket.__init__(self)
        MSNDCConnecter.__init__(self, ips)

    @callbacks.callsback
    def connect(self, callback=None):
        self.tryconnect(self._ips, callback.success, callback.error, self._timeout, cls=BufferedTimeoutSocket)

    def cleanup(self):
        pass

class MSNDCSocket(common.socket, Events.EventMixin):
    events = Events.EventMixin.events | set((
        'on_message',
        'on_close',
        'on_error',
        'on_send',
    ))

    def __init__(self, conn, prev_data = ''):
        common.socket.__init__(self, conn)
        self.set_terminator(self.hdr_size)
        self.ac_in_buffer = prev_data
        Events.EventMixin.__init__(self)
        self.data = ''
        self.getting_hdr = True

    def collect_incoming_data(self, data):
        self.data += data

    def handle_close(self):
        self.event('on_close')
        common.socket.handle_close(self)
        self.close()

    def handle_expt(self):
        self.event('on_error')
        common.socket.handle_expt(self)

    def handle_error(self, e=None):
        import traceback; traceback.print_exc()
        self.event('on_error')
        self.close()
        common.socket.handle_error(self, e)

    @property
    def localport(self):
        try:
            return self.socket.getsockname()[1]
        except:
            return 0

    def __repr__(self):
        pn = None
        try:     pn = self.socket.getpeername()
        finally: return "<%s connected to %r>" % (self.__class__.__name__,pn)

    def getpeername(self):
        return self.socket.getpeername()

class MSNDirectTcpSocket(MSNDCSocket):
    hdr_size = 4
    p2p_overhead = 52
    p2p_max_msg_size = 1400

    def build_data(self, header, body, footer):
        return ''.join((struct.pack('<I', len(header) + len(body)), header, body))

    def found_terminator(self):
        data, self.data = self.data, ''
        #print 'IN2<<<',repr(data)
        self.getting_hdr = not self.getting_hdr

        if not self.getting_hdr:
            next_term, = struct.unpack('<I', data)
            #sock_in.log(15, 'Socket waiting for %d bytes', next_term)
            if next_term:
                self.set_terminator(next_term)
            else:
                self.found_terminator()
        else:
            #sock_in.info('Received %d bytes', len(data))
            #sock_in.log(5, '    MSNDCSocket Data in: %r', data[:100])
            self.set_terminator(self.hdr_size)
            self.event('on_message', data)

    def _send(self, data):
        log.log(5, '    MSNDirectTcpSocket Data out: %r', data[:100])
        real_data = struct.pack('<I', len(data)) + data
        return common.socket.push(self, real_data)

class BufferedTimeoutSocket(common.TimeoutSocket):
    def __init__(self, *a, **k):
        common.TimeoutSocket.__init__(self, *a, **k)
        self.set_terminator(0)
        self._data = ''

    def collect_incoming_data(self, data):
        #print 'IN4<<<', repr(data)
        self._data += data

    def recv(self, bytes):
        if self._data:
            data, self._data = self._data[:bytes], self._data[bytes:]
        else:
            data = self.socket.recv(bytes)

        return data

    def handle_close(self):
        self.socket.close()
