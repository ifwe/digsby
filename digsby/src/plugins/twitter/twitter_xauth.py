from urllib2 import Request, urlopen
import oauth.oauth as oauth
from util import threaded, callsback
from datetime import datetime
import time

# for digsby app
CONSUMER_KEY = ''
CONSUMER_SECRET = ''

@callsback
def get_oauth_token(username, password, callback=None):
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

    @threaded
    def on_thread():
        return auth.get_xauth_access_token(username, password)

    on_thread(callback=callback)

class AuthHandler(object):

    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'twitter.com'
    OAUTH_ROOT = '/oauth/'

    def __init__(self, consumer_key, consumer_secret, callback=None, secure=False):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None
        self.secure = secure

    def _get_oauth_url(self, endpoint, secure=False):
        if self.secure or secure:
            prefix = 'https://'
        else:
            prefix = 'http://'

        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        url = self._get_oauth_url('request_token')
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, callback=self.callback
        )
        request.sign_request(self._sigmethod, self._consumer, None)
        resp = urlopen(Request(url, headers=request.to_header()))
        return oauth.OAuthToken.from_string(resp.read())

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_twitter=False):
        """Get the authorization URL to redirect the user"""

        # get the request token
        self.request_token = self._get_request_token()

        # build auth request and return as url
        if signin_with_twitter:
            url = self._get_oauth_url('authenticate')
        else:
            url = self._get_oauth_url('authorize')
        request = oauth.OAuthRequest.from_token_and_callback(
            token=self.request_token, http_url=url
        )

        return request.to_url()

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        url = self._get_oauth_url('access_token')

        # build request
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer,
            token=self.request_token, http_url=url,
            verifier=str(verifier)
        )
        request.sign_request(self._sigmethod, self._consumer, self.request_token)

        # send request
        resp = urlopen(Request(url, headers=request.to_header()))
        self.access_token = oauth.OAuthToken.from_string(resp.read())
        return self.access_token

    def get_xauth_access_token(self, username, password):
        """
        Get an access token from an username and password combination.
        In order to get this working you need to create an app at
        http://twitter.com/apps, after that send a mail to api@twitter.com
        and request activation of xAuth for it.
        """
        url = self._get_oauth_url('access_token', secure=True) # must use HTTPS
        request = oauth.OAuthRequest.from_consumer_and_token(
            oauth_consumer=self._consumer,
            http_method='POST', http_url=url,
            parameters = {
                'x_auth_mode': 'client_auth',
                'x_auth_username': to_utf8(username),
                'x_auth_password': to_utf8(password),
                'oauth_timestamp': generate_corrected_timestamp()
            }
        )
        request.sign_request(self._sigmethod, self._consumer, None)

        resp = urlopen(Request(url, data=request.to_postdata()))
        self.access_token = oauth.OAuthToken.from_string(resp.read())
        return self.access_token

    def get_username(self):
        #if self.username is None:
            #api = API(self)
            #user = api.verify_credentials()
            #if user:
                #self.username = user.screen_name
            #else:
                #raise Exception("Unable to get username, invalid oauth token!")
        return self.username

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
    import logging
    now = time.time()
    if _time_correction is not None:
        t = now + _time_correction
        logging.getLogger('twitter').warn('using corrected timestamp: %r', datetime.fromtimestamp(t).isoformat())
    else:
        t = now
        logging.getLogger('twitter').warn('using UNcorrected timestamp: %r', datetime.fromtimestamp(t).isoformat())
    return t


