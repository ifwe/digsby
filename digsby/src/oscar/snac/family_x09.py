import struct
import logging

import util
import util.primitives.bits as bits
import oscar

x09_name="Privacy management"
subcodes = {}

log = logging.getLogger('oscar.snac.x09')
@util.gen_sequence
def x09_init(o, sock, cb):
    log.info('initializing')
    me = (yield None); assert me

    sock.send_snac(*oscar.snac.x09_x02(), req=True, cb=me.send)
    o.gen_incoming((yield None))
    cb()
    log.info('finished initializing')

def x09_x01(o, sock, data):
    '''
    SNAC (x9, x1): Privacy management Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x09, (errcode, errmsg), (subcode, submsg))

def x09_x02():
    '''
    SNAC (x9, x2): Request privacy params

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_02.html}
    '''
    return 0x09, 0x02

def x09_x03(o, sock, data):
    '''
    SNAC (x9, x3): Privacy limits response

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_03.html}
    '''
    format = (('tlvs', 'tlv_dict'),)
    tlvs, data = oscar.unpack(format, data)
    assert not data

    max_visible = max_invisible = None
    if 1 in tlvs:
        max_visible = tlvs[1]
    if 2 in tlvs:
        max_invisible = tlvs[2]

    return max_visible, max_invisible

def x09_x04(groups=None):
    '''
    SNAC (x9, x4): Set group permissions

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_04.html}
    '''

#    0x0001       UNCONFIRMED#        AOL unconfirmed user flag
#    0x0002       ADMINISTRATOR#      AOL administrator flag
#    0x0004       AOL_STAFF#          AOL staff user flag
#    0x0008       COMMERCIAL#         AOL commercial account flag
#    0x0010       FREE#               ICQ non-commercial account flag
#    0x0020       AWAY#               Away status flag
#    0x0040       ICQ#                ICQ user sign
#    0x0080       WIRELESS#           AOL wireless user
#    0x0100       UNKNOWN100#         Unknown bit
#    0x0200       UNKNOWN200#         Unknown bit
#    0x0400       UNKNOWN400#         Unknown bit
#    0x0800       UNKNOWN800#         Unknown bit

    names = 'unconfirmed admin aol_staff commercial '\
            'free away icq wireless unknown1 unknown2 '\
            'unknown4 unknown8'.split()

    bitflags = bits.bitfields(*names)

    groups = groups or names
    result = reduce(lambda a,b:a|b, (getattr(bitflags, name, 0) for name in groups))

    return 0x09, 0x04, struct.pack('!I', result)

def x09_x05(names):
    '''
    SNAC (x9, x5): Add to visible list

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_05.html}
    '''
    return 0x09, 0x05, sn_list(names)

def x09_x06(names):
    '''
    SNAC (x9, x6): Delete from visible list

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_06.html}
    '''
    return 0x09, 0x06, sn_list(names)

def x09_x07(names):
    '''
    SNAC (x9, x7): Add to invisible list

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_07.html}
    '''
    return 0x09, 0x07, sn_list(names)

def x09_x08(names):
    '''
    SNAC (x9, x8): Delete from invisible list

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_08.html}
    '''
    return 0x09, 0x09, sn_list(names)

def x09_x09(o, sock, data):
    '''
    SNAC (x9, x9): Service error

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_09.html}
    '''
    errcode, data = oscar.unpack((('_', 'H'),), data)

    if data:
        fmt = (('tlvs', 'tlv_dict'),)

        tlvs, data = oscar.unpack(fmt, data)
        assert not data

        subcode, tlvs[8] = oscar.unpack((('code', 'H'),),tlvs[8])
        errmsg = tlvs[4]

        if errcode == 1:
            errmsg = 'Wrong mode'
        else:
            errmsg = None
            errcode = 'Unknown Error'
    else:
        subcode = None
    raise oscar.SnacError((0x09, x09_name), (errcode, errmsg), (subcode, subcodes[subcode]))

def x09_x0a(names):
    '''
    SNAC (x9, xa): Add to visible(?)

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_0a.html}
    '''

    return 0x09, 0x0a, sn_list(names)

def x09_x0b(names):
    '''
    SNAC (x9, xb): Delete from visible(?)

    reference: U{http://iserverd.khstu.ru/oscar/snac_09_0b.html}
    '''
    return 0x09, 0x0b, sn_list(names)

def sn_list(names):
    return ''.join(struct.pack('!B%ds' % len(sn), len(sn), sn) for sn in names)
