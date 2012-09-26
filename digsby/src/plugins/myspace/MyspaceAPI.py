import cgi
import simplejson as json
import lxml.objectify as objectify
import logging

import feedparser

import oauth.oauth as oauth
import util
import util.net as net
import util.Events as Events
import util.httptools as httptools
import util.callbacks as callbacks
import common.asynchttp as asynchttp
import common.oauth_util as oauth_util

log = logging.getLogger('myspace.new.api')

REAUTHORIZE_ERROR_MESSAGES = ("Application does not have permission to view person's basic info and details.",
                              'Application does not have permission to update resources.',
                              'Application does not have permission to update statusmood and comments.',
                              )

class MyspaceOAuthConsumer(oauth_util.OAuthConsumerBase):
    KEY = ''
    SECRET = ''

class MyspaceOAuthRequest(oauth_util.OAuthRequest):
    pass

class MyspaceOAuthClient(oauth_util.OAuthClientBase):
    DEFAULT_FORMAT = 'json'
    API_BASE = 'http://api.myspace.com/v1/'
    OS_API_BASE = 'http://api.myspace.com/1.0/'
    OPENID = False


    required_permissions = [
        ## Access to media
        #'AddPhotosAlbums',
        #'AccessToPrivateVideosPhotos',

        ## Profile access
        'ViewContactInfo',
        #'ViewFullProfileInfo',

        ## Stream acccess
        'AllowActivitiesAutoPublish',
        'SendUpdatesToFriends',
        'ShowUpdatesFromFriends',

        ## notificiations
        'AllowReceivingNotifications',
        #'AllowSendingNotifications',
        'UpdateMoodStatus',
        #'AccessToReadFriendRequests',
        #'AccessToUpdateFriendRequests',
    ]

    urls = {
            'request_token' : 'http://api.myspace.com/request_token',
            'access_token'  : 'http://api.myspace.com/access_token',
            'authorization' : 'http://api.myspace.com/authorize',
            }

    events = oauth_util.OAuthClientBase.events | set((
    ))

    ConsumerFactory = MyspaceOAuthConsumer
    def RequestFactory(self, *a, **k):
        return MyspaceOAuthRequest(self, *a, **k)

    def build_request_access_token(self, *a, **k):
        req = self.build_request_default(method = 'GET', parameters = {'oauth_token' : self.token.key, 'oauth_verifier' : self.verifier}, *a, **k)
        return req

    def token_authorized(self, results):
        log.info("Got authorized token results: %r", results)
        self.token.key = results.get('oauth_token').decode('url')
        self.verifier = results.get('oauth_verifier')

    @callbacks.callsback
    def authorize_token(self, callback = None):

        params = util.odict((
                             ('myspaceid.consumer_key',   self.consumer.key),
                             ('myspaceid.target_domain',  'http://www.digsby.com/myspace/'),
                             ('myspaceid.permissions',    '|'.join(self.required_permissions).lower())
                             ))

        def callback_url_function(cb_url):
            url = self.RequestFactory(
                                      self.urls['authorization'],
                                      callback_url = cb_url,
                                      oauth_url = True,
                                      sign = False,
                                      parameters = params,
                                      ).get_full_url()
            log.info("Callback URL function returning %r", url)
            return url

        self.event("open_oauth_page", callback_url_function, callback)


class MyspaceOpenSocialRequest(MyspaceOAuthRequest):
    def get_sig_params(self, params, data):
        sig_params = params.copy()
        return sig_params

    def finalize_fields(self, oauth_url, data, headers, method, oauth_request):
        _method, _url, _headers, _data = MyspaceOAuthRequest.finalize_fields(self, oauth_url, data, headers, method, oauth_request)

        if data:
            _headers['Content-Type'] = 'application/json'
            jsondata = json.dumps(_data, separators = (',',':'), sort_keys = False, use_speedups = False)
        else:
            jsondata = None

        return _method, _url, _headers, jsondata

class MyspaceOpenSocialClient(MyspaceOAuthClient):
    # the server uses json for its default format (see MyspaceOpenSocialRequest), but this format parameter is
    # supplied to the server in a different way than with the basic OAUTH client. setting it to empty string
    # here makes everything work nicely.
    DEFAULT_FORMAT = ''
    API_BASE = 'http://api.myspace.com/1.0/'
    #OS_API_BASE = 'http://opensocial.myspace.com/1.0/'
    OPENID = False

    if OPENID:
        urls = {
                'request_token' : 'http://api.myspace.com/openid',
                'access_token'  : 'http://api.myspace.com/access_token',
                'authorization' : 'http://api.myspace.com/authorize',
                }

    def RequestFactory(self, *a, **k):
        openid = self.OPENID and k.pop('openid_request', False)
        if openid:
            return asynchttp.Request(*a, **k)
        else:
            return MyspaceOpenSocialRequest(self, *a, **k)

    @callbacks.callsback
    def authorize_token(self, callback = None):

        if self.OPENID:
            params = util.odict((
                                 ('myspaceid.consumer_key',   self.consumer.key),
                                 ('openid.oauth.consumer',    self.consumer.key),
                                 ('openid.mode',              'checkid_setup'),
                                 ('openid.realm',             'http://www.digsby.com/'),
                                 ('myspaceid.target_domain',  'http://www.digsby.com/myspace/'),
                                 ('openid.return_to',         'http://www.digsby.com/myspace/'),
                                 ('openid.ns',                'http://specs.openid.net/auth/2.0'),
                                 ('openid.ns.oauth',          'http://specs.openid.net/extensions/oauth/1.0'),
                                 ('openid.claimed_id',        'http://specs.openid.net/auth/2.0/identifier_select'),
                                 ('openid.identity',          'http://specs.openid.net/auth/2.0/identifier_select'),
                                 ('myspaceid.permissions',    '|'.join(self.required_permissions))
                               ))
        else:
            params = util.odict((
                                 ('myspaceid.consumer_key',   self.consumer.key),
                                 ('myspaceid.target_domain',  'http://www.digsby.com/myspace/'),
                                 ('myspaceid.permissions',    '|'.join(self.required_permissions))
                               ))

        callback_url_function = lambda cb_url: self.RequestFactory(
                                                   net.UrlQuery(self.urls['request_token'], params),
                                                   openid_req = self.OPENID,
                                                   ).get_full_url()

        self.event("open_oauth_page", callback_url_function, callback)

    def call(self, endpoint, **kw):
        return MyspaceOpenSocialCall(self, endpoint, **kw)

class MyspaceOpenSocialCall(oauth_util.OAuthAPICall):
    def unauthorized_handler(self, url, method, data, callback, **kw):
        client = self.client

        def auth_error(e):
            client.authenticate_error(e)
            callback.error(e)

        def unauthorized(e):
            log.error('Error accessing resource %r', self.endpoint)

            code = getattr(e, 'code', 0)
            emsg = getattr(e, 'message', None)

            if code or (emsg == 'conn_fail'):
                is_error = True
                early_return = True
                headers = getattr(e, 'headers', {})
                opensocial_err = headers.get('x-opensocial-error')
                if emsg == "conn_fail":
                    log.error("\tconnection error occurred")

                elif code == 404:
                    log.error("\tResource %r does not exist.", self.endpoint)

                elif code == 401:
                    log.error('\tPermissions error accessing resource %r: %r', self.endpoint, e)
                    early_return = not (opensocial_err is None or opensocial_err in REAUTHORIZE_ERROR_MESSAGES)

                    if hasattr(e, 'document') and isinstance(e.document, basestring):
                        try:
                            json_error_info = json.loads(e.document)
                        except Exception:
                            pass
                        else:
                            if 'timestamp' in json_error_info.get('statusDescription', '').lower():
                                log.error("\tGot timestamp message from error response: %r", json_error_info)
                                early_return = True
                                is_error = True
                                e = oauth.OAuthError(oauth_data = {'oauth_problem' : 'timestamp_refused'})

                elif code == 409:
                    is_error = False
                    log.error('\tConflict while performing action: %r', self.endpoint)

                else:
                    log.error('\tError is being handled as non-fatal. code = %r', code)

                if opensocial_err is not None:
                    log.error("\tadditionally, an opensocial error was encountered: %r", opensocial_err)

                if early_return:
                    if is_error:
                        log.info("callback.error = %r", callback.error)
                        return callback.error(e)
                    else:
                        return callback.success(e)

            etxt = ''
            if hasattr(e, 'read'):
                etxt = e.read()
            if not etxt:
                etxt = repr(e)

            log.error("\terror text = %r", etxt)

            if not client.allow_authenticate():
                log.info('authenticate not allowed')
                return

            client.authenticate_start()

            client.authorize_token(
                  error = auth_error,
                  success = lambda results: (
            client.token_authorized(results),
            client.fetch_access_token(
                  error = auth_error,
                  success = lambda results: (
            client.access_token_fetched(results),
            client.request(url,
                           method = method, data = data,
                           error = callback.error,
                           success = lambda resp: callback.success(resp.document),
                           **kw)))))

        return unauthorized

