from .YahooSocket import DEFAULT_YMSG_VERSION
from .login import yahoo64, YahooRateLimitException, \
    YahooAuthException
from hashlib import md5
from logging import getLogger
from common.asynchttp.cookiejartypes import CookieJarHTTPMaster
from .yahoolookup import ykeys
import urllib2
import cookielib
import common
import util.net
log = getLogger('YahooLogin.base')

class YahooLoginBase(object):
    def __init__(self, yahoo):
        pass

    def logon(self):
        'Login generator.'

        y = self.yahoo
        def fail(exc = None):
            y.set_disconnected(y.Reasons.CONN_FAIL)

        user, password = y.username, y.password
        log.info('logging in %s', user)

        y.change_state(y.Statuses.AUTHENTICATING)

        yield self.send_auth_req(user)
        print 'waiting for auth'
        (_hdr, data) = (yield self.gwait('auth', 'brb', self.logon_err))
        print 'got auth_brb'
        # got a auth challenge back
        auth_challenge = self.from_ydict(data)

        if not '94' in auth_challenge:
            log.warning('auth challenge packet did not have challenge str (94): %r', auth_challenge)
            fail()
            return

        challenge_str = auth_challenge['94']
        common.callsback(self.yahoo_15_weblogin)(user, password, challenge_str, error=fail)

    def yahoo_15_weblogin(self, user, password, challenge_str, callback=None):
        '''
        Version 15 login, using an SSL connection to an HTTP server.
        '''
        y = self.yahoo
        jar = getattr(y, 'jar', None)
        def yahoo_v15_auth_success(crumb, yc, t, jar):
            y.cookies.update(Y = yc.split()[0][:-1],
                             T = t.split()[0][:-1])
            y.jar = jar

            crumbchallengehash = yahoo64(md5(crumb + challenge_str).digest())

            log.info('logging on with initial status %s', y.initial_status)
            common.netcall(lambda: y.send('authresp', y.initial_status, [
                                   1,          user,
                                   0,          user,
                                   'ycookie',  yc,
                                   'tcookie',  t,
                                   'crumbchallengehash', crumbchallengehash,
                                   'mystery_login_num', '8388543',#str(0x3fffbf),#'4194239',
                                   'identity', user,
                                   'locale', 'us',
                                   'version_str', '10.0.0.1270']))
        def yahoo_v15_auth_error(e):
            if isinstance(e, YahooRateLimitException):
                return y.set_disconnected(y.Reasons.RATE_LIMIT)
            if isinstance(e, YahooAuthException):
                y._auth_error_msg = getattr(e, 'error_msg', None) or getattr(e, 'error_type', None)
                return y.set_disconnected(y.Reasons.BAD_PASSWORD)
            callback.error(e)
        common.callsback(self.yahoo_v15_auth)(challenge_str, password, user, jar=jar,
                                     success=yahoo_v15_auth_success,
                                     error  = yahoo_v15_auth_error)

    def yahoo_v15_auth(self, challenge, password, username, jar=None, callback=None):
        jar = jar if jar is not None else cookielib.CookieJar()
        http_opener = CookieJarHTTPMaster(jar = jar)

        from time import time
        now = int(time())

        def bar(req, resp):
            resp = resp.read()
            log.info('Yahoo response starts: %r', resp[:100])
            if not resp.startswith('0'):
                return callback.error(YahooAuthException(resp))
            token = resp.split('\r\n')[1].split('=')[1]
            url2 = util.net.UrlQuery("https://login.yahoo.com/config/pwtoken_login",
                           src='ymsgr',
                           ts=str(now),
                           token=token)
            http_opener.open(url2,
                             success = lambda req, resp: self.cookie_crumbs_success(resp, jar, callback=callback),
                             error = callback.error)

        url_password = util.net.UrlQuery("https://login.yahoo.com/config/pwtoken_get",
                       src='ymsgr',
                       ts=str(now),
                       login=username,
                       passwd=password,
                       chal=challenge)
        http_opener.open(url_password,
                         success=bar,
                         error = callback.error)

    def cookie_crumbs_success(self, resp2, jar, callback=None):
        try:
            resp2 = resp2.read()
            log.info('Yahoo response2 starts: %r', resp2[:100])
            #got '100' here from the sbcglobal response above
            lines = resp2.split('\r\n')

            crumb = lines[1].split('=')[1]
            y = lines[2]
            t = lines[3]
            y = y[2:]
            t = t[2:]
        except Exception:
            callback.error()
        else:
            callback.success(crumb, y, t, jar)

    def send_auth_req(self, user):
        return self.gsend('auth', 'custom', {1:user}, v=DEFAULT_YMSG_VERSION)

    def logon_err(self):
        return NotImplemented

    def generic_error(self):
        y = self.yahoo
        y.set_disconnected(y.Reasons.CONN_FAIL)

    def chatlogon(self, command, status, data):
        def gen(command, status, data):
            me = self.yahoo.self_buddy.name

            yield self.gsend('chatonline', 'available',
                             {'1': me, '109': me, '6': 'abcde'})
            yield self.gwait('chatonline', 'brb', self.generic_error)
            yield self.gsend(command, status, data)
        self.async_proc(gen(command, status, data))

    def _unwrap_gwait(self, res):
        '''given the result of yielding to a packet generator, returns a ydict'''

        _hdr, data = res
        return self.from_ydict(data)

    def conflogon(self, roomname, callback):
        def gen():
            me = self.yahoo.self_buddy.name

            yield self.gsend('conflogon', 'available',
                             {'1': me, '3': me, '57': roomname})

            ydict = self._unwrap_gwait((yield self.gwait('conflogon', 'brb', self.generic_error)))
            actual_roomname = ydict[ykeys.conf_name]

            conf = self.yahoo._create_conference(actual_roomname)
            conf.buddy_join(self.yahoo.self_buddy)
            callback(conf)

        self.async_proc(gen())

