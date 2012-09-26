from __future__ import with_statement

import struct
import logging
import util
import oscar

x01_name="Generic"
log = logging.getLogger('oscar.snac.x01')

version = 4

tlv_types = {0x05: 'server_addr',
             0x06: 'cookie',
             0x0d: 'service_id',}

subcodes = {}

ignorable = [
             (1,8),            # not supported by user
             ]



@util.gen_sequence
def x01_init(o, sock, cb):
    log.info('initializing')
    me = (yield None)
    sock.send_snac(*oscar.snac.x01_x06(), req=True, cb=me.send)
    rate_classes, rate_groups = o.gen_incoming((yield None))
    sock.send_snac(*oscar.snac.x01_x08(rate_classes))
    status = (o.status != 'online') * 0x100

    sock.send_snac(*oscar.snac.x01_x1e(o))
    cb()
    log.info('finished initializing')

def x01_x01(o, sock, data):
    '''
    SNAC (x1, x1): Generic Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_01.html}
    '''

    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None

    e = oscar.snac.SnacError(0x01, (errcode, errmsg), (subcode, submsg))
    log.warning('SNACError: %r', e)

    if (1, errcode) not in ignorable:
        raise e

def x01_x02(families):
    '''
    SNAC (x1, x2): Client ready

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_02.html}
    '''
    to_send = ''
    for family in families:
        fam = getattr(oscar.snac, 'family_x%02x' % family, None)

        if fam is None:
            continue

        version  = getattr(fam, 'version',  oscar.snac.version)
        dll_high = getattr(fam, 'dll_high', oscar.snac.dll_high)
        dll_low  = getattr(fam, 'dll_low',  oscar.snac.dll_low)

        to_send += struct.pack('!HHHH', family, version, dll_high, dll_low)

    log.debug('sending client ready')
    return 0x01, 0x02, to_send

def x01_x03(o, sock, data):
    '''
    SNAC (x1, x3): Server ready

    This is a list of families the server supports. Generally,
    The BOS server supports about 10-12 families, and other
    servers support family x01 and one other (applicable to the
    kind of server).

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_03.html}
    '''
    snac_format = (('families', 'list', 'H'),)
    families, data = oscar.unpack(snac_format, data)
    assert not data
    return families

def x01_x04(service_id):
    '''
    SNAC (x1, x4): New service request

    Used to request a new service from BOS. In most cases this is just
    sending the family number to the server, but for chat an additional
    TLV structure must be sent.

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_04.html}
    '''
    if isinstance(service_id, basestring):
        assert service_id != 'bos'
        family = 0x0e
        slen = len(service_id)
        exch = int(service_id.split('-')[1])
        additional = oscar.util.tlv(1, struct.pack
                                    ('!HB%dsH' % slen,
                                     exch, slen, service_id, 0))
    elif isinstance(service_id, int):
        family = service_id
        additional = ''
    else:
        assert False
    return 0x01, 0x04, struct.pack('!H', family) + additional

def x01_x05(o, sock, data):
    '''
    SNAC (x1, x5): Service redirect

    The server is telling is to go to another server. This happens
    initially at signon and any time a service is successfully requested

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_05.html}
    '''
    format = (('tlvs', 'named_tlvs', -1, tlv_types),)
    tlvs, data = oscar.unpack(format, data)
    id, addr, cookie = tlvs.service_id, tlvs.server_addr, tlvs.cookie
    (id,) = struct.unpack('!H', id)

    assert all([id, addr, cookie])
    return id, addr, cookie

def x01_x06():
    '''
    SNAC (x1, x6): Rate limit request

    This is just a request, so there is no data.
    The server should respond with x01, x07

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_06.html}
    '''

    return 0x01, 0x06

def x01_x07(o, sock, data):
    '''
    SNAC (x1, x7): Rate limit information

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_07.html}
    '''
    log.info('got rate info')

    ch_ids = [k for k,v in o.sockets.items()
              if v is sock and isinstance(k, basestring)]

    snac_format = (('num_rates', 'H'),
                   ('rate_classes', 'rate_class_list', 'num_rates'),
                   ('rate_groups',  'rate_group_list', 'num_rates'))
    num_rates,     \
    rate_classes,  \
    rate_groups,   \
    data = oscar.unpack(snac_format, data)
    log.info('Received %d rate classes, %d rate groups',
             len(rate_classes), len(rate_groups))

    assert not data
    sock.apply_rates(rate_classes, rate_groups)
    return rate_classes, rate_groups

def x01_x08(rate_classes):
    '''
    SNAC (x1, x8): Rate info acknowledgement

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_08.html}
    '''
    log.info('sending rate acknowledgement')
    ids = [rate.id for rate in rate_classes]
    to_send = ''.join(struct.pack('!H', id) for id in ids)
    return 0x01, 0x08, to_send

def x01_x09(o, sock, data):
    '''
    SNAC (x1, x9): 0x1, 0x9: Server deleted a rate group and you didn't handle it

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_09.html}
    '''
    rate_classes = oscar.unpack((('rate_classes', 'list', 'H'),), data)
    with sock.rate_lock:
        for (id, index) in ((rc.id, sock.rate_classes.index(rc)) for rc in sock.rate_classes):
            if id in rate_classes: del sock.rate_classes[index]

def x01_x0a(o, sock, data):
    '''
    SNAC (x1, xa): Rate info change

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_0a.html}
    '''
    rate_codes = {0x0001: 'Rate limits parameters changed',
                  0x0002: 'Rate limits warning (current level < alert level)',
                  0x0003: 'Rate limit hit (current level < limit level)',
                  0x0004: 'Rate limit clear (current level become > clear level)',}

    msg, data = oscar.unpack((('msg','H'),), data)
    log.warning(rate_codes.get(msg, 'Unknown rate message %r' % msg))
    
    rates, data = oscar.unpack((('rate_info', 'rate_class_list', -1),), data)
    sock.apply_rates(rates, {})


    assert not data, repr(data)


def x01_x0b(o, sock, data):
    '''
    SNAC (x1, xb): Server pause

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_0b.html}
    '''
    if data:
        format = (('families', 'list', 'H'),)
        families, data = oscar.unpack(format, data)
        assert not data
    else:
        families = []

    o.pause_service(sock, families)


def x01_x0c(families):
    '''
    SNAC (x1, xc): Client pause ack

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_0c.html}
    '''
    return 0x01, 0x0c, ''.join(struct.pack('!H', fam) for fam in families)

def x01_x0d(o, sock, data):
    '''
    SNAC (x1, xd): Server resume

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_0d.html}
    '''
    if data:
        format = (('families', 'list', 'H'),)
        families, data = oscar.unpack(format, data)
        assert not data
    else:
        families = []

    o.unpause_service(sock, families)

def x01_x0e():
    '''
    SNAC (x1, xe): Request self info

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_0e.html}
    '''
    return 0x01, 0x0e

def x01_x0f(o, sock, data):
    '''
    SNAC (x1, xf): Self info reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_0f.html}
    '''
    selfinfo, data = oscar.unpack((('info', 'userinfo'),), data)

    if 'user_status_icq' in selfinfo:
        selfinfo.status, selfinfo.webaware = oscar.util.process_status_bits(selfinfo.user_status_icq)
        log.info('self buddy status: %r', selfinfo.status)

    try:
        o.self_buddy.update(selfinfo)
    except Exception:
        import traceback;traceback.print_exc()

def x01_x10(o, sock, data):
    '''
    SNAC (x1, x10): 0x1, 0x10: You've been eviled!

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_10.html}
    '''
    warn_level, data = oscar.unpack((('warn', 'H'),), data)

    user_infos = []
    while data:
        uinfo, data = oscar.unpack((('info', 'userinfo'),), data)
        user_infos.append(uinfo)

    return warn_level, user_infos

def x01_x11(time):
    '''
    SNAC (x1, x11): Set idle time

    time is how long you've been idle, so 60 means you've been
    idle for a minute

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_11.html}
    '''
    return 0x01, 0x11, struct.pack('!I', time)

def x01_x12(o, sock, data):
    '''
    SNAC (x1, x12): Server migration notice and information

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_12.html}
    '''
    format = (('num_fams', 'H'),
              ('families', 'H', 'num_fams'),
              ('tlvs', 'tlv_dict'))

    __, families, tlvs, data = oscar.unpack(format, data)
    server_addr, cookie = tlvs[5], tlvs[6]

    assert not any(o.sockets[fam]
                   for fam in families
                   if fam in o.sockets and
                   isinstance(o.sockets[fam], oscar.SnacQueue))

    sock_ids = set(list(families) + [s_id for (s_id, s) in o.sockets.items() if s is sock])

    server = util.srv_str_to_tuple(server_addr, o.server[-1])
    bos, sock.bos = sock.bos, False # If our old socket was the BOS socket, it isn't anymore.

    if bos:
        sock_ids.add('bos')

    o.connect_socket(server, cookie, sock_ids, bos = bos)

def x01_x13(o, sock, data):
    '''
    SNAC (x1, x13): Got message of the day

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_13.html}
    '''
    # this is ignored in oscar socket, so we should never get here!
    assert (0x01, 0x13) in sock.ignored_snacs

def x01_x14(idle_time=True, member_time=True):
    '''
    SNAC (x1, x14): Set privacy flags

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_14.html}
    '''
    idle = idle_time*1
    member = member_time*2

    return 0x01, 0x14, struct.pack('!I', idle | member)

def x01_x15(o, sock, data):
    '''
    SNAC (x1, x15): Well-known URLs

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_15.html}
    '''
    return NotImplemented

def x01_x16(o, sock, data):
    '''
    SNAC (x1, x16): NOP (keep-alive packet)

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_16.html}
    '''
    return 0x01, 0x16

def x01_x17(o, families, sock):
    '''
    SNAC (x1, x17): Tell server what families/versions we support

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_17.html}
    '''
    to_send = []
    for family in families:
        try:
            fam = getattr(oscar.snac, 'family_x%02x' % family)
        except AttributeError:
            log.info('Unknown/unsupported family: %d (0x%02x)', family, family)
            continue

        if family in o.sockets and isinstance(o.sockets[family], oscar.SnacQueue):
            o.sockets[family].sock = sock
        else:
            o.sockets[family] = sock
        version = getattr(fam, 'version', oscar.snac.version)
        to_send.append(struct.pack('!HH', family, version))

    return 0x01, 0x17, ''.join(to_send)

def x01_x18(o, sock, data):
    '''
    SNAC (x1, x18): Server service versions response

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_18.html}
    '''
    snac_format = (('fams', 'list', 'H'),)
    fams_vers, data = oscar.unpack(snac_format, data)
    assert not data
    family_versions = dict(zip(fams_vers[::2], fams_vers[1::2]))

    #assert all(fam in o.sockets for fam in family_versions)

    sock.server_snac_versions = family_versions

    return True

def x01_x1e(o):
    '''
    SNAC (x1, x1e): Set extended status/location info (also for direct connect info)

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_1e.html}
    '''

    '''
    From http://www.micq.org/ICQ-OSCAR-Protocol-v7-v8-v9/Packets/Fam1/Com30.html
    '''
    statuses = {
     'available'      : 0x00000000,
     'online'         : 0x00000000,     #The user is online. / Set status to online.
     'offline'        : 0xffffffff,     #The user is offline. / Set status to offline.
     'invisible'      : 0x00000100,     #Set status to invisible.
     'do not disturb' : 0x00000013,     #Set status to do not disturb.
     'busy'           : 0x00000011,     #Set status to occupied.
     'not available'  : 0x00000005,     #Set status to not available.
     'away'           : 0x00000001,     #Set status to away.
     'free for chat'  : 0x00000020,     #Set status to free for chat.
    }

    b = o.self_buddy
    if b.invisible:
        status = statuses['invisible']
    else:
        status = statuses.get(o.status.lower(), statuses['away'])

    webaware = 0x00010000 * o.webaware

    status  |= 0x10000000
    status  |= webaware

    if b.avail_msg is not None:
        message = b.avail_msg
        if isinstance(message, unicode):
            message = message.encode('utf8')

        extraflag = 0
        if o.icq:
            message += oscar.util.tlv(0x01, 'utf-8')
            message += oscar.util.tlv(0x0e, '')
            extraflag = 1

        mlen = len(message)
        mbytes = struct.pack('!H%dsH' % mlen, mlen, message, extraflag)
    else:
        mbytes = ''

    tlvs = ((0x1d, oscar.util.tflv(2,4,mbytes)),
            (0x06, 4, status))

    return 0x01, 0x1e, oscar.util.tlv_list(*tlvs)

def x01_x1f(o, sock, data):
    '''
    SNAC (x1, x1f): Evil AIM prove yourself packet

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_1f.html}
    '''
    raise oscar.LoginError('Evil AIM prove yourself packet')

def x01_x20(o, sock, data):
    '''
    SNAC (x1, x20): Response to prove yourself

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_20.html}
    '''
    raise NotImplementedError

def x01_x21(o, sock, data):
    '''
    SNAC (x1, x21): Set Extended status info (buddy icon and available message)

    reference: U{http://iserverd.khstu.ru/oscar/snac_01_21.html}
    '''
    tlvs, data = oscar.unpack((('tlvs', 'tlv_list'),), data)
    assert not data

    if 1 in tlvs:
        fmt = (('flags', 'B'),
               ('hash_len', 'B'),
               ('hash', 'B', 'hash_len'),)
        icon_flags, __, hash, tlvs[1] = oscar.unpack(fmt, tlvs[1])
        assert not tlvs[1]
        o.self_buddy.icon_hash = hash

    if 2 in tlvs:
        fmt = (('len', 'H'),
               ('msg', 's', 'len'),)

        __, msg, tlvs[2] = oscar.unpack(fmt, tlvs[2])
        assert not tlvs[2]
        o.self_buddy._avail_msg = msg
