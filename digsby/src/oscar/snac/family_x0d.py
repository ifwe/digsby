'''
family 0x0d

Chat navigation.
'''
import struct
import logging

import util
import oscar

x0d_name="Chat nav"

log = logging.getLogger('oscar.snac.x0d')
subcodes = {}
@util.gen_sequence
def x0d_init(o, sock, cb):
    log.info('initializing')
    me = (yield None); assert me
    sock.send_snac(*oscar.snac.x0d_x02(), req=True, cb=me.send)
    o.gen_incoming((yield None))
    cb()
    log.info('finished initializing')

def x0d_x01(o, sock, data):
    '''
    SNAC (xd, x1): Chat nav Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x0d, (errcode, errmsg), (subcode, submsg))

def x0d_x02():
    '''
    SNAC (xd, x2): Request limits

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_02.html}
    '''
    return 0x0d, 0x02

def x0d_x03():
    '''
    SNAC (xd, x3): Request exchange info

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_03.html}
    '''
    return 0x0d, 0x03, '\0\0'

def x0d_x04(exchange, cookie, instance=1, detail=0):
    '''
    SNAC (xd, x4): Request room info

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_04.html}
    '''
    clen = len(cookie)
    return 0x0d, 0x04, struct.pack('!HB%dsHB' % clen, exchange, clen, cookie, instance, detail)

def x0d_x05(o, sock, data):
    '''
    SNAC (xd, x5): Request extended room info

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_05.html}
    '''
    raise NotImplementedError

def x0d_x06(exchange, cookie, instance=1):
    '''
    SNAC (xd, x6): Request member list

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_06.html}
    '''
    clen = len(cookie)
    return 0x0d, 0x06, struct.pack('!HB%dsH' % clen, exchange, clen, cookie, instance)

def x0d_x07(o, sock, data):
    '''
    SNAC (xd, x7): Search for room

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_07.html}
    '''
    raise NotImplementedError

def x0d_x08(o, roomname=None, cookie=None):
    '''
    SNAC (xd, x8): Create room

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_08.html}
    '''
    exch = 4

    #if roomname in o.sockets:
        #log.warning('Already in chat room %s, joining anyway' % roomname)

    if roomname is None:
        assert cookie is not None
        roomname = cookie.split('-', 2)[-1]

    if isinstance(roomname, unicode):
        roomname = roomname.encode('utf8')

    cookie = cookie or 'create'
    instance = 0xFFFF
    detail = 1
    tlvs = [(0xD3, roomname),
            (0xD6, o.encoding),
            (0xD7, o.lang),]
    c_len = len(cookie)
    to_send = struct.pack('!HB%dsHBH' % c_len,
                          exch, c_len, cookie,
                          instance, detail, len(tlvs)) + \
              oscar.util.tlv_list(*tlvs)

    return 0x0d, 0x08, to_send

def x0d_x09(o, sock, data):
    '''
    SNAC (xd, x9): Chat navigation info

    reference: U{http://iserverd.khstu.ru/oscar/snac_0d_09.html}
    '''
    tlv_names = {
                 0x01:'redirect',
                 0x02:'max_concurrent',
                 0x03:'exchange',
                 0x04:'room',
                 }

    fmt = (('tlvs', 'named_tlvs', -1, tlv_names),)
    tlvs, data = oscar.unpack(fmt, data)
    assert not data

    redirect = max_concurrent = exchange = room = None
    if 'redirect' in tlvs:
        redirect = x0d_x09_redirect(o, sock, tlvs.redirect)
    if 'max_concurrent' in tlvs:
        max_concurrent = x0d_x09_max_concurrent(o, sock, tlvs.max_concurrent)
    if 'exchange' in tlvs:
        exchange = x0d_x09_exchange(o, sock, tlvs.exchange)
    if 'room' in tlvs:
        room = x0d_x09_room(o, sock, tlvs.room)
    return redirect, max_concurrent, exchange, room

def x0d_x09_redirect(o, sock, data):
    #TODO: figure out what goes in here
    pass

def x0d_x09_max_concurrent(o, sock, data):
    #TODO: figure out what goes here
    pass

def x0d_x09_exchange(o, sock, data):
    fmt = (('id', 'H'),
           ('num_tlvs','H'),
           ('tlvs','named_tlvs', 'num_tlvs', x0d_tlv_names))

    id, __, tlvs, data = oscar.unpack(fmt, data)
    assert not data
    #TODO: something with this info
    return id, tlvs

def x0d_x09_room(o, sock, data):
    fmt = (('exchange', 'H'),
           ('cookie','pstring'),
           ('instance', 'H'),
           ('detail', 'B'),
           ('num_tlvs', 'H'),
           ('tlvs','named_tlvs', 'num_tlvs', x0d_tlv_names))
    exchange, cookie, instance, detail, __, tlvs, data = oscar.unpack(fmt, data)
    assert not data
    return exchange, cookie, instance, detail, tlvs

x0d_tlv_names = {
                 0x01    :    'tree',
                 0x02    :    'for_class',
                 0x03    :    'max_concurrent',
                 0x04    :    'max_name_length',
                 0x05    :    'root',
                 0x06    :    'search_tags',
                 0x65    :    'child_rooms',
                 0x66    :    'contain_user_class',
                 0x67    :    'contain_user_array',
                 0x68    :    'evil_generated',
                 0x69    :    'evil_generated_array',
                 0x6A    :    'qualified_name',
                 0x6B    :    'moderator',
                 0x6C    :    'more_info',
                 0x6D    :    'num_children',
                 0x6E    :    'num_instances',
                 0x6F    :    'occupancy',
                 0x70    :    'occupancy_array',
                 0x71    :    'occupant_array',
                 0x72    :    'occupant_evil_array',
                 0x73    :    'occupants',
                 0x74    :    'parent',
                 0x75    :    'activity',
                 0x76    :    'activity_array',
                 0x77    :    'gross_evil',
                 0x78    :    'net_evil',
                 0x79    :    'speaker',
                 0xC9    :    'chat_flag',
                 0xCA    :    'create_time',
                 0xCB    :    'creator',
                 0xCC    :    'description',
                 0xCD    :    'description_url',
                 0xCE    :    'closed',
                 0xCF    :    'language',
                 0xD0    :    'mandatory_chan',
                 0xD1    :    'max_html_length',
                 0xD2    :    'max_occupants',
                 0xD3    :    'name',
                 0xD4    :    'optional_chan',
                 0xD5    :    'create_permission',
                 0xD6    :    'encoding_1',
                 0xD7    :    'language_1',
                 0xD8    :    'encoding_2',
                 0xD9    :    'language_2',
                 0xDA    :    'max_msg_length',
                 0xDB    :    'encoding',
                 }
