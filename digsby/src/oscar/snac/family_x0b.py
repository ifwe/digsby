import logging

import oscar

'''
This is remaining unimplemented
'''

x0b_name="Usage stats"
log = logging.getLogger('oscar.snac.x0b')
subcodes = {}
def x0b_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x0b_x01(o, sock, data):
    '''
    SNAC (xb, x1): Usage stats Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_0b_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x0b, (errcode, errmsg), (subcode, submsg))

def x0b_x02(o, sock, data):
    '''
    SNAC (xb, x2): Set minimum report interval

    reference: U{http://iserverd.khstu.ru/oscar/snac_0b_02.html}
    '''
    interval, data = oscar.unpack((('interval', 'H'),), data)
    o.log.debug('Minimum report interval: %d' % interval)

    return interval

def x0b_x03(o, sock, data):
    '''
    SNAC (xb, x3): Usage stats report

    reference: U{http://iserverd.khstu.ru/oscar/snac_0b_03.html}
    '''
    raise NotImplementedError

def x0b_x04(o, sock, data):
    '''
    SNAC (xb, x4): Stats report ack

    reference: U{http://iserverd.khstu.ru/oscar/snac_0b_04.html}
    '''
    raise NotImplementedError

