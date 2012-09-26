from time import clock
from threading import RLock
import wx.webview
from util.primitives.mapping import dictdiff
from .permchecks import PermCheck
import sys
import threading
import types
import facebookapi
import traceback
import util.net as net
from logging import getLogger
import util.callbacks as callbacks
import simplejson
from provider_facebook import facebookapp
log = getLogger('fb20.connect')

from facebookapi import \
DIGSBY_API_KEY, DIGSBY_APP_SECRET, DIGSBY_APP_ID, \
DIGSBY_ACHIEVEMENTS_API_KEY, DIGSBY_ACHIEVEMENTS_APP_SECRET, DIGSBY_ACHIEVEMENTS_APP_ID

HTTP_FBLOGIN = "http://www.facebook.com/login.php"
INVITE_URL_FAKE = "http://apps.facebook.com/digsbyim/invite.php"

DIGSBY_LOGIN_URL = 'https://accounts.digsby.com/login.php'

FACEBOOK_URL      = 'http://www.facebook.com/'
ADD_APP_URL       = FACEBOOK_URL + 'add.php'

LOGIN_SUCCESS_PAGE = 'https://apps.facebook.com/digsbyim/index.php?c=skipped'

FB_CONNECT_OPTS = dict(fbconnect='true', v='1.0', connect_display='popup', return_session='true')

DPERMS_DA = ['read_stream'] + ['publish_stream'] + ['user_events'] + ['xmpp_login'] + ['manage_notifications']
DPERMS_D  = DPERMS_DA #+ ['publish_stream']
DPERMS_REQUIRED = ['read_stream'] + ['user_events'] + ['xmpp_login'] + ['manage_notifications']
APERMS = ['publish_stream']
APERMS_REQUIRED = APERMS[:]

DIGSBY_LOGIN_PERMS = net.UrlQuery(HTTP_FBLOGIN, api_key = DIGSBY_API_KEY, **FB_CONNECT_OPTS)
DIGSBY_ACHIEVEMENTS_LOGIN_PERMS = net.UrlQuery(HTTP_FBLOGIN, api_key = DIGSBY_ACHIEVEMENTS_API_KEY, **FB_CONNECT_OPTS)

def print_fn(func):
    def wrapper(*a, **k):
        print clock(), func.__name__
        return func(*a, **k)
    return wrapper

class MethodPrinter(type):
    def __init__(cls, name, bases, dict):
        for k,v in list(dict.items()): #explicit copy
            if isinstance(v, types.FunctionType):
                setattr(cls, k, print_fn(v))
        super(MethodPrinter, cls).__init__(name, bases, dict)

class FBProto(object):
#    __metaclass__ = MethodPrinter
    def __init__(self):
        self.lock = RLock()
        self._init_apis()

    def _init_apis(self):
        self._init_digsby()
        self._init_digsby_ach()

    def _init_digsby(self, session_key='', secret=''):
        self.digsby = facebookapi.DigsbyAPI(session_key, secret, name='digsby')

    def _init_digsby_ach(self, session_key='', secret=''):
        self.digsby_ach = facebookapi.DigsbyAchievementsAPI(session_key, secret, name='digsby_ach')

class LoginCheck(FBProto):

    def __init__(self, digsby_api=None, digsby_ach_api=None, login_success=None, login_error=None, username=None, do_ach=True, acct=None, ask_ach=None, *a, **k):
        FBProto.__init__(self)
        if digsby_api is not None: self.digsby = digsby_api
        if digsby_ach_api is not None: self.digsby_ach = digsby_ach_api
        self.ask_ach = ask_ach if ask_ach is not None else do_ach
        self.login_success_cb = login_success
        self.login_error_cb = login_error
        self.dead = False
        self.do_ach = do_ach
        self.username = username
        self.window = None

        self.acct = acct

        self.try_login = False
        #need locks
        self.waiting_d_init  = False
        self.d_init_succ     = False
        self.waiting_da_init = False
        self.da_init_succ    = False
        self.lock            = threading.RLock()

    def _finished(self):
        if self.window is not None:
            window, self.window = self.window, None
            window.close()
        self.dead = True

    def login_success(self, *a, **k):
        # close window somehow?
        self._finished()
        self.login_success_cb(*a, **k)

    def login_error(self, *a, **k):
        # close window somehow?
        self._finished()
        self.login_error_cb(*a, **k)

    def initiatiate_check(self, try_login = False):
        self.try_login = try_login
        if not self.digsby.logged_in:
            log.info('digsby api not logged in')
            log.info_s('not logged in: api: %r, session: %r', self.digsby.name, self.digsby.session_key)
            return self.do_not_logged_in()
        if self.do_ach and not self.digsby_ach.logged_in:
            log.info('ach api not logged in')
            log.info_s('not logged in: api: %r, session: %r', self.digsby_ach.name, self.digsby_ach.session_key)
            return self.do_not_logged_in()

        d_p = PermCheck(self.digsby, perms=DPERMS_REQUIRED)
        self.waiting_d_init  = True
        if self.do_ach:
            da_p = PermCheck(self.digsby_ach, perms=APERMS_REQUIRED)
            self.waiting_da_init = True
            da_p.check(success=self.da_init_check_succ, error=self.da_init_check_fail)
        d_p.check(success=self.d_init_check_succ, error=self.d_init_check_fail)

    def d_init_check_succ(self, answer):
        do_success = False
        with self.lock:
            self.d_init_succ = True
            self.waiting_d_init  = False
            log.info('d_succ do_ach %r, waiting_da_init %r, da_init_succ %r', self.do_ach, self.waiting_da_init, self.da_init_succ)
            if not self.do_ach:
                do_success = True
            elif not self.waiting_da_init and self.da_init_succ:
                do_success = True
        if do_success:
            self.login_success(self)

    def d_init_check_fail(self, answer):
        do_fail = False
        with self.lock:
            self.d_init_succ = False
            self.waiting_d_init  = False
            log.info('d_fail do_ach %r, waiting_da_init %r, da_init_succ %r', self.do_ach, self.waiting_da_init, self.da_init_succ)
            if not self.do_ach:
                do_fail = True
            elif self.waiting_da_init or ((not self.waiting_da_init) and self.da_init_succ):
                do_fail = True
        if do_fail:
            self.do_not_logged_in(answer)

    def da_init_check_succ(self, answer):
        do_success = False
        with self.lock:
            self.da_init_succ = True
            self.waiting_da_init  = False
            log.info('da_succ waiting_d_init %r, d_init_succ %r', self.waiting_d_init, self.d_init_succ)
            if not self.waiting_d_init and self.d_init_succ:
                do_success = True

        if do_success:
            self.login_success(self)

    def da_init_check_fail(self, answer):
        do_fail = False
        with self.lock:
            self.da_init_succ = False
            self.waiting_da_init  = False
            log.info('waiting_d_init %r, d_init_succ, %r', self.waiting_d_init, self.d_init_succ)
            if self.waiting_d_init:
                do_fail = True
        if do_fail:
            self.do_not_logged_in()

    def do_not_logged_in(self, answer=None):
        if self.try_login:
            wx.CallAfter(self.do_initial_login)
        else:
            self.login_error(self)

    def do_initial_login(self):
        self.continue_login2(LOGIN_SUCCESS_PAGE)

    def continue_login2(self, forward_to):
        from common import pref
        next = forward_to
        ach_next = ''
        if self.ask_ach:
            ach_next = next
            next = ach_url = net.UrlQuery(DIGSBY_ACHIEVEMENTS_LOGIN_PERMS, next=ach_next, req_perms=','.join(APERMS))
            if not pref('facebook.webkitbrowser', default=False, type=bool):
                next = net.UrlQuery(LOGIN_SUCCESS_PAGE, next=next)

        digsby_next = next
        if self.ask_ach:
            d_req_perms = DPERMS_DA
        else:
            d_req_perms = DPERMS_D
        if self.ask_ach:
            url = net.UrlQuery(DIGSBY_LOGIN_PERMS, next=next, skipcookie='true', req_perms=','.join(d_req_perms),
                           cancel_url = ach_url)
        else:
            url = net.UrlQuery(DIGSBY_LOGIN_PERMS, next=next, skipcookie='true', req_perms=','.join(d_req_perms),
                           )
        log.info("facebook creating window")
        window = self.window = FBLoginWindow(self.username, self.acct)

        def on_nav(e = None, b = None, url=None, *a, **k):
            if not window.ie:
                e.Skip()
                #careful with name collision
                url = e.URL
            try:
                parsed = net.UrlQuery.parse(url)
            except Exception:
                traceback.print_exc()
            else:
                log.info('url: %r', url)
                session = parsed['query'].get('session')
                auth_token = parsed['query'].get('auth_token')

                log.info('has session?: %r', session is not None)
                log.info('has auth_token?: %r', auth_token is not None)

                target = None
                if auth_token or session:
                    parsed_base = dict(parsed)
                    parsed_base.pop('query')
                    parsed_base.pop('scheme')
                    digsby_next_parsed = net.UrlQuery.parse(digsby_next)
                    log.info('digsby_next_parsed: %r', digsby_next_parsed)
                    digsby_next_parsed['query'].pop('', None) #this happens for urls with no query, which we may/maynot have
                    digsby_next_parsed.pop('scheme') #http/https is not what interests us
                    digsby_next_parsed_base = dict(digsby_next_parsed)
                    digsby_next_parsed_base.pop('query')
                    ach_next_parsed = net.UrlQuery.parse(ach_next)
                    log.info('ach_next_parsed: %r', ach_next_parsed)
                    ach_next_parsed['query'].pop('', None) #this happens for urls with no query, which we may/maynot have
                    ach_next_parsed.pop('scheme') #http/https is not what interests us
                    ach_next_parsed_base = dict(ach_next_parsed)
                    ach_next_parsed_base.pop('query')

                    if parsed_base == digsby_next_parsed_base:
                        target = 'digsby'
                    elif parsed_base == ach_next_parsed_base:
                        target = 'digsby_ach'

                if target is None:
                    return

                if auth_token:
                    log.info('parsed: %r', parsed)
                elif session:
                    #not sure how to clean this up right now.
                    log.info('parsed: %r', parsed)
                    log.info('Parsing url: %r, %r', parsed_base, parsed['query'])
                    if target == 'digsby':
                        log.info('got digsby session')
                        log.info_s('\tsession = %r, auth_token = %r', session, auth_token)
                        self.digsby.set_session(session)
                        self.digsby.logged_in = True
                        if not self.ask_ach and not self.dead:
                            self.login_success(self, did_login = True)
                        if not self.dead:
                            if not pref('facebook.webkitbrowser', default=False, type=bool):
                                b.Stop()
                                b.LoadUrl(digsby_next_parsed['query']['next'])
                    elif target == 'digsby_ach':
                        log.info('got ach session')
                        log.info_s('\tsession = %r, auth_token = %r', session, auth_token)
                        self.digsby_ach.set_session(session)
                        self.digsby_ach.logged_in = True
                        if not (self.digsby.logged_in and self.digsby.uid == self.digsby_ach.uid):
                            #wtf happened if these fail? - IE cookies
                            return self.login_error(self)
                        if not self.dead:
                            return self.login_success(self, did_login = True)

        def on_close(*a, **k):
            if not self.dead:
                return self.login_success(self, did_login = True)
#                self.login_error(self)
        if window.webkit:
            def on_load(e, browser):
                if e.URL == url:
                    browser.RunScript('document.getElementById("offline_access").checked=true;')
                    browser.RunScript('document.getElementById("email").value = %s;' % simplejson.dumps(self.username))
        else:
            def on_load(*a, **k):
                pass

        window.set_callbacks(on_nav, on_load, on_close)
        window.clear_cookies()
        window.LoadURL(url)

class FBLoginWindow(object):
#    __metaclass__ = MethodPrinter
    def clear_cookies(self):
        if hasattr(self.browser, 'ClearCookies'): self.browser.ClearCookies()
    def __init__(self, account_name = '', acct=None):
        fbSize = (720, 640)
        if account_name:
            account_name = ' (' + account_name + ')'
        self._browser_frame = frame = wx.Frame(None, size = fbSize, title = 'Facebook Login' + account_name, name = 'Facebook Login' + account_name)
        self.acct = acct
        if acct is not None:
            bmp = getattr(acct, 'icon', None)
            if bmp is not None:
                frame.SetIcon(wx.IconFromBitmap(bmp.Resized(32)))
        from common import pref
        if pref('facebook.webkitbrowser', default=True, type=bool) or sys.platform.startswith('darwin'):
            self.webkit = True
            self.ie = False
            from gui.browser.webkit.webkitwindow import WebKitWindow as Browser
        else:
            self.webkit = False
            self.ie = True
            from gui.browser import Browser
        frame.CenterOnScreen()
        frame.fblogin = self
        self.browser = b = Browser(frame)

        if self.webkit:
            b.Bind(wx.webview.EVT_WEBVIEW_BEFORE_LOAD, self.on_nav)
            b.Bind(wx.webview.EVT_WEBVIEW_LOAD, self._on_load)
        elif self.ie:
            b.OnNav += self.on_nav
            b.OnBeforeNav += self.on_nav
            b.OnDoc += self.on_nav #note the difference from _on_load
            b.OnDoc += self.on_loaded #note the difference from _on_load

        frame.Bind(wx.EVT_CLOSE, self.on_close)
        self._browser = b
        self.closed = False
        self.have_loaded = False

    def set_callbacks(self, nav=None, load=None, close=None):
        self.nav = nav
        self.load = load
        self.close = close

    def LoadURL(self, url):
        if self.webkit:
            self._browser.LoadURL(url)
        elif self.ie:
            self._browser.LoadUrl(url)

    def on_close(self, e):
        assert not self.closed
        self.closed = True
        e.Skip()
        if self.close:
            self.close(e, self._browser)

    def on_nav(self, e):
        if self.ie:
            if self.nav:
                self.nav(e, self._browser, url=e)
            return
        e.Skip()
        if self.nav:
            self.nav(e, self._browser)

    def _on_load(self, e):
        e.Skip()
        if e.State == wx.webview.WEBVIEW_LOAD_DOC_COMPLETED:
            self.have_loaded = True
            return self.on_loaded(e)
        elif e.State == wx.webview.WEBVIEW_LOAD_FAILED:
            if self.have_loaded == False \
              and self._browser_frame is not None \
              and not wx.IsDestroyed(self._browser_frame) \
              and not self._browser_frame.Shown:
                self._browser_frame.Close()

    def on_loaded(self, e):
        if self._browser_frame is None:
            return

        if not self._browser_frame.Shown:
            self._browser_frame.Show()
        if self.load:
#            load, self.load = self.load, None
            if self.webkit:
                ret = self.load(e, self._browser)
            elif self.ie:
                ret = self.load(e, self._browser, url=e)
#            if not ret:
#                self.load = load

    def Close(self):
        if self._browser_frame is not None:
            bf, self._browser_frame = self._browser_frame, None
            bf.Close()
