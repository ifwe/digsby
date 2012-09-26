import logging; log = logging.getLogger('msn.p2p.header')
import msn.P2P as P2P

import struct
import util.primitives.funcs as funcs
import util.primitives.structures as structures

class P2PHeader(object):
    HeaderLength = funcs.iproperty('_get_HeaderLength')
    Identifier = 0
    MessageSize = 0
    TotalSize = 0
    SessionId = 0
    AckIdentifier = funcs.iproperty('_get_AckIdentifier', '_set_AckIdentifier')
    IsNak = funcs.iproperty('_get_IsNak')
    IsAck = funcs.iproperty('_get_IsAck')
    RequireAck = funcs.iproperty('_get_RequireAck')

    def CreateAck(self):
        raise NotImplementedError

    def CreateNak(self):
        raise NotImplementedError

    def ParseHeader(self, data):
        raise NotImplementedError

    def GetBytes(self):
        raise NotImplementedError

    def __repr__(self):
        varstr = ', ' .join('%s=%r' % i for i in vars(self).items())
        return '%s(%s)' % (type(self).__name__, varstr)

    def Copy(self):
        new = type(self)()
        new.ParseHeader(self.GetBytes())
        return new

class V1Header(P2PHeader):
    Offset = 0
    Flags = 0
    AckSessionId = 0
    AckTotalSize = 0
    ackIdentifier = 0

    def _get_AckIdentifier(self):
        return self.ackIdentifier

    def _set_AckIdentifier(self, value):
        self.ackIdentifier = value

    def _get_HeaderLength(self):
        return 48

    def _get_IsAck(self):
        return self.AckIdentifier != 0 and ((self.Flags & P2P.Flags.Ack) == P2P.Flags.Ack)

    def _get_IsNak(self):
        return self.AckIdentifier != 0 and ((self.Flags & P2P.Flags.Nak) == P2P.Flags.Nak)

    def _get_RequireAck(self):
        if self.AckIdentifier != 0:
            return False
        if self.Flags == P2P.Flags.Ack:
            return False
        if (self.MessageSize + self.Offset) == self.TotalSize:
            return True

        return False

    def CreateAck(self):
        ack = V1Header()
        ack.SessionId = self.SessionId
        ack.TotalSize = 0
        ack.Flags = P2P.Flags.Ack
        ack.AckSessionId = self.Identifier
        ack.AckIdentifier = self.AckSessionId
        ack.AckTotalSize = self.TotalSize
        return ack

    def CreateNak(self):
        nak = self.CreateAck()
        nak.Flags = P2P.Flags.Nak
        return nak

    def ParseHeader(self, data):
        (self.SessionId,
         self.Identifier,
         self.Offset,
         self.TotalSize,
         self.MessageSize,
         self.Flags,
         self.AckSessionId,
         self.AckIdentifier,
         self.AckTotalSize) = struct.unpack('<IIQQIIIIQ', data[:self.HeaderLength])

        return self.HeaderLength

    def GetBytes(self):
        return struct.pack('<IIQQIIIIQ',
                           self.SessionId,
                           self.Identifier,
                           self.Offset,
                           self.TotalSize,
                           self.MessageSize,
                           self.Flags,
                           self.AckSessionId,
                           self.AckIdentifier,
                           self.AckTotalSize)


class V2Header(P2PHeader):
    OperationCode = 0
    ackIdentifier = 0
    nakIdentifier = 0
    TFCombination = 0
    PackageNumber = 0
    dataRemaining = 0

    def __init__(self):
        # these are big endian
        self.HeaderTLVs = {}
        self.DataPacketTLVs = self.dataPacketTLVs = {}

    def _get_HeaderLength(self):
        length = 8
        if self.HeaderTLVs:
            for val in self.HeaderTLVs.values():
                length += (1 + 1 + len(val))

            if (length % 4) != 0:
                length += (4 - (length % 4))

        return length

    @property
    def DataPacketHeaderLength(self):
        if self.MessageSize == 0:
            return 0

        length = 8
        if self.dataPacketTLVs:
            for val in self.dataPacketTLVs.values():
                length += (1 + 1 + len(val))

            if (length % 4) != 0:
                length += (4 - (length % 4))
        return length


    def _get_AckIdentifier(self):
        if self.ackIdentifier == 0 and (2 in self.HeaderTLVs):
            self.ackIdentifier = struct.unpack('>I', self.HeaderTLVs[2])[0]

        return self.ackIdentifier

    def _set_AckIdentifier(self, value):
        self.HeaderTLVs[2] = struct.pack('>I', value)

    def _get_NakIdentifier(self):
        if self.nakIdentifier == 0 and (3 in self.HeaderTLVs):
            self.nakIdentifier = struct.unpack('>I', self.HeaderTLVs[3])[0]

        return self.nakIdentifier

    def _set_NakIdentifier(self, value):
        self.HeaderTLVs[3] = struct.pack('>I', value)

    NakIdentifier = funcs.iproperty('_get_NakIdentifier', '_set_NakIdentifier')

    def _get_IsAck(self):
        return 2 in self.HeaderTLVs

    def _get_IsNak(self):
        return 3 in self.HeaderTLVs

    def _get_RequireAck(self):
        rak = (self.OperationCode & P2P.OperationCode.RAK) != 0

#        if rak and self.MessageSize == 0 and (len(self.HeaderTLVs) - (self.IsAck + self.IsNak)) == 0 and len(self.DataPacketTLVs) == 0:
#            log.error("Ignoring RAK flag because packet has no data")
#            return False

        return rak

    def _get_DataRemaining(self):
        if self.dataRemaining == 0 and (1 in self.DataPacketTLVs):
            self.dataRemaining = struct.unpack('>Q', self.DataPacketTLVs[1])[0]

        return self.dataRemaining

    def _set_DataRemaining(self, value):
        self.dataRemaining = value
        if value == 0:
            self.DataPacketTLVs.pop(1, None)
        else:
            self.DataPacketTLVs[1] = struct.pack('>Q', value)

    DataRemaining = funcs.iproperty('_get_DataRemaining', '_set_DataRemaining')

    def AppendPeerInfoTLV(self):
        self.OperationCode |= P2P.OperationCode.SYN
        self.HeaderTLVs[1] = self.CreatePeerInfoValue()

    def CreateAck(self):
        ack = V2Header()
        if self.RequireAck:
            ack.AckIdentifier = self.Identifier + self.MessageSize
            ack.OperationCode = P2P.OperationCode.NONE

            if self.MessageSize > 0:
                if not self.IsAck:
                    if (self.OperationCode & P2P.OperationCode.SYN) != 0:
                        ack.OperationCode |= P2P.OperationCode.RAK

                        if 1 in self.HeaderTLVs:
                            ack.HeaderTLVs[1] = self.HeaderTLVs[1]
                            ack.OperationCode |= P2P.OperationCode.SYN
        else:
            raise Exception("Can't ack a non-RAK header")

        return ack

    def CreateNak(self):
        nak = V2Header()
        nak.NakIdentifier = self.Identifier + self.MessageSize
        return nak

    def ParseHeader(self, data):
        (headerLen, self.OperationCode, self.MessageSize, self.Identifier), data = struct.unpack('>BBHI', data[:8]), data[8:]

        if headerLen > 8:
            TLVs_data, data = data[:headerLen - 8], data[headerLen - 8:]
            tlvs = unpack_tlvs(TLVs_data)
            for tlv in tlvs:
                self.ProcessHeaderTLVData(*tlv)

        dataHeaderLen = 0
        if self.MessageSize > 0:
            (dataHeaderLen, self.TFCombination, self.PackageNumber, self.SessionId), data = struct.unpack('>BBHI', data[:8]), data[8:]
            if dataHeaderLen > 8:
                TLVs_data, data = data[:dataHeaderLen - 8], data[dataHeaderLen - 8:]
                tlvs = unpack_tlvs(TLVs_data)
                for tlv in tlvs:
                    self.ProcessDataPacketTLVData(*tlv)

        return headerLen + dataHeaderLen

    def ProcessHeaderTLVData(self, t, l, v):
        self.HeaderTLVs[t] = v

        if t == 1:
            pass
        elif t == 2:
            return
            if L == 4:
                pass
        elif t == 3:
            pass

    def ProcessDataPacketTLVData(self, t, l, v):
        self.DataPacketTLVs[t] = v

    def CreatePeerInfoValue(self):
        return struct.pack('<HHHHI', 512, 0, 3584, 0, 271)

    def GetBytes(self):
        headerLen = self.HeaderLength
        dataHeaderLen = self.DataPacketHeaderLength

        data = ''
        data += struct.pack('>BBHI', headerLen, self.OperationCode, self.MessageSize, self.Identifier)
        for key, val in self.HeaderTLVs.items():
            data += struct.pack('BB', key, len(val)) + val

        missing_bytes = 4 - len(data) % 4
        if  missing_bytes != 4:
            data += '\0' * missing_bytes

        data += struct.pack('>BBHI', dataHeaderLen, self.TFCombination, self.PackageNumber, self.SessionId)
        for key, val in self.DataPacketTLVs.items():
            data += struct.pack('BB', key, len(val)) + val

        missing_bytes = 4 - len(data) % 4
        if  missing_bytes != 4:
            data += '\0' * missing_bytes

        return data

def unpack_tlvs(TLVs_data):
    tlvs = []
    index = 0
    while index < len(TLVs_data):
        T = ord(TLVs_data[index])
        if T == 0:
            break
        L = ord(TLVs_data[index+1])
        V = TLVs_data[index+2:index+2+L]
        tlvs.append((T, L, V))
        index += 2 + L

    return tlvs
