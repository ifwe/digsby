import logging; log = logging.getLogger("msn.p2p.tcpbridge")
import util
import util.callbacks as callbacks
import util.Events as Events
import uuid
import msn.P2P as P2P
import msn.P2P.P2PBridge as Bridge
import common

import msn.P2P.P2PDirectProcessor as DirectProcessor

class TCPBridge(Bridge.P2PBridge):
    events = Bridge.P2PBridge.events | set((
        'DestinationAddressUpdated',
    ))

    BridgeType = 'TCPv1'

    ns = None
    session = None
    dc = None
    remote = None
    remoteEpid = uuid.UUID(int = 0)

    def _get_IsOpen(self):
        return self.dc is not None and self.dc.DCState == DirectProcessor.DirectConnectionState.Established

    def _get_MaxDataSize(self):
        return 11748

    def _get_Remote(self):
        if self.remote is not None:
            return self.remote

        if self.session is not None:
            return self.session.Remote

        for session in self.SendQueues.keys():
            return session.Remote

        return None

    def _get_RemoteEpid(self):
        return self.remoteEpid

    RemoteEpid = property(_get_RemoteEpid)

    def SuitableFor(self, session):
        return super(TCPBridge, self).SuitableFor(session) and session.RemoteContactEndPointID == self.RemoteEpid

    @property
    def RemoteEndPoint(self):
        if self.dc is None:
            return '', 0
        return self.dc.RemoteEndPoint

    @property
    def LocalEndPoint(self):
        if self.dc is None:
            return '', 0
        return self.dc.LocalEndPoint

    def __init__(self, ver, replyGuid, remoteNonce, hashed, session, ns, remote, remoteGuid):
        super(TCPBridge, self).__init__(queueSize = 0)

        self.session = session
        self.ns = ns
        self.remote = remote
        self.remoteEpid = remoteGuid

        self.dc = DirectProcessor.P2PDirectProcessor(ver, replyGuid, remoteNonce, hashed, session, ns)
        self.dc.bind_event('HandshakeCompleted',        self.dc_HandshakeCompleted)
        self.dc.bind_event('P2PMessageReceived',        self.dc_P2PMessageReceived)
        self.dc.bind_event('SendCompleted',             self.dc_SendCompleted)

        self.dc.bind_event('DirectNegotiationTimedOut', self.dc_DirectNegotiationTimedOut)
        self.dc.bind_event('ConnectionClosed',          self.dc_ConnectionClosed)
        self.dc.bind_event('ConnectingException',       self.dc_ConnectingException)
        self.dc.bind_event('ConnectionException',       self.dc_ConnectionException)

    def OnDestinationAddressUpdated(self, endpoints):
        if self.dc is not None and self.dc.Connected and self.dc.RemoteEndPoint != ('', 0):
            remoteEP = self.dc.RemoteEndPoint
            trustedPeer = False
            for endpoint in endpoints:
                if endpoint == remoteEP:
                    trustedPeer = True
                    break

            if not trustedPeer:
                log.info("Shutting down because unknown peer")
                self.Shutdown()

        self.DestinationAddressUpdated(endpoints)

    def Shutdown(self):
        if self.dc is not None:
            self.dc, dc = None, self.dc
            dc.Disconnect()
            self.OnBridgeClosed()
            if self is self.Remote.DirectBridge:
                self.Remote.DirectBridge = None

    def dc_HandshakeCompleted(self):
        self.OnBridgeOpened()
        self.Remote.DirectBridgeEstablished()

    def dc_DirectNegotiationTimedOut(self):
        self.Shutdown()

    def dc_ConnectingException(self):
        self.Shutdown()

    def dc_ConnectionException(self):
        self.Shutdown()

    def dc_ConnectionClosed(self):
        self.Shutdown()

    def Listen(self, where):
        host, port = where
        self.dc.Listen(host, port)

    def Connect(self, endpoints):
        self.dc.Connect(endpoints)

    def dc_P2PMessageReceived(self, message):
        if self.ns.P2PHandler is not None:
            self.ns.P2PHandler.ProcessP2PMessage(self, self.Remote, self.RemoteEpid, message)
        else:
            self.Shutdown()

    def SendOnePacket(self, session, remote, remoteGuid, msg, callback = None):
        message = self.SetSequenceNumberAndRegisterAck(session, remote, msg, callback)

        if msg.Header.Identifier == 0:
            log.error("Sending message with no identifier: %r", msg)

        self.dc.SendMessage(session, msg, callback)
    SendOnePacket = callbacks.callsback(SendOnePacket, ('success', 'error', 'after_send', 'progress'))

    def dc_SendCompleted(self, session, msg):
        util.call_later(0, self.OnBridgeSent, session, msg)

