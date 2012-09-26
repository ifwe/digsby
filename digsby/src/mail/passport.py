from urllib2 import urlopen, quote, unquote, Request, HTTPError, URLError

from hashlib import sha1
from hmac import HMAC

import logging
log = logging.getLogger('mail.passport')

import util
import util.xml_tag
import util.packable as packable
import util.primitives.bits as bits
import util.primitives.funcs as funcs

csd_to_dict = util.fmt_to_dict(',','=')

def escape(s):
    return s.encode('xml').replace("'", '&apos;')

def unescape(s):
    return s.decode('xml')

class SecurityTokenRequest(object):
    def __init__(self, id, domain, policyref):
        id = 'RST%d'%id
        util.autoassign(self, locals())
        self.__gotdata = False
        self._received = None

    def _set_received(self, val):
        self._received = val
        self.__gotdata = True

    def _get_received(self):
        return self._received

    received = property(_get_received, _set_received)

    def _get_Token(self):
        if self.__gotdata:
            return str(self.received.RequestedSecurityToken.BinarySecurityToken)
        else:
            return None

    def _set_Token(self, newtoken):
        if self.__gotdata:
            self.received.RequestedSecurityToken.BinarySecurityToken._cdata = newtoken

        else:
            raise AttributeError("can't set attribute")

    Token = property(_get_Token, _set_Token)

    @property
    def number(self):
        return int(self.id[3:])

def csd_to_storage(str):
    '''
    turn mime headers into a storage object
    '''
    info = csd_to_dict(str)
    for k in info.keys():
        info[util.pythonize(k)] = info.pop(k)

    return util.to_storage(info)

@util.callsback
def do_tweener_auth_2(username, password, twn_str, callback=None):
    '''
    TWN (Tweener) authorization

    MSN's authorization procedure to login with a passport.
    This makes 2 https requests, no wonder it takes so long to login
    to MSN.

    @param twn_str:        The TWN ticket from an earlier logon stage
    '''
    twn_str, = twn_str
    data = urlopen("https://nexus.passport.com/rdr/pprdr.asp" ).headers.get('passporturls')

    info = csd_to_storage(data)

    login_url = info['DALogin']
    if login_url.find("https://" ) == -1:
        login_url = 'https://' + login_url

    login_request = Request(login_url)

    login_request.add_header('Authorization',
                             'Passport1.4 OrgVerb=GET,OrgURL=%s,sign-in=%s,pwd=%s,%s' %
                             (quote("http://messenger.msn.com"),
                              quote(username),
                              quote(password),
                              twn_str))
    login_response = None
    try:
        login_response = urlopen(login_request).headers
    except (HTTPError, URLError):
        log.critical(login_response)
        log.critical("Login failed")
        callback.error('Error connecting to login server (%s)' % login_response)

    if 'www-authenticate' in login_response:
        response_data = login_response['www-authenticate'].split()[1]
    elif 'authentication-info' in login_response:
        response_data = login_response['authentication-info'].split()[1]

    info = csd_to_storage(response_data)

    status = info.da_status

    if status == 'success':
        callback.success(info.from_pp.strip("'"))
    elif status == 'failed':
        log.error('Login response status was "failed". heres the info.cbtxt: %r', info.cbtxt)
        callback.error(unquote(info.cbtxt))

@util.callsback
def do_tweener_auth_3(username, password, twn_str, use_ssl=True, callback=None):
    '''
    use_ssl is ignored in this version of passport;
    all authentication is done via ssl
    '''
    twn_str, = twn_str
    twn_str = unquote(twn_str).replace(',','&')

    if not twn_str.startswith('?'):
        twn_str = '?'+twn_str

    sectoks = (
           SecurityTokenRequest(id, dom, pol)
           for id,(dom,pol) in
           enumerate((('http://Passport.NET/tb',''),
                      ('messengerclear.live.com', twn_str)))
           )

    env = make_auth_envelope(username, password, sectoks)

    t = util.xml_tag.post_xml('https://loginnet.passport.com/RST.srf',
                 env._to_xml(),
                 success=lambda _t: _tweener_auth_3_success(username, password, callback, _t, twn_str),
                 error=  lambda _e: callback.error('Authentication error: %s' % str(_e)))

def _tweener_auth_3_success(username, password, callback, t, twn_str):
    try:
        ticket = str(t._find('BinarySecurityToken')[0])
        assert ticket, 'no ticket: <%r>'%ticket
    except:
        log.warning('Passport v3.0 failed, trying passport 2.0')
        return do_tweener_auth_2(username, password,(twn_str,), callback=callback)

    return callback.success(ticket.replace('&amp;','&'))

@util.callsback
def do_tweener_auth_4(username, password, tweener, iv=None, xml=None, callback=None):

    ###
    # Build and send SOAP request
    #
    policy_uri, nonce = tweener
    sectoks = [
       SecurityTokenRequest(id, dom, pol)
       for id,(dom,pol) in
       enumerate((('http://Passport.NET/tb',''),
                  ('contacts.msn.com','?fs=1&id=24000&kv=9&rn=93S9SWWw&tw=0&ver=2.1.6000.1'),
                  ('spaces.live.com', 'MBI'),
                  ('messenger.msn.com', '?id=507'),
                  ('messengersecure.live.com','MBI_SSL'),
                  ('messengerclear.live.com', policy_uri),
                  ))
       ]

    env = make_auth_envelope(username, password, sectoks)

    request_tokens(env, sectoks, xml,
                   success=lambda tok,sec, toks:callback.success(tok,mbi_crypt(sec, nonce,iv), toks),
                   error=callback.error)

#    ###
#    # Now that we have the nonce and "binary secret" key,
#    # we need to do fancy crypto to create the challenge response.
#
#    #mbi_blob = mbi_crypt(secret, nonce)
#    #result = '%s %s' % (token,mbi_blob)
#    #callback.success(result)
#
#    callback.success(token, mbi_crypt(secret, nonce))

@util.callsback
def request_tokens(env, sectoks, xml=None, login_check=True, callback=None, url='https://login.live.com/RST.srf'):
    ###
    # Received SOAP response is now in xml. Get out the important bits.
    #

    return util.xml_tag.post_xml(url,
                    env._to_xml(),
                    success=lambda _t: _handle_token_response(env,sectoks, _t,callback=callback),
                    error  =lambda _t: _handle_token_request_error(_t, (env, sectoks, xml, login_check), callback))

@util.callsback
def _handle_token_response(env, sectoks, xml, login_check = True, callback = None, url = 'https://login.live.com/RST.srf'):

    if type(xml) is not util.xml_tag.tag:
        t = util.xml_tag.tag(xml)
    else:
        t = xml

    if t.Fault:
        errmsg = 'SOAP Fault trying to authenticate. Here\'s the fault xml: %r' % t.Fault._to_xml()
        log.error(errmsg)
        callback.error(Exception(errmsg))
        return

    tokens = {}

    RSTS = t.Body.RequestSecurityTokenResponseCollection.RequestSecurityTokenResponse

    #assert len(RSTS) == len(sectoks)

    login_token = None

    for sectok, RST in zip(sectoks, RSTS):
        tokenref = RST.RequestedTokenReference

        sectok.received = RST

        tokens[sectok.domain] = sectok

        if (funcs.get(tokenref.KeyIdentifier,'ValueType',None) == 'urn:passport:compact' and
            funcs.get(tokenref.Reference,    'URI',      None) == ('#Compact%d'% sectok.number)):
            login_token = sectok
    if login_token is None:
        errmsg = 'Could not find binary secret in response. Heres the response: %r' % t._to_xml()
        log.error(errmsg)
        return callback.error(Exception(errmsg))

    token  = str(login_token.received.RequestedSecurityToken.BinarySecurityToken).strip()
    secret = str(login_token.received.RequestedProofToken.BinarySecret).strip()

    callback.success(token, secret, tokens)

def _handle_token_request_error(soapexc, args, callback):
    '''
    <S:Envelope>
      <S:Fault>
        <faultcode>
          psf:Redirect
        </faultcode>
        <psf:redirectUrl>
          https://msnia.login.live.com/pp550/RST.srf
        </psf:redirectUrl>
        <faultstring>
          Authentication Failure
        </faultstring>
      </S:Fault>
    </S:Envelope>
    '''

    if not isinstance(soapexc, util.xml_tag.SOAPException):
        import sys
        print >>sys.stderr, soapexc
        import traceback;traceback.print_exc()
        callback.error(soapexc)

    elif 'Redirect' in str(soapexc.fault.faultcode):
        redirect_url = soapexc.fault.redirectUrl._cdata
        request_tokens(callback=callback, url=redirect_url, *args)
    else:
        log.error('Exception when requesting tokens. heres the response XML: %r', soapexc.t._to_xml())
        callback.error(soapexc)


def mbi_crypt(key, nonce, iv=None):
    wssec = "WS-SecureConversation"
    from util.cryptography import DES3

    if iv is None:
        iv = bits.getrandbytes(8)

    key1 = key.decode('base64')
    key2 = derive_key(key1, wssec+'SESSION KEY HASH')
    key3 = derive_key(key1, wssec+'SESSION KEY ENCRYPTION')

    hash = HMAC(key2, nonce, sha1).digest()

    des = DES3(key3, 2, iv)

    # wincrypt pads with '\x08' bytes
    pad = lambda s: s+((8-(len(s)%8))*chr(8))
    cipher = des.encrypt(pad(nonce))

    return keystruct(iv, hash, cipher).pack().encode('base64').replace('\n','')

def derive_key(key, message):
    hmac_attack = lambda s: HMAC(key, s, sha1).digest()

    hash1 = hmac_attack(message)
    hash2 = hmac_attack(hash1 + message)
    hash3 = hmac_attack(hash1)
    hash4 = hmac_attack(hash3 + message)

    return hash2 + hash4[:4]

class keystruct(packable.Packable):
    byteorder = '<'
    fmt = util.strlist('''
        size      L    # always 28
        mode      L    # always 1 for CBC
        cipheralg L    # always 0x6603 for 3DES
        hashalg   L    # always 0x8004 for SHA-1
        ivlen     L    # always 8
        hashlen   L    # always 20
        cipherlen L    # always 72

        iv        8s   # random data for initialization vector
        hash      20s  # SHA-1 result
        cipher    72s  # Crypted data
        ''')

    def __init__(self, *args):
        if len(args) == 3:
            iv, hash, cipher = args
            packable.Packable.__init__(self, 28, 1, 0x6603, 0x8004, 8, 20, 72, iv, hash, cipher)
        else:
            packable.Packable.__init__(self, *args)

ns = lambda ns, name: '%s:%s' % (ns, name)

ns_map = dict(ps="http://schemas.microsoft.com/Passport/SoapServices/PPCRL",
              wsse='http://schemas.xmlsoap.org/ws/2003/06/secext',
              saml='urn:oasis:names:tc:SAML:1.0:assertion',
              wsp="http://schemas.xmlsoap.org/ws/2002/12/policy",
              wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd",
              wsa="http://schemas.xmlsoap.org/ws/2004/03/addressing",
              wssc="http://schemas.xmlsoap.org/ws/2004/04/sc",
              wst="http://schemas.xmlsoap.org/ws/2004/04/trust",)

def make_auth_envelope(uname, password, sec_toks):
#    uname = escape(uname)
#    print 'password before escape:',repr(password)
#    password = escape(password)
#    print 'password after escape:',repr(password)

    #tag._set_ns_dict(ns_map)

    authinfo = util.xml_tag.tag('AuthInfo', Id='PPAuthInfo', _ns_dict=ns_map)
    auth_tags = (('HostingApp', '{7108E71A-9926-4FCB-BCC9-9A9D3D32E423}'),
                 ('BinaryVersion', 4),
                 ('UIVersion', 1),
                 ('Cookies', ''),

                 ('RequestParams', 'AQAAAAIAAABsYwQAAAAzMDg0'))#'AQAAAAIAAABsYwQAAAAyMDUy')) # 'AQAAAAIAAABsYwQAAAAxMDMz'

    for atag in auth_tags:
        authinfo += atag

    authinfo._recurse_ns('ps')

    security = util.xml_tag.tag('Security', _ns_dict=ns_map)
    utoken = util.xml_tag.tag('UsernameToken', Id='user', _ns_dict=ns_map)

    utoken += 'Username', uname
    utoken += 'Password', password

    security += utoken

    security._recurse_ns('wsse')

    tokens = util.xml_tag.tag(('ps', 'RequestMultipleSecurityTokens'), Id= 'RSTS', _ns_dict=ns_map)

    for tok in sec_toks:
        tokens += SecTok_to_tag(tok)

    env = util.xml_tag.tag('Envelope', xmlns="http://schemas.xmlsoap.org/soap/envelope/", _ns_dict=ns_map)
    env.Header += authinfo
    env.Header += security
    env.Body += tokens

    #tag._set_ns_dict({})

    return env

def SecTok_to_tag(tok):
    token = util.xml_tag.tag(('wst', 'RequestSecurityToken'), Id=tok.id, _ns_dict=ns_map)
    token += ('wst', 'RequestType'), 'http://schemas.xmlsoap.org/ws/2004/04/security/trust/Issue'
    token += ('wsp', 'AppliesTo'),
    token.AppliesTo += ('wsa', 'EndpointReference'),
    token.AppliesTo.EndpointReference += ('wsa', 'Address'), tok.domain

    if tok.policyref:
        token += util.xml_tag.tag(('wsse','PolicyReference'), URI=escape(tok.policyref), _ns_dict=ns_map)

    return token


if __name__ == '__main__':
    import util.primitives.bits as bits
    data_sets = [
                 ('pBsAH1PE97Iapn9KSBgnwhXrYSMW4pR8owDHuEl2uHHYOcuIkTlXJv/He09hM8EK','26 54 8a 6d 78 ef b6 a0', '7d6QketNdj77tbJ60OYrfRaFxK8wHDVU', '''t=EwDYAW+jAAAU7/9PdvvYJ23zPPtor/FYp6zOOb+AAMIw/mhop1kwJEXzEh3RL9m1NtZSQjKhl5VdZ+YORglKpsZkjaDMp4OxbT4k2DycwGJp0TOm9NrHMRkMlfBxyTuoSz7ykvPxcA7aGRFzpKSb/9qFHrrouhOM0xmfNG+bse1mLJZBvJ8arY97Sl+bknzkzK7OWTkjYYatCWC/HA6GA2YAAAi5hIbJSpr+aigBVtdThK4FdpmbcFCEOV0n5sZSzbIPgDXJshII7WO8hHy6YT6W671nHJ6u0biRQEAcK6StXHTMT9XjesBd22m6vU0Zd84fZBm4rA/5yP0aeAjbLDELznzL0nga2J1HxPQzh3GrGGuncOYS3s8VgdMuBEkkQu6COooKE47D08wIvsMLqqrzuMTdrgJs23yabcw6IKtW+h7Umzod8eW2PAsoFDeMnQqPMPlK+WkqVXwrN5BSInq6TQOSPPiuVbFVeipozqTrwUxm7HYytyOJCCXJEC7+RNCfYGDNvHCYqzg6YtXsqRKqCqcfYVVoyEOzme41+sjdezYG3hp7UxYQd622SkVtG4iL/x15ElmTFricGa4b3aI5nnT9JkejpxtDu9QXJLri92tDEZ5AAQ==&p=''', '''HAAAAAEAAAADZgAABIAAAAgAAAAUAAAASAAAACZUim1477agqOu2i/I8hk+Pg/+E7NqzIuMdhhKttQYvu/iTM1R5ffPn4lWJ97ffVqadDf9AV2AWaSSmNqTqat1Zkt1lmmB1pV+zSS+RG6v3wxOtnqOTrOwIuLScAACurFwszUw='''),
                 ('B/zj+2hwriu8x+Pw/bJIouMbeVy0QOVeFw3Lr+aHbXN8oyMxgpddC2eRMequq+g+','11 e9 f7 9e 7c 14 a8 b9', '2yF3I/LHM6+2RnUgZKbM9eBN/ufdJysB', '''t=EwDYAW+jAAAU7/9PdvvYJ23zPPtor/FYp6zOOb+AADbMUMrwrh00M/sccjmDtcfq0lf20h1At/eQQJfL5K7+ouDgJEd/GuRpe3vopy9jT/U0YNVmZyIfQyQnPYKWGU8pHkXMhcuh/HRnFZu7mJWJAFIS/+wpr+7F1LfOnXjrunJnRxZq3y3nwWDLEkh+x+tQOGD7M0B93KcXODigkydFA2YAAAhywJ/PdD2v2igBV+o6Htfb83lgo8pH9Wlpra7pAUb7MK5L9NjvwWxUk7sEVbNErEJZXuvTfkhZcEhTKGrkZpJRzzx4Qmy3K6317uT3+pVd/Dv4bGxC3ZD/BPWfo9Sj1XXZL8bgGMDgI/rJCBKSAL2nM+gpjGbtTdW8q0QhNzy8WD6FeHrFdOzDcc/339ckMjQvkE5wNieCoRUDpFRjKFr7rVytmAe+8vzecQ2TibxZp5mAke192hbIfa6H8PUUMyKK/mhFqTdfV2HyjZY5YPGXLMrpnmr3fdfv92+a2CIwzSFfhRMVOxnu3X3Gbn0YPryAdiA0gv5Nwuf7wEwFkdQQeebHDSjMsvSZNwJH5SoV92lyiLKicLIPlpaO54PnQ3Y9/JOYdf2d0gYfxSW6JaK+K8tAAQ==&p=''', '''HAAAAAEAAAADZgAABIAAAAgAAAAUAAAASAAAABHp9558FKi5q1MxG97qu/j2H+kxfUff2sq9xTGIpx71DCKtX40WmvnvuuUPGhNyViNKtAnksnnhsQuGVhw+ZCV9vBHoN8oNYBy10cHUyTxLzOVcbCtS55rWlt4pQU+6CGpOPHU='''),
                 ]

    for nonce, iv, key, their_ticket, their_token in data_sets:

        def checker(ticket, token, alltokens):
            mine = '%s %s' % (ticket, token)
            print ticket == their_ticket, ticket, their_ticket
            print token == their_token, token, their_token
            assert ticket == their_ticket
            assert token == their_token

        def error(*a):
            print 'there was error:',a
            raise a

        mine = mbi_crypt(nonce, key, bits.hex2bin(iv))
        print mine
        print their_token
        assert mine == their_token
        #do_tweener_auth_4('', '', ('MBI', nonce), iv=bits.hex2bin(iv), xml=xml, success=checker, error=error)
    print 'success'
