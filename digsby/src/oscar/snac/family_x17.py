import logging

import oscar

x17_name="Authorization"
log = logging.getLogger('oscar.snac.x17')
subcodes = {}

def x17_init(o, sock, cb):
    log.info('initializing')
    cb()
    log.info('finished initializing')

def x17_x01(o, sock, data):
    '''
    SNAC (x17, x1): Authorization Family Error

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_01.html}
    '''
    errcode, errmsg, subcode = oscar.snac.error(data)
    submsg = subcodes.setdefault(subcode, 'Unknown') if subcode else None
    raise oscar.snac.SnacError(0x17, (errcode, errmsg), (subcode, submsg))

def x17_x02(o, pass_hash):
    '''
    SNAC (x17, x2): Client login request (md5)

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_02.html}
    '''

    fam, sub = 0x17, 0x02
    data = oscar.util.tlv_list(*o.get_login_info(pass_hash))
    
    return fam, sub, data

def x17_x03(o, sock, data):
    '''
    SNAC (x17, x3): Server login response (md5)

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_03.html}
    '''
    snac_format = (('tlvs','tlv_list'),)
    tlvs, data = oscar.util.apply_format(snac_format, data)
    tlvs = oscar.util.tlv_list_to_dict(tlvs)

    if 0x54 in tlvs:
        oscar.password_url = tlvs[0x54]

    if 0x05 in tlvs:    #w00t login
        # return server string, auth cookie
        srvstr = tlvs.get(0x05, None)
        cookie = tlvs.get(0x06, None)
        if None in (srvstr, cookie):
            raise oscar.LoginError()

        return tlvs[0x05], tlvs[0x06]

    else:    # oh noes, teh errors
        code, url = tlvs.get(0x08, None), tlvs.get(0x04, None)
        log.warning('LoginError. code: %r, repr(code): (%r) url: %s', code, code, url)
        raise oscar.LoginError(code, url)



def x17_x04(o, sock, data):
    '''
    SNAC (x17, x4): Request new screen name

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_04.html}
    '''
    raise NotImplementedError

def x17_x05(o, sock, data):
    '''
    SNAC (x17, x5): New screen name response

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_05.html}
    '''
    raise NotImplementedError

def x17_x06(username):
    '''
    SNAC (x17, x6): Client signon request

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_06.html}
    '''
    return 0x17, 0x06, oscar.util.tlv_list((1, username))#, (0x4B,), (0x5A,))

def x17_x07(o, sock, data):
    '''
    SNAC (x17, x7): Server logon response

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_07.html}
    '''
    snac_format = (('key_len', 'H'),
                   ('key', 's', 'key_len')
                   )

    __, key, data = oscar.util.apply_format(snac_format, data)

    return key


def x17_x0a(o, sock, data):
    '''
    SNAC (x17, xa): Server SecureID request

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_0a.html}
    '''
    raise NotImplementedError

def x17_x0b(o, sock, data):
    '''
    SNAC (x17, xb): Client SecureID response

    reference: U{http://iserverd.khstu.ru/oscar/snac_17_0b.html}
    '''
    raise NotImplementedError

