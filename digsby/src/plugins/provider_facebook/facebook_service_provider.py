import oauth.oauth as oauth

import services.service_provider as SP
import util.callbacks as callbacks
from util.primitives.structures import oset
from peak.util import addons
import threading
from . import facebookapp
from facebook import facebookapi
from facebook import fbconnectlogin
from facebook import oauth2login
from facebook import graphapi

import logging
log = logging.getLogger('facebook_sp')

class FacebookServiceProvider(SP.UsernameServiceProvider):
    password = None
    digsby_access_token = None
    uid                = None

    def update_info(self, info):
        super(FacebookServiceProvider, self).update_info(info)
        self.informed_ach = info.get('informed_ach', False)
        if 'filters' in info:
            self.filters = info.get('filters')

    def update_components(self, info):
        info = dict(info)
        info.pop('password')
        super(FacebookServiceProvider, self).update_components(info)

    def add_account_im(self, acct):
        acct_options = acct.get_options()
        if acct.enabled or not self.digsby_access_token:
            self.digsby_access_token = getattr(acct, 'access_token', None)
        if acct.enabled or not self.uid:
            uid = acct_options.pop('uid', None)
            if uid is not None:
                self.uid = uid

    def add_account_social(self, acct):
        acct_options = acct.get_options()
        self.informed_ach = acct_options.get('informed_ach', False)
        if 'filters' in acct_options:
            self.filters = acct_options.get('filters')
        if acct.enabled or not self.digsby_access_token:
            self.digsby_access_token = getattr(acct, 'access_token', None)
        if acct.enabled or not self.uid:
            uid = acct_options.pop('uid', None)
            if uid is not None:
                self.uid = uid

    def get_options(self, type):
        opts = super(FacebookServiceProvider, self).get_options(type = type)
#        opts.update(password = self.password)
        opts['informed_ach'] = self.informed_ach
        if hasattr(self, 'filters'):
            opts['filters'] = self.filters
        return opts

    def rebuilt(self):
        log.info('rebuilt with %r', self.accounts)
        logins = [FacebookLogin(a) for a in self.accounts.values()]
        log.debug('logins: %r', logins)
        loginmanager = FacebookLoginManger(self)
        with FacebookLogin.lock:
            for login in logins:
                login.loginmanager = loginmanager
                loginmanager.logins.add(login)
        loginmanager.go()

class FacebookLoginManger(object):
    def __init__(self, provider):
        self.logins = oset()
        self.provider = provider
        self.active = False

    def go(self):
        self.digsby = graphapi.LegacyRESTAPI(uid = getattr(self.provider, 'uid', None),
                                             access_token = getattr(self.provider, 'access_token', None))
        with FacebookLogin.lock:
            if not any(login.active for login in self.logins):
                return
            self.active = True
            from gui.pref.pg_accounts import IServiceProviderGUIMetaData
            self.loginproto = oauth2login.LoginCheck(
                api = self.digsby,
                login_success=self.success,
                login_error=self.fail,
                username=self.provider.accounts.values()[0].username,
                acct=IServiceProviderGUIMetaData(self.provider),
            )
            self.loginproto.initiatiate_check(True)
        #calc which perms are needed.
        #has login been requested?
        #  if not, return
        #do we need more permissions than the last request?  -start over/start again?
        #run check/login
        #run callbacks

    def success(self, check_instance, did_login=False, *a, **k):
        with FacebookLogin.lock:
            self.provider.uid = self.digsby.uid
            self.active = False
            for login in self.logins:
                if login.loginmanager is not self:
                    continue
                if login.active:
                    login.active = False
                    login.login_success(check_instance, login.did_login or did_login, *a, **k)
                    login.did_login = False
                else:
                    login.did_login = login.did_login or did_login

    def fail(self, *a, **k):
        log.error('Failed to login: %r, %r (%r)', a, k, self.provider)
        with FacebookLogin.lock:
            self.active = False
            for login in self.logins:
                if login.loginmanager is not self:
                    continue
                if login.active:
                    login.active = False
                    login.login_error(*a, **k)

class FacebookLogin(addons.AddOn):
    lock = threading.RLock()

    def __init__(self, subject):
        self.acct = subject
        self.active = False
        self.did_login = False
        self.loginmanager = None

    def do_check(self, login_success, login_error):
        with self.lock:
            self.active = True
            self.login_success = login_success
            self.login_error = login_error
            if self.loginmanager is not None and not self.loginmanager.active:
                self.loginmanager.go()


    def __enter__(self):
        self.lock.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()


