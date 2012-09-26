import oscar
from util import lookup_table
import time, struct

rendezvous_tlvs = lookup_table({
    0x000a: 'request_num',
    0x000f: 'mystery',
    0x000e: 'locale',
    0x000d: 'encoding',
    0x000c: 'user_message',
    0x0002: 'proxy_ip',
    0x0016: 'proxy_ip_check',
    0x0003: 'client_ip',
    0x0005: 'external_port',
    0x0017: 'port_check',
    0x0010: 'proxy_flag',
    0x2711: 'extended_data',
    0x2712: 'filename_encoding',
    0x0004: 'verified_ip',
})

# Rendezvous file transfer messages are either REQUEST, CANCEL, or ACCEPT.
rdv_types = rendezvous_message_types = lookup_table(dict(
    request = 0,
    cancel  = 1,
    accept  = 2,
))


def oscarcookie():
    '''
    Generate an oscar peer session cookie, which is handed back and forth
    in rendezvous packets during a direct IM session or filetransfer.
    '''

    return int(time.time()**2)


def rendezvous_header(message_type, cookie, capability, data = ''):
    'Constructs a rendezvous TLV block header.'

    type = map_intarg(message_type, rendezvous_message_types)
    return struct.pack('!HQ16s', type, cookie, capability) + data


def rdv_snac(screenname, capability, type, cookie = None,  data = ''):

    if cookie is None:
        cookie = int(time.time()**2)

    header = rendezvous_header(type, cookie, capability)
    rendezvous_data = oscar.OscarUtil.tlv(0x05, header + data)
    return oscar.snac.x04_x06(screenname, cookie, 2, rendezvous_data)


def map_intarg(arg, map):
    'Dictionary lookup with extra type checking.'

    if isinstance(arg, basestring):
        if not arg in map:
            raise ValueError('%s is not a valid argument' % arg)
        return map[arg]
    elif not isinstance(arg, int):
        raise ValueError('integer or string expected')
    return arg
