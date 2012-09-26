'''
Ads family. This is deprecated, so it's not implemented.

Besides, who wants ads anyway?
'''
import logging


import oscar

x05_name="ads - deprecated"
log = logging.getLogger('oscar.snac.x05')
subcodes = {}
def x05_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x05_x01(o, sock, data):
    '''
    SNAC (x5, x1): ads Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_05_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x05, (errcode, errmsg), (subcode, submsg))

def x05_x02(o, sock, data):
    '''
    SNAC (x5, x2): Request ads

    reference: U{http://iserverd.khstu.ru/oscar/snac_05_02.html}
    '''
    raise NotImplementedError

def x05_x03(o, sock, data):
    '''
    SNAC (x5, x3): Ads response

    reference: U{http://iserverd.khstu.ru/oscar/snac_05_03.html}
    '''
    raise NotImplementedError

