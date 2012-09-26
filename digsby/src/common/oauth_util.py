import time
import logging
import cgi
import simplejson as json
import lxml.objectify as objectify

import oauth.oauth as oauth

import util
import util.net as net
import util.httptools as httptools
import util.Events as Events
import util.callbacks as callbacks

import common
import common.asynchttp as asynchttp
import common.asynchttp.server as httpserver

log = logging.getLogger("common.oauth_util")

class Unauthorized(Exception):
    pass

class UserCancelled(Exception):
    pass

class OAuthConsumerBase(oauth.OAuthConsumer):
    KEY = None
    SECRET = None
    def __init__(self):
        oauth.OAuthConsumer.__init__(self, self.KEY, self.SECRET)

class OAuthRequest(asynchttp.HTTPRequest):
    def __init__(self, client, url, data = None, headers = None, method = None,
                 oauth_url = False, callback_url = None, sign = True, parameters = None, **k):

        params = self.get_params(client, parameters, k.pop('use_default_params', True))
        sig_params = self.get_sig_params(params, data)

        oauth_request = self.create_oauth_request(callback_url, client, url, method, sig_params, data)

        if sign:
            self.sign_request(oauth_request, client, data)

        final_method, final_url, final_headers, final_data = self.finalize_fields(oauth_url, data, headers, method, oauth_request)

        asynchttp.HTTPRequest.__init__(self, final_url, final_data, final_headers, method = final_method)

    def get_params(self, client, parameters, use_default_params):
        if use_default_params:
            params = client.default_params.copy()
        else:
            params = {}

        if parameters is not None:
            params.update(parameters)

        if 'oauth_timestamp' not in params:
            server_time_offset = getattr(client, '_server_time_offset', None)
            if server_time_offset is not None:
                #log.info('adding oauth_timestamp to request')
                #params['oauth_timestamp'] = int(time.time() - server_time_offset)
                pass

        return params

    def get_sig_params(self, params, data):
        sig_params = params.copy()
        if data is not None and hasattr(data, 'items'):
            sig_params.update(data)

        return sig_params

    def create_oauth_request(self, callback_url, client, url, method, sig_params, data):
        if callback_url is None:
            oauth_request = oauth.OAuthRequest.from_consumer_and_token(client.consumer,
                                                                       client.token,
                                                                       http_url = url,
                                                                       http_method = method,
                                                                       parameters = sig_params,
                                                                       )
        else:
            _data = sig_params.copy()
            if data:
                _data.update(data)
            oauth_request = oauth.OAuthRequest.from_token_and_callback(client.token, callback_url, method, url, _data)

        token = oauth_request.parameters.get('oauth_token', None)
        if not token:
            oauth_request.parameters.pop('oauth_token', None)

        return oauth_request

    def sign_request(self, oauth_request, client, data):
        oauth_request.sign_request(client.signature_method, client.consumer, client.token)

        if data is not None:
            for k in data:
                oauth_request.parameters.pop(k, None)

    def finalize_fields(self, oauth_url, data, headers, method, oauth_request):
        if oauth_url: #or method == 'GET':
            assert not data, "Can't use data with oauth_url"
            assert not headers, "Can't use headers with oauth_url"
            assert method in ('GET', None), "Must use GET with oauth_url"
            url = oauth_request.to_url()
            final_headers = {}
            method = None
        else:
            url = net.UrlQuery(oauth_request.http_url, **oauth_request.get_nonoauth_parameters())
            final_headers = oauth_request.to_header(getattr(self, 'realm', ''))
            if headers is not None:
                final_headers.update(headers)

            method = oauth_request.http_method

        return method, url, final_headers, data

class OAuthAPICall(object):
    def __init__(self, client, endpoint, **kw):
        self.client = client
        self.endpoint = endpoint
        self.kw = kw

    @callbacks.callsback
    def PUT(self, data, callback = None, **kw):
        self._request('PUT', data, callback = callback, **kw)

    @callbacks.callsback
    def POST(self, data, callback = None, **kw):
        self._request('POST', data, callback = callback, **kw)

    @callbacks.callsback
    def DELETE(self, callback = None, **kw):
        self._request('DELETE', callback = callback, **kw)

    @callbacks.callsback
    def GET(self, callback = None, **kw):
        self._request('GET', callback = callback, **kw)

    def _normalize_url(self, client, **kw):
        if kw.get('OpenSocial', False):
            api_base = getattr(client, 'OS_API_BASE', client.API_BASE)
            kw['use_default_params'] = False
        else:
            api_base = client.API_BASE

        url = net.httpjoin(api_base, self.endpoint, keepquery = True)

        format = kw.pop('format', client.DEFAULT_FORMAT)
        if url.endswith('.json'):
            format = 'json'
        elif url.endswith('.xml'):
            format = 'xml'
        elif url.endswith('.atom'):
            format = 'atom'

        kw['format'] = format

        return url, format

    @callbacks.callsback
    def _request(self, method, data = None, **kw):
        kw.update(self.kw)
        client = self.client
        callback = kw.pop('callback')

        url, format = self._normalize_url(client, **kw)

        log.debug("%s %s", method, url)
        log.debug_s("\tdata = %r", data)
        log.debug_s("\t  kw = %r", kw)

        if kw.pop('vital', True):
            error_handler = self.unauthorized_handler(url, method, data, callback, **kw)
        else:
            error_handler = callback.error

        client.request(url,
                       success = self.success_handler(url, method, data, callback, **kw),
                       error = error_handler,
                       method = method,
                       data = data,
                       **kw)

    def unauthorized_handler(self, url, method, data, callback, **kw):
        client = self.client
        def auth_error(e):
            client.authenticate_error(e)
            callback.error(e)

        def unauthorized(e):
            log.info("unauthorized: %r", e)

            if not ((getattr(e, 'oauth_problem', None) == 'permission_denied') or
                    (getattr(e, 'oauth_problem', None) == 'signature_invalid') or
                    (getattr(e, 'code', 0) == 401 and util.try_this(lambda: e.headers['x-opensocial-error'], None) is not None) or
                    (getattr(e, 'code', 0) == 401 and util.try_this(lambda: "Invalid digital signature" in e.document.get('statusDescription', ''))) or
                    (isinstance(e, Unauthorized))
                    ):
                return callback.error(e)

            etxt = None
            if hasattr(e, 'read'):
                etxt = e.read()
            if not etxt:
                etxt = repr(e)
            log.error('Error accessing resource %r: %r', self.endpoint, etxt)

            if not client.allow_authenticate():
                return

            client.authenticate_start()

            client.fetch_request_token(
                 error = auth_error,
                 success = lambda results: (
            client.request_token_fetched(results),
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
                           **kw)))))))

        return unauthorized

    def success_handler(self, url, method, data, callback, **kw):
        def success(resp):
            log.info("success handler for %r : %r", self.endpoint, getattr(resp, 'code', None))
            if (resp.code // 100) == 2:
                try:
                    callback.success(resp.document)
                except Exception as e:
                    import traceback; traceback.print_exc()
                    callback.error(e)
            else:
                if resp.code == 401:
                    return self.unauthorized_handler(url, method, data, callback, **kw)(resp)
                raise Exception(resp)

        return success

def load_document(resp, expected):
    data = resp.content

    #log.info_s('Loading document: %r', data)
    if not data:
        resp.document = None
        return

    ctype = resp.headers.get('Content-Type', 'application/%s; charset=utf-8' % expected)
    ctype, params = cgi.parse_header(ctype)

    cenc = resp.headers.get('Content-Encoding', 'identity')

    if cenc != 'identity':
        try:
            # this will probably only work with gzip...
            data = data.decode(cenc)
        except Exception, e:
            log.error('Error decoding data with Content-Encoding=%r. Error = %r, data[:500] = %r', cenc, e, data[:500])

    charset = params.get('charset', 'utf-8')

    if ctype != expected:
        log.warning('was expecting content-type=%r, got content-type=%r', expected, ctype)

    if hasattr(data, 'read'):
        data = data.read()

    if ctype in ('text/xml', 'application/xml'):
        document = objectify.fromstring(data)
    elif ctype == 'application/json':
        document = json.loads(data, object_hook = util.Storage)
    elif ctype == 'application/x-www-form-urlencoded':
        document = net.WebFormData.parse(data)
    elif ctype == 'application/None':
        log.warning("Attempting json decode for content-type = %r for data = %r.", ctype, data)
        document = json.loads(data, object_hook = util.Storage)
    else:
        log.warning('Unknown data type %r for data: %r', ctype, data)
        document = data.decode(charset)

    return document

class OAuthClientBase(oauth.OAuthClient, httptools.WebScraper, Events.EventMixin):
    DEFAULT_FORMAT = None
    API_BASE = None

    urls = {}

    events = Events.EventMixin.events | set((
        'authenticate_start',
        'authenticate_done',
        'authenticate_error',

        'requests_complete',

        'token_expired',

        'open_oauth_page',
    ))

    APICallFactory = OAuthAPICall
    ConsumerFactory = None
    RequestFactory = None

    def __init__(self, username, token, consumer = None, signature_method = None, default_params = None, time_offset = None):
        Events.EventMixin.__init__(self)
        self.pending_auth = False
        self.username = username
        self._server_time_offset = time_offset
        if default_params is None:
            default_params = {}

        if signature_method is None:
            signature_method = 'hmac-sha1'
        if consumer is None:
            consumer = self.ConsumerFactory()

        if signature_method == "hmac-sha1":
            self.signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
        else:
            raise ValueError('Don\'t know what to do with this signature method: %r', signature_method)

        if token:
            try:
                token = oauth.OAuthToken.from_string(token)
            except oauth.OAuthError:
                import traceback; traceback.print_exc()
                token = None
        else:
            token = None

        self.default_params = default_params
        oauth.OAuthClient.__init__(self, consumer, token)
        httptools.WebScraper.__init__(self)

    def get_time_offset(self):
        return self._server_time_offset

    def done_waiting(self):
        log.info('done waiting')
        self.event('requests_complete')

    def allow_authenticate(self):
        return not self.pending_auth

    @Events.event
    def authenticate_start(self):
        log.info("authenticate start")
        self.pending_auth = True
        self.token = oauth.OAuthToken('', '')

    @Events.event
    def authenticate_error(self, error):
        log.info("authenticate error")
        self.pending_auth = False
        return error

    @Events.event
    def authenticate_done(self):
        log.info("authenticate done")
        self.pending_auth = False

    @callbacks.callsback
    def fetch_request_token(self, callback = None):
        self.request('request_token',
                     callback = callback)

    def request_token_fetched(self, results):
        self.token = results.get('token')

    def preprocess_resp_default(self, name, resp, **req_options):
        code = resp.code

        server_time = net.http_date_to_timestamp(resp.headers.get('Date', None))
        if server_time is not None:
            time_diff = int(time.time() - server_time)
            self._server_time_offset = time_diff
            log.info("Got server time offset: %r", time_diff)

        if self._server_time_offset is None:
            log.error("Server does not report Date header.")

        log.info('response for %r: code = %r, headers = %r', name, code, str(resp.headers))
        log.debug_s('\tcontent: %s', repr(resp.content)[:5000])
        document = load_document(resp, expected = req_options.get('format'))

        if code not in (200, 201, 204, 401):
            # check for oauth error, parse it out and raise as an exception
            raise Exception(document)

        resp.document = document
        return resp

    def preprocess_resp_request_token(self, name, resp, **req_options):
        return resp

    def handle_success_default(self, name, resp, **req_options):
        pass

    def handle_success_request_token(self, name, resp, **req_options):
        content = resp.content
        content = content.replace(', ', '&')
        return dict(token = oauth.OAuthToken.from_string(content))

    @callbacks.callsback
    def fetch_access_token(self, callback = None):
        self.request('access_token', callback = callback)

    def access_token_fetched(self, results):
        log.info("Access token acquired")
        self.token = results.get('token')
        self.authenticate_done()

    def handle_success_access_token(self, name, resp, **req_options):
        content = resp.content
        content = content.replace(', ', '&')
        return dict(token = oauth.OAuthToken.from_string(content))

    @callbacks.callsback
    def authorize_token(self, callback = None):
        callback_url_function = lambda cb_url: self.RequestFactory(
                                                   self.urls['authorization'],
                                                   callback_url = cb_url,
                                                   oauth_url = True,
                                                   sign = False,
                                                   #params = {'myspaceid.permissions' : '|'.join(self.required_permissions)}
                                                   ).get_full_url()

        self.event("open_oauth_page", callback_url_function, callback)

    def token_authorized(self, results):
        self.token.key = results.get('key')

    def build_request_default(self, name, **req_options):
        link = self.urls.get(name, name)

        if callable(link):
            link = link()

        link = link.format(**req_options)

        req = self.RequestFactory(link, **req_options)
        return req

    def call(self, endpoint, **kw):
        return self.APICallFactory(self, endpoint, **kw)

class OAuthProtocolBase(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'on_connect',

        'authenticate_pre',
        'authenticate_post',
        'authenticate_error',

        'update_pre',
        'update_post',
        'update_error',

        'need_cache',
        'open_oauth_page',
        'openurl',

        'on_feedinvalidated',
        'need_permissions',
    ))

    def __init__(self, username, token):
        Events.EventMixin.__init__(self)
        self._dirty = True
        self._authenticating = False

        self.username = username
        self.token = token

        self.api = None

    def connect(self):
        self.init_api()
        self.event('on_connect')

    def init_api(self):
        sto = None
        if self.api is not None:
            sto = getattr(self.api, '_server_time_offset', None)
            self.uninit_api()

        self._create_api()
        self.api._server_time_offset = sto
        self.api.bind_event('requests_complete', self.check_update_complete)
        self.api.bind_event('authenticate_start', self.authenticate_pre)
        self.api.bind_event('authenticate_done',  self.authenticate_post)
        self.api.bind_event('authenticate_error', self.authenticate_error)
        self.api.bind_event('open_oauth_page',   self.open_oauth_page)

    def uninit_api(self):
        api, self.api = self.api, None
        api.unbind('requests_complete', self.check_update_complete)
        api.unbind('authenticate_start', self.authenticate_pre)
        api.unbind('authenticate_done',  self.authenticate_post)
        api.unbind('authenticate_error', self.authenticate_error)
        api.unbind('open_oauth_page',   self.open_oauth_page)

    @Events.event
    def open_oauth_page(self, callback_url_function, callback):
        return callback_url_function, callback

    def get_oauth_token(self):
        if self.token is None:
            return None
        return self.token.to_string()

    @Events.event
    def authenticate_pre(self):
        self._authenticating = True

    @Events.event
    def authenticate_error(self, e = None):
        self._authenticating = False

    @Events.event
    def authenticate_post(self):
        self._authenticating = False
        self.token = self.api.token
        log.info("Getting oauth token from API for %r: %r", self, self.token)

    def clear_oauth_token(self):
        self.api.token = self.token = None

    def set_dirty(self):
        self._dirty = True

    @Events.event
    def update_post(self):
        self.apply_pending()
        if not self._dirty:
            log.info('\tno changes.')
        self.pending.clear()

    @Events.event
    def update_error(self, e):
        if getattr(e, 'code', None) == 404:
            return Events.Veto
        log.info('Error updating: %r', e)
        return e

    def _feed_invalidated(self):
        self._dirty = True
        self.event('on_feedinvalidated')

class OAuthAccountBase(Events.EventMixin):

    def __init__(self, **k):
        Events.EventMixin.__init__(self)
        self.oauth_token = k.get('oauth_token', None)
        self._auth = None
        self._has_updated = False
        self._forcing_login = False


    def get_options(self):
        try:
            get_opts = super(OAuthAccountBase, self).get_options
        except AttributeError:
            opts = {}
        else:
            opts = get_opts()

        opts['oauth_token'] = self.oauth_token
        return opts

    def _get_auth_class(self, prefkey):
        auth_class_name = common.pref(prefkey, default = None)
        if auth_class_name == 'internal-openid':
            AuthClass = InternalBrowserAuthenticatorOpenID
        elif auth_class_name == 'internal':
            AuthClass = InternalBrowserAuthenticator
        elif auth_class_name == 'browser':
            AuthClass = UserBrowserAuthenticator
        elif auth_class_name == 'auto':
            AuthClass = AutoAuthenticator
        else:
            AuthClass = self.AuthClass

        return AuthClass

    def bind_events(self):
        log.info("bind_events: %r / %r", self, self.connection)

        self.connection.bind('on_connect', self._on_protocol_connect)

        self.connection.bind('authenticate_pre', self._authenticate_pre)
        self.connection.bind('authenticate_post', self._authenticate_post)
        self.connection.bind('authenticate_error', self._authenticate_error)

        self.connection.bind('update_pre', self._update_pre)
        self.connection.bind('update_post', self._update_post)
        self.connection.bind('update_error', self._update_error)

        self.connection.bind('need_cache', self._cache_data)
        self.connection.bind('open_oauth_page', self._on_oauth_url)

        self.connection.bind('openurl', self.openurl)

        self.connection.bind('on_feedinvalidated', self.on_feed_invalidated)
        self.connection.bind('need_permissions', self.initiate_login)

        return self.connection

    def unbind_events(self):
        conn = self.connection
        log.info("unbind_events: %r / %r", self, conn)

        if conn is None:
            return

        conn.unbind('on_connect', self._on_protocol_connect)

        conn.unbind('authenticate_pre', self._authenticate_pre)
        conn.unbind('authenticate_post', self._authenticate_post)
        conn.unbind('authenticate_error', self._authenticate_error)

        conn.unbind('update_pre', self._update_pre)
        conn.unbind('update_post', self._update_post)
        conn.unbind('update_error', self._update_error)

        conn.unbind('need_cache', self._cache_data)
        conn.unbind('open_oauth_page', self._on_oauth_url)

        conn.unbind('openurl', self.openurl)

        conn.unbind('on_feedinvalidated', self.on_feed_invalidated)
        conn.unbind('need_permissions', self.initiate_login)

        return conn

    def clear_oauth_token(self):
        if self.connection is not None:
            self.connection.clear_oauth_token()
        self.save_oauth_token()

    def save_oauth_token(self):
        self._on_auth_done()
        if self.connection is not None:
            oauth_token = self.connection.get_oauth_token()
            self.update_info(oauth_token = oauth_token)

    def _authenticate_pre(self):
        if not self._forcing_login:
            self.change_state(self.Statuses.AUTHENTICATING)

    def _authenticate_post(self):
        self.save_oauth_token()
        if not self._forcing_login:
            self.change_state(self.Statuses.CONNECTING)

    def _authenticate_error(self, e):
        log.info('authentication error: %r', e)
        self._autherror = e
        import oauth.oauth as oauth
        if isinstance(e, (oauth.OAuthError, asynchttp.httptypes.HTTPResponse)):
            if isinstance(e, oauth.OAuthError):
                data = getattr(e, 'oauth_data', '')
                details = net.WebFormData.parse(data)
            else:
                data = e.read()
                if data:
                    details = dict(x.strip().split('=', 1) for x in data.split(','))
                else:
                    details = {}

            return self._handle_oauth_error(details)

        self.clear_oauth_token()
        self.Disconnect(self.Reasons.BAD_PASSWORD)

    def _update_pre(self):
        if self._has_updated or self._forcing_login:
            st = self.Statuses.CHECKING
        else:
            st = self.Statuses.CONNECTING

        self.change_state(st)

    def _update_post(self):
        # the first time that MyspaceProtocol fire on_feedinvalidated, its event handlers are not bound yet.
        if self.state != self.Statuses.ONLINE:
            self.on_feed_invalidated()

        self.change_state(self.Statuses.ONLINE)
        self._has_updated = True
        self._forcing_login = False
        self._dirty = self.connection._dirty

    def _update_error(self, e):
        log.debug("%r got update error: %r", self, e)
        if hasattr(e, 'read'):
            log.debug_s('\tbody: %r', e.read())

        if self.state == self.Statuses.OFFLINE:
            return

        if self._has_updated:
            rsn = self.Reasons.CONN_LOST
        else:
            rsn = self.Reasons.CONN_FAIL

        self.Disconnect(rsn)

    def _on_oauth_url(self, callback_url_function, callback):
        if self._auth is None:
            self._auth = self.get_authenticator(callback_url_function)
            self._auth.bind('on_done', self._on_auth_done)
        else:
            self._auth.url_hook = callback_url_function

        self._auth.authenticate(callback = callback)

    def _on_auth_done(self):
        auth, self._auth = self._auth, None
        if auth is not None:
            auth.unbind('on_done', self._on_auth_done)
            auth.done()
        self._auth = None

    def openurl(self, url):
        import wx
        wx.CallAfter(wx.GetApp().OpenUrl, url)

    def initiate_login(self, *a, **k):
        self._forcing_login = True
        self._has_updated = False
        self.clear_oauth_token()
        self.update_now()

    def _update(self):
        if not getattr(self, 'should_update', lambda: True)():
            return

        log.info("calling connection.update")
        util.threaded(self.connection.update)()

class OAuthCallbackHandler(object):
    def __init__(self, client, callback):
        self.oauth_client = client
        self.callback = callback

    def init_handler(self, *a):
        return self

    def handle(self, http_client, request):
        http_client.push('HTTP/1.1 200 OK\r\n'
                         'Connection: close\r\n'
                         'Content-Type: text/html\r\n'
                         '\r\n'
                         '<html><head></head>'
                          '<body style="text-align:center;">'
                           'You may now close this window'
                          '</body>'
                         '</html>'
                         )
        http_client.close_when_done()
        httpserver.shutdown()

        callback, self.callback = self.callback, None
        callback(request)
        import sys
        sys.stderr.flush()


def show_browser(url):
    import webbrowser
    webbrowser.open(url)
    print('opened in browser: %s' % url)

class OAuthenticatorBase(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'on_done',
    ))
    def __init__(self, username, url_hook, path_to_serve, window_title, watch_url, frame_icon_skinkey):
        self._watch_url = watch_url
        self.serve_path = path_to_serve
        self.window_title = window_title
        self.username = username
        self.url_hook = url_hook
        self.frame_icon_skinkey = frame_icon_skinkey
        Events.EventMixin.__init__(self)

    @callbacks.callsback
    def authenticate(self, callback = None):
        return NotImplemented

    def done(self):
        try:
            self.stop_serving()
        except Exception:
            pass
        self.event('on_done')

    @callbacks.callsback
    def serve(self, callback = None):
        # Start 1-shot localhost HTTP server, bind to something like
        # http://localhost/oauth/myspace/{username}
        # when it gets hit, save the new token (in oauth_token variable in the url)
        # (also check for oauth_problem)
        # call callback.success or callback.error appropriately
        def on_oauth_callback(request):
            httpserver.stop_serving(path, host, port)
            # parse oauth URL query string
            data = net.UrlQuery.parse(request.get_full_url())
            query = data.get('query')
            oauth_problem = query.get('oauth_problem')
            if oauth_problem:
                callback.error(Exception(oauth_problem))
            else:
                callback.success(query.get('oauth_token'))

        path = self.serve_path
        host, port = httpserver.serve(path, OAuthCallbackHandler(self, on_oauth_callback).init_handler, host = 'localhost', port = 0)
        callback_url = 'http://localhost:{port}{path}'.format(path = path, port = port)

        self._path = path
        self._host = host
        self._port = port

        url = self.url_hook(callback_url)

        log.info('oauth url: %r', url)
        return url

    def stop_serving(self):
        path, host, port = getattr(self, '_path', None), getattr(self, '_host', None), getattr(self, '_port', None)

        if None not in (path, host, port):
            self._path = self._host = self._port = None
            httpserver.stop_serving(path, host, port)

class UserBrowserAuthenticator(OAuthenticatorBase):
    @callbacks.callsback
    def authenticate(self, callback = None):
        url = self.serve(callback = callback)
        return show_browser(url)

class AutoAuthenticator(OAuthenticatorBase):
    @callbacks.callsback
    def authenticate(self, callback = None):
        url = self.serve(callback = callback)
        # create browser, bind events
        # nav to url, submit form with self.account credentials
        self._callback = callback
        import wx
        def _gui_stuff():

            frame = wx.Frame(None, size = (840, 660), title = self.window_title, name = self.window_title)
            from gui.browser.webkit.webkitwindow import WebKitWindow as Browser
            frame.CenterOnScreen()
            b = Browser(frame)

            frame.Bind(wx.EVT_CLOSE, self.on_close)
            b.LoadURL(url)
            frame.Show()

        wx.CallAfter(_gui_stuff)

    def on_close(self, e):
        self._do_callback('error', Exception("user closed auth window"))
        e.Skip()

    def _do_callback(self, which, *a):
        cb, self._callback = self._callback, None
        if cb is not None:
            f = getattr(cb, which, None)
            if f is not None:
                f(*a)

class InternalBrowserAuthenticator(OAuthenticatorBase):
    frame_shown = False
    frame_size = (630, 520)
    @callbacks.callsback
    def _fallback_authenticate(self, callback = None):
        return UserBrowserAuthenticator(self.username, self.url_hook).authenticate(callback = callback)

    @callbacks.callsback
    def authenticate(self, callback = None):
        log.info('login_gui start')
        if self._watch_url is None:
            url = self.serve(callback = callback)
            args = (url,)
        else:
            url = self.url_hook(self._watch_url)
            args = (url, callback)
        import wx
        wx.CallAfter(lambda: self._do_gui(*args))

    def _do_gui(self, url, callback = None):
        import wx, wx.webview
        import gui.skin as skin
        import gui.browser as B

        log.info('login_gui before frame')
        if getattr(self, 'frame', None) is not None:
            log.info("already have a web frame open!")
            return

        self.frame = frame = wx.Frame(None, size = self.frame_size, title = self.window_title, name = self.window_title)

        icon = skin.get(self.frame_icon_skinkey)
        if icon is not None:
            frame.SetIcon(wx.IconFromBitmap(icon))
        log.info('login_gui before center')
        frame.CentreOnScreen()
        log.info('login_gui before frame')

        try:
            b = B.Browser(frame, url = url, external_links=False)
        except Exception:
            # some people are getting
            # COMError: (-2147024809, 'The parameter is incorrect.', (None, None, None, 0, None))
            # try a fallback with just the browser
            from traceback import print_exc
            print_exc()

            self.frame.Destroy()
            self.frame = None

            # don't use this
            ## Fallback to a real browser.

            if callback is not None:
                callback.error("Unable to authenticate")
            return

        self.success = False
        log.info('login_gui after frame')

        def on_close(e):
            e.Skip()
            if self.frame_shown and not self.success:
                # Broswer window closed before successful login.
                if callback is not None:
                    callback.error(UserCancelled("User cancelled."))
            self.frame = None

        log.info('login_gui before bind')
        frame.Bind(wx.EVT_CLOSE, on_close)

        b.OnDoc += lambda navurl: self.before_load(b, navurl, callback)
        b.OnTitleChanged += lambda e: self.on_title_changed(b, e, callback)
        log.info('login_gui end')
        wx.CallLater(2000, lambda: setattr(self, 'frame_shown', self.frame.Show() if not getattr(self.frame, 'Shown', True) else False))

    def on_title_changed(self, browser, event, callback):
        pass

    def before_load(self, browser, navurl, callback):
        import wx
        log.info('before_load: %r', navurl)

        if self._watch_url and navurl.startswith(self._watch_url):

            parsed = net.UrlQuery.parse(navurl)
            log.info('parsed url: %r', parsed)
            query = parsed.get('query')

            oauth_problem = query.get('oauth_problem')

            if oauth_problem:
                if callback is not None:
                    callback.error(Exception(oauth_problem))
            else:
                self.success = True
                if callback is not None:
                    log.info("success calling %r with %r", callback.success, query)
                    callback.success(query)

            wx.CallAfter(self.frame.Close)
            self.frame = None

class InternalBrowserAuthenticatorOpenID(InternalBrowserAuthenticator):
    def before_load(self, navurl, callback):
        import wx
        log.info('before_load: %r', navurl)

        if navurl.startswith(self._watch_url):
            parsed = net.UrlQuery.parse(navurl)

            log.info('parsed url: %r', parsed)
            query = parsed.get('query')

            mode = query.get('openid.mode', None)
            log.info('\topenid mode is: %r', mode)

            if mode == 'error':
                callback.error(Exception(query.get('openid.error')))

            else:
                self.success = True
                callback.success(dict(key = query.get('openid.oauth.request_token')))

            wx.CallAfter(self.frame.Close)
            self.frame = None
