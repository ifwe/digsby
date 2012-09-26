import logging

import struct
import oscar

x07_name="Admin"
log = logging.getLogger('oscar.snac.x07')
subcodes = {
            0x01:       'validate nickame',
            0x02:       'validate password',
            0x03:       'validate e-mail',
            0x04:       'service temporarily unavailable',
            0x05:       'field change temporarily unavailable',
            0x06:       'invalid nickname',
            0x07:       'invalid password',
            0x08:       'invalid e-mail',
            0x09:       'invalid registration preference',
            0x0A:       'invalid old password',
            0x0B:       'invalid nickname length',
            0x0C:       'invalid password length',
            0x0D:       'invalid e-mail length',
            0x0E:       'invalid old password length',
            0x0F:       'need old password',
            0x10:       'read only field',
            0x11:       'write only field',
            0x12:       'unsupported type',
            0x13:       'all other errors',
            0x14:       'bad snac',
            0x15:       'invalid account',
            0x16:       'deleted account',
            0x17:       'expired account',
            0x18:       'no database access',
            0x19:       'invalid database fields',
            0x1A:       'bad database status',
            0x1B:       'migration cancel',
            0x1C:       'internal error',
            0x1D:       'pending request',
            0x1E:       'not dt status',
            0x1F:       'outstanding confirm',
            0x20:       'no e-mail address',
            0x21:       'over limit',
            0x22:       'e-mail host fail',
            0x23:       'dns fail',
}

tlv_types = {
             0x01:'screenname',
             0x11:'email',
             0x13:'reg_status',
             0x08:'errcode',
             0x04:'errurl',

             }

def x07_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x07_x01(o, sock, data):
    '''
    SNAC (x7, x1): Admin Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x07, (errcode, errmsg), (subcode, submsg))

def x07_x02(tlv_id):
    '''
    SNAC (x7, x2): Request account info

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_02.html}
    '''

    '''
    tlv_ids: 1 is request nickname, x11 is email request,
             x13 is registration status
    '''

    if isinstance(tlv_id, basestring):
        tlv_id = dict(nickname = 0x1,
                      email = 0x11,
                      registration = 0x13)[tlv_id]

    return 0x07, 0x02, oscar.util.tlv(tlv_id)

def x07_x03(o, sock, data):
    '''
    SNAC (x7, x3): Requested account info

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_03.html}
    '''
    fmt = (
           ('flags', 'H'),
           ('num_tlvs', 'H'),
           ('tlvs', 'tlv_dict', 'num_tlvs')
           )

    #TODO: this may not be correct, docs say 1 and 2 are both read
    read = 1
    write = 2

    flags, __, tlvs, data = oscar.unpack(fmt, data)

    assert not data

    can_read = flags & read
    can_write = flags & read

    if 8 in tlvs:
        subcode = struct.unpack('!H', tlvs[8])[0]
        errmsg = tlvs[4]

        raise oscar.SnacError(0x07, (subcode, errmsg), (subcode, subcodes.get(subcode, 'unknown')))

    return tlvs

def x07_x04(screenname=None, email=None, password=(None, None), reg_status=None):
    '''
    SNAC (x7, x4): Request change account info

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_04.html}
    '''
    to_send = []
    if screenname is not None:
        to_send.append(oscar.util.tlv(0x01, screenname))

    if email is not None:
        to_send.append(oscar.util.tlv(0x11, email))

    old_password, new_password = password
    if all(password):
        to_send.append(oscar.util.tlv(0x12, old_password))
        to_send.append(oscar.util.tlv(0x02, new_password))

    if reg_status is not None:
        to_send.append(oscar.util.tlv(0x13, 2, reg_status))

    return 0x07, 0x04, ''.join(to_send)

def x07_x05(o, sock, data):
    '''
    SNAC (x7, x5): Change account info ack

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_05.html}
    '''
    return x07_x03(o, sock, data) # they look the same according to the docs...

def x07_x06():
    '''
    SNAC (x7, x6): Account confirm request

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_06.html}
    '''
    return 0x07, 0x06

def x07_x07(o, sock, data):
    '''
    SNAC (x7, x7): account confirm response

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_07.html}
    '''
    stat_codes = {0x00: _('You should receive an email with confirmation instructions shortly.'),
                  0x1e: _('Your account is already confirmed.'),
                  0x23: _('There was an unknown server error.'),
                  }

    error, data = oscar.unpack((('code', 'H'),), data)
    if data:
        tlv, data = oscar.unpack((('tlv', 'tlv'),), data)
        url = tlv.v
    else:
        url = 'This is not an error.'

    assert not data
    status_msg = stat_codes[error]

    o.hub.user_message(status_msg, _('Confirm Account: {username}').format(username=o.self_buddy.name))

def x07_x08(o, sock, data):
    '''
    SNAC (x7, x8): account delete request

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_08.html}
    '''
    return 0x07, 0x08

def x07_x09(o, sock, data):
    '''
    SNAC (x7, x9): Account delete ack

    reference: U{http://iserverd.khstu.ru/oscar/snac_07_09.html}
    '''
    if data:
        fmt = (('tlvs', 'tlv_dict'),)

        tlvs, data = oscar.unpack(fmt, data)
        assert not data

        subcode, tlvs[8] = oscar.unpack((('code', 'H'),),tlvs[8])
        errmsg = tlvs[4]

        raise oscar.SnacError((0x07, x07_name), (None, errmsg), (subcode, subcodes[subcode]))
