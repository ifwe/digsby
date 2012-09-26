import sys

import logging
_log = log = logging.getLogger('msn.p2p.bridge')

import msn.P2P as P2P
import msn.P2P.P2PSendQueue as P2PSendQueue

import util.Events as Events
import util.primitives.funcs as funcs
import util.callbacks as callbacks

def randid():
    import random
    return random.randint(5000, sys.maxint//2)

class P2PBridge(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'BridgeOpened',
        'BridgeSynced',
        'BridgeClosed',
        'BridgeSent',
    ))

    bridgeCount = 0
    syncIdentifier = 0
    bridgeID = 0
    queueSize = 0
    packageNumber = 0

    IsOpen = funcs.iproperty('_get_IsOpen')
    MaxDataSize = funcs.iproperty('_get_MaxDataSize')
    Remote = funcs.iproperty('_get_Remote')

    def _get_Synced(self):
        return self.SyncId != 0

    Synced = funcs.iproperty('_get_Synced')

    def _get_SyncId(self):
        return self.syncIdentifier
    def _set_SyncId(self, value):
        if value != self.syncIdentifier:
            self.syncIdentifier = value
            if value != 0:
                self.OnBridgeSynced()

    SyncId = funcs.iproperty('_get_SyncId', '_set_SyncId')

    def _get_SyncQueues(self):
        return self.sendQueues

    SendQueues = funcs.iproperty('_get_SyncQueues')

    def __init__(self, queueSize):
        self.localTrackerId = randid()
        Events.EventMixin.__init__(self)
        type(self).bridgeCount += 1
        self.bridgeID = self.bridgeCount

        self.queueSize = queueSize

        self.sendQueues = {}
        self.sendingQueues = {}
        self.stoppedSessions = []

    def IncrementPackageNumber(self):
        self.packageNumber += 1
        return self.packageNumber

    def Dispose(self):
        self.sendQueues.clear()
        self.sendingQueues.clear()
        self.stoppedSessions.Clear()

    def SuitableFor(self, session):
        remote = self.Remote
        return session is not None and remote is not None and session.Remote.account == remote.account

    def Ready(self, session):
        if not self.IsOpen:
            return False
        if session in self.stoppedSessions:
            return False

        if self.queueSize == 0:
            return True

        if session not in self.sendingQueues:
            return self.SuitableFor(session)

        ready = len(self.sendingQueues[session]) < self.queueSize
        #log.debug("Queue status %r/%r", len(self.sendingQueues[session]), self.queueSize)
        if not ready:
            log.info("Queue is full!")

        return ready

    def Send(self, session, remote, remoteGuid, msg, callback = None, **kw):
        if remote is None:
            raise Exception()

        msg1 = self.SetSequenceNumberAndRegisterAck(session, remote, msg, callback)
        if msg1 is None:
            log.info("Message was finished already, not sending: %r", msg)
            callback.after_send()
            self.ProcessSendQueues()
            return

        if session is None:
            if not self.IsOpen:
                log.error("Send called with no session on a closed bridge: %r", self)
                return

            if msg1 is not None:
                self.SendOnePacket(None, remote, remoteGuid, msg1, after_send = callback.after_send)

            return

        if not self.SuitableFor(session):
            log.error("Send called with a session this bridge is not suitable for: %r", self)
            return

        if session not in self.sendQueues:
            self.sendQueues[session] = P2PSendQueue.P2PSendQueue()

        if msg1 is not None:
            self.sendQueues[session].Enqueue(remote, remoteGuid, msg1, callback)

#        self.sendQueues[session].Enqueue(remote, remoteGuid, msg)
        self.ProcessSendQueues()
    Send = callbacks.callsback(Send, ('success', 'error', 'after_send', 'progress'))

    def SetSequenceNumberAndRegisterAck(self, session, remote, message, callback):
        version1 = message.Version == P2P.Version.V1
        version2 = message.Version == P2P.Version.V2
        if message.Header.Identifier == 0:
            if session is None:
                message.Header.Identifier = self.localTrackerId
                if version1:
                    self.localTrackerId += 1
                    message.Header.Identifier = self.localTrackerId
                elif version2:
                    message.Header.Identifier = self.localTrackerId
            else:
                self.localTrackerId = message.Header.Identifier = session.NextLocalIdentifier(message.Header.MessageSize)

        if version1 and message.Header.AckSessionId == 0:
            message.Header.AckSessionId = randid()
        elif version2 and message.Header.PackageNumber == 0:
            message.Header.PackageNumber = self.packageNumber

        if message.IsFinished():
            return None

        firstMessage, firstCallback = message.GetNextMessage(self.MaxDataSize)

        if firstMessage is None:
            assert message.IsFinished()
            firstMessage = message
            firstCallback = callback
        else:
            for key in firstCallback:
                cb_type = getattr(callback, key, None)
                if cb_type is not None:
                    cb_type += firstCallback[key]

#        if version2:
            #self.localTrackerId = message.Header.Identifier + message.Header.TotalSize
            #self.localTrackerId = session.NextLocalIdentifier(message.Header.TotalSize)
        self.localTrackerId = message.Header.Identifier

        if remote.client.self_buddy.protocol.P2PHandler is not None:
            remote.client.self_buddy.protocol.P2PHandler.RegisterAckHandler(firstMessage, callback)
        else:
            callback.error("Connection shutting down!")
            self.Dispose()

        return firstMessage

    def ProcessSendQueues(self):
        to_send = []
        #_log.debug("ProcessSendQueues:")
        for session, queue in self.sendQueues.items():
            #_log.debug("\tSession = %r", session)
            #_log.debug("\tQueue = %r", queue)
            #_log.debug('\tlen(queue) = %r', len(queue))

            spin_check = 10
            while self.Ready(session) and len(queue) and spin_check:
                item = queue.Dequeue()
                #_log.debug("\titem = %r", item)
                if item is None:
                    spin_check -= 1
                    continue
                spin_check = 10

                if session not in self.sendingQueues:
                    self.sendingQueues[session] = P2PSendQueue.P2PSendList()

                self.sendingQueues[session].append(item)
                to_send.append((session, item.Remote, item.RemoteGuid, item.p2pMessage, item.callback))

        for args in to_send:

            self.SendOnePacket(*args[:-1], callback = args[-1])

        moreQueued = False

        for session, queue in self.sendQueues.items():
            if len(queue):
                moreQueued = True
                break

        if not moreQueued:
            #log.debug("All queues empty")
            pass

    def SendOnePacket(self, session, remote, remoteGuid, msg, callback = None):
        raise NotImplementedError

    def StopSending(self, session):
        if session not in self.stoppedSessions:
            self.stoppedSessions.append(session)

        else:
            log.debug("Session already stopped: %r", session)

    def ResumeSending(self, session):
        if session in self.stoppedSessions:
            self.stoppedSessions.remove(session)
            self.ProcessSendQueues()

        else:
            log.debug("Session is not stopped: %r", session)

    def MigrateQueue(self, session, newBridge):
        newQueue = P2PSendQueue.P2PSendQueue()

        if session in self.sendingQueues:
            if newBridge is not None:
                for item in self.sendingQueues[session]:
                    newQueue.Enqueue(item)

            self.sendingQueues.pop(session, None)

        if session in self.sendQueues:
            if newBridge is not None:
                while len(self.sendQueues[session]):
                    newQueue.Enqueue(self.sendQueues[session].Dequeue())

            self.sendQueues.pop(session, None)

        if session in self.stoppedSessions:
            self.stoppedSessions.remove(session)

        if newBridge is not None:
            newBridge.AddQueue(session, newQueue)

    def AddQueue(self, session, queue):
        if session in self.sendQueues:
            while len(queue):
                self.sendQueues[session].Enqueue(queue.Dequeue())

        else:
            self.sendQueues[session] = queue

        self.ProcessSendQueues()

    def OnBridgeOpened(self):
        self.event('BridgeOpened')
        self.ProcessSendQueues()

    def OnBridgeSynced(self):
        self.event('BridgeSynced')

    def OnBridgeClosed(self):
        self.event('BridgeClosed')

    def OnBridgeSent(self, session, message):
        version1 = message.Version == P2P.Version.V1
        version2 = message.Version == P2P.Version.V2

        if message.Header.Identifier != 0:
            self.localTrackerId = (message.Header.Identifier + 1) if version1 else (message.Header.Identifier + message.Header.MessageSize)

        #_log.info("OnBridgeSent: %r, %r", session, message)
        if session is not None and session in self.sendingQueues:
            if message in self.sendingQueues[session]:
                #_log.info("\tSession in queue and message in session queue")
                try:
                    self.sendingQueues[session].remove(message)
                except ValueError as e:
                    #_log.info("\terror removing! %r", e)
                    pass

        self.event('BridgeSent', session, message)
        self.ProcessSendQueues()
