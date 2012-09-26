import logging

import oscar

'''
This family is deprecated, so it is remaining unimplemented
'''


x0c_name="Translation - deprecated"
log = logging.getLogger('oscar.snac.x0c')
subcodes = {}
def x0c_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x0c_x01(o, sock, data):
    '''
    SNAC (xc, x1): Translation Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_0c_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x0c, (errcode, errmsg), (subcode, submsg))

def x0c_x02(o, sock, data):
    '''
    SNAC (xc, x2): client translate request

    reference: U{http://iserverd.khstu.ru/oscar/snac_0c_02.html}
    '''
    raise NotImplementedError

def x0c_x03(o, sock, data):
    '''
    SNAC (xc, x3): translate response

    reference: U{http://iserverd.khstu.ru/oscar/snac_0c_03.html}
    '''
    raise NotImplementedError

