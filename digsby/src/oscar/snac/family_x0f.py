import logging

import oscar

x0f_name="Directory user search"

'''
There is no documentation for this family, and it has very
limited use. So, it is remaining unimplemented.
'''
log = logging.getLogger('oscar.snac.x0f')
subcodes = {}
def x0f_init(o, sock,cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x0f_x01(o, sock, data):
    '''
    SNAC (xf, x1): Directory user search Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_0f_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x0f, (errcode, errmsg), (subcode, submsg))

def x0f_x02(o, sock, data):
    '''
    SNAC (xf, x2): Client search request

    reference: U{http://iserverd.khstu.ru/oscar/snac_0f_02.html}
    '''
    raise NotImplementedError

def x0f_x03(o, sock, data):
    '''
    SNAC (xf, x3): Search reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_0f_03.html}
    '''
    raise NotImplementedError

def x0f_x04(o, sock, data):
    '''
    SNAC (xf, x4): Request interests list

    reference: U{http://iserverd.khstu.ru/oscar/snac_0f_04.html}
    '''
    raise NotImplementedError

def x0f_x05(o, sock, data):
    '''
    SNAC (xf, x5): Interest list response

    reference: U{http://iserverd.khstu.ru/oscar/snac_0f_05.html}
    '''
    raise NotImplementedError

