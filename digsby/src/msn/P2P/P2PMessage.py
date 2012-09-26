import time
import io
import struct
import logging
log = logging.getLogger('msn.p2p.message')
import util.primitives.funcs as funcs
import msn.MSNUtil as MSNU
import msn.P2P as P2P
import msn.P2P.P2PHeader as Header
import msn.P2P.MSNSLPMessages as SLPMessage

class P2PMessage(object):
    Version = P2P.Version.V1
    Header = None
    Footer = 0

    innerMessage = None
    innerBody = None

    nextRak = None
    RAK_WAIT_TIME = 8

    def __repr__(self):
        varstr = ', ' .join('%s=%r' % i for i in sorted(vars(self).items()))
        return '%s(%s)' % (type(self).__name__, varstr)

    @classmethod
    def Copy(cls, message):
        copy = cls(message.Version)
        copy.Header = message.Header.Copy()
        copy.Footer = message.Footer
        copy.InnerBody = message.InnerBody

        return copy

    def __init__(self, version):
        self._gen = None
        self.Finished = False
        self.sendingData = True
        self.Version = version
        if version == P2P.Version.V1:
            self.Header = Header.V1Header()
        elif version == P2P.Version.V2:
            self.Header = Header.V2Header()

    def IsFinished(self):
        return self.Finished

    @property
    def VHeader(self):
        return self.Header

    def _get_InnerBody(self):
        # TODO: make innerbody a file-like object
        return self.innerBody

    def _set_InnerBody(self, value):
        # TODO: make innerbody a file-like object
        self.innerBody = value
        self.innerMessage = None

        if self.Version == P2P.Version.V1:
            self.Header.MessageSize = len(value)
            self.Header.TotalSize = max(self.Header.TotalSize, len(value))

        else:
            if value is not None and len(value):
                self.Header.MessageSize = len(value)
                self.Header.MessageSize += self.Header.DataPacketHeaderLength

                self.Header.TotalSize = max(self.Header.TotalSize, len(value))

            else:
                self.Header.MessageSize = 0
                self.Header.TotalSize = 0

    InnerBody = property(_get_InnerBody, _set_InnerBody)

    def _get_InnerMessage(self):
        if self.innerMessage is None and self.InnerBody is not None and len(self.InnerBody):
            if self.Version == P2P.Version.V1 and self.Header.MessageSize == self.Header.TotalSize:
                self.innerMessage = SLPMessage.SLPMessage.Parse(self.InnerBody)
            elif self.Version == P2P.Version.V2 and self.Header.DataRemaining == 0 and self.Header.TFCombination == P2P.TFCombination.First:
                self.innerMessage = SLPMessage.SLPMessage.Parse(self.InnerBody)

        return self.innerMessage

    def _set_InnerMessage(self, value):
        if hasattr(value, 'GetBytes'):
            self.InnerBody = value.GetBytes()
        else:
            self.InnerBody = str(value)

    InnerMessage = property(_get_InnerMessage, _set_InnerMessage)

    @property
    def IsSLPData(self):
        if self.Header.MessageSize > 0 and self.Header.SessionId == 0:
            if self.Version == P2P.Version.V1:
                if self.Header.Flags in (P2P.Flags.Normal, P2P.Flags.MSNSLPInfo):
                    return True
            elif self.Version == P2P.Version.V2:
                if self.Header.TFCombination in (P2P.TFCombination.NONE, P2P.TFCombination.First):
                    return True

        return False

    def CreateAck(self):
        ack = P2PMessage(self.Version)
        ack.Header = self.Header.CreateAck()
        if self.Version == P2P.Version.V1:
            ack.Footer = self.Footer

        return ack

    def GetNextMessage(self, maxSize):
        if self.sendingData:
            if self._gen is None:
                self._gen = self.SplitMessage(maxSize)
                return self._gen.next()

            try:
                message, callback_dict = self._gen.send(maxSize)
            except StopIteration:
                assert self.Finished
                return None, {}
            else:
                return message, callback_dict
        else:
            return None, {}

    def SplitMessage(self, maxSize):
        # Generator. Yields packets
        payloadMessageSize = 0
        version1 = self.Version == P2P.Version.V1
        version2 = self.Version == P2P.Version.V2

        if version1:
            payloadMessageSize = self.Header.MessageSize
        elif version2:
            payloadMessageSize = self.Header.MessageSize - self.Header.DataPacketHeaderLength

        if payloadMessageSize <= maxSize:
            maxSize = (yield self, {})
            self.Finished = True
            raise StopIteration

        if self.InnerBody is not None:
            totalMessage = self.InnerBody
        else:
            totalMessage = self.InnerMessage.GetBytes()

        if not hasattr(totalMessage, 'seek'):
            messageLen = len(totalMessage)
            totalMessage = io.BytesIO(totalMessage)
        else:
            messageLen = len(totalMessage.getvalue())

        offset = 0
        if version1:
            firstMessage = True
            while offset < messageLen:
                chunkMessage = P2PMessage(self.Version)
                messageSize = min(maxSize, messageLen - offset)
                totalMessage.seek(offset)
                chunk = totalMessage.read(messageSize)

                chunkMessage.Header.Flags           = self.Header.Flags
                chunkMessage.Header.AckIdentifier   = self.Header.AckIdentifier
                chunkMessage.Header.AckTotalSize    = self.Header.AckTotalSize
                chunkMessage.Header.Identifier      = self.Header.Identifier
                chunkMessage.Header.SessionId       = self.Header.SessionId
                chunkMessage.Header.TotalSize       = self.Header.TotalSize
                chunkMessage.Header.Offset          = offset
                chunkMessage.Header.MessageSize     = messageSize
                chunkMessage.InnerBody = chunk

                chunkMessage.Header.AckSessionId = self.Header.AckSessionId
                chunkMessage.Footer = self.Footer

#                chunkMessage.PrepareMessage()

                if firstMessage:
                    firstMessage = False

                maxSize = (yield chunkMessage, {})

                offset += messageSize

        elif version2:
            nextId = self.Header.Identifier
            dataRemain = self.Header.DataRemaining
            firstMessage = True
            while offset < messageLen:
                chunkMessage = P2PMessage(self.Version)
                maxDataSize = maxSize

                if offset == 0 and len(self.Header.HeaderTLVs):
                    for key, value in self.Header.HeaderTLVs.items():
                        chunkMessage.Header.HeaderTLVs[key] = value

                    maxDataSize = maxSize - chunkMessage.Header.HeaderLength

                dataSize = min(maxDataSize, messageLen - offset)
                totalMessage.seek(offset)
                chunk = totalMessage.read(dataSize)

                if offset == 0:
                    chunkMessage.Header.OperationCode = self.Header.OperationCode

                chunkMessage.Header.SessionId = self.Header.SessionId
                chunkMessage.Header.TFCombination = self.Header.TFCombination
                chunkMessage.Header.PackageNumber = self.Header.PackageNumber

                if (messageLen + dataRemain - (dataSize + offset)) > 0:
                    chunkMessage.Header.DataRemaining = messageLen + dataRemain - (dataSize + offset)

                if offset and ((self.Header.TFCombination & P2P.TFCombination.First) == P2P.TFCombination.First):
                    chunkMessage.Header.TFCombination = self.Header.TFCombination - P2P.TFCombination.First

                now = time.time()
                if firstMessage or self.nextRak < now:
                    self.nextRak = now + self.RAK_WAIT_TIME
                    chunkMessage.SetRAK()
                    firstMessage = False
                    self.sendingData = False

                    def _resume_sending(*a):
                        log.info("Resume sending!")
                        self.sendingData = True

                    callbacks = dict(success = _resume_sending)
                else:
                    callbacks = {}

                chunkMessage.InnerBody = chunk
#                chunkMessage.Header.Identifier = nextId
                chunkMessage.Header.Identifier = 0

                nextId += chunkMessage.Header.MessageSize

                maxSize = (yield chunkMessage, callbacks)

                offset += dataSize

        self.Finished = True

    def SetRAK(self):
        if self.Version == P2P.Version.V2 and not self.Header.IsAck:
            self.Header.OperationCode |= P2P.OperationCode.RAK
        return (self.Header.OperationCode & P2P.OperationCode.RAK) == P2P.OperationCode.RAK

    def GetBytes(self, append_footer = True):
        self.InnerBody = self.GetInnerBytes()
        if append_footer:
            footer = struct.pack('>I', self.Footer)
        else:
            footer = ''

        return self.Header.GetBytes() + self.InnerBody + footer

    def ParseBytes(self, data):
        header_len = self.Header.ParseHeader(data)
        bodyAndFooter = data[header_len:]

        innerBodyLen = 0
        if self.Header.MessageSize > 0 or self.Header.TotalSize > 0:
            if self.Version == P2P.Version.V1:
                self.InnerBody = bodyAndFooter[:(self.Header.MessageSize or self.Header.TotalSize)]
                innerBodyLen = len(self.InnerBody)
            elif self.Version == P2P.Version.V2:
                self.InnerBody = bodyAndFooter[:self.Header.MessageSize - self.Header.DataPacketHeaderLength]
                innerBodyLen = len(self.InnerBody)
        else:
            self.InnerBody = ''

        footer_data = bodyAndFooter[innerBodyLen:]
        if len(footer_data) >= 4:
            self.Footer = struct.unpack('>I', footer_data[:4])[0]

    def GetInnerBytes(self):
        if self.InnerBody is not None:
            return self.InnerBody
        else:
            return getattr(self.InnerMessage, 'GetBytes', lambda:'')()

class P2PDataMessage(P2PMessage):
    def WritePreparationBytes(self):
        self.InnerBody = '\0'*4

    def feed(self, stream, maxread = -1):
        position = stream.tell()
        # figure out length
        stream.seek(0, 2) # 2 is relative to EOF
        length = stream.tell()
        stream.seek(position)

        read_amount = min(maxread, length - position)
        if self.Version == P2P.Version.V1:
            self.Header.Offset = position
            self.Header.TotalSize = length
        else:
            self.Header.DataRemaining = length - (position + read_amount)

        bytes = stream.read(read_amount)
        assert len(bytes) == read_amount
        self.InnerBody = bytes

        return len(bytes)

class P2PDCMessage(P2PDataMessage):
    def GetBytes(self):
        data = super(P2PDCMessage, self).GetBytes(False)
        return struct.pack('<I', len(data)) + data

class P2PDCHandshakeMessage(P2PDCMessage):
    Guid = funcs.iproperty('_get_Guid', '_set_Guid')
    guid = None
    def _get_Guid(self):
        return self.guid

    def _set_Guid(self, value):
        self.guid = value
        if self.Version == P2P.Version.V1:

            self.Header.AckSessionId = self.guid.bytes_le[0:4]
            self.Header.AckIdentifier = self.guid.bytes_le[4:8]
            self.Header.AckTotalSize = self.guid.bytes_le[8:16]

    @classmethod
    def Copy(cls, message):
        copy = super(P2PDCHandshakeMessage, cls).Copy(message)
        copy.Guid = message.Guid
        return copy

    def __init__(self, version):
        super(P2PDCHandshakeMessage, self).__init__(version)
        if self.Version == P2P.Version.V1:
            self.Header.Flags = P2P.Flags.DirectHandshake

        self.InnerBody = ''

    def CreateAck(self):
        ackMessage = self.Copy(self)
        ackMessage.Header.Identifier = 0
        return ack

    def ParseBytes(self, data):
        if self.Version == P2P.Version.V1:
            super(P2PDCHandshakeMessage, self).ParseBytes(data)
            self.Guid = uuid.UUID(bytes_le = self.Header.GetBytes()[-16:])

        else:
            # Don't call super()
            self.Guid = MSNU.CreateGuidFromData(self.Version, data)

        self.InnerBody = ''

    def GetBytes(self):
        self.InnerBody = ''
        guidData = self.Guid.bytes_le
        if self.Version == P2P.Version.V1:
            handshakeMessage = super(P2PDCHandshakeMessage, self).GetBytes()
            return handshakeMessage[:-16] + guidData
        else:
            # Doesn't call super.
            packetSize = struct.pack("<I", 16)
            return packetSize + guidData
