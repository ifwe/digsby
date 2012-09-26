import logging
log = logging.getLogger('msn.p2p.file')
import path
import hashlib
import struct
import sys
import io
import random
import uuid
import time
import msn.P2P as P2P
import msn.P2P.P2PApplication as P2PApp
import msn.P2P.P2PMessage as P2PMessage

import util.packable as packable
import common.filetransfer as FT

@P2PApp.P2PApplication.RegisterApplication
class FileTransfer(P2PApp.P2PApplication, FT.FileTransfer):
    AppId = 2
    EufGuid = uuid.UUID("5D3E02AB-6190-11D3-BBBB-00C04F795683")
    context = None
    dataStream = None
    sending = False
    sendingData = False
    packNum = 0

    numfiles = 1

    @property
    def Context(self):
        return self.context
    @property
    def DataStream(self):
        return self.dataStream
    @property
    def Sending(self):
        return self.sending
    @property
    def Transferred(self):
        return self.completed
    @property
    def InvitationContext(self):
        return self.context.GetBytes().encode('b64')

    @property
    def size(self):
        return self.context.filesize

    def __init__(self, session = None, contact = None, fileobj = None, filename = None):

        if session is None:
            P2PApp.P2PApplication.__init__(self, ver = contact.P2PVersionSupported, remote = contact, remoteEP = contact.SelectBestEndPointId())
            self.sending = True
            self.direction = 'outgoing'
            self.dataStream = fileobj or filename.open('rb')
            self.context = FTContext(filename, filename.size)
            self.filepath = filename

        else:
            P2PApp.P2PApplication.__init__(self, session = session)
            self.sending = False
            self.direction = 'incoming'
            self.context = FTContext.parse(session.Invitation.BodyValues['Context'].decode('b64'))
            self.dataStream = None

        self.name = self.context.filename
        # way gross violation of encapsulation
        self.buddy = self.Remote.client.protocol.get_buddy(self.Remote.account)

        FT.FileTransfer.__init__(self)

    @property
    def protocol(self):
        return self.Remote.client.protocol

    def accept(self, fobj):
        self.state = self.states.CONNECTING
        self.filepath = path.path(fobj.name)
        self.dataStream = fobj
        self.P2PSession.Accept(True)

    def Dispose(self):
        if self.dataStream is not None:
            self.dataStream.close()
        super(FileTransfer, self).Dispose()

    def OnProgressed(self, stream_position):
        self._setcompleted(stream_position)

    def SetupInviteMessage(self, slp):
        slp.BodyValues['RequestFlags'] = '16'
        super(FileTransfer, self).SetupInviteMessage(slp)

    def ValidateInvitation(self, invite):
        ret = super(FileTransfer, self).ValidateInvitation(invite)
        try:
            context = FTContext.parse(invite.BodyValues['Context'].decode('b64'))
            return ret and context.filename and context.filesize
        except Exception as e:
            log.error("Couldn't parse context for filetransfer: error = %r, invite = %r", e, invite)
            return False

    def Start(self):
        if self.dataStream is None:
            raise Exception("No open fileobject yet")

        if self.Remote.DirectBridge is None:
            log.warning("Don't have a direct bridge! (Start)")

        if not super(FileTransfer, self).Start():
            if self.status == P2PApp.AppStatus.Active:
                self.SendChunk()
            return False

        log.info("FileTransfer.Start() (FT = %r)", self)
        if self.Sending:
            self.P2PSession.SendDirectInvite()
            self.dataStream.seek(0)
            self.sendingData = True

            self.packNum = self.P2PSession.Bridge.IncrementPackageNumber()
            if self.P2PSession.Bridge.Ready(self.P2PSession):
                log.info("Sending first file chunk")
                self.SendChunk()

    def SendChunk(self):
        if not self.sendingData:
            return

        if self.P2PSession is None:
            log.info("File transfer cancelled!")
            return self.cancel(self.state)

        if self.Remote.DirectBridge is None:
            log.warning("Don't have a direct bridge! (SendChunk)")

        self.P2PSession.ResetTimeoutTimer()

        if self.state != self.states.TRANSFERRING:
            self.state = self.states.TRANSFERRING

        chunk = P2P.P2PMessage.P2PDataMessage(self.version)
        offset = self.dataStream.tell()

        version1 = self.version == P2P.Version.V1
        version2 = self.version == P2P.Version.V2

        if offset == 0:
            if version1:
                self.P2PSession.IncreaseLocalIdentifer()
                chunk.Header.TotalSize = self.context.filesize
            elif version2:
                chunk.Header.TFCombination = P2P.TFCombo.First

#        chunk.Header.Identifier = self.P2PSession.LocalIdentifier
#        chunk.feed(self.dataStream, self.P2PSession.Bridge.MaxDataSize)
#        if version1:
#            chunk.Header.Flags |= P2P.Flag.FileData
#        elif version2:
#            chunk.Header.PackageNumber = self.packNum
#            chunk.Header.TFCombination |= P2P.TFCombo.FileTransfer
#            self.P2PSession.CorrectLocalIdentifier(chunk.Header.MessageSize)

        chunk.feed(self.dataStream, self.P2PSession.Bridge.MaxDataSize)
        chunk.Header.Identifier = self.P2PSession.NextLocalIdentifier(chunk.Header.MessageSize)
        if version1:
            chunk.Header.Flags |= P2P.Flag.FileData
        elif version2:
            chunk.Header.PackageNumber = self.packNum
            chunk.Header.TFCombination |= P2P.TFCombo.FileTransfer
            #self.P2PSession.CorrectLocalIdentifier(chunk.Header.MessageSize)

        def after_send(*a):
            self.OnProgressed(offset)
            self.SendChunk()
        callback = dict(after_send = after_send)

        if self.dataStream.tell() == self.context.filesize:
            log.info("File transfer: all data sent!")
            self.sendingData = False
            # Last chunk!
            self.SendMessage(chunk)

            # Now ask for an ack
            rak = P2P.P2PMessage.P2PMessage(self.version)
            self.SendMessage(rak)

            # All done on our side
            self.OnProgressed(offset)
            self.OnTransferFinished()
            self.Abort()

        else:
            self.SendMessage(chunk, **callback)

#        if self.sendingData:
#            self.SendChunk()

    def BridgeIsReady(self):
        #log.info("Bridge is ready (sending data = %r)", self.sendingData)
        pass

    def ProcessData(self, bridge, data, reset):
        if self.sending:
            return False

        if self.P2PSession is None:
            self.OnTransferError()
            return False

        self.P2PSession.ResetTimeoutTimer()

        if self.state != self.states.TRANSFERRING:
            self.state = self.states.TRANSFERRING

        if reset:
            self.dataStream.truncate(0)

        if hasattr(data, 'getvalue'):
            data = data.getvalue()
            if len(data) > (32 * 1024):
                log.warning("FileTransfer got chunk larger than 32k, re-evaluate buffering (size = %r)", len(data))

        if len(data):
            self.dataStream.write(data)

        self.OnProgressed(self.dataStream.tell())

        log.info("Received %r / %r", self.dataStream.tell(), self.context.filesize)
        if self.dataStream.tell() == self.context.filesize:
            self.OnTransferFinished()
            if self.P2PSession is not None:
                self.P2PSession.Close()

        return True

    def OnTransferFinished(self):
        super(FileTransfer, self).OnTransferFinished()
        self._ondone()

    def OnTransferError(self):
        if self.dataStream is not None:
            self.dataStream.close()
        super(FileTransfer, self).OnTransferError()
        if self.state not in (self.states.FailStates | self.states.CompleteStates):
            self.state = self.states.CONN_FAIL
        self.on_error()

    def OnTransferAborted(self, who):
        if self.state not in self.states.CompleteStates:
            if who is self.Local:
                self.state = self.states.CANCELLED_BY_YOU
            elif who is self.Remote:
                self.state = self.states.CANCELLED_BY_BUDDY

            self._ondone()

        super(FileTransfer, self).OnTransferAborted(who)

    def cancel(self, state = None):
        if getattr(self, 'dataStream', None) is not None:
            self.dataStream.close()

        if self.state == self.states.FINISHED:
            state = self.states.FINISHED

        if state is None:
            state = self.states.CANCELLED_BY_YOU
            self.sendingData = False

        self.state = state

        if state == self.states.BUDDY_GONE:
            self.OnTransferError()
        elif state == self.states.CONN_FAIL:
            self.OnTransferError()
        else:
            log.info("Aborting P2PFileTransfer because: %r", state)
            self.OnTransferError()

        if self.P2PSession is not None:
            self.P2PSession.SendBye()

class FTContext(object):
    def __init__(self, filename, filesize, preview = ''):
        import path
        self.filename = path.path(filename).name
        self.filesize = filesize
        self._preview = preview

    @classmethod
    def parse(cls, data):
        _data = data
        (length, version, filesize, type), data = struct.unpack('<IIQI', data[:20]), data[20:]
        filename = data[:520].decode('utf-16-le').rstrip(u'\0').strip()

        if len(_data) > length:
            preview = data[length:]
        else:
            preview = ''

        return cls(filename, filesize, preview)

    def GetBytes(self):
        version = 2

        if version == 3:
            length = 638 + len(self._preview)
        else:
            length = 574 + len(self._preview)

        data = struct.pack('<IIQI',
                           length,
                           version, # version
                           self.filesize,
                           1, # type
                           )

        data += self.Pad(self.filename.encode('utf-16-le'), 520)
        data += self.Pad('', 30)
        data += '\xff\xff\xff\xff'
        if version == 3:
            data += self.Pad('', 54)

        if self._preview:
            data += self._preview

        return data

    def Pad(self, data, length):
        if len(data) > length:
            return data[:length]
        if len(data) == length:
            return data

        missing = length - len(data)
        return data + ('\0' * missing)
