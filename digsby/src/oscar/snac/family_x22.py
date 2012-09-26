import logging

log = logging.getLogger('oscar.snac.x22')
subcodes = {}

def x22_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x22_x01(o, data, sock):
    errcode, errmsg, subcode = o.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise o.snac.SnacError(0x22, (errcode, errmsg), (subcode, submsg))