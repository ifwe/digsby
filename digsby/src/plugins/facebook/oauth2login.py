'''
Created on Apr 10, 2012

@author: Christopher
'''
from facebook.fbconnectlogin import FBLoginWindow
import util.net as net
import traceback
import simplejson
from facebook.graphapi import build_oauth_dialog_url
from facebook.facebookapi import DIGSBY_APP_ID
from facebook.fbconnectlogin import DPERMS_D
from logging import getLogger
import wx
from common import profile
from permchecks import PermCheck
from fbconnectlogin import DPERMS_REQUIRED
from util import callbacks
log = getLogger('fb.oauth2login')


class GraphPermCheck(PermCheck):
    @callbacks.callsback
    def check(self, callback=None):
        log.critical('checking with callback: %r', callback)
        self.callback = callback
        if not self.perms:
            return self.callback.success({})
        self.api.batch(self.api.GET('me/permissions'),
                       self.api.GET('me'),
                       self.api.GET('app'),
                       success=self.check_success, error=self.check_error)

    def check_success(self, ret):
        log.debug('check_success: %r', ret)
        try:
            perms = simplejson.loads(ret[0]['body'])['data']
            me = simplejson.loads(ret[1]['body'])
            app = simplejson.loads(ret[2]['body'])
            if app['id'] != DIGSBY_APP_ID:
                log.debug('app id has changed')
                return self.callback.error(None)
            self.api._me = me
            self.api.uid = me['id']
            return super(GraphPermCheck, self).check_success(perms)
        except Exception as e:
            log.debug('check_success Exception: %r', e)
            return self.check_error(e)


class LoginCheck(object):
    _windows = {}

    @classmethod
    def window_for_username(cls, username):
        return cls._windows.get(username, None)

    def __init__(self, api, login_success=None, login_error=None, username=None, acct=None, *a, **k):
        self.dead = False
        self.api = api
        self.access_token = getattr(self.api, 'access_token', None)
        self.login_success_cb = login_success
        self.login_error_cb = login_error
        self.username = username
        self.window = None
        self.acct = acct

    def _finished(self):
        self.dead = True
        log.debug('_finished, self.window = %r', self.window)
        if self.window is not None:
            window, self.window, _cls_window = self.window, None, self._windows.pop(self.username, None)
            window.Close()

    def login_success(self, *a, **k):
        log.debug('login_success: %r, %r', a, k)
        self.api.logged_in = True
        self._finished()
        log.debug('login_success_cb: %r', self.login_success_cb)
        self.login_success_cb(*a, **k)

    def login_error(self, *a, **k):
        log.debug('login_error: %r, %r', a, k)
        self.api.access_token = self.access_token = None
        self.access_token = None
        self._finished()
        log.debug('login_error_cb: %r', self.login_error_cb)
        self.login_error_cb(*a, **k)

    def initiatiate_check(self, try_login = False):
        log.debug('initiatiate_check: try_login: %r', try_login)
        self.try_login = try_login
        d_p = GraphPermCheck(self.api, perms=DPERMS_REQUIRED)
        d_p.check(success=self._init_check_succ, error=self._init_check_fail)

    def _init_check_succ(self, answer):
        self.login_success(self)

    def _init_check_fail(self, answer):
        self.do_not_logged_in(answer)

    def _verify_check_succ(self, answer):
        self.login_success(self, did_login = True)

    def _verify_check_fail(self, answer):
        self.login_error(self)

    def do_not_logged_in(self, answer=None):
        log.debug('do_not_logged_in: answer: %r', answer)
        if self.try_login:
            wx.CallAfter(self.start)
        else:
            self.login_error(self)

    def start(self):
        log.debug('start')

        window = self.window = type(self).window_for_username(self.username)
        if window is None:
            self._windows[self.username] = window = self.window = FBLoginWindow(self.username)

        url = build_oauth_dialog_url(DPERMS_D)

        def on_nav(e = None, b = None, url = None, *a, **k):
            if not window.ie or url is None:
                e.Skip()
                #careful with name collision
                url = e.URL

            log.debug('on_nav: e: %r, b: %r, url: %r, a: %r, k: %r', e, b, url, a, k)
            try:
                parsed = net.UrlQuery.parse(url)
            except Exception:
                traceback.print_exc()
            else:
                if not parsed['fragment']:
                    return
                frag_parsed = net.WebFormData.parse(parsed['fragment'])
                access_token = frag_parsed.get('access_token')
                log.debug_s("access_token from url: %r", access_token)
                if not access_token:
                    return

                log.debug_s("self.access_token: %r", self.access_token)
                if self.access_token != access_token:
                    self.api.access_token = self.access_token = access_token

                d_p = GraphPermCheck(self.api, perms=DPERMS_REQUIRED)
                return d_p.check(success=self._verify_check_succ, error=self._verify_check_fail)

        def on_close(*a, **k):
            log.debug('on_close: %r, %r', a, k)
            log.debug('on_close: dead: %r, access_token: %r', self.dead, self.access_token)
            if not self.dead:
                if self.access_token is None:
                    self.login_error(self)

        on_load = lambda *a, **k: None
        if window.webkit:
            def on_load(e, browser):
                pass
#                if e.URL == url:
#                    browser.RunScript('document.getElementById("email").value = %s;' % simplejson.dumps(self.username))

        window.set_callbacks(on_nav, on_load, on_close)
        window.clear_cookies()
        window.LoadURL(url)
