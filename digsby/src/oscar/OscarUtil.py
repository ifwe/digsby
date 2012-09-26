from peak.util.imports import lazyModule
from util.primitives import odict
import struct
util         = lazyModule('util')
auxencodings = lazyModule('util.auxencodings')
import sys
import array
import logging
import string

from collections import defaultdict

import oscar

log = logging.getLogger('oscar.util')

flagged = lambda f, v: f&v==f

len_to_fmt = {0: '',  1: 'B',
              2: 'H', 4: 'I',
              8: 'Q', 16:'16s',}

def lowerstrip(s):
    return s.lower().replace(' ','')

def tflv(type_, flags=1, data=''):
    return struct.pack('!HBB', type_, flags, len(data)) + data

def tflv_list(*tflvs): return ''.join(tflv(*t) for t in tflvs)

def tlv(type_, length=0, value=0):
    '''
    Constructs a TLV, returning the bytes that would go out on the network.

    TLV stands for "type, length, value" and is one of the building blocks of
    OSCAR binary data packets.

    >>> tlv(0x05)
    >>> tlv(0x03, 'some string')
    >>> tlv(0x02, 4, 13)
    '''

    assert isinstance(type_, int)
    if isinstance(length, basestring):
        value = length
        length = len(value)
    else:
        assert isinstance(length, int)

        if not isinstance(value, (int, long)):
            raise AssertionError('%r is not an integer' % value)
        assert length in [0,1,2,4,8,16]
    if isinstance(value, basestring):
        assert length == len(value)
        fmt_string = '%ds' % length if value else ''
    else:
        fmt_string = len_to_fmt[length]

    assert struct.calcsize(fmt_string) == length

    args = [type_]
    args += [length] if length else [0]
    args += [value] if value else [0] if length else []

    try:
        # this causes DeprecationWarning:
        #  'H' format requires 0 <= number <= 65535.
        # what to do when the overflow is desired?
        return struct.pack('!HH'+fmt_string, *args)
    except Exception:
        print fmt_string, args
        raise


def tlv_list(*tlvs):
    return ''.join(tlv(*t) for t in tlvs)

def s_tlv(data, byte_order='!'):
    '''
    Creates a TLV object from network data.

    The returned object is a Storage with t, l, and v attributes.
    '''

    t, l = struct.unpack(byte_order + 'HH', data[:4])
    data = data[4:]
    v, data = data[:l], data[l:]
    return util.Storage(t=t, l=l, v=v), data

def tlv_list_to_dict(tlv_list):
    return odict((tlv.t, tlv.v) for tlv in tlv_list)

def s_tflv(data, byte_order = '!'):
    fmt = (
        ('type', 'H'),
        ('flags', 'B'),
        ('length', 'B'),
        ('value', 's', 'length'),
        )
    t, f, l, v, data = apply_format(fmt, data)
    return util.Storage(t=t, f=f, l=l, v=v), data

def list_reader(of_what, byte_order = '!'):
    def read_list(data, count = -1):
        objs = []
        while data and count:
            thing, data = of_what(data, byte_order)
            objs.append(thing)
            try:
                count -= 1
            except TypeError:
                print count
                raise

        return objs, data
    return read_list

s_tflv_list = list_reader(s_tflv)
s_tlv_list = list_reader(s_tlv)

def decode(s, enc):
    '''
    Returns a unicode string for a Oscar network string and an Oscar encoding.

    Encodings look like
    text/x-aolrtf; charset="unicode-2-0"
    '''
    encodings = {'unicode-2-0':'utf-16be',
                 'utf-8':      'utf-8',
                 'us-ascii':   'ascii' }
    if enc.find('; charset="') != -1:
        msgtype, encoding = enc.split('; charset="')
        encoding = encoding[:-1]
    elif enc in encodings:
        encoding = enc
    else:
        log.warning('oscar.decode encountered "%s", no charset--assuming utf-8', enc)
        encoding = 'utf-8'

    encoding = encoding.split('\0', 1)[0]
    encoding = encodings.get(encoding, encoding)

    return auxencodings.fuzzydecode(s, encoding)

struct_types = set('xcbhilqfdsp')
oscar_types  = set(['tlv', 'tlv_list', 'tlv_dict', 'named_tlvs', 'list', 'tflv', 'tflv_list',
                    'rate_class_list', 'rate_group_list', 'pstring', 'message_block',
                    'ssi_dict','ssi','tlv_list_len','tlv_dict_len','userinfo',
                    'dc_info', 'rate_class', 'msg_fragment','lnts'])
all_format_types = struct_types | oscar_types

digits = set(string.digits)

def apply_format(format, data, byte_order='!'):
    if not (isinstance(format, (tuple, list)) and
            isinstance(format[0], (tuple, list))):
        raise TypeError('apply_format needs a tuple of tuples')

    fields = {}
    to_return = []
    for item in format:
        name, kind, args = item[0], item[1], item[2:]

        # for format strings like "4B"...strip numbers
        skind = kind
        while len(skind) > 0 and skind[0] in digits:
            skind = skind[1:]

        assert skind.lower() in all_format_types, 'bad format: %s' % kind.lower()

        if kind.lower() in oscar_types:
            f = globals().get('apply_format_%s' % kind, None)
            if f is None:
                raise Exception('%r is not a valid format type' % kind)
            fields[name], data = f(data, fields, byte_order, *args)
            to_return.append(fields[name])
            continue

        prev_name = args[0] if args else None
        if prev_name is not None:
            fmt = '%d%s' % (prev_name if isinstance(prev_name, int) \
                            else fields[prev_name], kind)
        else:
            fmt = kind

        fmt = byte_order + fmt

        try:
            sz = struct.calcsize(fmt)
        except Exception:
            print 'BAD FORMAT:', fmt
            raise

        try:
            fields[name] = struct.unpack(fmt, data[:sz])
        except Exception:
            print name, fmt, util.to_hex(data)
            raise

        #make single-element tuples/lists into the value instead
        if len(fields[name]) == 1:
            fields[name] = fields[name][0]
        data = data[sz:]
        to_return.append(fields[name])

    to_return.append(data)
    return to_return

# ah! the eyes get lost in the sea of underscores. -10 style points

def apply_format_tlv(data, fields, byte_order):
    return s_tlv(data)

def apply_format_tlv_dict(data, fields, byte_order, num_tlvs_s=-1):
    tlvs, data = apply_format_tlv_list(data, fields, byte_order, num_tlvs_s)
    return tlv_list_to_dict(tlvs), data

def apply_format_tlv_dict_len(data, fields, byte_order, byte_count_s):
    tlvs, data = apply_format_tlv_list_len(data, fields, byte_order, byte_count_s)
    return tlv_list_to_dict(tlvs), data

def apply_format_tlv_list(data, fields, byte_order, num_tlvs_s=-1):
    if isinstance(num_tlvs_s, basestring):
        num_tlvs = fields[num_tlvs_s]
    else:
        assert isinstance(num_tlvs_s, int)
        num_tlvs = num_tlvs_s
    return s_tlv_list(data, num_tlvs)

def apply_format_tlv_list_len(data, fields, byte_order, byte_count_s):
    if isinstance(byte_count_s, basestring):
        byte_count = fields[byte_count_s]
    else:
        assert isinstance(byte_count_s, int)
        byte_count = byte_count_s

    indata, rdata = data[:byte_count], data[byte_count:]
    tlvs, outdata = apply_format_tlv_list(indata, fields, byte_order, -1)
    assert not outdata
    return tlvs, rdata

def apply_format_named_tlvs(data, fields, byte_order, tlv_count_s, tlv_types):
    if isinstance(tlv_count_s, basestring):
        tlv_count = fields[tlv_count_s]
    else:
        assert isinstance(tlv_count_s, int)
        tlv_count = tlv_count_s
    tlvs, data = s_tlv_list(data, tlv_count)

    bynumber = tlv_list_to_dict(tlvs)

    named_tlvs = util.Storage()
    for type, tlv in bynumber.iteritems():
        named_tlvs[tlv_types.get(type, type)] = tlv

    return named_tlvs, data

def apply_format_tflv(data, fields, byte_order):
    return s_tflv(data)

def apply_format_tflv_list(data, fields, byte_order, num_tflvs_s=-1):
    if isinstance(num_tflvs_s, basestring):
        num_tflvs = fields[num_tflvs_s]
    else:
        assert isinstance(num_tflvs_s, int)
        num_tflvs = num_tflvs_s

    return s_tflv_list(data, num_tflvs)

def apply_format_userinfo(data, fields, byte_order):
    '''
    Turns a user info block into a Storage.

    U{http://iserverd.khstu.ru/oscar/info_block.html}
    '''

    userinfo_types = {  # the Storage has some (or all) of these keys:
        0x01: 'user_class',
        0x02: 'create_time',
        0x03: 'signon_time',
        0x04: 'idle_time',
        0x05: 'account_creation_time',
        0x06: 'user_status_icq',
        0x0a: 'external_ip_icq',
        0x0c: 'dc_info',
        0x0d: 'capabilities',
        0x0f: 'online_time',
        0x1d: 'avail_msg',
        0x23: 'profile_updated',  # 4 byte timestamps
        0x26: 'mystery_updated',
        0x27: 'away_updated',
    }

    fmt = (('sn', 'pstring'),
           ('warning', 'H'),
           ('num_tlvs','H'),
           ('tlvs', 'named_tlvs', 'num_tlvs', userinfo_types))

    sn, warning, __, userdict, data = apply_format(fmt, data)

    userdict.nice_name = sn
    userdict.name = sn.lower().replace(' ', '')
    userdict.warning_level = warning
    return userdict, data

def apply_format_dc_info(data, fields, byte_order):
    names = 'ip port type version cookie web_port features info_update_time '.split()
    sizes = '4B I    B    H       I      I        I        I                '.split()

    names +='ext_update_time status_update_time unknown'.split()
    sizes +='I               I                  H      '.split()

    stuff = apply_format(zip(names, sizes), data)
    return util.Storage(zip(names, stuff[:-1])), data[-1]

def apply_format_list(data, fields, byte_order, kind, count_s=-1):
    '''
    works for any kind of data that apply_format accepts
    '''

    if isinstance(count_s, basestring):
        count = fields[count_s]
    else:
        assert isinstance(count_s, int)
        count = count_s

    result = []
    while data and count:
        info, data = apply_format((('info', kind),), data, byte_order)
        result.append(info)
        count -= 1
    return result, data

def apply_format_rate_class(data, fields, byte_order):

    fmt_str1 = 'id               H '\
               'window           I '\
               'clear_level      I '\
               'alert_level      I '\
               'limit_level      I '\
               'disconnect_level I '\
               'current_level    I '\
               'max_level        I '\
               'last_time        I '\
               'state            B'.split()

    rate_class_fmt = zip(fmt_str1[::2], fmt_str1[1::2])

    info = apply_format(rate_class_fmt, data, byte_order)
    data, rate_class = info.pop(), util.Storage(zip(fmt_str1[::2],info))
#    if ord(data[1:2]) != int(rate_class.id) + 1:
#          fmt_str2 ='last_time        I '\
#                    'state            B '.split()
#
#          last_time, state, data = apply_format(zip
#                                                (fmt_str2[::2],
#                                                 fmt_str2[1::2]),
#                                                 data)
#
#          rate_class.last_time, rate_class.state = last_time, state
#
#    else:
#        rate_class.last_time, rate_class.state = 0,0

    return rate_class, data

def apply_format_rate_class_list(data, fields, byte_order, num_classes_s):
    if isinstance(num_classes_s, basestring):
        num_classes = fields[num_classes_s]
    else:
        assert isinstance(num_classes_s, int)
        num_classes = num_classes_s

    classes = []
    while data and num_classes:
        rate_class, data = apply_format_rate_class(data, fields, byte_order)
        classes.append(rate_class)
        num_classes -= 1

    return classes, data

def apply_format_pstring(data, fields, byte_order):
    'Unpacks a Pascal string. Which the struct module does NOT do.'

    l = struct.unpack('B', data[:1])[0]    # grab the length of the string
    string_ = struct.unpack(str(l) + 's', data[1:1+l])[0]

    return string_, data[l+1:]

def apply_format_message_block(data, fields, byte_order):
    'Channel 1 message block.'
    msg = util.Storage()

    fmt = (('msg_fragments', 'list', 'msg_fragment'),)
    msg_fragments, data = apply_format(fmt, data)
    msgs = [x[1] for x in msg_fragments if x[0] == 1]

    res = dict(msg_fragments)
    if msgs:
        res[1] = msgs
    return res, data

def apply_format_msg_fragment(data, fields, byte_order):
    fmt = (('type', 'B'),
           ('version', 'B'),
           ('length', 'H'),
           ('data','s','length'))

    type, __, __, data, remaining_data = apply_format(fmt, data,
                                                    byte_order)

    return (type, data), remaining_data


def apply_format_rate_group(data, fields, byte_order):
    _data = data[:]
    rate_group_fmt = (('id', 'H'),
                      ('num_pairs', 'H'),
                      ('pairs_list', 'list', 'I', 'num_pairs'))
    try:
        stuff = apply_format(rate_group_fmt, data, byte_order)
    except ValueError, e:
        stuff = apply_format(rate_group_fmt, _data, '<')
    id, num_pairs, pairs_list, data = stuff
    pairs = []
    for pair in pairs_list:
        fam, sub = struct.unpack(byte_order+'HH', struct.pack(byte_order+'I', pair))
        pairs.append((fam, sub))

    return dict.fromkeys(pairs, id), data

def apply_format_rate_group_list(data, fields, byte_order, num_groups_s):
    if isinstance(num_groups_s, basestring):
        num_groups = fields[num_groups_s]
    else:
        assert isinstance(num_groups_s, int)
        num_groups = num_groups_s

    rate_groups = {}
    while data and num_groups:
        rate_group, data = apply_format_rate_group(data, fields, byte_order)
        rate_groups.update(rate_group)
        num_groups -= 1

    return rate_groups, data

def apply_format_ssi(data, fields, byte_order):
    ssi_fmt = (('name_len', 'H'),
               ('name', 's', 'name_len'),
               ('group_id', 'H'),
               ('item_id', 'H'),
               ('type_', 'H'),
               ('data_len', 'H'),
               ('tlvs','tlv_dict_len','data_len'))
    __, name, group_id, item_id, type_, __, tlvs, data = \
     apply_format(ssi_fmt, data, byte_order)

    return oscar.ssi.item(name, group_id, item_id, type_, tlvs), data

def apply_format_ssi_list(data, fields, byte_order, num_ssis_s=-1):

    if isinstance(num_ssis_s, basestring):
        num_ssis = fields[num_ssis_s]
    else:
        assert isinstance(num_ssis_s, int)
        num_ssis = num_ssis_s

    l = []
    while data and num_ssis != 0:
        ssi, data = apply_format_ssi(data, fields, byte_order)
        l.append(ssi)
        num_ssis -= 1
    return l, data

def apply_format_ssi_dict(*args):
    l, data = apply_format_ssi_list(*args)
    d = {}
    for item in l:
        d[(item.group_id, item.item_id)] = item
    return d, data

def apply_format_lnts(data, fields, byte_order='<'):
    if byte_order != '<':
        import warnings
        warnings.warn('oscar.apply_format_lnts got a byte order other than little-endian')
    length, data = struct.unpack(byte_order+'H', data[:2])[0], data[2:]
    val, data = data[:length], data[length:]
    if length:
        assert val[-1] == '\x00'
    return val[:-1], data

def chat_cookie(room_name, exchange=4):
    '''
    make_chat_cookie(room_name, exchange=4)

    returns a valid aol chat cookie
    '''
    cookie =  "!aol://2719:10-" + str(exchange)+ "-" + str(room_name.replace(" ","").lower())
    assert is_chat_cookie(cookie)
    return cookie

def process_status_bits(user_status_icq):
    offline     = 0xffffffff
    webaware    = 0x00010000
    invisible   = 0x00000100
    dnd         = 0x00000002
    busy        = 0x00000010
    na          = 0x00000004
    away        = 0x00000001
    ffc         = 0x00000020
    online      = 0x00000000

    webaware = False
    status = None
    flags, status_bits = struct.unpack('!HH', user_status_icq)

    webaware = flagged(webaware, status_bits)

    if flagged(offline, status_bits):
        status = 'offline'
    elif flagged(invisible, status_bits):
        status = 'invisible'
    elif flagged(dnd, status_bits):
        status = 'do not disturb'
    elif flagged(busy, status_bits):
        status = 'busy'
    elif flagged(na, status_bits):
        status = 'not available'
    elif flagged(away, status_bits):
        status = 'away'
    elif flagged(ffc, status_bits):
        status = 'free for chat'
    elif flagged(online, status_bits):
        status = 'available'

    return status, webaware

def is_chat_cookie(cookie):
    return isinstance(cookie, basestring) and (
            cookie.startswith('aol://') or
            cookie.startswith('!aol://'))

