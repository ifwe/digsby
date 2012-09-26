
class TFCombination:
    NONE         = 0
    First        = 1
    Unknown2     = 2
    MsnObject    = 4
    FileTransfer = 6

TFCombo = TFCombination

class OperationCode:
    NONE = 0
    SYN = 1
    RAK = 2

OpCode = OperationCode

class Version:
    V1 = 1
    V2 = 2

class Flags:
    Normal = 0
    Nak = 1
    Ack = 2
    RAK = 4
    Error = 8
    File = 0x10
    Data = 0x20
    CloseSession = 0x40
    TlpError = 0x80
    DirectHandshake = 0x100
    MSNSLPInfo = 0x01000000
    FileData = MSNSLPInfo | Data | File
    MSNObjectData = MSNSLPInfo | Data
Flag = Flags
