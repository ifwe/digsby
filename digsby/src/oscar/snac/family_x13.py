'''
Family 13 - SSI
'''
import logging
import struct

import util
import util.primitives.funcs as funcs
import oscar

log = logging.getLogger('oscar.snac.x13')
subcodes = {}
x13_name="SSI"
version = 4

@util.gen_sequence
def x13_init(o, sock, cb):
    me = (yield None); assert me
    log.info('initializing')
    o.change_state(o.Statuses.LOADING_CONTACT_LIST)
    # request params
    sock.send_snac(*oscar.snac.x13_x02(), req=True, cb=me.send)
    o.gen_incoming((yield 'waiting for x13, x03'))
    o.buddies.freeze()
    # request buddy list
    oscar.snac.request_buddy_list(o, sock, me())
    yield None
    # SSI activate
    from util import Timer
    Timer(2.0, o.buddies.thaw).start()
    sock.send_snac(*oscar.snac.x13_x07())
    cb()
    log.info('finished initializing')

def x13_x01(o, sock, data):
    '''
    SNAC (x13, x1): SSI Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x13, (errcode, errmsg), (subcode, submsg))

def x13_x02():
    '''
    SNAC (x13, x2): Request SSI params

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_02.html}
    '''
    return 0x13, 0x02

def x13_x03(o, sock, data):
    '''
    SNAC (x13, x3): SSI Limitations

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_03.html}
    '''
    tlvs, data = oscar.unpack((('tlvs','tlv_dict'),), data)
    return tlvs[0x04]

def x13_x04(o, sock, data):
    '''
    SNAC (x13, x4): Request contact list (first time)

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_04.html}
    '''
    return 0x13, 0x04

def x13_x05():
    '''
    SNAC (x13, x5): Contact list request

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_05.html}
    '''
    return 0x13, 0x05, struct.pack("!IH", 0, 0)

def x13_x06(o, sock, data):
    '''
    SNAC (x13, x6): Server contact list reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_06.html}
    '''
    roster_reply_fmt=(('ssi_protocol_ver','B'),
                      ('num_ssis', 'H'),
                      ('ssis', 'ssi_dict', 'num_ssis'),)
    __,__,ssis,data = oscar.unpack(roster_reply_fmt, data)

    return ssis, data
    print "13 6 update with" + repr(ssis)
def x13_x07():
    '''
    SNAC (x13, x7): Request contact list (after login)

    After this, the server will send presence notifications.

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_07.html}
    '''

    return 0x13, 0x07

def x13_x08(o, sock, data):
    '''
    SNAC (x13, x8): SSI add item

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_08.html}
    '''
    ssis, data = oscar.unpack((('ssis', 'ssi_dict'),), data)
    o.ssimanager.ssis.update(ssis)

def x13_x09(o, sock, data):
    '''
    SNAC (x13, x9): SSI modify item

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_09.html}
    '''
    ssis, data = oscar.unpack((('ssis', 'ssi_dict'),), data)
    o.ssimanager.ssis.update(ssis, modify=True)

def send_x13_x09(ssi_item):
    return 0x13, 0x09, ssi_item.to_bytes()

def x13_x0a(o, sock, data):
    '''
    SNAC (x13, xa): SSI delete item

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_0a.html}
    '''
    d, data = oscar.unpack((('ssis', 'ssi_dict'),), data)
    [o.ssimanager.ssis.pop(k) for k in d if k in o.ssimanager.ssis]

def x13_x0e(o, sock, data):
    '''
    SNAC (x13, xe): SSI acknowledgement

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_0e.html}
    '''
    fmt = (('errcodes', 'list', 'H'),)
    errcodes, data = oscar.unpack(fmt, data)
    assert not data

#    errors = filter(None, errcodes)
    return errcodes
#
#    if not errors:
#        return True
#    else:
#        #TODO: raise snacerrors?
#        return False

def x13_x0f(o, sock, data):
    '''
    SNAC (x13, xf): client local SSI is up-to-date

    xx xx xx xx             dword             modification date/time of server SSI
    xx xx                   word              number of items in server SSI

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_0f.html}
    '''

    time, num, data = oscar.unpack((('time','I'),
                                    ('num','H')),
                                    data)

    log.info('SSIs up to date:')

    return {},''

def x13_x11(o, sock, data):
    '''
    SNAC (x13, x11): Contact edit start

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_11.html}
    '''
    ## append 0x00010000 for import transaction (ICQ?): used for contacts
    ## requiring authorization.
    d, data = oscar.unpack((('ssis', 'ssi_dict'),), data)
    o.ssimanager.ssis.update(d)

def send_x13_x11(import_transaction=False):
    '''
    SNAC (x13, x11): Contact edit start

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_11.html}
    '''
    if not import_transaction:
        return 0x13, 0x11
    else:
        return 0x13, 0x11, struct.pack("!I", 0x00010000)

def x13_x12(o, sock, data):
    '''
    SNAC (x13, x12): Contact edit end

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_12.html}
    '''
    d, data = oscar.unpack((('ssis', 'ssi_dict'),), data)
    o.ssimanager.ssis.update(d)

def send_x13_x12():
    '''
    SNAC (x13, x12): Contact edit end

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_12.html}
    '''
    return 0x13, 0x12


def icq_reason_string(uin, reason):
    uin = str(uin)
    (lu, lr) = len(uin), len(reason)
    return struct.pack("!B%dsH%dsH" % (lu, lr), lu, uin, lr, reason, 0)

def unpack_icq_reason_string(o, sock, data):
    name, __, reason, __, data = oscar.unpack((("name", "pstring"),
                         ("reason_len", "H"),
                         ("reason", "s", "reason_len"),("zero", "H"), ),
                         data)
    return name, reason

def x13_x14(uin, reason):
    '''
    SNAC (x13, x14): Grant future authorization to client

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_14.html}
    '''
    return 0x13, 0x14, icq_reason_string(uin, reason)

def x13_x15(o, sock, data):
    '''
    SNAC (x13, x15): Future authorization granted

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_15.html}
    '''
    name, reason = unpack_icq_reason_string(o, sock, data)
    log.info("You were Future authorized by %s, with reason %s", name, reason)

def x13_x16(uin):
    '''
    SNAC (x13, x16): Delete yourself from another list (supported?)

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_16.html}
    '''
    return 0x13, 0x16, struct.pack("B", len(str(uin)), str(uin))

def x13_x18(uin, reason):
    '''
    SNAC (x13, x18): Send authorization request

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_18.html}
    '''
    return 0x13, 0x18, icq_reason_string(uin, reason)

def x13_x19(o, sock, data):
    '''
    SNAC (x13, x19): incoming authorization request

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_19.html}
    '''
    name, reason = unpack_icq_reason_string(o, sock, data)
    reason_d = reason.decode('fuzzy utf-8')
    log.info("%r wants to add you to their contact list, with reason %r", name, reason_d)
    o.auth_requested(name, reason_d)

def x13_x1a(uin, reason, accept=True):
    '''
    SNAC (x13, x1a): Send authorization reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_1a.html}
    '''
    uin = str(uin)
    (lu, lr) = len(uin), len(reason)
    mysnac = struct.pack("!B%dsBH%ds" % (lu, lr), lu, uin, accept, lr, reason)
    return 0x13, 0x1a, mysnac

def x13_x1b(o, sock, data):
    '''
    SNAC (x13, x1b): incoming authorization reply

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_1b.html}
    '''
    name, accept, __, reason, data = oscar.unpack((("name", "pstring"),
                                                  ("accept", "B"),
                                                  ("reason_len", "H"),
                                                  ("reason", "s", "reason_len"), ),
                                                  data)

    assert not data
    log.info("%s has %s you with reason: %s", name,
             "Accepted" if accept else "Denied", reason)

def x13_x1c(o, sock, data):
    '''
    SNAC (x13, x1c): "You were added" message

    reference: U{http://iserverd.khstu.ru/oscar/snac_13_1c.html}
    '''
    name, data = oscar.unpack((("name", "pstring"),), data)
    assert not data
    log.info("You were added by", name)

@util.gen_sequence
def request_buddy_list(o, sock, parent):
    me = (yield None)

    ssis = {}

    sock.send_snac(*oscar.snac.x13_x05(), req=True, cb=me.send)
    while True:
        ssis_, data = o.gen_incoming((yield 'waiting for x13, x06'))
        if not ssis_: break
        ssis.update(ssis_)

        # if there is data left, it must be last change time, signaling the end
        # of this packet
        if data:
            last_change, data = oscar.unpack((('last_change', 'I'),), data)
            # if last_change is not 0, then we have the whole list.
            if last_change: break
        assert not data
    o.ssimanager.ssis.update(ssis)
    try:
        grouped = sorted(funcs.groupby(ssis.values(), key = lambda s: s.type))

        log.info('SSI report:\nTotal ssis: %d\nBy type:\n%s',
                 len(ssis),'\n'.join('%r = %r items' % (id, len(items)) for (id, items) in grouped))
    except Exception, e:
        log.error("Error generating SSI report: %r", e)

    parent.next()

