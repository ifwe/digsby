'''
Family 4

Messaging
'''

import struct, time, logging

import hooks
import oscar
import util.auxencodings
import oscar.capabilities as capabilities
import oscar.rendezvous as rendezvous
log = logging.getLogger('oscar.snac.x04'); info = log.info; warn = log.warning

from common import pref

x04_name="ICBM"

tlv_types = {0x01: 'class',
             0x02: 'message_data',
             0x03: 'account_created',
             0x04: 'auto',
             0x06: 'offline',
             0x0b: 'typing',
             0x0f: 'idletime',
             0x16: 'timestamp',
             }

subcodes = {
            0x04 : 'you are trying to send message to offline client',
            0x09 : 'message not supported by client',
            0x0E : 'your message is invalid (incorrectly formatted)',
            0x10 : 'receiver/sender blocked',
            }

@util.gen_sequence
def x04_init(o, sock, cb):
    log.info('initializing')
    me = (yield None); assert me
    sock.send_snac(*oscar.snac.x04_x04(), req=True, cb=me.send)
    channel_params = o.gen_incoming((yield None))
    sock.send_snac(*oscar.snac.x04_x02(channel_params))
    cb()
    log.info('finished initializing')

def x04_x01(o, sock, data):
    '''
    SNAC (x4, x1): ICBM Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x04, (errcode, errmsg), (subcode, submsg))

def x04_x02(channel_params):
    '''
    SNAC (x4, x2): Set ICBM params

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_02.html}

    '''
    all_channels = 0

    # features
    allow = 1
    missed_calls = 2
    no_typing_notifications = 4
    unknown = 8 # i don't know what this is, but aim does it...

    # set values for all channels
    channel_params[0] = all_channels

    # enable all features

    # This value is what AIM 6 sends
    channel_params[1] = 0x3db

    # increase message size limit. This is what AIM 5.9 sets,
    # and it allows the wall street journal bot to work.
    channel_params[2] = 8000

    # This is what we used to send.
    #channel_params[1] = allow | missed_calls | unknown

    log.info('message snac size limit: %d', channel_params[2])

    channel_params[-1] = 0

    return 0x04, 0x02, struct.pack('!HIHHHHH', *channel_params)

def x04_x03(o, sock, data):
    '''
    SNAC (x4, x3): Reset ICBM params

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_03.html}
    '''
    return 0x04, 0x03

def x04_x04():
    '''
    SNAC (x4, x4): Request ICBM params

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_04.html}
    '''
    return 0x04, 0x04

def x04_x05(o, sock, data):
    '''
    SNAC (x4, x5): Messaging limits

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_05.html}
    '''

    format = (('channel', 'H'),
              ('flags', 'I'),
              ('max_snac_size', 'H'),
              ('max_snd_warn', 'H'),
              ('max_rcv_warn', 'H'),
              ('min_msg_interval', 'H'),
              ('unknown', 'H'))

    info = oscar.unpack(format, data)

    assert not info[-1] # leftover data
    return info[:-1]    # real info

def x04_x06(sn, cookie, chan, chan_data):
    '''
    SNAC (x4, x6): Outgoing message

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_06.html}
    '''
    snlen = len(sn)

    return 0x04, 0x06, struct.pack('!QHB%ds'%snlen, cookie, chan, snlen, sn) + chan_data

def x04_x07(o, sock, data):
    '''
    SNAC (x4, x7): Incoming message

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_07.html}
    '''
    snac_format = (('msgcookie',    'Q'),
                   ('channel',      'H'),
                   ('userinfo', 'userinfo'))
    info = oscar.unpack(snac_format, data)
    channel = info[1]
    # There are more TLVs, but they depend on the channels
    log.info('Received channel %d message', channel)
    globals().get('rcv_channel%d_message' % channel, rcv_unknown_channel)(o, *info)

def x04_x08(sn, anon=True):
    '''
    SNAC (x4, x8): Evil request

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_08.html}
    '''
    snlen = len(sn)
    return 0x04, 0x08, struct.pack('!HB%ds' %snlen, anon, snlen, sn)

def x04_x09(o, sock, data):
    '''
    SNAC (x4, x9): Server evil ack

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_09.html}
    '''
    fmt = (('incr_val', 'H'),
           ('new_val', 'H'))

    incr_val, new_val, data = oscar.unpack(fmt, data)
    print 'yay warn', incr_val, new_val
    assert not data

def x04_x0a(o, sock, data):
    '''
    SNAC (x4, xa): Msg not delivered

    Someone tried to send a message to you but server did not deliver

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_0a.html}
    '''
    fmt = (('chan', 'H'),
           ('info', 'userinfo'),
           ('num_missed', 'H'),
           ('reason', 'H'))

    reasons = {0: 'Invalid message',
               1: 'Message too large',
               2: 'Message rate exceeded',
               3: 'Sender is too evil',
               4: 'You are too evil',}

    infolist = []
    while data:
        chan, info, num_missed, reason, data = oscar.unpack(fmt, data)
        log.warning('could not deliver %d ch%d messages, %r, %r' % \
                    (num_missed, chan, info, reasons.get(reason, 'unknown')))

def x04_x0b(o, sock, data):
    '''
    SNAC (x4, xb): client/server message error (or data!)

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_0b.html}
    '''

    fmt = (('cookie', 'Q'),
           ('channel','H'),
           ('screenname','pstring'),
           ('reason', 'H'))
    reasons = {1: 'Unsupported channel',
               2: 'Busted payload',
               3: 'Channel specific'}

    cookie, channel, screenname, reason, data = oscar.unpack(fmt, data)

    warn("ch%d message error for cookie %r, screenname %s:", channel, cookie, screenname)
    warn('\t\t' + reasons.get(reason, '<UNKNOWN REASON>'))
    warn('\t\t' + repr(data))

    if reason == 3:
        channel, data = oscar.unpack((('channel','H'),), data)
        if channel == 2:
            messagetype, data = oscar.unpack((('msgtype','H'),), data)
            rendezvous.handlech2(o, None, screenname, cookie, messagetype, data)

            return

    log.error("data not handled: %r", data)


def send_x04_x0b(cookie, channel, bname, reason, ex_data):
    '''
    Constructs "client auto response" message for sending.
    '''
    return 0x04, 0x0b, (struct.pack('!QHB%dsH' % len(bname), cookie, channel, len(bname), bname, reason) + ex_data)

def x04_x0c(o, sock, data):
    '''
    SNAC (x4, xc): Server message ack

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_0c.html}
    '''
    format = (
      ('cookie',  'Q'),
      ('channel', 'H'),
      ('screenname', 'pstring')
    )

    cookie, channel, screenname, data = oscar.unpack(format, data)
    assert not data
    info('ACK for ch%d message to %s', channel, screenname)

def x04_x10():
    '''
    Request offline messages
    '''
    log.info('Requesting offline messages...')
    return 0x04, 0x10, ''

def x04_x14(o=None, sock=None, data=None, status=None, bname=None, channel=None):
    '''
    SNAC (x4, x14): MTN

    reference: U{http://iserverd.khstu.ru/oscar/snac_04_14.html}
    '''

    status_to_num = { None: 0, 'typed': 1, 'typing': 2 }
    num_to_status = util.dictreverse(status_to_num)

    if all([o, sock, data]):
        # Incoming typing notifications.
        assert not any([status, bname, channel])
        fmt = ('cookie      Q '
               'channel     H '
               'bname       pstring '
               'code        H').split()

        fmt = zip(fmt[::2], fmt[1::2])
        __,__, bname, code, data = oscar.unpack(fmt, data)
        assert not data
        bname = bname.lower().replace(' ','')

        if not code in num_to_status:
            return log.warning("x04_x14: num_to_status doesn't have key %r", code)
        status = num_to_status[code]

        if bname in o.conversations:
            o.conversations[bname].set_typing_status(bname, status)
        elif status == 'typing' and pref('messaging.psychic', False):
            # If "psychic" mode is on, and there is no active conversation for
            # the buddy, make one.
            c = o.convo_for(bname)
            o.hub.on_conversation(c, quiet = True)
            c.tingle()
            c.set_typing_status(bname, status)

    else:
        # Sending typing notifications.
        assert not any([o,sock,data]) and all([bname, channel])

        if status not in status_to_num:
            raise ValueError('Typing status must be one of: "typing", "typed", None')

        state = status_to_num[status]
        cookie = int(time.time()**2)
        to_send = struct.pack("!QHB%dsH" % len(bname), cookie, channel,
                              len(bname), bname, state)
        return 0x04, 0x14, to_send

def x04_x17(o, sck, data):
    '''
    End of offline messages
    '''

    assert not data
    log.info('All offline messages have been retrieved')

def rcv_channel1_message(o, cookie, chan, userinfo, data):
    '''Returns the message from a channel 1 message block.

    The result can be a string or unicode object.'''
    msgtlvs, data = oscar.unpack((('msgtlvs','named_tlvs', -1, tlv_types),),
                                 data)
    assert not data
    assert 'message_data' in msgtlvs

    is_auto_response = 'auto' in msgtlvs
    is_offline = 'offline' in msgtlvs
    timestamp = msgtlvs.get('timestamp', None)

    message_fragments, data = oscar.unpack((('msg', 'message_block'),),
                                           msgtlvs.message_data)
    assert not data
    assert 1 in message_fragments

    required = map(ord, message_fragments.get(5, ''))

    if any(x in required for x in (2,6)) or required == [1]:
        # Also observed: [5,1] from eBuddy android client; is_html should be True.
        is_html = True
    else:
        is_html = False

    fmt = (('charset', 'H'),('subset', 'H'),)
    for msg in message_fragments[1]:
        charset, subset, msg = oscar.unpack(fmt, msg)

        # multipart SMS messages come in with message-NULL-mysterious_ascii_characters
        # so just grab everything up to null

        # (disabled b/c of #4677 -- ICQ messages get cut off)
        # msg = msg.split('\x00')[0]

        codec = {3   : 'locale',
                 2   : 'utf-16-be',
                 0   : 'utf-8',
                 0xd : 'utf-8'}.get(charset, 'utf-8')

        log.info('incoming channel1 message:')
        log.info('\tCharset=%d, subset=%d, codec=%s, is_html=%r, msg[:4]=%r', charset, subset, codec, is_html, msg[:4])
        log.info('\tRequired types for message fragments are: %r', required)
        log.info_s('\tdata=%r', msg)

        msg = util.auxencodings.fuzzydecode(msg, [codec, 'utf-8'])

        o.incoming_message(userinfo, msg, is_auto_response, offline=is_offline, timestamp=timestamp, html=is_html)

def rcv_channel2_message(o, cookie, chan, userinfo, data):
    'Handle channel two (rendezvous) messages.'

    # At this point, data should be the rendezvous TLV only.
    rendtlv, data = oscar.util.s_tlv(data)
    assert 0x05 == rendtlv.t

    data = rendtlv.v
    c2format = (('message_type', 'H'),
                ('cookie', 'Q'),
                ('capability', 's', 16),)
    message_type, cookie, capability, data = oscar.unpack(c2format, data)

    rendezvous_type = capabilities.by_bytes[capability]

    # Direct Connection, File Transfer, Chat Rooms
    rendezvous.handlech2( o, rendezvous_type, userinfo.name, cookie,
                          message_type, data )

def rcv_extended_message(o, userinfo, cookie, msg_type, data):
    log.info('Got fancy message from %s', userinfo.name)

    fmt = (('tlvs','tlv_dict'),)
    tlvs, data = oscar.unpack(fmt, data)

    log.info('Fancy message TLVS: %r', tlvs)
    assert not data

    if 0x2711 not in tlvs:
        log.warning('  Not sure what to do with those fancy tlvs.')
        return

    data = tlvs[0x2711]

    fmt = ( ('length1', 'H'),
            ('chunk1',  's',   'length1'),
            ('length2', 'H'),
            ('chunk2',  's',   'length2')
          )

    # chunk1 and 2 don't seem to have any useful information.
    # XXX: Not sure if the number of chunks is always the same or not
    length1, chunk1, length2, chunk2, data = oscar.unpack(fmt, data, byte_order='<')

    # data now holds the message block
    fmt = ( ('type',     'B'),
            ('flags',    'B'),
            ('status',   'H'),
            ('priority', 'H'),
            ('length',   'H'),
            ('message',  's',    'length'),
          )

    type,flags,status,priority,length,message,data = oscar.unpack(fmt, data, byte_order='<')

    log.info('type=%r,flags=%r,status=%r,priority=%r,length=%r,message=%r,data=%r',
             type,flags,status,priority,length,message,data)

    if message:
        assert message[-1] == '\0'
        message = message[:-1]

        # this is wrong...seems to always be true
        auto = (flags & 0x2) == 0x2

        if message:
            o.incoming_rtf_message(userinfo, message, )#auto)
    else:
        # Possibly a 'TZer' ?

        log.error("message not handled, unknown type")
        '''
        With type 0x1a (26) the following data was received:

        '0\x00O\xa6\xf3L\t\xb7\xfdH\x92\x08~\x85z\xe0s0\x00\x00\t\x00\x00\x00Send Tzer\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb3\x00\x00\x00\xaf\x00\x00\x00<tzerRoot id="gangSh" url="http://c.icq.com/xtraz2/img/teaser/common/gangsta.swf" thumb="http://c.icq.com/xtraz2/img/teaser/common/gangsta.png" name="Gangsta\'" freeData=""/>\r\n'

        on another occasion this was received:
        type=26,flags=0,status=0,priority=1,length=0,message='', data:
        ':\x00\x81\x1a\x18\xbc\x0el\x18G\xa5\x91o\x18\xdc\xc7o\x1a\x01\x00\x13\x00\x00\x00Away Status Message\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x15\x00\x00\x00\x00\x00\x00\x00\r\x00\x00\x00text/x-aolrtf'
        '''
from oscar.misc_consts import MType

def rcv_channel4_message(o, cookie, chan, userinfo, data):
    'Returns the message from a channel 4 message block.'

    mblock, data = oscar.util.s_tlv(data)

    mblock = mblock.v

    # watch out! little endian data.
    snd_uin, msg_type, msg_flags, msg_len = struct.unpack("<IBBH",mblock[:8])
    mblock = mblock[8:]

    log.info('Channel 4 message: %r',(snd_uin, msg_type, msg_flags, msg_len, mblock))
    super_old_style_msg(o, userinfo, snd_uin, mblock, msg_type)

def super_old_style_msg(o, userinfo, snd_uin, msg, msg_type, offline=False, timestamp=None):
    if msg_type != MType.PLUGIN:
        msg = msg[:-1] # ends with a null byte
    else:
        msg = msg

    if msg_type == MType.WWP: #web pager

        name, _1,_2, email, unknown, msg = msg.split(chr(0xfe))

        print 'got channel 4 web message message:'
        print repr((name, _1, _2, email, unknown, msg))

    elif msg_type == MType.ADDED: #you were added
        o.auth_requested(str(snd_uin))
        return

    elif msg_type == MType.AUTHDENY:
        # authorization failed
        return

    elif msg_type == MType.AUTHOK:
        # authorization successful
        return

    elif msg_type == MType.AUTHREQ:
        __, __,__, __, __, msg = msg.split(chr(0xfe))
        msg = msg.strip('\x00')
        msg_decode = msg.decode('fuzzy utf-8')
        o.auth_requested(str(snd_uin), msg_decode)
        return
    elif msg_type == MType.URL:
        # web url message?
        pass

    elif msg_type==MType.PLAIN:
        #nothing else to do
        pass
    elif msg_type == MType.PLUGIN:
        # sms message?
        fmt = (('length1', 'H'),
               ('string1','s','length1'),
               ('unknown', 'I'),
               ('length2','H'),('garbage','3B'),
               ('string2','s','length2'))

        __, s1, unk, __, __, msg, data = oscar.unpack(fmt, msg, byte_order = '!')

        # msg is now a short XML string.
        # <sms_message>
        #   <source>ICQ</source>
        #   <destination_UIN>230391135</destination_UIN>
        #   <sender>+19177577555</sender>
        #   <text>Test</text>
        #   <time>Sat, 03 Nov 2007 13:21:07 EDT</time>
        # </sms_message>
        import util.xml_tag
        t = util.xml_tag.tag(msg)
        sender = t.sender._cdata
        userinfo.nice_name = userinfo.name = sender
        msg = t.text._cdata

    o.incoming_message(userinfo, msg, offline=offline, timestamp=timestamp)

def rcv_unknown_channel(o, *info):
    log.warning('Unknown channel/message received for oscar=%r. data=%r', o, info)

def snd_channel1_message(o, sn, message, cookie=None, req_ack=False, save=True, auto=False, html=False):
    if message is None:
        raise TypeError('message must be a string or unicode')

    try:
        charset = 0
        msg = str(message)

#        charset = 0xd
#        if isinstance(message, unicode):
#            msg = message.encode('utf-8')
#        else:
#            msg = message

    except UnicodeEncodeError:
        charset = 2
        msg = message
        msg = msg.encode('utf-16-be')

    subset = 0
    message_data = struct.pack('!HH%ds' % len(msg), charset, subset, msg)

    tlv = oscar.util.tlv
    if html:
        fragments = [1, 1, 1, 2] # mimic aim 6
    else:
        fragments = [1, 6] # mimic pidgin as icq

    mobile = o.is_mobile_buddy(sn)
    if mobile:
        fragments = [1]
        save = False

    to_send = ''.join([
        tlv(2, required_fragment(fragments) + fragment_header(1, message_data)),
        tlv(3) if req_ack or save else '',
        tlv(6) if save else '',
        tlv(4) if auto else '',
        tlv(0x0d, o.get_self_bart_data()) if mobile else '',
        tlv(0x08, '\x00\x00\n\xa6\x00\x01\xb0\xd1<1BP') if mobile else '', # mystery bytes!
    ])

    if cookie is None:
        cookie = int(time.time()**2)

    return oscar.snac.x04_x06(sn, cookie, 1, to_send)

def snd_channel2_message(sn, cookie=None, data=''):
    if cookie is None:
        cookie = int(time.time()**2)

    return x04_x06(sn, cookie, 2, data)

def required_fragment(required):
    return fragment_header(5, ''.join(struct.pack('!B', req) for req in required))

def fragment_header(id, data, ver=1):
    return struct.pack('!BBH', id, ver, len(data))+data
