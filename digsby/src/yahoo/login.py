import base64
import cookielib
import logging
import traceback
import types
import urllib2
import util.net

log = logging.getLogger('yahoo.login')

class YahooAuthException(Exception):
    error_type = "Unknown"
    error_msg  = None
    known_codes = {}
    def __init__(self, resp_str):
        Exception.__init__(self, resp_str)
        try:
            code = self.code = resp_str.split()[0]
        except Exception:
            self.code = None
        else:
            self.error_msg = _error_messages.get(code)
            if code in self.known_codes:
                self.__class__ = self.known_codes[code]

_error_types = [ #these are NOT translatable
               ('1212', 'Bad Password'),
               ('1213', 'Security Lock'),
               ('1221', 'Account Not Set Up'),
               ('1235', 'Bad Username'),
               ('1236', 'Rate Limit'),
               ]

_error_messages = { #these ARE translatable
                   '1212': _('Bad Password'),
                   '1213': _('There is a security lock on your account. Log in to http://my.yahoo.com and try again.'),
                   '1221': _('Account Not Set Up'),
                   '1235': _('Bad Username'),
                   '1236': _('Rate Limit'),
                   }

for code, error_type in _error_types:
    name = ''.join(['Yahoo'] + error_type.split() + ['Exception'])
    klass = types.ClassType(name, (YahooAuthException,), dict(error_type = error_type))
    globals()[name] = YahooAuthException.known_codes[code] = klass
    del name, klass, code, error_type #namespace pollution

def yahoo_v15_auth(challenge, password, username, jar=None):
    jar = jar if jar is not None else cookielib.CookieJar()
    http_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar), *util.net.GetDefaultHandlers())
    from time import time
    now = int(time())
    url_password = util.net.UrlQuery("https://login.yahoo.com/config/pwtoken_get",
                   src='ymsgr',
                   ts=str(now),
                   login=username,
                   passwd=password,
                   chal=challenge)
    resp = http_opener.open(url_password)
    resp = resp.read()
    log.info('Yahoo response starts: %r', resp[:100])

    if not resp.startswith('0'):
        raise YahooAuthException(resp)

    token = resp.split('\r\n')[1].split('=')[1]
    url2 = util.net.UrlQuery("https://login.yahoo.com/config/pwtoken_login",
                   src='ymsgr',
                   ts=str(now),
                   token=token)
    resp2 = http_opener.open(url2)
    resp2 = resp2.read()
    log.info('Yahoo response2 starts: %r', resp2[:100])
    #got '100' here from the sbcglobal response above
    lines = resp2.split('\r\n')

    crumb = lines[1].split('=')[1]
    y = lines[2]
    t = lines[3]
    y = y[2:]
    t = t[2:]
    return crumb, y, t, jar

def yahoo64(buffer):
    'Wacky yahoo base 64 encoder.'
    return base64.b64encode(buffer, '._').replace('=', '-')

LOAD_BALANCERS = ['http://vcs2.msg.yahoo.com/capacity', #2 had a lower ping
                  'http://vcs1.msg.yahoo.com/capacity']

HTTP_LOAD_BALANCERS = ['http://httpvcs2.msg.yahoo.com/capacity',
                       'http://httpvcs1.msg.yahoo.com/capacity']

def get_load_balance_info(server):
    data = util.net.wget(server)
    site = data.split()
    pairs = [line.split('=') for line in site]
    d = dict(pairs)
    return d['CS_IP_ADDRESS']

def async_get_load_balance_info(server, callback=None):
    from common import asynchttp
    def success(req, resp):
        try:
            data = resp.read()
            site = data.splitlines()
            pairs = [line.strip().split('=') for line in site]
            d = dict((x.strip(), y.strip()) for x,y in pairs)
            callback.success(d['CS_IP_ADDRESS'])
        except Exception, e:
            traceback.print_exc()
            callback.error(e)
    def error(*a):
        callback.error(None)
    def timeout(*a):
        callback.timeout(None)

    asynchttp.httpopen(server,
                       success = success,
                       error   = error,
                       timeout=timeout)

