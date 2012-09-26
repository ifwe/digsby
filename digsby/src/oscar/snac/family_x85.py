import logging

import oscar

x85_name="Broadcast"
log = logging.getLogger('oscar.snac.x85')
subcodes = {}

def x85_init(o,sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x85_x01(o, sock, data):
    '''
    SNAC (x85, x1): Broadcast Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_85_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x85, (errcode, errmsg), (subcode, submsg))

def x85_x02(o, sock, data):
    '''
    SNAC (x85, x2): Send broadcast message to server

    reference: U{http://iserverd.khstu.ru/oscar/snac_85_02.html}
    '''
    raise NotImplementedError

def x85_x03(o, sock, data):
    '''
    SNAC (x85, x3): Server broadcast reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_85_03.html}
    '''
    raise NotImplementedError

