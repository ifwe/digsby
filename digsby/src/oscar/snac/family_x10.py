'Buddy icons.'

from __future__ import with_statement
import functools

import logging
import struct
import hashlib

import util
import oscar

MAX_ICON_SIZE = 7168

x10_name="SSBI"

log = logging.getLogger('oscar.snac.x10')

subcodes = {}
icon_queue = []

__icon_data = None
def x10_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x10_x01(o, sock, data):
    '''
    SNAC (x10, x1): SSBI Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_10_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x10, (errcode, errmsg), (subcode, submsg))

def x10_x02(icon_data):
    '''
    SNAC (x10, x2): Upload your icon

    reference: U{http://iserverd.khstu.ru/oscar/snac_10_02.html}
    '''

    # send an SSI request for changing 'self' icon.

    icon_len = len(icon_data)

    return 0x10, 0x02, struct.pack('!HH%ds' % icon_len, 1, icon_len, icon_data)

def x10_x03(o, sock, data):
    '''
    SNAC (x10, x3): Upload buddy icon reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_10_03.html}
    '''

    fmt = (('_1', 'H'),
           ('_2', 'H'),
           ('icon_hash', 'pstring'))

    __,__, hash, data = oscar.unpack(fmt, data)
    return hash

def x10_x04(o, sn):
    '''
    SNAC (x10, x4): Request buddy icon

    reference: U{http://iserverd.khstu.ru/oscar/snac_10_04.html}
    '''
    snlen = len(sn)
    hash = o.buddies[sn].icon_hash
    hashlen = len(hash)

    to_send = struct.pack('!B%dsBHBB%ds' %
                          (snlen, hashlen),
                          snlen, sn,
                          1, 1, 1,         # mystery bytes!
                          hashlen, hash)

    return 0x10, 0x04, to_send

def x10_x05(o, sock, data):
    '''
    SNAC (x10, x5): Requested buddy icon

    reference: U{http://iserverd.khstu.ru/oscar/snac_10_05.html}
    '''

    fmt = (('sn', 'pstring'),
           ('unknown', 'H'),
           ('flags', 'B'),
           ('hash', 'pstring'),
           ('icon_len', 'H'),
           ('icon', 's', 'icon_len'))

    sn, __,__, hash, __, icon, data = oscar.unpack(fmt, data)
    assert not data, util.to_hex(data)
    return sn, hash, icon

def x10_x06(o, sock, data):
    '''
    SNAC (x10, x6): SNAC(0x10, 0x06)

    reference: U{http://iserverd.khstu.ru/oscar/snac_10_06.html}
    '''
    raise NotImplementedError

def x10_x07(o, sock, data):
    '''
    SNAC (x10, x7): SNAC(0x10, 0x07)

    reference: U{http://iserverd.khstu.ru/oscar/snac_10_07.html}
    '''
    raise NotImplementedError

def set_buddy_icon(o, icon_data):

    log.info('set_buddy_icon called with %d bytes of data', len(icon_data))

    if len(icon_data) > MAX_ICON_SIZE:
        raise AssertionError('Oscar can only set buddy icon data less than 8k')

    hash = hashlib.md5(icon_data).digest()
    hashlen = len(hash)

    #globals().get('set_buddy_icon_ssi_%s' % o.name)(o, hash)
    set_buddy_icon_ssi(o, hash)

    def on_success(sock, snac):
        # On a successful icon set, server returns with the icon hash.
        icon_hash = x10_x03(o, sock, snac.data)

        if icon_hash:
            log.info('upload self icon successful, received hash %r (%d bytes)', icon_hash, len(icon_hash))

            from util import Timer
            Timer(3, o.self_buddy.cache_icon, icon_data, icon_hash).start()
        else:
            log.warning('buddy icon server did not return a hash.')

    log.info('sending snac 0x10 0x02 (icon data)')
    o.send_snac(*oscar.snac.x10_x02(icon_data), **{'req': True, 'cb': on_success})

def set_buddy_icon_ssi_aim(o, iconhash):

    ssi_info = dict(type = 0x0014, name = '1', group_id = 0)
    existing_ssis = o.ssimanager.find(**ssi_info)

    if existing_ssis:
        ssi = existing_ssis[0].clone()
    else:
        ssi = oscar.ssi.item(item_id  = o.ssimanager.new_ssi_item_id(0),
                             **ssi_info)

    hashlen = len(iconhash)
    ssi.tlvs.update({0x131: "",
                     0x0d5: struct.pack('!2B%ds' % hashlen, 1, hashlen, iconhash)})

    log.info('modifying self icon SSI')
    o.ssimanager.add_modify(ssi)

set_buddy_icon_ssi = set_buddy_icon_ssi_aim

#def set_buddy_icon_ssi_icq(o, iconhash):
#    ssi_info = dict(type = 0x0014, name = '1', group_id = 0)
#
#    existing_ssis = o.ssimanager.find(**ssi_info)
#
#    if existing_ssis:
#        ssi = existing_ssis[0].clone()
#    else:
#        ssi = oscar.ssi.item(item_id  = o.ssimanager.new_ssi_item_id(0),
#                             **ssi_info)
#
#    hashlen = len(iconhash)
#    ssi.tlvs.update({0x131: "",
#                     0x0d5: struct.pack('!2B%ds' % hashlen, 1, hashlen, iconhash)})
#
#    log.info('modifying self icon SSI')
#    o.ssimanager.add_modify(ssi)

@util.gen_sequence
def get_buddy_icon(o, sn):
    me = (yield None); assert me

    if not isinstance(sn, basestring):
        raise TypeError('get_buddy_icon requires a string: %r %r' % (type(sn), sn))

    if not o.buddies[sn].icon_hash:
        log.warning('get_buddy_icon called for %s but that buddy has no '
                    'icon_hash', sn)
        raise StopIteration

    # Send the icon request.
    log.info("Requesting %s's icon", sn)
    o.send_snac(req=True, cb=me.send, *oscar.snac.x10_x04(o, sn))

    # Wait for response.
    rcv_sn, rcv_hash, rcv_icon = o.gen_incoming((yield 'waiting for 0x10, 0x05'))
    log.debug('Received %d bytes of hash and %d bytes of icon for '
             '%s', len(rcv_hash), len(rcv_icon), rcv_sn)

    if rcv_sn != sn:
        log.debug('Requested buddy icon for %s, but got one for %s',
                  sn, rcv_sn)

    # store the hash/icon for later + update the gui
    buddy = o.buddies[rcv_sn]
    log.info('caching icon for %s', buddy)
    buddy.cache_icon(rcv_icon, rcv_hash)
    buddy.notify('icon')
