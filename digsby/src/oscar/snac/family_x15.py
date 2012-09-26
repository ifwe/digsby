import struct
import logging
import datetime
import util
import traceback
import oscar
import icq_country

x15_name="ICQ extensions"
version = 2
log = logging.getLogger('oscar.snac.x15')
subcodes = {}


SUCCESS = 10

def icq_reqid():
    i = 0
    while True:
        i = (i + 1) % 0xFFFF
        yield i
reqids = icq_reqid()

def lnts(s):
    '''
    Make a Little eNdian null-Terminated String
    '''
    # TODO: assert unicode entering, encode to unicode.
    s = s + '\x00'
    return struct.pack('<H', len(s))+s

def x15_init(o, sock, cb):
    log.info('initializing')

#    sock.send_snac(*x15_x02(o,2000,
#                            struct.pack('<H', 0xc3a)+
#                            '\x0c\x03\x01\x00\x00'+
#                            '\xf8\x02\x01\x00\x00'))
    sock.send_snac(*request_icq_info(o, o.username))
    cb()

    log.info('finished initializing')

def x15_x01(o, sock, data):
    '''
    SNAC (x15, x1): ICQ extensions Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_15_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x15, (errcode, errmsg), (subcode, submsg))

def x15_x02(o, req_type, data='', uid=None):
    '''
    SNAC (x15, x2): To Server

    reference: U{http://iserverd.khstu.ru/oscar/snac_15_02.html}
    '''

    if not o.icq:
        return

    reqid = reqids.next()
    assert reqid not in o.icq_req_cbs
    o.icq_req_cbs[reqid] = uid

    return 0x15, 0x02, \
    oscar.util.tlv(1, struct.pack('<HIHH', 8+len(data), int(o.username), req_type,reqid) + data)

def x15_x03(o, sock, data):
    '''
    SNAC (x15, x3): From Server

    reference: U{http://iserverd.khstu.ru/oscar/snac_15_03.html}
    '''
    tlv, data = oscar.util.s_tlv(data)
    assert not data
    data = tlv.v

    fmt = '''
          size    H
          uid     I
          reqtype H
          reqid   H
          '''.split()

    fmt = zip(fmt[::2],fmt[1::2])

    sz, uid, reqtype, reqid, data = oscar.unpack(fmt, data, '<')
    assert len(data) == (sz - 8)

    try:
        f = getattr(oscar.snac, 'icq_srv_%04x'%reqtype)
    except AttributeError:
        print 'received ICQ response: %d %04x reqid=%d / %s' % (uid, reqtype, reqid,util.to_hex(data))
        return

    uid = o.icq_req_cbs.get(reqid, (lambda: None, (), {}))
    f(o, uid, data)

def request_offline_messages_icq(o):
    log.info('Requesting ICQ offline messages')

    def ack_msgs(*a, **k):
        o.send_snac(*ack_offline_msgs(o))

    return x15_x02(o,0x3c, struct.pack('<H',1)) + (ack_msgs,)


def icq_cli_003e(o):
    return x15_x02(o, 0x3e)
ack_offline_msgs = icq_cli_003e

def icq_srv_0041(o, uid, data):
    '''
    Offline message from server

    xx xx           word (LE)      data chunk size (TLV.Length-2)
    xx xx xx xx     dword (LE)     msg target uin
    41 00           word (LE)      data type: offline messge
    02 00           word (LE)      request sequence number

    xx xx xx xx     dword (LE)     message sender uin
    xx xx           word (LE)      year when message was sent
    xx              char           month when message was sent
    xx              char           day when message was sent
    xx              char           hour (GMT) when message was sent
    xx              char           minute when message was sent
    xx              char           message type
    xx              char           message flags
    xx xx           char           message string length
    xx .. xx 00     char*          message string (asciiz)
    '''

    fmt = '''
          sender        I
          year          H
          month         B
          day           B
          hour          B
          minute        B
          mtype         B
          mflags        B
          mlength       H
          '''.split()

    fmt = zip(fmt[::2],fmt[1::2])
    sender, year, month, day, hour, minute, mtype, mflags, mlength, message = oscar.unpack(fmt, data, '<')

    try:
        assert mlength == len(message)
    except Exception:
        print (mlength, len(message))

    # TODO: Decode message to unicode.

    try:
        log.info('Trying to fuzzy decode message with locale + utf8')
        message = message.decode('fuzzy utf8')
    except Exception, e:
        log.error('error decoding message: %r', e)
        traceback.print_exc()

    me, sender = str(uid), str(sender)
    try:
        assert me == o.username
    except Exception:
        print me, o.username

    for key in 'year month day hour minute mtype mflags mlength'.split():
        print key, locals()[key]

    timestamp = datetime.datetime(year, month, day, hour, minute)

    oscar.snac.super_old_style_msg(o, util.Storage(name=sender), snd_uin=uid, msg=message, msg_type=mtype, timestamp=timestamp, offline=True)

def icq_srv_0042(o, uid, data):
    assert len(data) == 1 and ord(data) == 0
    o.send_snac(*ack_offline_msgs(o))

def icq_cli_07d0(o, data, uid):
    return x15_x02(o, 0x07d0, data, uid)

#def icq_cli_07d0_0c3a(o, data, uid):
#    return x15_x02(o, 0x07d0, data, uid)
#
#def set_require_auth(o, require):
#    return icq_cli_07d0_0c3a(o, struct.pack('!10B', 0xf8, 0x02, 0x01, 0x00,
#                                            int(bool(require)), 0x0c, 0x03, 0x01,
#                                            0x00, 0x00))

def icq_cli_07d0_03ea(o):

    data = [struct.pack('<H', 0x03ea)]
    b = o.self_buddy
    for attr in 'nick first last email city state phone fax street cellular zip'.split():
        data.append(lnts(getattr(b, attr, '')))

    data.append(struct.pack('<H', getattr(b, 'country', 0)))
    data.append(chr(getattr(b, 'timezone', 0)))
    data.append(chr(getattr(b, 'publish', False)))

    return icq_cli_07d0(o, ''.join(data))

send_general_info = icq_cli_07d0_03ea

def icq_cli_07d0_03f3(o):
    '''
    LNTS      xx xx ...     CITY         The work city.
    LNTS      xx xx ...     STATE        The work state.
    LNTS      xx xx ...     PHONE        The work phone number.
    LNTS      xx xx ...     FAX          The FAX number as a string.
    LNTS      xx xx ...     STREET       The work street address.
    LNTS      xx xx ...     ZIP          The work ZIP code.
    WORD.L    xx xx         COUNTRY      The work country code.
    LNTS      xx xx ...     COMPANY      The work company's name.
    LNTS      xx xx ...     DEPART       The work department.
    LNTS      xx xx ...     POSITION     The work position. (directly after DEPART)
    LNTS      xx xx ...     ZIP          The work ZIP code (huh, again?).
    WORD.L    xx xx         OCCUPATION   The work occupation.
    LNTS      xx xx ...     HOMEPAGE     the work home page.
    '''

    work = getattr(o.self_buddy, 'work',util.Storage())

    data = [struct.pack('<H', 0x03f3)]

    for attr in 'city state phone fax street zip'.split():
        data.append(lnts(getattr(work, attr, '')))

    data.append(struct.pack('<H', getattr(work, 'country', 0)))

    for attr in 'company department position zip'.split():
        data.append(lnts(getattr(work, attr, '')))

    data.append(struct.pack('<H', getattr(work, 'occupation', 0)))
    data.append(lnts(getattr(work, 'website', '')))

    return icq_cli_07d0(o, ''.join(data))

send_work_info = icq_cli_07d0_03f3

def icq_cli_07d0_03fd(o):
    '''
    WORD.L      xx xx      AGE       Your age.
    BYTE        xx         GENDER    Your gender.
    LNTS        xx xx ...  HOMEPAGE  Your personal home page.
    WORD.L      xx xx      YEAR      Your year of birth.
    BYTE        xx         MONTH     Your month of birth.
    BYTE        xx         DAY       Your day of birth.
    BYTE        xx         LANG1     Your first language.
    BYTE        xx         LANG2     Another language you speak.
    BYTE        xx         LANG3     Another language you speak.
    '''

    info = getattr(o.self_buddy, 'personal ',util.Storage())

    data = [struct.pack('<H', 0x03fd)]

    data.append(struct.pack('<H', getattr(info, 'age', 0)))
    data.append(struct.pack('<B', getattr(info, 'gender', 0)))
    data.append(lnts(getattr(info, 'website', 0)))
    data.append(struct.pack('<H', getattr(info, 'birthyear', 0)))

    for attr in 'month day lang1 lang2 lang3'.split():
        data.append(lnts(getattr(info, attr, 0)))

    return icq_cli_07d0(o, ''.join(data))

send_personal_info = icq_cli_07d0_03fd

def icq_cli_07d0_0406(o, profile):
    return icq_cli_07d0(o, struct.pack('<H', 0x0406) + lnts(profile))

send_icq_profile = icq_cli_07d0_0406

def icq_cli_07d0_040b(o, emails):
    count = len(emails)
    data = [struct.pack('<H', 0x040b)]
    data.append(struct.pack('<B', count))
    for email, visible in emails:
        data.append(struct.pack('<B', int(bool(visible))))
        data.append(lnts(email))

    return icq_cli_07d0(o, ''.join(data))
send_emails = icq_cli_07d0_040b

def icq_cli_07d0_0410(o, interests):
    count = len(interests)
    data = [struct.pack('<H', 0x0410)]
    data.append(struct.pack('<B', count))

    for topic, desc in interests:
        data.append(struct.pack('<H', topic))
        data.append(lnts(desc))

    return icq_cli_07d0(o, ''.join(data))
send_interests = icq_cli_07d0_0410

def icq_cli_07d0_041a(o, affils, orgs):
    data = [struct.pack('<H', 0x041a)]

    count = len(affils)
    data.append(struct.pack('<B', count))

    for kind, desc in affils:
        data.append(struct.pack('<H', kind))
        data.append(lnts(desc))

    count = len(orgs)
    data.append(struct.pack('<B', count))

    for kind, desc in orgs:
        data.append(struct.pack('<H', kind))
        data.append(lnts(desc))

    return icq_cli_07d0(o, ''.join(data))
send_backgrounds = icq_cli_07d0_041a

#def icq_cli_07d0_0424(o, require_auth, block_web, require_dc_auth=None):
#    dc_flag = 2 if require_dc_auth is None else require_dc_auth
#    return icq_cli_07d0(o, struct.pack('<HBBBB', 0x424, require_auth, block_web, dc_flag, 0), o.username)
#
#set_icq_privacy = icq_cli_07d0_0424


def icq_cli_07d0_0c3a(o):

    return icq_cli_07d0(o, struct.pack('<H', 0xc3a) +
                        struct.pack('<HHBBBBBB',
                                    0x030c, 0x0001, o.webaware,
                                    0xf8, 0x02, 0x01, 0x00, not o.auth_required),
                        int(o.username))

set_icq_privacy = icq_cli_07d0_0c3a

def icq_cli_07d0_042e(o, new_password):
    return icq_cli_07d0(o, struct.pack('<H', 0x042e) + lnts(new_password),int(o.username))
set_icq_password = icq_cli_07d0_042e

def icq_cli_07d0_0442(o, cat, desc):
    return icq_cli_07d0(o, struct.pack('<HBH', 0x442, 1, cat) + lnts(desc), int(o.username))
set_homepage_info = icq_cli_07d0_0442

def icq_cli_07d0_04b2(o, uin):
    return icq_cli_07d0(o, struct.pack('<HI',0x04b2, int(uin)), uin)
request_more_icq_info = icq_cli_07d0_04b2

def icq_cli_07d0_04d0(o, uin):
    return icq_cli_07d0(o, struct.pack('<HI',0x04d0, int(uin)), uin)
request_icq_info = icq_cli_07d0_04d0

def icq_cli_07d0_1482(o, phone, message):
    from util.xml_tag import tag
    icq_sms_message = tag('icq_sms_message')
    icq_sms_message.destination = phone
    icq_sms_message.text = message
    icq_sms_message.senders_UIN = o.username
    try:    name = o.self_buddy.first + o.self_buddy.last
    except Exception: name = o.username
    icq_sms_message.senders_name = name
    icq_sms_message.delivery_receipt = 'Yes'
    icq_sms_message.time = str(datetime.today())

    return icq_cli_07d0(o, struct.pack('<HHHQ',0x1482, 1, 16, 0) + oscar.util.tlv(0, str(icq_sms_message._to_xml(pretty=False))))

send_icq_sms = icq_cli_07d0_1482

def icq_cli_07d0_0fd2(o, message):
    '''
    For setting 'status note' (that is, personal status message for new ICQ).
    '''

    '''25 00
       05 b9 00 03 80 00 00 00 00 00 00 06 00 01 00
       02 00 02 00 00 04 e4 00 00 00 02 00 03 00 07
       02 26 00 03 77 75 74'''

    if message:
        d1 = struct.pack('!H', len(message)) + message

        # I think this might be a TLV type
        x = '\x02\x26' + d1
    else:
        x = ''

    # The content of this string completely eludes me.
    x = '\x05\xb9\x00\x03\x80\x00\x00\x00\x00\x00\x00\x06\x00\x01\x00\x02\x00\x02\x00\x00\x04\xe4\x00\x00\x00\x02' + oscar.util.tlv(3, x)
    d3 = struct.pack('<H', len(x)) + x
    return icq_cli_07d0(o, struct.pack('<H', 0x0fd2) + d3, o.username)

set_icq_psm = icq_cli_07d0_0fd2

def icq_cli_07d0_0fa0(o, uin):
    # see ticket 2768
    '''
    Response is icq_srv_07d0_0fb4
    '''
    uin_tlv = oscar.util.tlv(0x32, str(uin))
    data = ('05b90002800000000000000600010002'+ # I dont know what this all means but its what ICQ6 sends...
            '0002000004e400000002000300000001').decode('hex') \
            + struct.pack('!H', len(uin_tlv)) + uin_tlv

    return icq_cli_07d0(o, struct.pack('<HH', 0x0fa0, len(data),) + data, uin)

icq_request_profile_unicode = icq_cli_07d0_0fa0

def icq_srv_07da(o, uid, data):
    kind, result, data = oscar.unpack((('kind','H'),('result','B')), data, '<')
    try:
        f = getattr(oscar.snac, 'icq_srv_07da_%04x' % kind)
    except Exception:
        log.info('Unknown ICQ 07DA response: uid = %r, kind = %r, result = %r, data = %r',
                 uid, hex(kind), result, data.encode('hex'))
        return
    f(o, uid, result, data)

def icq_srv_07da_0fb4(o, uid, result, data):
    '''
    Request is icq_cli_07d0_0fa0 (icq_request_profile_unicode)
    '''
    log.info('Got profile response for %r. result = %r, data = %r', uid, result, data)
    _data = data
    data = data[0x31:]

    tlv_types = { 50  :'__name',
                  100 :'first',
                  110 :'last',
                  120 :'nick',
                  150 :'personal',
                  160 :'original',
                  250 :'personal_url',
                  280 :'work',
                  390 :'profile',
                  550 :'status_message',
                  590 :'phone',
                  }

    fmt = (('tlvs', 'named_tlvs', -1, tlv_types),)
    tlvs, data = oscar.unpack(fmt, data)

    unknown_tlvs = {}
    for k in tlvs.keys():
        try:
            int(k)
        except ValueError:
            if k in ('personal', 'work', 'original'):
                tlvs[k] = process_address_info(k, tlvs[k])
            elif k in ('first', 'last', 'nick', 'personal_url','profile','status_message'):
                tlvs[k] = tlvs[k].decode('fuzzy utf-8')
        else:
            unknown_tlvs[k] = tlvs.pop(k)

    log.debug_s('unicode profile info: %r', tlvs)
    log.debug('\tunknown TLVs: %r', unknown_tlvs)

    b = o.get_buddy(uid)
    b.update(tlvs)

def process_address_info(addr_type, data):
    log.debug_s('Got %r address data: %r', addr_type, data)

    addr_info = _get_tlv1_data(data)
    if addr_info is None:
        log.error('Couldnt find TLV(1) for address info (%r) in %r', addr_type, data)
        return {}

    if addr_type == 'work':
        return _extract_address_info_work(addr_info)
    elif addr_type in ('personal', 'original',):
        return _extract_address_info_basic(addr_info)
    else:
        log.debug('Unknown address type %r. data is %r', addr_type, data)
        return {}

def _extract_address_info(data, tlv_names):
    fmt = (('tlvs', 'named_tlvs', -1, tlv_names),)
    tlvs, data = oscar.unpack(fmt, data)

    for k in tlvs:
        tlvs[k] = tlvs[k].decode('fuzzy utf-8') # this is supposed to be utf-8 but using fuzzy just in case
    return tlvs

def _extract_address_info_basic(data):
    tlv_names = {
        100 : 'street',
        110 : 'city',
        120 : 'state',
        }
    return _extract_address_info(data, tlv_names)

def _extract_address_info_work(data):
    tlv_names = {
        100 : 'position',
        110 : 'company',
        120 : 'website',
        170 : 'street',
        180 : 'city',
        190 : 'state',
        }
    return _extract_address_info(data, tlv_names)

def _get_tlv1_data(data):
    tlvs, data = oscar.unpack((('tlvs', 'tlv_dict',),), data)
    tlv_data = tlvs.get(1, None)
    if data:
        log.error('leftover data from tlvs: %r', data)
    return tlv_data

def icq_srv_07da_00c8(o, uid, result, data):
    if result != SUCCESS:
        log.warning('icq got response %d', result)
        return

    vals = 'nick first last email city state phone fax street cellular zip country timezone publish webaware data'.split()

    fmt = [(x, 'lnts') for x in vals[:11]]

    fmt.extend([
                (vals[11],   'H'),
                (vals[12],   'B'),
                (vals[13],   'H'),
                (vals[14],   'B')
                ])

    #locals.update(zip(vals, oscar.unpack(fmt, data, '<')))

    (nick, first, last, email, city, state, phone, fax, street,
     cellular, zip, country_code, timezone, publish, webaware), data = unpack_decode(fmt, data, '<')

    country = icq_country.codes.get(country_code, sentinel)
    if country is sentinel:
        log.warning('Unknown country code %r. Maybe you can guess from these locals? %r', country_code, locals())
    country = u'Unknown'
    del country_code

    if data:
        log.warning('icq user info got extra data: %r', util.to_hex(data))
    webaware = bool(webaware%2)

    b = o.buddies[str(uid)]
    try:    personal = b.personal
    except Exception: personal = b.personal = util.Storage()
    set = b.setnotifyif

    for x in vals:
        set(x, locals()[x])
        setattr(personal, x, locals()[x])

def unpack_decode(fmt, data, byteorder='!'):
    unpacked = oscar.unpack(fmt, data, byteorder)
    values, data = unpacked[:-1], unpacked[-1]

    real_vals = []
    for val in values:
        if isinstance(val, str):
            real_vals.append(val.decode('fuzzy utf8'))
        else:
            real_vals.append(val)

    return real_vals, data

def icq_srv_07da_00d2(o, uid, result, data):
    fmt = '''
          city            lnts
          state           lnts
          phone           lnts
          fax             lnts
          street          lnts
          zip             lnts
          country         H
          company         lnts
          department      lnts
          position        lnts
          occupation      H
          website        lnts
          zip             lnts
          '''.split()

    names, types = fmt[::2],fmt[1::2]
    fmt = zip(names, types)
    values, data = unpack_decode(fmt, data, '<')

    info = dict(zip(names, values))

    info['country'] = icq_country.codes[info['country']]

    b = o.buddies[uid]
    try:    work = b.work
    except Exception: work = b.work = util.Storage()
    for x in names:
        setattr(work, x, info[x])

def icq_srv_07da_00dc(o, uid, result, data):
    '''
    WORD.L      xx xx     AGE        The age of the user. 0 or -1 is invalid and means not entered.
    BYTE        xx        GENDER     The gender of the user.
    LNTS        xx ..     HOMEPAGE   The homepage of the user.
    WORD.L      xx xx     YEAR       The year of birth of the user.
    BYTE        xx        MONTH      The month of birth of the user.
    BYTE        xx        DAY        The day of birth of the user.
    BYTE        xx        LANG1      The language the user speaks fluently.
    BYTE        xx        LANG2      Another language the user speaks.
    BYTE        xx        LANG3      Another language the user speaks.
    WORD.L      xx xx     UNKNOWN    Unknown: Empty.
    LNTS        xx ..     OCITY      city, the user is originally from
    LNTS        xx ..     OSTATE     state, the user is originally from
    WORD.L      xx xx     OCOUNTRY   The country the user originally is from.
    WORD.L      xx xx     MARITAL    the user's marital status.
    '''

    fmt = '''
          age            H
          gender         B
          website        lnts
          year           H
          month          B
          day            B
          lang1          B
          lang2          B
          lang3          B
          unknown        H
          hometown       lnts
          homestate      lnts
          homecountry    H
          marital        H
          '''.split()

    names, types = fmt[::2],fmt[1::2]
    fmt = zip(names, types)
    info = dict(zip(names+['data'], oscar.unpack(fmt, data,'<')))
    b = o.buddies[uid]

    translate = dict(
         gender = {0: None, 1: _(u'Female'), 2: _(u'Male')},
    )

    #info['country'] = icq_country.codes[info['country']]


    try:    personal = b.personal
    except Exception: personal = b.personal = util.Storage()

    from common import pref
    import time

    # format a birthday string
    if not all(info[c] == 0 for c in ('year', 'month', 'day')):
        try:
            personal['birthday'] = time.strftime(pref('infobox.birthday_format', '%m/%d/%y'),
                                                 (info['year'], info['month'], info['day'],
                                                  0, 0, 0, 0, 0, 0)).decode('fuzzy utf8')
        except Exception, e:
            personal['birthday'] = u''
            log.error("couldn't convert to string: %r, %r", e, info)
    else:
        personal['birthday'] = u''


    for x in names:
        setattr(personal, x.decode('fuzzy utf8'), translate.get(x, {}).get(info[x], info[x]))

def icq_srv_07da_00e6(o, uid, result, data):
    profile, data = oscar.unpack((('info','lnts'),), data, '<')
    o.buddies[uid].profile = profile.decode('fuzzy utf8')

def icq_srv_07da_00eb(o, uid, result, data):
    count, data = oscar.unpack((('count','B'),), data, '<')

    emails = []
    for _ in range(count):
        flags, email, data = oscar.unpack(
                                          (('flags','B'),
                                          ('email','lnts')),
                                          data, '<'
                                          )

        emails.append((flags, email))

    o.buddies[uid].emails = emails

def icq_srv_07da_00f0(o, uid, result, data):
    count, data = oscar.unpack((('count','B'),), data, '<')

    interests = []
    for _ in range(count):
        interest, desc, data = oscar.unpack(
                                          (('interest','H'),
                                          ('desc','lnts')),
                                          data, '<'
                                          )

        interests.append((interest, desc))

    o.buddies[uid].interests = interests

def icq_srv_07da_00fa(o, uid, result, data):
    count, data = oscar.unpack((('count','B'),), data, '<')

    orgs = []
    for _ in range(count):
        org, desc, data = oscar.unpack(
                                       (('org','H'),
                                        ('desc','lnts')),
                                       data, '<'
                                       )

        orgs.append((org, desc))
    o.buddies[uid].organizations = orgs


    count, data = oscar.unpack((('count','B'),), data, '<')

    affils = []
    for _ in range(count):
        affil, desc, data = oscar.unpack(
                                         (('affil','H'),
                                          ('desc','lnts')),
                                         data, '<'
                                         )

        affils.append((affil, desc))

    o.buddies[uid].affiliations= affils

def icq_srv_07da_0106(o, uid, result, data):
    fmt = [(x, 'lnts') for x in 'nick first last email'.split()]

    nick, first, last, email, data = oscar.unpack(fmt, data, '<')
    b = o.buddies[uid]

    try:    b.personal
    except Exception: b.personal = util.Storage()

    set = lambda k,v: (b.setnotifyif(k,v), setattr(b.personal, k,v))

    set('nick', nick)
    set('first', first)
    set('last', last)
    set('email', email)


def icq_srv_07da_019a(o, uid, result, data):
    fmt = '''
          length    H
          uin       I
          nick      lnts
          first     lnts
          last      lnts
          _         lnts
    '''.split()

    names, types = fmt[::2],fmt[1::2]
    fmt = zip(names, types)

    __, _uin, nick, first, last, __ = oscar.unpack(fmt, data, '<')

    assert _uin == uid

    b = o.buddies[uid]

    try:    personal = b.personal
    except Exception: personal = b.personal = util.Storage()

    for x in 'nick first last'.split():
        setattr(personal, x, locals()[x])


