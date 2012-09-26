import logging

import time
import traceback
import struct

import oscar.snac
from pprint import pformat

x0e_name = "Chat"
log = logging.getLogger('oscar.snac.x0e')

subcodes = {}

def x0e_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x0e_x01(o, sock, data):
    '''
    SNAC (xe, x1): Chat Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x0e, (errcode, errmsg), (subcode, submsg))

def x0e_x02(o, sock, data):
    '''
    SNAC (xe, x2): Chat room info update

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_02.html}
    '''
    fmt = (('exchange', 'H'),
           ('cookie','pstring'),
           ('instance', 'H'),
           ('detail', 'B'),
           ('num_tlvs', 'H'),
           ('tlvs','named_tlvs', 'num_tlvs', oscar.snac.x0d_tlv_names))

    exchange, cookie, instance, detail, __, tlvs, data = oscar.unpack(fmt, data)
    assert not data

    convo = o._get_chat(cookie)
    if convo is not None:
        convo._update_chat_info(tlvs)

    #TODO: something with this info
    return exchange, cookie, instance, detail, tlvs

def x0e_x03(o, sock, data):
    '''
    SNAC (xe, x3): User joined chat room

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_03.html}
    '''
    user_infos, data = oscar.unpack((('user_infos', 'list', 'userinfo'),), data)
    o.buddies.update_buddies(user_infos)
    for info in user_infos:
        sock_convo(o, sock).buddy_join(info.name)

def x0e_x04(o, sock, data):
    '''
    SNAC (xe, x4): User left chat room

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_04.html}
    '''
    user_infos, data = oscar.unpack((('user_infos', 'list', 'userinfo'),), data)
    log.info('user left room: %r', user_infos)
    assert not data
    o.buddies.update_buddies(user_infos)
    for info in user_infos:
        sock_convo(o, sock).buddy_leave(o.buddies[info.name])


def x0e_x05(o, message, whisper=False, reflect=True):
    '''
    SNAC (xe, x5): Outgoing chat message

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_05.html}
    '''
    cookie = int(time.time())
    channel = 3
    content_type = 'text/x-aolrtf'
    mode = 'binary'
    message = message.encode('utf-16be')
    to_send = struct.pack('!IIH', cookie, cookie, channel)
    if whisper: to_send += oscar.util.tlv(1)
    if reflect: to_send += oscar.util.tlv(6)
    to_send += oscar.util.tlv(5,
                              oscar.util.tlv_list
                              ((4, content_type),
                               (2, 'unicode-2-0'),
                               (3, o.lang),
                               (5, mode),
                               (1, message)))

    return 0x0e, 0x05, to_send

def x0e_x06(o, sock, data):
    '''
    SNAC (xe, x6): Incoming chat message

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_06.html}
    '''
    tlv_types = {1:'reflection', 3:'sender', 5:'message'}

    fmt = (('cookie', 'Q'),
           ('chan', 'H'),
           ('tlvs', 'named_tlvs', -1, tlv_types))

    cookie, chan, tlvs, data = oscar.unpack(fmt, data)
    assert not data

    sender, data = oscar.unpack((('info', 'userinfo'),),tlvs.sender)
    assert not data

    tlv_types = {1:'message', 2:'encoding', 3:'lang'}
    tlvs.message, data = oscar.unpack((('info', 'named_tlvs', -1, tlv_types),),
                                      tlvs.message)
    assert not data
    message = tlvs.message['message']

    try:
        encoding = tlvs.message['encoding']
        message = oscar.decode(message, encoding)
    except Exception:
        traceback.print_exc()

    buddy = o.get_buddy(sender.name)
    convo = sock_convo(o, sock)

    if buddy is not o.self_buddy:
        o._forward_message_to_convo(convo, buddy, message)

def x0e_x07(o, sock, data):
    '''
    SNAC (xe, x7): Evil request

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_07.html}
    '''
    raise NotImplementedError

def x0e_x08(o, sock, data):
    '''
    SNAC (xe, x8): Evil response

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_08.html}
    '''
    raise NotImplementedError

def x0e_x09(o, sock, data):
    '''
    SNAC (xe, x9): Chat error or data

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_09.html}
    '''
    raise oscar.SnacError((0x0e, x0e_name), (None, 'Chat error'), (None, None))

def x0e_x26(o, sock, data):
    '''
    SNAC (xe, x26): Chat room info?

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_26.html}
    '''
    fmt = (('num', 'H'),
           ('tlvs', 'tlv_list', 'num'))

    __, tlvs, data = oscar.unpack(fmt, data)
    assert not data

    log.info('chat room info?')
    log.info(pformat(tlvs))

def x0e_x30(o, sock, data):
    '''
    SNAC (xe, x30): Room information?

    reference: U{http://iserverd.khstu.ru/oscar/snac_0e_30.html}
    '''

    return # unknown data: room information? unpacking as buddynames is incorrect.
    
    fmt = (('bnames', 'list', 'pstring'),)
    bnames, data = oscar.unpack(fmt, data)
    assert not data
    c = sock_convo(o, sock)
    for bname in bnames: c.buddy_join(bname)

def sock_convo(o, sock):
    for k, v in o.sockets.items():
        v = getattr(v, 'sock', v) # if it's a SnacQueue

        if v is sock and isinstance(k, basestring) and k != 'bos':
            assert k in o.conversations
            return o.conversations[k]
