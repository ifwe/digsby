import logging
x25_name="Unknown servcie"
log = logging.getLogger('oscar.snac.x25')

version = 4

def x25_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')
