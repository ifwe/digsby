import logging

import oscar

x06_name="Invite"
log = logging.getLogger('oscar.snac.x06')
subcodes = {}
def x06_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x06_x01(o, sock, data):
    '''
    SNAC (x6, x1): Invite Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_06_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x06, (errcode, errmsg), (subcode, submsg))

def x06_x02(email, message):
    '''
    SNAC (x6, x2): Invite a friend

    reference: U{http://iserverd.khstu.ru/oscar/snac_06_02.html}
    '''
    return 0x06, 0x02, oscar.util.tlv(0x11, email) + oscar.util.tlv(0x15, message)

def x06_x03(o, sock, data):
    '''
    SNAC (x6, x3): Invitation ack

    reference: U{http://iserverd.khstu.ru/oscar/snac_06_03.html}
    '''
    assert not data