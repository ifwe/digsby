'''
Basic types for requests and responses.
'''
import gzip
import urllib, urllib2
import logging
import util
import sys
import email.message as message

__all__ = ['HTTPRequest',
           'HTTPHeaders',
           'HTTPResponse',
           ]

log = logging.getLogger('asynchttp.httptypes')

_hostprog = None
def splithost(url):
    """splithost('//host[:port]/path') --> 'host[:port]', '/path'."""
    global _hostprog
    if _hostprog is None:
        import re
        _hostprog = re.compile('^/+([^/?]*)(.*)$')

    match = _hostprog.match(url)
    if match: return match.group(1, 2)
    return None, url

class HTTPRequest(urllib2.Request, util.Events.EventMixin):
    '''
    An http request.
    HTTPRequest(url, data = None, headers = {},
                origin_req_host = None, unverifiable = False,
                method = None, follow_redirects = True,
                on_redirect = None)

    url:              the url to fetch
    data:             the data to POST or PUT, if any.
    headers:          Mapping of headers to be added to the request
    origin_req_host:  Original host the request originated for.
    unverifiable:     True if the user had no option to approve the request (??)
    method:           GET, POST, PUT, DELETE. Selected automatically if not
                         provided (GET is chosen unless 'data' is not None,
                         in which case POST is used)
    follow_redirects: Determines if the redirects are attempted for this request,
                         the server responds with a redirect code.
    on_redirect:      this function is called with the request object if a redirect
                         status code is received. The function can return a Request
                         object to be used (it can be the same one it was called with)
                         or veto the redirect entirely by returning None.
    '''

    events = util.Events.EventMixin.events | set((
            'on_chunk',
            ))

    def __init__(self, url, data = None, headers = {},
                 origin_req_host = None, unverifiable = False,
                 method = None, follow_redirects = True,
                 on_redirect = None, accumulate_body = True,
                 adjust_headers = True):

        self.adjust_headers = adjust_headers
        self._original = urllib.unwrap(url)

        util.Events.EventMixin.__init__(self)
        urllib2.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)
        self.follow_redirects = follow_redirects
        self._method = method
        self.headers = HTTPHeaders(self.headers)
        self.unredirected_hdrs = HTTPHeaders(self.unredirected_hdrs)

        self.redirect_cb = on_redirect
        self.callback = None
        self.accumulate_body = accumulate_body

        self.redirected = False

    def get_type(self):
        if self.type is None:
            self.type, self._r_type = urllib2.splittype(self._original)
            if self.type is None:
                raise ValueError, "unknown url type: %s" % self._original
        return self.type

    def get_full_url(self):
        return self._original

    def get_host(self):
        if self.host is None:
            if getattr(self, '_r_type', None) is None: self.get_type()
            self.host, self._r_host = splithost(self._r_type)
            if self.host:
                self.host = urllib2.unquote(self.host)

        return self.host

    def get_selector(self):
        return self._r_host

    def set_proxy(self, host, type):
        self.host, self.type = host, type
        self._r_host = self._original

    def has_proxy(self):
        return self._r_host == self._original

    def on_redirect(self, *a, **k):
        self.redirected = True
        if self.redirect_cb is not None:
            return self.redirect_cb(*a, **k)
        else:
            return None

    @util.Events.event
    def on_chunk(self, data):
        '''
        A single chunk has been received

        event args: bytes chunk data
        '''

    def get_method(self):
        '''
        Returns the HTTP method (GET, POST, PUT, DELETE) for this request. If it not
        provided in the constructor, POST is returned if there is data associated with
        this request, otherwise GET is returned.
        '''
        if self.has_data() and self._method in (None, 'GET'):
            return 'POST'

        elif self._method in (None, 'GET'):
            return 'GET'

        else:
            return self._method

    def copy(self, url = None, data = Sentinel, headers = None, origin_req_host = None, unverifiable = False,
             method = None, follow_redirects = None, on_redirect = None, adjust_headers = None, accumulate_body = None, callback = None):
        '''
        copy this request, overriding any provided attributes.
        '''
        if url is None:
            url = self.get_full_url()
        if data is Sentinel:
            data = self.get_data()
        if origin_req_host is None:
            origin_req_host = self.origin_req_host
        if unverifiable is None:
            unverifiable = self.unverifiable
        if method is None:
            method = self._method
        if headers is None:
            headers = self.headers.copy()
        if follow_redirects is None:
            follow_redirects = self.follow_redirects
        if on_redirect is None:
            on_redirect = self.redirect_cb
        if adjust_headers is None:
            adjust_headers = self.adjust_headers
        if accumulate_body is None:
            accumulate_body = self.accumulate_body

        if callback is None:
            callback = getattr(self, 'callback', None)

        newreq = type(self)(url, data, headers, origin_req_host, unverifiable, method, follow_redirects, on_redirect, accumulate_body, adjust_headers)
        newreq.callback = callback
        return newreq


    def __repr__(self):
        if sys.DEV:
            header_string = 'headers = %r' % (str(self.headers),)
        else:
            header_string = 'headers.keys() = %r' % (self.headers.keys(),)

        return ('<%s host = %r, path = %r, method = %r, %s, data[:50] = %r, id = 0x%x>' %
                (type(self).__name__,
                 self.get_host(),
                 self.get_selector(),
                 self.get_method(),
                 header_string,
                 repr(self.data)[:50] if self.data is not None else self.data,
                 id(self)))

    def add_header(self, key, val):
        if self.adjust_headers:
            new_key = key.capitalize()
        else:
            new_key = key
        self.headers[new_key] = val

    def add_unredirected_header(self, key, val):
        if self.adjust_headers:
            new_key = key.capitalize()
        else:
            new_key = key

        self.unredirected_hdrs[new_key] = val

class HTTPResponse(object):
    '''
    HTTPResponse(status, headers, body)

    status:         tuple (version, code, reason)
    headers:        mapping
    body:           str of response content
    '''
    def __init__(self, status, headers, body, url = None):
        # status: tuple = (version, code, reason)
        # headers: dictionary (ordered?)
        # body: file-like obj (stringio)
        object.__init__(self)
        self.url = url
        version, code, reason = status
        if '1.0' in version:
            self.version = 10
        elif '1.' in version:
            self.version = 11
        elif '0.9' in version:
            self.version = 9
        else:
            raise ValueError("Don't know what version this is supposed to be: %r", version)

        if self.version < 10:
            log.warning("This is supposed to be an HTTP/1.1 response, but it's %r instead. this is untested!", version)

        if 'gzip' in headers.get('Content-Encoding', ''):
            # todo: body = io.StringIO(body.getvalue().decode('z'))
            log.debug("Response has gzip encoding. Auto-decompressing!")
            body = gzip.GzipFile(fileobj=body)
            headers['Content-Encoding'] = headers['Content-Encoding'].replace('gzip', 'identity')

        self.status = self.code = code
        self.reason = reason
        self.body = self.content = body
        self.read = body.read
        self.seek = body.seek
        self.close = body.close

        try:
            self.seek(0)
        except IOError: # not seekable... could be trouble for someone else!
            pass
        self.headers = message.Message()

        def getheaders(key):
            return self.headers.get_all(key, [])

        self.headers.getheaders = getheaders

        for key, value in headers.items():
            self.headers.add_header(key, value)
        self.getheader = self.headers.get
        self.getheaders = self.headers.items

        self.msg = None

    def info(self):
        return self.headers

    def __getitem__(self, key):
        return self.headers.__getitem__(key)

    def __setitem__(self, key, val):
        return self.headers.__setitem__(key)

    def __contains__(self, key):
        return self.headers.__contains__(key)

    def __delitem__(self, key):
        return self.headers.__delitem__(key)

    def __repr__(self):
        if sys.DEV:
            header_string = 'headers = %r' % (str(self.headers),)
        else:
            header_string = 'headers.keys() = %r' % (self.headers.keys(),)

        return ('<%s status = %r, %s, id = 0x%x>' %
                (type(self).__name__,
                 (self.status, self.reason),
                 header_string,
                 id(self)))

    def geturl(self):
        return self.url

class HTTPHeaders(object):
    '''
    Case insensitive mapping, uses an odict as a backing data structure.
    Can be serialized by calling str(HTTPHeaders()).
    '''
    def __init__(self, d = None, **kwds):
        object.__init__(self)
        if d is None:
            d = util.odict(**kwds)
        else:
            d = util.odict(d)
            d.update(kwds)
        self.dict = d
        self.orig_keys = dict((k.lower(), k) for k in self.dict)

    def __getitem__(self, key):
        return self.dict[self.orig_keys[key.lower()]]

    def get(self, key, default = None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __setitem__(self, key, value):
        self.orig_keys[key.lower()] = key
        self.dict[key] = value

    def __delitem__(self, key):
        del self.dict[self.orig_keys.pop(key.lower())]

    def __contains__(self, key):
        return key.lower() in self.orig_keys

    def setdefault(self, key, default):
        if key not in self:
            self[key] = default

        return self[key]

    def copy(self):
        new = HTTPHeaders()
        new.dict = self.dict.copy()
        new.orig_keys = self.orig_keys.copy()
        return new

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    def iteritems(self):
        return self.dict.iteritems()
    def iterkeys(self):
        return self.dict.iterkeys()
    def itervalues(self):
        return self.dict.itervalues()
    def __iter__(self):
        return self.iterkeys()

    def __str__(self):
        return '\r\n'.join('%s: %s' % i for i in self.iteritems())

    def update(self, other):
        for k,v in other.items():
            self[k] = v
