import ctypes
import sys
import struct

class Ppmd7Error(Exception): pass
class Ppmd7DecodeError(Ppmd7Error): pass
class Ppmd7EncodeError(Ppmd7Error): pass

MAGICPREFIX = 'ppmd7'

ppmd = None
def _load_ppmd():
    global ppmd
    if ppmd is None:
        ppmd = ctypes.cdll.ppmd7
    return ppmd

def encode(buffer, order=64, memsize=((1<<26)*3)):
    ppmd = _load_ppmd()

    outBuffer = ctypes.POINTER(ctypes.c_char)()
    outBufferSize = ctypes.c_int()
    buffer_size = len(buffer)
    ret = ppmd.encode(buffer, buffer_size, order, memsize, ctypes.byref(outBuffer), ctypes.byref(outBufferSize))
    if ret < 0:
        raise Ppmd7EncodeError()
    val = ctypes.string_at(outBuffer, outBufferSize)
    ppmd.kill(ctypes.byref(outBuffer))
    return val

def pack(buffer):
    buffer_size = len(buffer)
    val = encode(buffer)
    assert buffer_size < sys.maxint
    return MAGICPREFIX + struct.pack('!I', buffer_size) + val

def unpack(buffer):
    ppmd = _load_ppmd()
    if not buffer.startswith(MAGICPREFIX):
        raise Ppmd7DecodeError('invalid header')
    buffer = buffer[len(MAGICPREFIX):]
    (size,) = struct.unpack('!I', buffer[:4])
    buffer = buffer[4:]
    return decode(buffer, size)

def decode(buffer, expected, order=64, memsize=((1<<26)*3)):
    outBuffer = ctypes.POINTER(ctypes.c_char)()
    outBufferSize = ctypes.c_int()
    expected = ctypes.c_int(expected)
    if -1 == ppmd.decode(buffer, len(buffer), order, memsize, expected, ctypes.byref(outBuffer), ctypes.byref(outBufferSize)):
        raise Ppmd7DecodeError()
    val = ctypes.string_at(outBuffer, outBufferSize)
    ppmd.kill(ctypes.byref(outBuffer))
    return val

if __name__ == '__main__':
#    from tests.testapp import testapp
#    with testapp(plugins=False):
        s = 'test foo foo bar foo foo bar'
        enc = pack(s)
        dec = unpack(enc)
        print s
        print dec

