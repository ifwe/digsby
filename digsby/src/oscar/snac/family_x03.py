'''
Family 3

buddy list management
'''

import struct, logging, oscar
from util.primitives.funcs import do
from datetime import datetime
unpack_int = lambda v: struct.unpack('!I', v)[0]

subcodes = {}
log = logging.getLogger('oscar.snac.x03')

x03_name="Buddy List management"

def x03_init(o, sock, cb):
    ###
    #>>>SNAC(03,02)       Client ask server BLM service limitations
    #<<<SNAC(03,03)       Server replies via BLM service limitations
    ###
    log.info('initializing')
    cb_args = dict(req=True, cb=oscar.snac.x03_x03, o=o)
    sock.send_snac(*oscar.snac.x03_x02(), **cb_args)
    cb()
    log.info('finished initializing')

def x03_x01(o, sock, data):
    '''
    SNAC (x3, x1): Buddy List management Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x03, (errcode, errmsg), (subcode, submsg))

def x03_x02():
    '''
    SNAC (x3, x2): Request BLM params

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_02.html}
    '''
    return 0x03, 0x02

def x03_x03(sock, data, o):
    '''
    SNAC (x3, x3): BLM limits response

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_03.html}
    '''
    assert (data.hdr.fam, data.hdr.sub) == (0x03, 0x03)
    format = (('tlvs','tlv_dict'),)
    tlvs, data = oscar.util.apply_format(format, data.data)
    assert not data

    max_contacts = max_watchers = max_notifications = None

    if 1 in tlvs:
        max_contacts = tlvs[1]
    if 2 in tlvs:
        max_watchers = tlvs[2]
    if 3 in tlvs:
        max_notifications = tlvs[3]

def x03_x04(sns):
    '''
    SNAC (x3, x4): add buddy to list

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_04.html}
    '''

    return 0x03, 0x04, sn_list(sns)

def x03_x05(sns):
    '''
    SNAC (x3, x5): remove buddy from list

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_05.html}
    '''

    return 0x03, 0x05, sn_list(sns)

def x03_x06(o, sock, data):
    '''
    SNAC (x3, x6): query for list of watchers (supported?)

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_06.html}
    '''
    return 0x03, 0x06

def x03_x07(o, sock, data):
    '''
    SNAC (x3, x7): watcher list response

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_07.html}
    '''
    rlist_fmt = (('rlist', 'list', 'pstring'),)
    rlist, data = oscar.unpack(rlist_fmt, data)
    assert not data

def x03_x08():
    '''
    SNAC (x3, x8): watcher sub request (wtf is this?)

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_08.html}
    '''
    raise NotImplementedError

def x03_x09(o, sock, data):
    '''
    SNAC (x3, x9): watcher notification

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_09.html}
    '''
    watcher_fmt = (('name', 'pstring'),
                   ('transition', 'H'))

    watchers = []
    while data:
        name, trans, data = oscar.unpack(watcher_fmt, data)
        watchers.append((name, trans))

def x03_x0a(o, sock, data):
    '''
    SNAC (x3, xa): Notification rejected!

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_0a.html}
    '''
    fmt = (('bnames', 'list', 'pstring'),)
    bnames, data = oscar.unpack(fmt, data)
    assert not data
    #TODO: notify user?
    do(log.info('Notification failed for %s', name) for name in bnames)

def x03_x0b(o, sock, data):
    '''
    SNAC (x3, xb): Oncoming buddy

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_0b.html}
    '''
    fmt = (('buddyinfo','list','userinfo'),)
    infos, data = oscar.unpack(fmt, data)
    assert not data

    for info in infos:
        b = o.buddies[info.name]

        if 'user_status_icq' in info:
            status, webaware = oscar.util.process_status_bits(info.user_status_icq)
        else:
            status = None
            webaware = False

        info.webaware = webaware

        if struct.unpack('!H', info.user_class)[0] & 0x20:
            status = 'away'

        if status is None:
            status = 'available'

        info.status = status

        old = b.status
        log.debug('oncoming buddy %s: %s -> %s', info.name, old, info.status)

        #
        # profile and away message timestamps
        #
        up_profile = up_away = False

        if 'profile_updated' in info:
            tstamp = unpack_int(info.profile_updated)
            up_profile = tstamp > b.profile_updated
        if 'away_updated' in info:
            tstamp = unpack_int(info.away_updated)
            up_away = tstamp > b.away_updated
        if 'mystery_updated' in info:
            tstamp = unpack_int(info.mystery_updated)
            up_profile = up_profile or tstamp > b.mystery_updated

        up_both = up_away or up_profile
        b.request_info(profile = up_both, away = up_both)

    o.buddies.update_buddies(infos)


def x03_x0c(o, sock, data):
    '''
    SNAC (x3, xc): Offgoing buddy

    reference: U{http://iserverd.khstu.ru/oscar/snac_03_0c.html}
    '''
    infos, data = oscar.unpack((('_', 'list', 'userinfo'),), data)
    assert not data
    for info in infos:
        info.status = 'offline'
    o.buddies.update_buddies(infos)

def sn_list(names):
    return ''.join(struct.pack('!B%ds' % len(sn), len(sn), sn) for sn in names)
