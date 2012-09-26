from util import Storage, to_hex
from util.packable import Packable
import struct
import oscar.capabilities as capabilities
from oscar.OscarUtil import tlv
from logging import getLogger; log = getLogger('rdv.proxy'); info = log.info

#
# rendezvous proxy communication packets
#

class ProxyHeader(Packable):
    version = 0x044a

    fmt = ('length',  'H',
           'version', 'H',
           'command', 'H',
           'null',    'I',
           'flags',   'H')

    # The version should always be 0x044a.
    invars = [lambda o: o.version == ProxyHeader.version]

    commands = Storage(error       = 0x01,
                       initsend    = 0x02,
                       ack         = 0x03,
                       initreceive = 0x04,
                       ready       = 0x05)

    @classmethod
    def initsend(cls, screenname, cookie):
        return make_proxy_init(screenname, cookie)

    @classmethod
    def initreceive(cls, screenname, cookie, port):
        return make_proxy_init(screenname, cookie, port)

# A TLV which is T:0x01 L:0x10 V:[sendfile capability]
# (sent along with proxy packets)
SENDFILE = capabilities.by_name['file_xfer']
_send_file_tlv = tlv(0x01, SENDFILE)

def make_proxy_init(sn, cookie, port=None):
    'Creates a proxy packet.'

    # Check for screenname as a string.
    if not isinstance(sn, str):
        raise TypeError('screenname must be a str object')

    # Cookie must be an eight byte string or a long.
    if isinstance(cookie, long):
        cookie = struct.pack('!Q', cookie)
    else:
        assert isinstance(cookie, str) and len(cookie) == 8

    # If a port was specified, use initreceive, since that is the only way
    # that and 'initsend' differ.
    command = 'initreceive' if port else 'initsend'

    # Length is everything that follows the two bytes of length.
    length = len(sn) + 41
    if port is None:
        # Init sends have two less byes.
        length -= 2

    info(command + ' length: %d', length)

    data = ProxyHeader(length,
                       ProxyHeader.version,
                       ProxyHeader.commands[command],
                       null = 0,
                       flags = 0).pack()

    # Screen name as a pascal string
    data += struct.pack('B', len(sn)) + sn

    # Add the two byte port if this is an init_receive request
    if port:
        assert isinstance(port, int)
        data += struct.pack('!H', port)

    fullpacket = data + cookie + _send_file_tlv #Send file capability on the end

    log.info_s('proxy packet assembled (%d bytes): %s', len(fullpacket),to_hex(fullpacket))
    return fullpacket

def unpack_proxy_ack(data):
    ack, data = ProxyHeader.unpack(data)
    assert \
        ack.version == ProxyHeader.version and \
        ack.length == 16 and \
        ack.command == ProxyHeader.commands['ack']
    ack.port, ack.ip = struct.unpack('!HI', data)
    return ack

def unpack_proxy_ready(data):
    ready, data = ProxyHeader.unpack(data)
    assert not data
    return ready
