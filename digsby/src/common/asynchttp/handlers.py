import logging
import urlparse, urllib, urllib2

log = logging.getLogger('asynchttp.handlers')

__all__ = [
           'AsyncHTTPBasicAuthHandler',
           'AsyncHTTPDigestAuthHandler',
           'AsyncHTTPRedirectHandler',
           'AsyncProxyBasicAuthHandler',
           'AsyncProxyDigestAuthHandler',
           'AsyncProxyHandler',
           ]

redirect_codes = frozenset((301, 302, 303, 307))

class AsyncHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
    # maximum number of redirections to any single URL
    # this is needed because of the state that cookies introduce
    max_repeats = 4
    # maximum total number of redirections (regardless of URL) before
    # assuming we're in a loop
    max_redirections = 10

    def http_response(self, request, response):
        if response.code not in redirect_codes or not request.follow_redirects:
            return None

        headers = response.headers
        newurl = headers.get('location', headers.get('uri', None))

        if newurl is None:
            return None
        newurl = urlparse.urljoin(request.get_full_url(), newurl).replace(' ', '%20')
        new_request = request.copy(url = newurl,
                                   unverifiable = True)
        del new_request.headers['Host']

        if hasattr(request, 'redirect_dict'):
            visited = new_request.redirect_dict = request.redirect_dict
            if visited.get(newurl, 0) >= self.max_repeats or len(visited) >= self.max_redirections:
                # Don't redirect forever
                return None
        else:
            visited = new_request.redirect_dict = request.redirect_dict = {}

        visited[newurl] = visited.get(newurl, 0) + 1

        log.info('redirect: %r -> %r', request.get_full_url(), new_request.get_full_url())
        return 'request', new_request

class AsyncProxyHandler(urllib2.ProxyHandler):
    def http_request(self, request):
        # Luckily we only need to worry about http proxies/urls.
        try:
            proxy = self.proxies['http']
        except KeyError:
            return None

        proxy_type, user, password, hostport = urllib2._parse_proxy(proxy)

        if proxy_type != 'http':
            log.warning('Got unexpected proxy type %r in asynchttp. not modifying request', proxy_type)
            return

        if proxy_type is None:
            proxy_type = 'http'
        if user and password:
            user_pass = '%s:%s' % (urllib2.unquote(user), urllib2.unquote(password))
            creds = user_pass.encode('base64').strip()
            request.headers['Proxy-Authorization'] = 'Basic ' + creds

        hostport = urllib.unquote(hostport)
        request.set_proxy(hostport, proxy_type)
        # don't need to return anything because all pre-processors get run. yay.

class AsyncAbstractBasicAuthHandler(urllib2.AbstractBasicAuthHandler):

    def http_error_auth_reqed(self, req, resp, host, authheader):
        authheader = resp.headers.get(authheader, None)
        if authheader:
            mo = urllib2.AbstractBasicAuthHandler.rx.search(authheader)
            if mo:
                scheme, a_, realm = mo.groups()
                if scheme.lower() == 'basic':
                    return self.retry_http_basic_auth(req, resp, host, realm)

        return None


    def retry_http_basic_auth(self, req, resp, host, realm):
        user, password = self.passwd.find_user_password(realm, host)
        if password is not None:
            raw = "%s:%s" % (user, password)
            auth = 'Basic %s' % raw.encode('base64').strip()
            if req.headers.get(self.auth_header, None) == auth:
                return None

            req.add_header(self.auth_header, auth)
            return 'request', req

        return None

class AsyncHTTPBasicAuthHandler(AsyncAbstractBasicAuthHandler, urllib2.BaseHandler):

    auth_header = 'Authorization'

    def http_response_401(self, req, resp):
        url = req.get_full_url()
        return self.http_error_auth_reqed(req, resp, url, 'www-authenticate')

class AsyncProxyBasicAuthHandler(AsyncAbstractBasicAuthHandler, urllib2.BaseHandler):

    auth_header = 'Proxy-authorization'

    def http_response_407(self, req, resp):
        authority = req.get_host()
        return self.http_error_auth_reqed(req, resp, authority, 'proxy-authenticate',)

class AsyncAbstractDigestAuthHandler(urllib2.AbstractDigestAuthHandler):

    def http_error_auth_reqed(self, req, resp, host, authheader):
        authreq = req.headers.get(authheader, None)
        if self.retried > 5:
            return None
        else:
            self.retried += 1

        if authreq:
            scheme = authreq.split()[0]
            if scheme.lower() == 'digest':
                return self.retry_http_digest_auth(req, resp, host, authreq)

        return None

    def retry_http_digest_auth(self, req, resp, host, auth):
        _token, challenge = auth.split(' ', 1)
        chal = urllib2.parse_keqv_list(urllib2.parse_http_list(challenge))
        auth = self.get_authorization(req, chal)
        if auth:
            auth_val = 'Digest %s' % auth
            if req.headers.get(self.auth_header, None) == auth_val:
                return None
            req.add_unredirected_header(self.auth_header, auth_val)
            return 'request', req

        return None

class AsyncHTTPDigestAuthHandler(AsyncAbstractDigestAuthHandler, urllib2.BaseHandler):
    auth_header = 'Authorization'
    handler_order = 490  # before Basic auth

    def http_response_401(self, req, resp):
        host = urlparse.urlparse(req.get_full_url())[1]
        val = self.http_error_auth_reqed(req, resp, host, 'www-authenticate',)
        self.reset_retry_count()
        return val


class AsyncProxyDigestAuthHandler(AsyncAbstractDigestAuthHandler, urllib2.BaseHandler):

    auth_header = 'Proxy-Authorization'
    handler_order = 490  # before Basic auth

    def http_response_407(self, req, resp):
        host = req.get_host()
        val = self.http_error_auth_reqed(req, resp, host, 'proxy-authenticate',)
        self.reset_retry_count()
        return val

