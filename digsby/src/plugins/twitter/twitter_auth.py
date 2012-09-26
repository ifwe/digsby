import time
import datetime
import logging
import lxml.html as html
import util
import util.net as net
import util.callbacks as callbacks
import oauth.oauth as oauth
import common.oauth_util as oauth_util
import rauth.service

log = logging.getLogger('twitter.auth')

CONSUMER_KEY = ''
CONSUMER_SECRET = ''

class DigsbyTwitterAuthHandler(rauth.service.OAuth1Service):
    name = 'twitter'
    consumer_key = CONSUMER_KEY
    consumer_secret = CONSUMER_SECRET
    request_token_url = 'https://api.twitter.com/oauth/request_token'
    access_token_url = 'https://api.twitter.com/oauth/access_token'
    authorize_url = 'https://api.twitter.com/oauth/authorize'

    def __init__(self):
        super(DigsbyTwitterAuthHandler, self).__init__(
            name = self.name,
            consumer_key = self.consumer_key,
            consumer_secret = self.consumer_secret,
            request_token_url = self.request_token_url,
            access_token_url = self.access_token_url,
            authorize_url = self.authorize_url,
            header_auth = True
        )
        self.callback = None

    @callbacks.callsback
    def get_oauth_access_token(self, username, password, callback = None):
        self.username = username
        self.password = password
        self.callback = callback
        self.send_user_to_oauth(success = self.process_authorize_response,
                                error = self.handle_error)

    @callbacks.callsback
    def send_user_to_oauth(self, callback = None):
        try:
            self.request_token, self.request_token_secret = self.get_request_token('GET')
            self.authorize_url = self.get_authorize_url(self.request_token)
        except Exception as e:
            log.error("Error requesting token or getting auth url: %r", e)
            import traceback; traceback.print_exc()
            return callback.error(e)

        log.info('got authorize url: %r', self.authorize_url)

        # TODO: send user to authorize_url, wait for them to hit callback URL?
        self._auth = TwitterPinAuthenticator(
            self.username,
            lambda url: url,
            '/twitter/{username}/oauth'.format(username = self.username),
            _('Twitter Login - %s') % self.username,
            self.authorize_url,
            'serviceicons.twitter'
        )

        self._auth.bind('on_done', self._on_auth_done)
        self._auth.authenticate(success = self.process_authorize_response,
                                error = callback.error)

    def _on_auth_done(self):
        auth, self._auth = self._auth, None
        if auth is not None:
            auth.unbind('on_done', self._on_auth_done)
            auth.done()
        self._auth = None

    def handle_error(self, *a):
        log.error('error during twitter auth: %r', a)
        cb, self.callback = self.callback, None
        if cb is not None:
            cb.error(*a)

    def process_authorize_response(self, verifier):
        log.info('got success during twitter auth: %r', verifier)
        self.verifier = verifier
        response = self.get_access_token(self.request_token, self.request_token_secret, http_method='GET', oauth_verifier=self.verifier)
        data = response.content
        self.access_token = data['oauth_token']
        self.access_token_secret = data['oauth_token_secret']
        cb, self.callback = self.callback, None

        if cb is not None:
            cb.success(oauth.OAuthToken(self.access_token, self.access_token_secret))

def to_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    else:
        return s

_time_correction = None

def get_time_correction():
    return _time_correction

def set_server_timestamp(server_time_now):
    assert isinstance(server_time_now, float)
    global _time_correction
    _time_correction = server_time_now - time.time()

def generate_corrected_timestamp():
    now = time.time()
    if _time_correction is not None:
        t = now + _time_correction
        log.warn('using corrected timestamp: %r', datetime.fromtimestamp(t).isoformat())
    else:
        t = now
        log.warn('using UNcorrected timestamp: %r', datetime.fromtimestamp(t).isoformat())
    return t

class TwitterPinAuthenticator(oauth_util.InternalBrowserAuthenticator):
    frame_size = (700, 675)
    close_rpc = 'digsby://digsbyjsonrpc/close'
    def do_close_frame(self):
        import wx
        wx.CallAfter(self.frame.Close)
        self.frame = None
        self.done()

    def on_title_changed(self, browser, event, callback):
        if event.Title.startswith(self.close_rpc):
            if not self.success and callback:
                callback.error(oauth_util.UserCancelled("User cancelled."))
            self.do_close_frame()
            return

    def before_load(self, browser, navurl, callback):
        import wx

        if wx.IsDestroyed(browser):
            if callback:
                callback.error()
            return

        close_rpc = 'digsby://digsbyjsonrpc/close'
        if navurl.startswith(close_rpc) or navurl.startswith('http://www.digsby.com/'):
            if not self.success and callback:
                callback.error(oauth_util.UserCancelled("User cancelled."))
            self.do_close_frame()
            return

        log.info('before_load: %r', navurl)
        doc = html.fromstring(browser.HTML)
        verifier = getattr(doc.find('.//*[@id="oauth_pin"]//code'), 'text', None)
        log.info("success calling %r with %r", getattr(callback, 'success', None), verifier)

        if verifier:
            self.success = True
            if callback:
                callback.success(verifier)
            self.do_close_frame()
        else:
            browser.RunScript('''
            using('imports/jquery', function($) {
                $('#username_or_email').val('%(username)s');
                $('#password').focus();
                var close_window_rpc = function() { document.title = '%(close_rpc)s'; };
                $('a.deny').live('click', close_window_rpc);
                $('input#deny').live('click', close_window_rpc);
            });''' % dict(username = str(self.username), close_rpc = close_rpc))

@callbacks.callsback
def get_oauth_token(username, password, callback = None):
    DigsbyTwitterAuthHandler().get_oauth_access_token(username, password, callback = callback)
