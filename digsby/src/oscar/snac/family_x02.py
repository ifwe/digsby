import struct
import logging

import util
import oscar

x02_name="Location"
log = logging.getLogger('oscar.snac.x02')
subcodes = {}

# ignorable error messages
ignorable = [
             (2,4),            # Recipient is not logged in
             ]

@util.gen_sequence
def x02_init(o, sock, cb):
    ####
    #>>>SNAC(02,02)       Client ask server location service limitations
    #<<<SNAC(02,03)       Server replies via location service limitations
    #>>>SNAC(02,04)       Client sends its capabilities / profile to server
    ###
    log.info('initializing')
    me = (yield None); assert me
    sock.send_snac(*oscar.snac.x02_x02(), req=True, cb=me.send)
    tlvs = o.gen_incoming((yield None))

    o.MAX_PROF_HTML = struct.unpack('!H', tlvs[1])[0]
    max_caps = tlvs[2]

    caps = oscar.capabilities.feature_capabilities

    my_caps = []
    for i in range(min(len(caps), max_caps)):
        my_caps.append(caps[i])

    o.self_buddy._capabilities = my_caps

    sock.send_snac(*oscar.snac.x02_x04(o))
    cb()
    log.info('finished initializing')


def x02_x01(o, sock, data):
    '''
    SNAC (x2, x1): Location Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    if (2, errcode) not in ignorable:
        raise oscar.snac.SnacError(0x02, (errcode, errmsg), (subcode, submsg))

def x02_x02():
    '''
    SNAC (x2, x2): Request limitation params for Location group

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_02.html}
    '''
    return 0x02, 0x02

def x02_x03(o, sock, data):
    '''
    SNAC (x2, x3): Location limitations response

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_03.html}
    '''
    format = (('tlvs', 'tlv_dict'),)
    tlvs, data = oscar.util.apply_format(format, data)
    assert not data

    return tlvs

def x02_x04(o):
    '''
    SNAC (x2, x4): Set user info

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_04.html}
    '''
    b = o.self_buddy
    encoding = 'text/x-aolrtf; charset="utf-8"'
    profile = b.profile
    if profile is None:
        profile = ''
    if isinstance(profile, unicode):
        profile = profile.encode('utf8')

    away_msg = b.away_msg
    if away_msg is None:
        away_msg = ''
    if isinstance(away_msg, unicode):
        away_msg = away_msg.encode('utf-8')

    capabilities = b.capabilities

    tlvs = ((1, encoding),
            (2, profile),
            (3, encoding),
            (4, away_msg),
            (5, ''.join(capabilities)))

    return 0x2, 0x4, oscar.util.tlv_list(*tlvs)

def x02_x05(sn, infotype):
    '''
    SNAC (x2, x5): Request user info

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_05.html}
    '''
    assert infotype in range(1,5)

    snlen = len(sn)
    return 0x02, 0x05, struct.pack('!HB%ds' % snlen, infotype, snlen, sn)

def x02_x06(o, sock, data):
    '''
    SNAC (x2, x6): Requested User information

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_06.html}
    '''

    tlv_types = { 1:'prof_enc',
                  2:'profile',
                  3:'away_enc',
                  4:'away_msg',
                  5:'capabilities', }
    fmt = (('_1', 'userinfo'),
           ('_2', 'named_tlvs', -1, tlv_types))

    userinfo, tlvs, data = oscar.unpack(fmt, data)

    # Decode profile and away message.
    if 'profile' in tlvs:
        tlvs['profile'] = oscar.decode(tlvs['profile'], tlvs['prof_enc'])

    if 'away_msg' in tlvs and tlvs['away_msg']:
        tlvs['away_msg'] = oscar.decode(tlvs['away_msg'], tlvs['away_enc'])

    userinfo.update(tlvs)
    buddy = o.buddies[userinfo.name]
    log.debug('Got userinfo: %r', userinfo)
    buddy.update(userinfo)
    #buddy._set_status(buddy.status)

def x02_x07():
    '''
    SNAC (x2, x7): Watcher sub request (??)

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_07.html}
    '''
    return 0x02, 0x07, struct.pack('!H',0)

def x02_x08(o, sock, data):
    '''
    SNAC (x2, x8): Watcher notification

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_08.html}
    '''
    format = (('names', 'list', 'pstring'),)
    names, data = oscar.apply_format(format, data)
    assert not data

def x02_x09(**kwargs):
    '''
    SNAC (x2, x9): Request to Update directory info

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_09.html}
    '''
    tlv_names = {
                 'first_name':    0x01,
                 'last_name':     0x02,
                 'middle_name':   0x03,
                 'maiden_name':   0x04,
                 'country':       0x06,
                 'state':         0x07,
                 'city':          0x08,
                 'unknown':       0x0a,
                 'nickname':      0x0c,
                 'zipcode':       0x0d,
                 'street_addr':   0x21,
                 }

    return 0x02, 0x09, ''.join(oscar.util.tlv(tlv_names[k], len(v), v)
                               for (k,v) in kwargs.items() if k in tlv_names)

def x02_x0a(o, sock, data):
    '''
    SNAC (x2, xa): Reply to update directory info

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_0a.html}
    '''
    teh_win, data = oscar.unpack((('result','H'),), data)
    assert not data

    if not teh_win:
        raise oscar.SnacError(0x02, (None, 'Directory info update failed'), (None, None))

def x02_x0b(sn):
    '''
    SNAC (x2, xb): Unknown info request

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_0b.html}
    '''
    return 0x02, 0x0b, struct.pack('!B%ds'%len(sn), len(sn), sn)

def x02_x0c(o, sock, data):
    '''
    SNAC (x2, xc): Unknown info response (may contain tlv)

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_0c.html}
    '''
    raise NotImplementedError

def x02_x0f(interests):
    '''
    SNAC (x2, xf): Update user directory interests

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_0f.html}
    '''
    to_send = oscar.util.tlv(0x0a, 4, 0)
    if len(interests) > 5:
        interests = interests[:5]

    for interest in interests:
        to_send += oscar.util.tlv(0x0b, interest)

    return 0x02, 0x0f, to_send

def x02_x10(o, sock, data):
    '''
    SNAC (x2, x10): User directory interest reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_10.html}
    '''
    teh_win, data = oscar.unpack((('result','H'),), data)
    assert not data

    if not teh_win:
        raise oscar.SnacError(0x02, (None, 'Interest info update failed'), (None, None))

def x02_x15(sn, profile = True, away = True, caps = True, cert = True):
    '''
    SNAC (x2, x15): User info query

    reference: U{http://iserverd.khstu.ru/oscar/snac_02_15.html}
    '''
    assert any([profile, away, caps, cert])

    prof = (1 << 0) * profile
    away = (1 << 1) * away
    caps = (1 << 2) * caps
    cert = (1 << 3) * cert

    request_bits = prof | away | caps | cert

    snlen = len(sn)
    return 0x02, 0x15, struct.pack('!IB%ds' % snlen, request_bits, snlen, sn)
