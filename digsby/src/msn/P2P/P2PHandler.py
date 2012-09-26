import logging; _log = log = logging.getLogger('msn.p2p.handler')
log.setLevel(11)
import path
import util.Events as Events
import util.callbacks as callbacks

import msn
import msn.P2P as P2P
import msn.P2P.P2PMessagePool as P2PMessagePool
import msn.P2P.P2PSession as P2PSession
import msn.P2P.MSNSLPMessages as MSNSLP

class P2PHandler(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'InvitationReceived',
    ))

    def OnInvitationReceived(self, session):
        self.event('InvitationReceived', self, session)

    def __init__(self, nsMessageHandler):
        self.protocol = self.nsMessageHandler = nsMessageHandler

        self.slpMessagePool = P2PMessagePool.P2PMessagePool()
        self.bridges = []
        self.v1sessions = []
        self.v2sessions = []
        self.v1ackHandlers = {}
        self.v2ackHandlers = {}

    @callbacks.callsback
    def RequestMsnObject(self, contact, msnobj, callback = None):
        if isinstance(contact, msn.buddy):
            contact = contact.contact
        import msn.P2P.P2PObjectTransfer as OT
        if msnobj is None:
            return callback.error()

        objtrans = OT.ObjectTransfer(obj = msnobj, remote = contact)

        objtrans.bind_event('TransferFinished', callback.success)
        objtrans.bind_event('TransferAborted', callback.error)
        objtrans.bind_event('TransferError', callback.error)

        self.AddTransfer(objtrans)
        return objtrans

    def SendFile(self, contact, filename, file):
        import msn.P2P.P2PFileTransfer as FT
        filetrans = FT.FileTransfer(contact = contact, fileobj = file, filename = path.path(filename))
        self.AddTransfer(filetrans)
        return filetrans

    def AddTransfer(self, app):
        session = P2PSession.P2PSession(app = app)
        session.bind('Closed', self.P2PSessionClosed)
        session.bind('Messages', self.P2PSessionMessages)

        if app.Version == P2P.Version.V2:
            self.v2sessions.append(session)
        else:
            self.v1sessions.append(session)

        session.Invite()
        return session

    def ProcessP2PMessage(self, bridge, source, sourceGuid, message):
        #_log.info("Got P2PMessage: bridge = %r, source = %r, sourceGuid = %r, message = %r", bridge, source, sourceGuid, message)
        requireAck = self.HandleRAK(bridge, source, sourceGuid, message)
        incomplete, message = self.slpMessagePool.BufferMessage(message)
        if incomplete and not message.Header.IsAck:
            #_log.info("Message not complete yet, buffered")
            return

        slp = None
        if message.IsSLPData:
            slp = message.InnerMessage
            if slp is None:
                assert message.InnerBody == '\0'*4
                log.info("Got Data prep message")
                return

            #_log.info("It's a slp message")
            if not self.CheckSLPMessage(bridge, source, sourceGuid, message, slp):
                log.info("invalid slp message")
                return

        else:
            #_log.error("non-slp message: header = %r", message.Header)
            pass

        if self.HandleAck(message):
            #_log.info("Message acked")
            return

        session = self.FindSession(message, slp)
        #_log.info("Got session for slp message: %r", session)
        if session is not None and session.ProcessP2PMessage(bridge, message, slp):
            #_log.info("Session processed message: %r / %r", message, slp)
            return
        elif session is not None:
            log.error("Session rejected message: %r", message)

        if slp is not None:
            if self.ProcessSLPMessage(bridge, source, sourceGuid, message, slp):
                log.info("Created new session based on SLP message")
                return
        elif session is None:
            log.info("Non-SLP message had no session to go to: %r", message)

        if not requireAck:
            log.error("Message was not processed")

    def Cleanup(self):
        del self.slpMessagePool, self.v1sessions, self.v2sessions, self.bridges, self.v1ackHandlers, self.v2ackHandlers
    Dispose = Cleanup

    def RegisterAckHandler(self, msg, handler):
        if msg.Version == P2P.Version.V2:
            ident = msg.Header.Identifier + msg.Header.MessageSize

            if msg.SetRAK():
                if ident in self.v2ackHandlers:
                    log.debug("Merging ack handler for ID = %r (Identifier = %r, MessageSize = %r, TotalSize = %r)", ident, msg.Header.Identifier, msg.Header.MessageSize, msg.Header.TotalSize)
                    self.v2ackHandlers[ident][0].append(msg)
                    old_handler = self.v2ackHandlers[ident][1]
                    old_handler.success += handler.success
                    old_handler.error += handler.error
                    old_handler.progress += handler.progress
                    old_handler.after_send += handler.after_send
                    log.debug("\tHandler = %r", old_handler)
                else:
                    log.debug("Setting ack handler for ID = %r (Identifier = %r, MessageSize = %r, TotalSize = %r)", ident, msg.Header.Identifier, msg.Header.MessageSize, msg.Header.TotalSize)
                    log.debug("\tHandler = %r", handler)
                    self.v2ackHandlers[ident] = [msg], handler

            else:
                log.error("Could not set ack handler for msg = %r", msg)
        elif msg.Version == P2P.Version.V1:
            ident = msg.Header.AckSessionId
            self.v1ackHandlers[msg.Header.AckSessionId] = [msg], handler

    def GetBridge(self, session):
        for bridge in self.bridges:
            if bridge.SuitableFor(session):
                break

        return self.protocol.SDGBridge

    def BridgeClosed(self, bridge):
        if bridge not in self.bridges:
            return

        self.bridges.remove(bridge)

    def HandleAck(self, message):
        isAckOrNak = False

        if message.Header.IsAck or message.Header.IsNak:
            ackNakId = 0
            isAckOrNak = True
            if message.Version == P2P.Version.V1:
                handlers = self.v1ackHandlers
                if message.Header.AckIdentifier in handlers:
                    ackNakId = message.Header.AckIdentifier
                    msgs, handler = handlers.pop(ackNakId, (None, None))
            elif message.Version == P2P.Version.V2:
                handlers = self.v2ackHandlers
                msgs = []
                if message.Header.AckIdentifier in handlers:
                    ackNakId = message.Header.AckIdentifier
                    msgs, handler = handlers.pop(ackNakId, (None, None))
                elif message.VHeader.NakIdentifier in handlers:
                    ackNakId = message.VHeader.NakIdentifier
                    msgs, handler = handlers.pop(ackNakId, (None, None))

                if msgs:
                    new_msgs = msgs[1:]

                    if new_msgs:
                        handlers[ackNakId] = new_msgs, handler

            if ackNakId != 0:
                log.debug("Got ack for message id = %r: %r", ackNakId, msgs)
                if handler is not None:
                    log.debug('\tcalling handler %r', handler)
                    handler.success(message)
            else:
                log.warning("Couldn't find message this ack is for: %r. pending ack ids are %r. message = %r", message.Header.AckIdentifier, handlers.keys(), message)

        return isAckOrNak

    def HandleRAK(self, bridge, source, sourceGuid, msg):
        if not msg.Header.RequireAck:
            return False
        log.debug("Acking message: %r", msg)
        ack = msg.CreateAck()
        ack.Header.Identifier = bridge.localTrackerId
        if ack.Header.RequireAck:
            def success(sync):
                log.debug("Sent ack for SYN")
                bridge.SyncId = sync.Header.AckIdentifier

            bridge.Send(None, source, sourceGuid, ack, success = success)
        else:
            bridge.Send(None, source, sourceGuid, ack)

        return True

    def FindSession(self, msg, slp):
        sessionId = msg.Header.SessionId
        if sessionId == 0 and slp is not None:
            if 'SessionID' in slp.BodyValues:
                try:
                    sessionId = int(slp.BodyValues['SessionID'])
                except:
                    sessionId = 0

            if sessionId == 0:
                if msg.Version == P2P.Version.V2:
                    sessions = self.v2sessions
                else:
                    sessions = self.v1sessions

                for session in sessions:
                    if session.Invitation.CallId == slp.CallId:
                        return session

        if sessionId == 0 and msg.Header.Identifier:
            if msg.Version == P2P.Version.V2:
                for session in self.v2sessions:
                    expected = session.RemoteIdentifier
                    if msg.Header.Identifier == expected:
                        return session
            else:
                for session in self.v1sessions:
                    expected = session.RemoteIdentifier + 1
                    if expected == session.RemoteBaseIdentifier:
                        expected += 1

                    if msg.Header.Identifier == expected:
                        return session

        if sessionId != 0:
            sessions = self.v1sessions if msg.Version == P2P.Version.V1 else self.v2sessions
            for session in sessions:
                if session.SessionId == sessionId:
                    return session

        return None

    def P2PSessionClosed(self, session, contact):
        session.unbind('Closed', self.P2PSessionClosed)
        session.unbind('Messages', self.P2PSessionMessages)
        if session.Version == P2P.Version.V2:
            if getattr(self, 'v2sessions'):
                self.v2sessions.remove(session)
        else:
            if getattr(self, 'v1sessions'):
                self.v1sessions.remove(session)

        session.Dispose()
        self.P2PSession = None

    def P2PSessionMessages(self, session):
        try:
            session.MigrateToOptimalBridge()
            session.AttemptBridgeSend()
        except Exception as e:
            import traceback; traceback.print_exc()
            session.OnError()

    def CheckSLPMessage(self, bridge, source, sourceGuid, msg, slp):
        src = source.account.lower()
        # target = self.protocol.ns.contact_list.owner.account.lower()
        target = self.protocol.self_buddy.name

        if msg.Version == P2P.Version.V2:
            src += ';{' + str(sourceGuid).lower() + '}'
            target += ';{' + str(self.protocol.get_machine_guid()).lower() + '}'

        if slp.Source.lower() != src:
            log.info("Source doesn't match: %r != %r", slp.Source.lower(), src)
            return False

        elif slp.Target.lower() != target:
            if slp.Source == target:
                log.info("Got a message from ourselves")
            else:
                log.info("Got a message addressed to someone else (%r != %r)", slp.Target.lower(), target)
                self.SendSLPStatus(bridge, msg, source, sourceGuid, 404, "Not Found")

            return False

        #_log.debug("SLP Message is valid")
        return True

    def ProcessSLPMessage(self, bridge, source, sourceGuid, msg, slp):
        if getattr(slp, 'Method', None) == 'INVITE' and slp.ContentType == 'application/x-msnmsgr-sessionreqbody':

            if msg.Version == P2P.Version.V2:
                sessions = self.v2sessions
            else:
                sessions = self.v1sessions

            for session in sessions:
                if session.Invitation.CallId == slp.CallId:
                    break
            else:
                session = P2PSession.P2PSession(slp, msg, self.protocol, bridge)
                log.info("Session created")
                session.bind("Closed", self.P2PSessionClosed)
                session.bind('Messages', self.P2PSessionMessages)
                sessions.append(session)

            return True
        return False

    def SendSLPStatus(self, bridge, msg, dest, destGuid, code, phrase):
        target = dest.name.lower()
        if msg.Version == P2P.Version.V2:
            target += ';{' + str(destGuid).lower() + '}'

        slp = MSNSLP.SLPStatusMessage(target, code, phrase)
        if msg.IsSLPData:
            msgSLP = SLPMessage.Parse(msg.InnerMessage)
            slp.Branch = msgSLP.Branch
            slp.Source = msgSLP.Target
            slp.CallId = msgSLP.CallId
            slp.ContentType = msgSLP.ContentType
        else:
            slp.ContentType = 'null'

        response = P2PMessage(msg.Version)
        response.InnerMessage = slp

        if msg.Version == P2P.Version.V1:
            response.VHeader.Flags = P2P.Flags.MSNSLPInfo
        else:
            response.VHeader.OperationCode = P2P.OperationCode.NONE
            response.VHeader.TFCombination = P2P.TFCombination.First

        bridge.Send(None, dest, destGuid, response, None)
