import logging

import oscar

x0a_name="User lookup"
log = logging.getLogger('oscar.snac.x0a')
subcodes = {}
def x0a_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x0a_x01(o, sock, data):
    '''
    SNAC (xa, x1): User lookup Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_0a_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x0a, (errcode, errmsg), (subcode, submsg))

def x0a_x02(email):
    '''
    SNAC (xa, x2): Search by email

    reference: U{http://iserverd.khstu.ru/oscar/snac_0a_02.html}
    '''
    return 0x0a, 0x02, email

def x0a_x03(o, sock, data):
    '''
    SNAC (xa, x3): Search response

    reference: U{http://iserverd.khstu.ru/oscar/snac_0a_03.html}
    '''
    fmt = (('tlvs', 'tlv_list'),)
    name_tlvs, data = oscar.unpack(fmt, data)
    assert not data
    names = [tlv.v for tlv in name_tlvs]
