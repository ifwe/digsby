import io
import msn.P2P as P2P
import msn.P2P.P2PMessage as P2PMessage
import msn.P2P.MSNSLPMessages as MSNSLP
import logging
log = logging.getLogger('msn.p2p.session')
import sys
import uuid
import struct
import common
import msn.AddressBook as MSNAB
import util
import util.net as net
import util.Events as Events
import util.primitives.funcs as funcs
import util.primitives.structures as structures
import util.callbacks as callbacks

import msn.P2P.P2PApplication as P2PApplication

def randid():
    import random
    return random.randint(5000, sys.maxint//2)

class P2PSessionStatus:
    Error = 0
    WaitingForLocal = 1
    WaitingForRemote = 2
    Active = 3
    Closing = 4
    Closed = 5

class DCNonceType:
    NONE = 0
    Plain = 1
    Sha1 = 2

class P2PSession(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'Error',
        'Activated',
        'Closing',
        'Closed',

        'Messages',
    ))

    SessionId = 0
    LocalBaseIdentifier = 0
    LocalIdentifier = 0
    RemoteBaseIdentifier = 0
    RemoteIdentifier = 0

    LocalContact = None
    RemoteContact = None
    LocalContactEPID = uuid.UUID(int = 0)
    remoteContactEPID = uuid.UUID(int = 0)

    Invitation = None
    Bridge = None
    App = None
    _sent_bye = False

    Version = P2P.Version.V1
    Status = P2PSessionStatus.Closed
    protocol = None

    def __repr__(self):
        varstr = ', ' .join('%s=%r' % i for i in vars(self).items())
        return '%s(%s)' % (type(self).__name__, varstr)

    @property
    def Local(self):
        return self.LocalContact

    @property
    def Remote(self):
        return self.RemoteContact

    @property
    def LocalContactId(self):
        if self.Version == P2P.Version.V1:
            return self.Local.account

        return self.Local.account + ';{' + str(self.LocalContactEPID).lower() + '}'

    @property
    def RemoteContactId(self):
        if self.Version == P2P.Version.V1:
            return self.Remote.account

        return self.Remote.account + ';{' + str(self.RemoteContactEPID).lower() + '}'

    def _get_RemoteContactEPID(self):
        if int(self.remoteContactEPID) == 0:
            self.remoteContactEPID = self.RemoteContact.SelectRandomEPID()

        return self.remoteContactEPID

    def _set_RemoteContactEPID(self, val):
        if not isinstance(val, uuid.UUID):
            if isinstance(val, int):
                val = uuid.UUID(int = val)
            else:
                # Assume string
                val = uuid.UUID(val)

        if int(val) == 0:
            val = self.RemoteContact.SelectRandomEPID()

        self.remoteContactEPID = val

    RemoteContactEPID = property(_get_RemoteContactEPID, _set_RemoteContactEPID)

    @property
    def NSMessageHandler(self):
        return self.protocol


    def __init__(self, slp = None, msg = None, ns = None, bridge = None, app = None):
        Events.EventMixin.__init__(self)
        self.directNegotiationTimer = None
        self.timeoutTimer = None

        self.sessionMessages = []
        self.dataMessages = []

        if app is not None:
            self.LocalInit(app)
        else:
            self.RemoteInit(slp, msg, ns, bridge)

        log.info("New session: %r", vars(self))


    def KillDirectNegotiationTimer(self):
        if self.directNegotiationTimer is not None:
            self.directNegotiationTimer.stop()
            self.directNegotiationTimer = None
            #log.info("Killing directNegotiationTimer")

        self.ResetTimeoutTimer()

    def DirectNegotiationSuccessful(self):
        self.KillDirectNegotiationTimer()

    def DirectNegotiationTimedOut(self, session = None):
        log.debug("DirectNegotiationTimedOut")
        self.DirectNegotiationFailed()

    def DirectNegotiationFailed(self):
        log.debug("DirectNegotiationFailed")
        self.KillDirectNegotiationTimer()

        if self.Bridge is not None:
            log.info("Resume sending on %r", self.Bridge)
            self.Bridge.ResumeSending(self)
        else:
            log.error("Can't resume sending, no bridge!")

        if self.App is not None:
            self.App.Start()

    def ConnectionType(self, protocol):
        connType = 'Unknown-Connect'

        local_ip = net.ip_from_bytes(net.myip())
        local_port = protocol.get_local_sockname()[1]

        netId = struct.unpack('>I', net.myip())[0]

        remote_ip = protocol.ip
        remote_port = protocol.port

        ip_restrict = local_ip != remote_ip
        port_restrict = local_port != remote_port

        if ip_restrict:
            if port_restrict:
                return 'Symmetric-NAT', netId
            else:
                return 'IP-Restrict-NAT', netId
        else:
            if port_restrict:
                return 'Port-Restrict-NAT', netId
            else:
                return 'Direct-Connect', netId

    def SendDirectInvite(self):
        if not common.pref('msn.p2p.allow_direct', type = bool, default = True):
            return False

        if self.Remote.DirectBridge is not None and self.Remote.DirectBridge.IsOpen:
            return False

        self.ResetDCTimer()

        connType, netId = self.ConnectionType(self.protocol)

        remote = self.Remote
        ver = self.Version
        message = P2PMessage.P2PMessage(ver)

        slp = MSNSLP.SLPRequestMessage(self.RemoteContactId, MSNSLP.RequestMethod.INVITE)
        slp.Source = self.LocalContactId
        slp.CSeq = 0
        slp.CallId = self.Invitation.CallId
        slp.MaxForwards = 0
        slp.ContentType = 'application/x-msnmsgr-transreqbody'

        slp.BodyValues['Bridges'] = 'TCPv1 SBBridge'
        slp.BodyValues['Capabilities-Flags'] = '1'
        slp.BodyValues['NetID'] = str(netId)
        slp.BodyValues['Conn-Type'] = connType
        slp.BodyValues['TCP-Conn-Type'] = connType
        slp.BodyValues['UPnPNat'] = 'false'
        slp.BodyValues['ICF'] = 'true' if connType == 'Firewall' else 'false'
        slp.BodyValues['Nat-Trav-Msg-Type'] = 'WLX-Nat-Trav-Msg-Direct-Connect-Req'

        remote.GenerateNewDCKeys()
        slp.BodyValues['Hashed-Nonce'] = '{%s}' % str(remote.dcLocalHashedNonce).upper()

        message.InnerMessage = slp

        if ver == P2P.Version.V2:
            message.Header.TFCombination = P2P.TFCombination.First
        else:
            message.Header.Flags = P2P.Flags.MSNSLPInfo

        Bridge = self.protocol.ns.SDGBridge
        Bridge.StopSending(self)
        self.ResetDCTimer()

        log.info("Sending direct invite")
        Bridge.Send(None, remote, self.RemoteContactEPID, message)

        return True

    def ResetDCTimer(self):
        self.KillTimeoutTimer()
        #log.info("Resetting directNegotiationTimer")
        if self.directNegotiationTimer is None:
            self.directNegotiationTimer = util.ResetTimer(17, self.DirectNegotiationTimedOut)
            self.directNegotiationTimer.start()
        else:
            self.directNegotiationTimer.reset()

    def InactivityClose(self):
        log.info("Closing session due to inactivity")
        if self.Status == P2PSessionStatus.Active and \
            self.App is not None and \
            self.App.status == P2PApplication.AppStatus.Active and \
            hasattr(self.App, 'Sending'):

            # Other client stopped sending data.
            if not self.App.Sending:
                self.OnClosed(self.Remote)
                self.SendBye()
                return

        self.Close()
        self.KillTimeoutTimer()

    def KillTimeoutTimer(self):
        if self.timeoutTimer is not None:
            #log.info("Killing timeoutTimer")
            self.timeoutTimer.stop()
            self.timeoutTimer = None

    def RemoteInit(self, slp, msg, client, bridge):
        self.protocol = client = getattr(client, 'ns', client).protocol
        if bridge is None:
            bridge = client.ns.SDGBridge

        self.Invitation = slp
        version1 = version2 = False
        if uuid.UUID(int = 0) in (slp.FromEndPoint, slp.ToEndPoint):
            version1 = True
            self.Version = P2P.Version.V1
        else:
            version2 = True
            self.Version = P2P.Version.V2

        if slp.ToEmailAccount == client.self_buddy.name:
            self.LocalContact = client.ns.contact_list.owner
        else:
            self.LocalContact = client.ns.contact_list.GetContact(slp.ToEmailAccount, MSNAB.IMAddressInfoType.WindowsLive)

        self.RemoteContact = client.ns.contact_list.GetContact(slp.FromEmailAccount, MSNAB.IMAddressInfoType.WindowsLive)

        if version2:
            self.LocalContactEPID = slp.ToEndPoint
            self.RemoteContactEPID = slp.FromEndPoint

        try:
            self.SessionId = int(slp.BodyValues.get('SessionID', '0'))
        except (TypeError, ValueError):
            self.SessionId = 0

        self.Bridge = bridge
        self.LocalIdentifier = self.LocalBaseIdentifier = bridge.localTrackerId

        self.Status = P2PSessionStatus.WaitingForLocal
        self.RemoteContact.bind_event('DirectBridgeEstablished', self.RemoteDirectBridgeEstablished)

        if msg is not None:
            self.RemoteIdentifier = self.RemoteBaseIdentifier = msg.Header.Identifier
            if version2:
                self.RemoteIdentifier += msg.Header.MessageSize

        appId = int(slp.BodyValues.get('AppID', 0))
        eufGuid = uuid.UUID(slp.BodyValues.get('EUF-GUID', str(uuid.UUID(int=0))))
        self.App = P2PApplication.P2PApplication.CreateInstance(eufGuid, appId, self)

        log.info("Attempting invitation validation for app = %r...", self.App)
        if self.App is not None and self.App.ValidateInvitation(self.Invitation):
            if self.App.AutoAccept:
                log.info("Valid invitation and AutoAccept")
                self.Accept(True)
            else:
                log.info("Valid invitation and asking user...")
                self.KillTimeoutTimer()
                self.protocol.OnInvitationReceived(self)
        else:
            log.info("Invalid invitation")
            self.Decline()

    def LocalInit(self, app):
        self.App = app
        self.Version = app.Version
        self.LocalContact = app.Local
        self.RemoteContact = app.Remote

        self.LocalContactEPID = app.client.get_machine_guid()
        self.RemoteContactEPID = app.Remote.SelectRandomEPID()

        self.protocol = getattr(app.Local.client, 'ns', app.Local.client).protocol
        self.SessionId = randid()

        invite = self.Invitation = MSNSLP.SLPRequestMessage(self.RemoteContactId, MSNSLP.RequestMethod.INVITE)
        invite.Target = self.RemoteContactId
        invite.Source = self.LocalContactId
        invite.ContentType = 'application/x-msnmsgr-sessionreqbody'
        invite.BodyValues['SessionID'] = str(self.SessionId)
        app.SetupInviteMessage(invite)
        app.P2PSession = self

        self.RemoteContact.bind('DirectBridgeEstablished', self.RemoteDirectBridgeEstablished)
        self.Status = P2PSessionStatus.WaitingForRemote

    def _PrepSLPMessage(self, slpMessage):
        slpMessage.Target = self.RemoteContactId
        slpMessage.Source = self.LocalContactId
        slpMessage.Branch = self.Invitation.Branch
        slpMessage.CallId = self.Invitation.CallId
        slpMessage.CSeq = 1
        slpMessage.ContentType = 'application/x-msnmsgr-sessionreqbody'
        slpMessage.BodyValues['SessionID'] = str(self.SessionId)

    def _MakeSLPStatusMessage(self, for_who, code, phrase):
        slpMessage = MSNSLP.SLPStatusMessage(for_who, code, phrase)
        self._PrepSLPMessage(slpMessage)
        return slpMessage

    def _MakeSLPRequestMessage(self, for_who, method):
        slpMessage = MSNSLP.SLPRequestMessage(for_who, method)
        self._PrepSLPMessage(slpMessage)
        return slpMessage

    def Invite(self):
        if self.Status != P2PSessionStatus.WaitingForRemote:
            log.info("My status is %r, should be %r. (self=%r)", self.Status, P2PSessionStatus.WaitingForRemote, self)
            return False

        self.MigrateToOptimalBridge()
        log.info("Setting LocalIdentifier to bridge's: %r", self.Bridge.localTrackerId)
        self.LocalIdentifier = self.LocalBaseIdentifier = self.Bridge.localTrackerId

        message = self.WrapSLPMessage(self.Invitation)

        if self.Version == P2P.Version.V2:
            if not self.Bridge.Synced:
                message.Header.OperationCode = P2P.OperationCode.SYN | P2P.OperationCode.RAK
                message.Header.AppendPeerInfoTLV()

        message.InnerMessage = self.Invitation

        def after_send(ack):
            if self.Remote.DirectBridge is None:
                self.SendDirectInvite()

            log.info("Invite send success. Got RemoteBaseIdentifier (%r)", ack.Header.Identifier)
            self.RemoteIdentifier = self.RemoteBaseIdentifier = ack.Header.Identifier

        log.info("Sending invitation for %r / %r", self, self.App)
        self.KillTimeoutTimer()
        self.Send(message, success = after_send)

    def Accept(self, sendDCInvite):
        if self.Status != P2PSessionStatus.WaitingForLocal:
            return False

        if sendDCInvite and self.Remote.DirectBridge is None:
            self.SendDirectInvite()

        slpMessage = self._MakeSLPStatusMessage(self.RemoteContactId, 200, 'OK')

        log.info("Accepting invite for %r / %r", self, self.App)

        def after_200(ack = None):
            log.info("Invite accept sent.")
            self.OnActive()

            log.info("\tStarting app: %r", self.App)
            if self.App is not None:
                self.App.Start()

        self.Send(self.WrapSLPMessage(slpMessage), success = after_200)

    def Decline(self):
        if self.Status != P2PSessionStatus.WaitingForLocal:
            return False

        slpMessage = self._MakeSLPStatusMessage(self.RemoteContactId, 603, 'Decline')

        msg = P2PMessage.P2PMessage(self.Version)
        if self.Version == P2P.Version.V1:
            msg.Header.Flags = P2P.Flags.MSNSLPInfo
        else:
            msg.Header.OperationCode = P2P.OperationCode.RAK
            msg.Header.TFCombination = P2P.TFCombination.First
            msg.Header.PackageNumber = self.Bridge.IncrementPackageNumber()

        msg.InnerMessage = slpMessage

        self.Send(msg, success = lambda ack: self.Close())

    def Close(self):
        if self.Status == P2PSessionStatus.Closing:
            self.OnClosed(self.Local)
            return

        self.OnClosing(self.Local)

        self.SendBye()

    def SendBye(self):
        if self._sent_bye:
            log.info("Already sent bye message. not re-sending")
            return
        self._sent_bye = True
        log.info("Constructing and queueing BYE message for %r", self)
        slpMessage = self._MakeSLPRequestMessage(self.RemoteContactId, 'BYE')
        slpMessage.MaxForwards = 0
        slpMessage.CSeq = 0
        slpMessage.Branch = self.Invitation.Branch
        slpMessage.ContentType = 'application/x-msnmsgr-sessionclosebody'

        msg = P2PMessage.P2PMessage(self.Version)
        if msg.Version == P2P.Version.V1:
            msg.Header.Flags = P2P.Flags.MSNSLPInfo
        else:
            msg.Header.OperationCode = P2P.OperationCode.RAK
            msg.Header.TFCombination = P2P.TFCombination.First
            if self.Bridge is not None:
                msg.Header.PackageNumber = self.Bridge.IncrementPackageNumber()

        msg.InnerMessage = slpMessage
        self.Send(msg, after_send = lambda ack=None: self.OnClosed(self.Local))

    def Dispose(self):
        self.KillTimeoutTimer()
        self.Remote.unbind('DirectBridgeEstablished', self.RemoteDirectBridgeEstablished)
        self.DisposeApp()
        self.Migrate(None)

    def OnClosing(self, contact):
        self.KillTimeoutTimer()
        self.Status = P2PSessionStatus.Closing
        self.event('Closing', self, contact)
        self.DisposeApp()

    def OnClosed(self, contact):
        self.KillTimeoutTimer()
        self.Status = P2PSessionStatus.Closed

        self.event('Closed', self, contact)
        self.DisposeApp()

    def OnError(self):
        self.Status = P2PSessionStatus.Error
        self.KillTimeoutTimer()
        self.event('Error', self)
        self.DisposeApp()

    def OnActive(self):
        self.Status = P2PSessionStatus.Active
        self.ResetTimeoutTimer()
        self.event('Activated', self)

    def DisposeApp(self):
        if self.App is not None:
            self.App.Dispose()
            self.App = None

    def ResetTimeoutTimer(self):
        #log.info("Resetting timeoutTimer")
        if self.Status not in (P2PSessionStatus.Closed, P2PSessionStatus.Active,):
            #log.debug("Wrong state for starting timeout timer")
            return

        if self.timeoutTimer is None:
            self.timeoutTimer = util.ResetTimer(12, self.InactivityClose)
            self.timeoutTimer.start()
        else:
            self.timeoutTimer.reset()

    def ProcessP2PMessage(self, bridge, message, slp):
        #log.info("Got message for %r: %r", self, message)
        self.ResetTimeoutTimer()

        self.RemoteIdentifier = message.Header.Identifier
        if self.Version == P2P.Version.V2:
            self.RemoteIdentifier += message.Header.MessageSize

        if self.Status in (P2PSessionStatus.Closed, P2PSessionStatus.Error):
            log.info("Session is closed / error'd. Not handling message %r", message)
            return False

        if slp is not None:
            if hasattr(slp, 'Method'):
                # Request
                if slp.ContentType == 'application/x-msnmsgr-sessionclosebody' and slp.Method == 'BYE':
                    log.info("Got BYE message from %r", self.Remote.account)
                    if message.Version == P2P.Version.V1:
                        byeAck = message.CreateAck()
                        byeAck.Header.Flags = P2P.Flags.CloseSession
                        self.Send(byeAck)
                    else:
                        slpMessage = MSNSLP.SLPRequestMessage(self.RemoteContactId, 'BYE')
                        slpMessage.Target = self.RemoteContactId
                        slpMessage.Source = self.LocalContactId
                        slpMessage.Branch = self.Invitation.Branch
                        slpMessage.CallId = self.Invitation.CallId
                        slpMessage.ContentType = 'application/x-msnmsgr-sessionclosebody'
                        slpMessage.BodyValues['SessionID'] = str(self.SessionId)

                        log.info("Sending my own BYE message")
                        self.Send(self.WrapSLPMessage(slpMessage))

                    self.OnClosed(self.Remote)
                    return True

                elif (slp.ContentType == 'application/x-msnmsgr-sessionreqbody') and (slp.Method == 'INVITE'):
                    slpMessage = MSNSLP.SLPStatusMessage(self.RemoteContactId, 500, 'Internal Error')
                    slpMessage.Target = self.RemoteContactId
                    slpMessage.Source = self.LocalContactId
                    slpMessage.Branch = self.Invitation.Branch
                    slpMessage.CallId = self.Invitation.CallId
                    slpMessage.ContentType = 'application/x-msnmsgr-sessionreqbody'
                    slpMessage.BodyValues['SessionID'] = str(self.SessionId)

                    errorMessage = self.WrapSLPMessage(slpMessage)
                    bridge.Send(None, self.Remote, self.RemoteContactEPID, errorMessage)
                    return True
                elif slp.ContentType in ('application/x-msnmsgr-transreqbody',
                                         'application/x-msnmsgr-transrespbody',
                                         'application/x-msnmsgr-transdestaddrupdate'):
                        ProcessDirectInvite(slp, self.protocol, self)
                        return True
            else:
                if slp.Code == 200:
                    if slp.ContentType == 'application-x-msnmsgr-transrespbody':
                        ProcessDirectInvite(slp, self.protocol, self)

                    else:
                        log.info("Got 200 OK for invite. Starting app = %r", self.App)
                        self.OnActive()
                        self.App.Start()

                    return True

                elif slp.Code == 603:
                    self.OnClosed(self.Remote)
                    return True

                elif slp.Code == 500:
                    return True

        if self.App is None:
            log.error("No app set up. Ignoring message = %r", message)
            return False

        if message.Header.MessageSize > 0 and message.Header.SessionId > 0:
            reset = False
            appData = io.BytesIO()
            if message.Header.MessageSize == 4 and message.InnerBody == ('\0'*4):
                reset = True

            else:
                appData.write(message.InnerBody)

            if message.Version == P2P.Version.V2 and P2P.TFCombination.First == (message.Header.TFCombination & P2P.TFCombination.First):
                reset = True

            return self.App.ProcessData(bridge, appData, reset)

        log.error("Nothing to do for message = %r", message)
        return False

    def Send(self, msg, callback = None, **kw):
        self.ResetTimeoutTimer()

        if msg is None:
            import traceback; traceback.print_stack()

        self.sessionMessages.append((msg, callback, kw))
        util.call_later(0, self.event, 'Messages', self)

    Send = callbacks.callsback(Send, ('success', 'error', 'after_send', 'progress'))

    def GetNextMessage(self, maxDataSize):
        messageSource = self.sessionMessages or self.dataMessages
        if not messageSource:
            return None, None, {}
        else:
            currentMessage, callback, kw = messageSource[0]
            if currentMessage.IsFinished():
                messageSource.pop(0)
                return self.GetNextMessage(maxDataSize)

            nextMessage, more_callbacks = currentMessage.GetNextMessage(maxDataSize)
            for key in more_callbacks:
                callback_part = getattr(callback, key, None)
                if callback_part is not None:
                    callback_part += more_callbacks[key]

            callback.progress()

        return nextMessage, callback, kw

    def AttemptBridgeSend(self):
        self.MigrateToOptimalBridge()

        message, callback, kw = self.GetNextMessage(self.Bridge.MaxDataSize)
        if message is None:
            return

        self.Bridge.SendOnePacket(self, self.Remote, self.RemoteContactEPID, message, callback = callback)
        #log.debug("Session.Bridge.Send(message = %r)", message)
        #self.Bridge.Send(self, self.Remote, self.RemoteContactEPID, message, callback = callback)

    def WrapSLPMessage(self, slp):
        message = P2PMessage.P2PMessage(self.Version)
        message.InnerMessage = slp

        if message.Version == P2P.Version.V2:
            message.Header.TFCombination = P2P.TFCombination.First
            message.Header.PackageNumber = self.Bridge.IncrementPackageNumber()
        else:
            message.Header.Flags = P2P.Flags.MSNSLPInfo

        return message

    def RemoteDirectBridgeEstablished(self):
        self.MigrateToOptimalBridge()

    def MigrateToOptimalBridge(self):
        if self.Remote.DirectBridge is not None and self.Remote.DirectBridge.IsOpen:
            self.Migrate(self.Remote.DirectBridge)

        else:
            self.Migrate(self.protocol.P2PHandler.GetBridge(self))

    def Migrate(self, bridge):
        if bridge is self.Bridge:
            return

        if self.Bridge is not None:
            self.Bridge.unbind('BridgeOpened', self.BridgeOpened)
            self.Bridge.unbind('BridgeSynced', self.BridgeSynced)
            self.Bridge.unbind('BridgeClosed', self.BridgeClosed)
            self.Bridge.unbind('BridgeSent', self.BridgeSent)

            self.Bridge.StopSending(self)
            self.Bridge.MigrateQueue(self, bridge)

        self.Bridge = bridge

        if self.Bridge is not None:
            self.Bridge.bind('BridgeOpened', self.BridgeOpened)
            self.Bridge.bind('BridgeSynced', self.BridgeSynced)
            self.Bridge.bind('BridgeClosed', self.BridgeClosed)
            self.Bridge.bind('BridgeSent', self.BridgeSent)
            self.LocalIdentifier = self.LocalBaseIdentifier = bridge.localTrackerId

            if self.directNegotiationTimer is not None and self.Bridge is not self.protocol.ns.SDGBridge:
                self.DirectNegotiationSuccessful()

    def BridgeOpened(self):
        log.info("Bridge opened: %r", self.Bridge)
        if self.Bridge is self.Remote.DirectBridge:
            self.DirectNegotiationSuccessful()

        if self.Bridge.Ready(self) and self.App is not None:
            self.App.BridgeIsReady()

    def BridgeSynced(self):
        self.LocalIdentifier = self.LocalBaseIdentifier = self.Bridge.SyncId

        if self.Bridge.Ready(self) and self.App is not None:
            self.App.BridgeIsReady()

    def BridgeClosed(self):
        buddy = self.protocol.get_buddy(self.Remote.account)
        if buddy.status == 'offline':
            self.OnClosed(self.Remote)
        else:
            self.MigrateToOptimalBridge()

    def BridgeSent(self, session, message):
        if self.Bridge is None:
            self.MigrateToOptimalBridge()

        if self.Bridge.Ready(self) and self.App is not None:
            self.App.BridgeIsReady()

    def NextLocalIdentifier(self, correction):
        if self.Version == P2P.Version.V1:
            self.IncreaseLocalIdentifier()
            return self.LocalIdentifier
        else:
            self.LocalIdentifier += correction
            return (self.LocalIdentifier - correction)

    def CorrectLocalIdentifier(self, correction):
        self.LocalIdentifier += correction

    def IncreaseLocalIdentifier(self):
        self.LocalIdentifier += 1
        if self.LocalIdentifier == self.LocalBaseIdentifier:
            self.LocalIdentifier += 1

    def IncreaseRemoteIdentifier(self):
        self.RemoteIdentifier += 1
        if self.RemoteIdentifier == self.RemoteBaseIdentifier:
            self.RemoteIdentifier += 1

def ProcessDirectInvite(slp, protocol, session):
    protocol = getattr(protocol, 'ns', protocol)

    if common.pref('msn.p2p.allow_direct', type = bool, default = True):

        try:
            if slp.ContentType == 'application/x-msnmsgr-transreqbody':
                return ProcessDCReqInvite(slp, protocol, session)
            elif slp.ContentType == 'application/x-msnmsgr-transrespbody':
                return ProcessDCRespInvite(slp, protocol, session)
            elif slp.ContentType == 'application/x-msnmsgr-transdestaddrupdate':
                return ProcessDirectAddrUpdate(slp, protocol, session)
        except Exception:
            import traceback; traceback.print_exc()

    if session is None:
        session = P2PSession(slp = slp, msg = None, ns = protocol)
    log.info("Sending 603 for Direct Invite")
    session.Decline()

def ProcessDCReqInvite(message, ns, session):
    if session is not None and session.Bridge is not None and session.Bridge.BridgeType == 'TCPv1':
        return

    if 'TCPv1' not in message.BodyValues.get('Bridges', message.BodyValues.get('Bridge', '')):
        if session is not None:
            session.DirectNegotiationFailed()
        return

    remoteGuid = message.FromEndPoint
    remote = ns.contact_list.GetContact(message.FromEmailAccount, MSNAB.IMAddressInfoType.WindowsLive)

    dcNonceType, remoteNonce = ParseDCNonce(message.BodyValues)
    if remoteNonce == uuid.UUID(int = 0):
        remoteNonce = remote.dcPlainKey

    hashed = dcNonceType == DCNonceType.Sha1
    nonceFieldName = 'Hashed-Nonce' if hashed else 'Nonce'
    myHashedNonce = remote.dcLocalHashedNonce if hashed else remoteNonce
    myPlainNonce = remote.dcPlainKey

    if dcNonceType == DCNonceType.Sha1:
        remote.dcType = dcNonceType
        remote.dcRemoteHashedNonce = remoteNonce

    else:
        remote.dcType = DCNonceType.Plain
        myPlainNonce = remote.dcPlainKey = remote.dcLocalHashedNonce = remote.dcRemoteHashedNonce = remoteNonce

    ipAddress = util.ip_from_bytes(util.myip())
    port = 0

    if (message.FromEndPoint != uuid.UUID(int=0) and message.ToEndPoint != uuid.UUID(int=0)):
        ver = P2P.Version.V2
    else:
        ver = P2P.Version.V1

    try:
        remote.DirectBridge = ListenForDirectConnection(remote, remoteGuid, ns, ver, session, ipAddress, port, myPlainNonce, remoteNonce, hashed)
    except Exception as e:
        import traceback; traceback.print_exc()
        log.error("Error setting up direct bridge: %r", e)
        port = 0
    else:
        port = remote.DirectBridge.LocalEndPoint[1]

    slp = MSNSLP.SLPStatusMessage(message.Source, 200, 'OK')
    slp.Target = message.Source
    slp.Source = message.Target
    slp.Branch = message.Branch
    slp.CSeq = 1
    slp.CallId = message.CallId
    slp.MaxForwards = 0
    slp.ContentType = 'application/x-msnmsgr-transrespbody'
    slp.BodyValues['Bridge'] = 'TCPv1'

    log.info("port = %r, ipaddress = %r, protocol.ip == %r, other_listening = %r", port, ipAddress, ns.protocol.ip, message.BodyValues.get("Listening", None))
    if port == 0 and message.BodyValues.get("Listening", None) != "false":
        slp.BodyValues['Listening'] = 'false'
        slp.BodyValues[nonceFieldName] = '{%s}' % str(uuid.UUID(int = 0))

    else:
        slp.BodyValues['Listening'] = 'true'
        slp.BodyValues['Capabilities-Flags'] = '1'
        slp.BodyValues['IPv6-global'] = ''
        slp.BodyValues['Nat-Trav-Msg-Type'] = 'WLX-Nat-Trav-Msg-Direct-Connect-Resp'
        slp.BodyValues['UPnPNat'] = 'false'

        slp.BodyValues['NeedConnectingEndpointInfo'] = 'true'
        slp.BodyValues['Conn-Type'] = 'Direct-Connect'
        slp.BodyValues['TCP-Conn-Type'] = 'Direct-Connect'

        slp.BodyValues[nonceFieldName] = '{%s}' % str(myHashedNonce).upper()
        slp.BodyValues['IPv4Internal-Addrs'] = ipAddress
        slp.BodyValues['IPv4Internal-Port'] = str(port)

        if ipAddress != ns.protocol.ip:
            slp.BodyValues['IPv4External-Addrs'] = ns.protocol.ip
            slp.BodyValues['IPv4External-Port'] = str(port)

    p2pmessage = P2PMessage.P2PMessage(ver)
    p2pmessage.InnerMessage = slp

    if ver == P2P.Version.V2:
        p2pmessage.Header.TFCombination = P2P.TFCombination.First
    else:
        p2pmessage.Header.Flags = P2P.Flags.MSNSLPInfo

    if session is not None:
        session.ResetDCTimer()
        session.Bridge.Send(None, session.Remote, session.RemoteContactID, p2pmessage)
        session.Bridge.StopSending(session)
    else:
        ns.SDGBridge.Send(None, remote, remoteGuid, p2pmessage)

def ProcessDCRespInvite(message, ns, session):
    body = message.BodyValues
    if body.get('Bridge', None) == 'TCPv1' and body.get('Listening', 'false').lower() == 'true':
        remote = ns.contact_list.GetContact(message.FromEmailAccount, MSNAB.IMAddressInfoType.WindowsLive)
        remoteGuid = message.FromEndPoint

        dcNonceType, remoteNonce = ParseDCNonce(body)
        hashed = dcNonceType == DCNonceType.Sha1
        replyGuid = remote.dcPlainKey if hashed else remoteNonce

        selectedPoints = SelectIPEndPoints(body, ns)
        log.info("SelectedPoints = %r", selectedPoints)

        if selectedPoints is None or len(selectedPoints) == 0:
            if session is not None:
                session.DirectNegotiationFailed()
            return

        if uuid.UUID(int = 0) in (message.FromEndPoint, message.ToEndPoint):
            version1 = True
            ver = P2P.Version.V1
        else:
            version2 = True
            ver = P2P.Version.V2

        remote.DirectBridge = CreateDirectConnection(remote, remoteGuid, ver, selectedPoints, replyGuid, remoteNonce, hashed, ns, session)

        needConnectingEndpointInfo = body.get('NeedConnectingEndpointInfo', 'false') == 'true'

        if needConnectingEndpointInfo:
            ipep = remote.DirectBridge.LocalEndPoint # Host, port
            if ipep is not None:
                port = ipep[-1]
            else:
                log.info("Not sending my address info to other client")
                return

            ips = map(util.ip_from_bytes, util.myips())
#            if ns.protocol.ip not in ips:
#                ips.append(ns.protocol.ip)

            hkey = 'IPv4InternalAddrsAndPorts'[::-1]
            hval = ' '.join(('%s:%s' % (ip, port) for ip in ips))[::-1]

            slp = MSNSLP.SLPRequestMessage(message.Source, MSNSLP.RequestMethod.ACK)
            slp.Source = message.Target
            slp.Via = message.Via
            slp.CSeq = 0
            slp.CallId = str(uuid.UUID(int=0))
            slp.MaxForards = 9
            slp.ContentType = 'application/x-msnmsgr-transdestaddrupdate'
            slp.BodyValues[hkey] = hval
            slp.BodyValues['Nat-Trav-Msg-Type'] = "WLX-Nat-Trav-Msg-Updated-Connecting-Port"

            msg = P2PMessage.P2PMessage(ver)
            msg.InnerMessage = slp
            Bridge = ns.SDGBridge
            Bridge.Send(None, remote, remoteGuid, msg)
    else:
        log.info("Sending transrespbody through transreqbody handler...")
        return ProcessDCReqInvite(message, ns, session)

def ProcessDirectAddrUpdate(msg, ns, session):
    import msn.AddressBook as MSNAB
    sender = ns.contact_list.GetContact(msg.FromEmailAccount, MSNAB.IMAddressInfoType.WindowsLive)
    ipeps = SelectIPEndPoints(msg.BodyValues, ns)
    if sender.DirectBridge is not None and ipeps:
        sender.DirectBridge.OnDestinationAddressUpdated(ipeps)

def ParseDCNonce(bodyValues):
    dcNonceType = DCNonceType.NONE
    nonce = uuid.UUID(int = 0)

    if 'Hashed-Nonce' in bodyValues:
        hnonce = bodyValues.get('Hashed-Nonce')
        #log.info("Got hashed-nonce from message: %r", hnonce)
        nonce = uuid.UUID(hnonce)
        dcNonceType = DCNonceType.Sha1

    elif 'Nonce' in bodyValues:
        _nonce = bodyValues.get('Nonce')
        #log.info("Got nonce from message: %r", _nonce)
        nonce = uuid.UUID(_nonce)
        dcNonceType = DCNonceType.Plain
    else:
        log.warning("Didn't get any nonce from message")

    return dcNonceType, nonce

def ListenForDirectConnection(remote, remoteGuid, ns, ver, session, host, port, replyGuid, remoteNonce, hashed):
    log.info("ListenForDirectConnection(remote = %r, ns = %r, ver = %r, session = %r, host = %r, port = %r, replyGuid = %r, remoteNonce = %r, hashed = %r)",
             remote, ns, ver, session, host, port, replyGuid, remoteNonce, hashed)

    import msn.P2P.TCPBridge as TCPBridge
    tcpBridge = TCPBridge.TCPBridge(ver, replyGuid, remoteNonce, hashed, session, ns, remote, remoteGuid)
    tcpBridge.Listen((host, port))
    return tcpBridge

def CreateDirectConnection(remote, remoteGuid, ver, endpoints, replyGuid, remoteNonce, hashed, ns, session):
    log.info("CreateDirectConnection(remote = %r, ver = %r, endpoints = %r, replyGuid = %r, remoteNonce = %r, hashed = %r, ns = %r, session = %r)",
             remote, ver, endpoints, replyGuid, remoteNonce, hashed, ns, session)

    import msn.P2P.TCPBridge as TCPBridge
    tcpBridge = TCPBridge.TCPBridge(ver, replyGuid, remoteNonce, hashed, session, ns, remote, remoteGuid)
    tcpBridge.Connect(endpoints)
    return tcpBridge

def SelectIPEndPoints(body, ns):
    external = _SelectSomeIPEndPoints(body, ns, 'External')
    internal = _SelectSomeIPEndPoints(body, ns, 'Internal')

    return internal + external

def _SelectSomeIPEndPoints(body, ns, whence):
    endpoints = []
    Addrs = 'IPv4%s-Addrs' % whence
    Ports = 'IPv4%s-Port' % whence
    AddrsAndPorts = 'IPv4%sAddrsAndPorts' % whence

    addrs = body.get(Addrs, '').split()
    ports = [int(body.get(Ports, '0'))]

    #log.info("Forward addrs, ports = (%r, %r)", addrs, ports)

    def JoinAddrPortList(addrs, ports):
        result = []
        for i, addr in enumerate(addrs):
            if i < len(ports):
                port = ports[i]
            if port > 0:
                result.append((addr, port))
        return result

    endpoints.extend(JoinAddrPortList(addrs, ports))

    addrsAndPorts = filter(None, body.get(AddrsAndPorts, '').split(' '))
    #log.info("Forward AddrsAndPorts = %r", addrsAndPorts)
    for addrport in addrsAndPorts:
        addr, port = addrpoort.split(':')
        port = int(port)
        endpoints.append((addr, port))

    # weird reversed things
    addrs = map(lambda x: x[::-1], body.get(Addrs[::-1], '').split())
    ports = map(lambda x: int(x[::-1]), body.get(Ports[::-1], '').split())

    #log.info("Reversed addrs, ports = (%r, %r)", addrs, ports)
    endpoints.extend(JoinAddrPortList(addrs, ports))

    addrsAndPorts = map(lambda x: x[::-1], filter(None, body.get(AddrsAndPorts[::-1], '').split()))
    #log.info("Reverse AddrsAndPorts = %r", addrsAndPorts)
    for addrport in addrsAndPorts:
        addr, port = addrport.split(':')
        port = int(port)
        endpoints.append((addr, port))

    log.info("Endpoints = %r", endpoints)
    return endpoints

