import logging

import oscar

x08_name="Popup"
log = logging.getLogger('oscar.snac.x08')
subcodes = {}
def x08_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x08_x01(o, sock, data):
    '''
    SNAC (x8, x1): Popup Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_08_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x08, (errcode, errmsg), (subcode, submsg))

def x08_x02(o, sock, data):
    '''
    SNAC (x8, x2): Display popup

    reference: U{http://iserverd.khstu.ru/oscar/snac_08_02.html}
    '''
    tlv_types = {
                 1:'message',
                 2:'url',
                 3:'width',
                 4:'height',
                 5:'delay',
                 }

    popup, data = oscar.unpack((('tlvs', 'tlv_dict'),), data)
    assert not data
