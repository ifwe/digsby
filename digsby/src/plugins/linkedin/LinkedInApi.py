'''
OAuth implementation for LinkedIn.

Also automatically uses content-type of XML is not otherwise specified, and allows a 'fields' keyword argument when
constructing requests, which are appended to the requested URL as a comma-separated list in parentheses, following a
colon (':'). e.g.: '%s:(field1,field2,fieldN)'
'''
import logging

import util.net as net
import util.callbacks as callbacks
import common.oauth_util as oauth_util

log = logging.getLogger('linkedin.new.api')

class LinkedInOAuthRequest(oauth_util.OAuthRequest):
    #realm = "https://api.linkedin.com"
    def finalize_fields(self, oauth_url, data, headers, method, oauth_request):
        _method, _url, _headers, _data = oauth_util.OAuthRequest.finalize_fields(self, oauth_url, data, headers, method, oauth_request)

        if data:
            _headers['Content-Type'] = 'text/xml'

        return _method, _url, _headers, _data

class LinkedInOAuthConsumer(oauth_util.OAuthConsumerBase):
    KEY = ''
    SECRET = ''

class LinkedInOauthAPICall(oauth_util.OAuthAPICall):
    @callbacks.callsback
    def _request(self, method, data = None, **kw):
        kw.update(self.kw)
        client = self.client
        url, format = self._normalize_url(client, **kw)
        if self.client.token is None:
            self.unauthorized_handler(url, method, data, **kw)(oauth_util.Unauthorized("No token stored"))
            return

        kw['format'] = format

        return oauth_util.OAuthAPICall._request(self, method, data = data, **kw)

    def _normalize_url(self, client, **kw):
        url, format = oauth_util.OAuthAPICall._normalize_url(self, client, **kw)

        urlparsed = net.UrlQuery.parse(url)

        if ':' in urlparsed['path'] or kw.get("fields", None) is None:
            return url, format

        urlparsed['path'] = '%s:(%s)' % (urlparsed['path'], ','.join(field.encode('url') for field in kw.get('fields', ())))

        return net.UrlQuery.unparse(**urlparsed), format

class LinkedInOAuthClient(oauth_util.OAuthClientBase):
    DEFAULT_FORMAT = ''
    API_BASE = 'http://api.linkedin.com/v1/'

    urls = {
            'request_token' : 'https://api.linkedin.com/uas/oauth/requestToken',
            'access_token'  : 'https://api.linkedin.com/uas/oauth/accessToken',
            'authorization' : 'https://api.linkedin.com/uas/oauth/authorize',
            }

    events = oauth_util.OAuthClientBase.events | set((
    ))

    APICallFactory  = LinkedInOauthAPICall
    ConsumerFactory = LinkedInOAuthConsumer

    def RequestFactory(self, *a, **k):
        return LinkedInOAuthRequest(self, *a, **k)

    def build_request_request_token(self, *a, **k):
        # Note: we're using the /myspace URL since their behavior is exactly the same.
        req = self.build_request_default(method = 'POST', parameters = {'oauth_callback' : "http://www.digsby.com/myspace"}, *a, **k)
        return req

    def build_request_access_token(self, *a, **k):
        req = self.build_request_default(method = 'POST', parameters = {'oauth_token' : self.token.key, 'oauth_verifier' : self.verifier}, *a, **k)
        return req

    def token_authorized(self, results):
        log.info("Got authorized token results: %r", results)
        self.token.key = results.get('oauth_token')
        self.verifier = results.get('oauth_verifier')
