import AsyncoreThread
import re, sys, traceback, types
import socket, socks, urlparse, urllib2, httplib, util.httplib2 as httplib2
import email
import logging
import ssl

from StringIO import StringIO as stringio

import util
import util.Events as Events
from util.net import producer_cb

from common.AsyncSocket import AsyncSocket, _ok_errors

import handlers
import httptypes

__all__ = [
           'AsyncHttpConnection',
           'AsyncHttpSocket',
           'HttpPersister',
           ]

class OOB_Exception(Exception):
    pass

def _fix_headers(data):
    '''
    Given a string containing one or more lines of HTTP headers,
    fixes any header key that contains spaces by replacing the spaces with
    the traditional dash character ('-').

    "Header Name: value with spaces"
      becomes
    "Header-Name: value with spaces"

    spaces in header keys are against the RFC but some servers do it (apple.com!)
    '''
    real_lines = []
    for line in data.splitlines():
        if not ':' in line:
            real_lines.append(line)
            continue

        space = line.find(' ')
        colon = line.find(':')

        while 0 < space < colon:
            line = line[:space] + '-' + line[space+1:]
            space = line.find(' ')
            colon = line.find(':')

        real_lines.append(line)

    return '\n'.join(real_lines)

status_line_re = re.compile(r'^(\S+?)\s+(\S+?)(?:\s+(.+?)?)?$')

log = logging.getLogger('asynchttp.conn')
_log = log

class AsyncHttpConnection(Events.EventMixin, httplib.HTTPConnection):
    timeout = 10

    RequestClass = httptypes.HTTPRequest

    events = Events.EventMixin.events | set((
            'on_connect',
            'on_connect_fail',
            'on_connect_lost',
            'on_close',

            'needs_request', # new_request -for redirects, authorization, etc.

            'on_response',     # request, response
            'on_error_response', # request, response. indicates a non-2xx response
            ))

    default_headers = httptypes.HTTPHeaders({
            'Accept-Encoding'  : 'identity',
            'Connection'       : 'Keep-Alive',
            'Proxy-Connection' : 'Keep-Alive',
            'User-Agent'       : 'digsby-asynchttp/0.1',
            })

    default_post_headers = httptypes.HTTPHeaders({
            'Content-Type'    : 'application/x-www-form-urlencoded',
            })

    DEFAULT_HANDLER_TYPES = [
        urllib2.HTTPCookieProcessor,
        handlers.AsyncHTTPRedirectHandler,
        handlers.AsyncHTTPBasicAuthHandler,
        handlers.AsyncProxyHandler,
        handlers.AsyncHTTPBasicAuthHandler,
        handlers.AsyncProxyBasicAuthHandler,
        handlers.AsyncHTTPDigestAuthHandler,
        handlers.AsyncProxyDigestAuthHandler,
        ]

    def __init__(self, host, port=None, strict=None, timeout = None, proxy_info = None, ssl = False):
        httplib.HTTPConnection.__init__(self, host, port, strict)
        Events.EventMixin.__init__(self)
        self.sock = None
        self.ssl = self.port == httplib.HTTPS_PORT or ssl
        self._connected = False
        self._connecting = False
        self._endpoints = None
        self.timeout = timeout
        self.proxy_info = proxy_info or httplib2.ProxyInfo.get_default_proxy()
        self._q = []
        self._requesting = False

        self.http_handlers = None
        self._logger = log

    def __repr__(self):
        return '<%s host=%r, port=%r, id=0x%x>' % (type(self).__name__, getattr(self, 'host', None), getattr(self, 'port', None), id(self))

    def add_handler(self, new_handler):
        if self.http_handlers is None:
            self.init_handlers()

        for i in range(len(self.http_handlers)):
            #isinstance doesn't work with old-style classes.
            if new_handler.__class__ == self.http_handlers[i].__class__:
                self.http_handlers[i] = new_handler
                break
        else:
            self.http_handlers.append(new_handler)

        self.http_handlers.sort(key = lambda h: h.handler_order)

    def init_handlers(self):
        self.http_handlers = []
        self.add_default_handlers()

    def add_default_handlers(self):
        is_class = lambda obj: isinstance(obj, types.ClassType) or hasattr(obj, "__bases__")

        for handler in self.DEFAULT_HANDLER_TYPES:
            if is_class(handler):
                if issubclass(handler, urllib2.AbstractBasicAuthHandler):
                    handler = handler(getattr(self, 'password_mgr', None))
                else:
                    handler = handler()

            self.http_handlers.append(handler)

        self.http_handlers.sort(key = lambda h: h.handler_order)

    def endpoint_generator(self):
        # yields: (family, socktype, (host,port), (proxyhost, proxyport)).
        # if proxy is not HTTP then (proxyhost, proxyport) == (None, None)
        # family and socktype will probably always be the same (AF_INET and SOCK_STREAM).

        proxy_info = (None, None)

        if self.proxy_info and self.proxy_info.isgood() and self.proxy_info.proxy_type == socks.PROXY_TYPE_HTTP:
            # get proxy (host,port) and yield that along with proxy settings.
            # Make sure to set _proxy_setup attribute of new socket.
            # TODO:
            proxy_info = (self.proxy_info.proxy_host, self.proxy_info.proxy_port)

        try:
            gai_res = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)
        except socket.gaierror:
            gai_res = []

        for res in gai_res:
            family, socktype, _unused, _unused, sockaddr = res
            yield family, socktype, sockaddr, proxy_info

        # last, send the hostname through the proxy getaddrinfo machinery.
        yield 2, 0, (self.host, self.port), proxy_info

    def fatal_error(self):
        self._endpoints = None
        self.connection_failed(fatal = True)

    def connect(self, socket = None, e = None):
        '''
        Starts connection attempts using info from endpoint_generator
        '''

        if isinstance(e, OOB_Exception):
            self.fatal_error()
            return

        if socket is None:
            if self._endpoints is None:
                log.debug('%r Creating new endpoint generator (host=%r, port=%r).', self, self.host, self.port)
                self._endpoints = self.endpoint_generator()
        else:
            # We've been called due to a connection error from self.sock.
            log.info('Socket connection attempt failed because: %r', e)
            if socket is not self.sock:
                raise ValueError("WTF whose socket is this? %r. My socket is %r", socket, self.sock)

        try:
            next = self._endpoints.next()
        except StopIteration:
            self.fatal_error()
            return

        self._connect_once(next)

    def _connect_once(self, sockinfo):
        '''
        Try connecting once to the address provided by sockinfo. Creates self.socket if necessary.
        '''
        _family, _socktype, sockaddr, proxyaddr = sockinfo

        if self.sock is not None:
            log.debug("socket is not none, closing it in preparation for next connect attempt")
            sock, self.sock = self.sock, None
            sock.close()

        if self.sock is None:
            log.debug("socket is none so creating a new AsyncHttpSocket")
            self.sock = AsyncHttpSocket()
            log.debug("binding events")
            self._bind_events(self.sock)

        assert self.sock is not None

        if proxyaddr == (None, None) or self.ssl:
            self._is_proxy = self.sock._is_proxy = False
            connect_addr = sockaddr
        else:
            self._is_proxy = self.sock._is_proxy = True
            connect_addr = proxyaddr

        log.debug("self.sock._is_proxy = %r", self.sock._is_proxy)
        self._set_timeout()
        log.debug("calling connect")
        self._connect_socket(connect_addr)

    def _connect_socket(self, where):
        '''
        Tell self.sock to connect to 'where'.
        '''
        sck = self.sock
        error = lambda e = None: self.connect(sck, e)
        self._connecting = True
        if sck._is_proxy: # Don't use proxy settings because we will handle our own HTTP proxy stuff.
            sck.connect(where, use_proxy = False, error = error)
        else:
            sck.connect(where, error = error) # Allow normal proxy craziness to happen.

    def _set_timeout(self):
        '''
        set timout on self.sock to self.timeout (if it's not None)
        '''
        if self.timeout is not None:
            self.sock.settimeout(self.timeout)

    def on_sock_connect(self, sck):
        '''
        Handler for self.sock's "on_connect" event.
        '''

        if self.ssl:
            self.sock.setup_ssl(lambda: self._on_sock_connect(sck))
        else:
            self._on_sock_connect(sck)

    def _on_sock_connect(self, sck):
        sck.unbind("on_connection_error", self.connect)
        sck.bind_event('on_connection_error', self.connection_lost)
        self._connected = True
        self._connecting = False
        self.event('on_connect', self)
        self._process()

    def is_connected(self):
        if self.sock is None:
            self._connected = False
        return self._connected

    def is_connecting(self):
        return getattr(self, '_connecting', False)

    def connection_failed(self, sck = None, e = None, fatal = False):
        '''
        Called when all attempts to connect socket have failed
        '''
        log.debug('connection failed for %r', self)
        self._close_socket()
        self.event('on_connect_fail', self, fatal)

    def connection_lost(self, sck = None, e = None):
        '''
        event handler for socket connection after it connects.
        '''
        log.debug('connection lost for %r', self)
        self._close_socket()
        self.event('on_connect_lost', self)

    def close(self):
        self._close_socket()
        self.event('on_close', self)

    def _close_socket(self):
        self._connected = False
        self._connecting = False
        if self.sock is not None:
            self._unbind_events(self.sock)
            sock, self.sock = self.sock, None
            log.debug('closing %r\'s socket %r', self, sock)
            sock.close()

    def on_sock_close(self, sck):
        self.close()

    def _bind_events(self, sck):
        bind = sck.bind_event
        bind('on_close', self.on_sock_close)
        bind('on_connect', self.on_sock_connect)
        bind('on_connection_error', self.connect)
        bind('on_body', self._handle_response)

    def _unbind_events(self, sck):
        unbind = sck.unbind
        unbind('on_connect', self.on_sock_connect)

        # might be bound to either of these, make sure both are unbound.
        unbind('on_connection_error', self.connection_failed)
        unbind('on_connection_error', self.connection_lost)
        unbind('on_close', self.on_sock_close)
        unbind('on_body', self._handle_response)
        unbind('on_connect', self.on_sock_connect)

    def make_request(self, *a, **k):
        k['default_host'] = self.host
        k['ssl'] = self.ssl

        return self.RequestClass.make_request(*a, **k)

    def request(self, request, data=None, *a, **k):

        if not isinstance(request, urllib2.Request):
            request = self.make_request(request, data, *a, **k)

        self._q.append(request)
        self._process()

    def _process(self):
        if (not self._connected) or self._requesting or (not self._q):
            return

        self._requesting = True
        request = self._q.pop(0)
        #_log.debug('Sending request %r to socket', request)

        if self.http_handlers is None:
            self.init_handlers()

        self.preprocess_request(request)
        self.sock.request(request)

    def _format_host(self, url, reqhost):
        netloc = ''
        if url.startswith('http'):
            nil, netloc, nil, nil, nil = urlparse.urlsplit(url)

        if netloc:
            host_str = netloc
            needs_port = False
        else:
            host_str = reqhost
            needs_port = True

        try:
            host = host_str.encode("ascii")
        except UnicodeEncodeError:
            host = host_str.encode("idna")

        if needs_port:
            if self.port != httplib.HTTP_PORT:
                host += (':%d'%self.port)

        return host

    def http_request(self, req):
        req.headers.setdefault('Host', self._format_host(req.get_full_url(), req.get_host()))
        if req.has_data():
            req.headers.setdefault('Content-Length', str(len(req.get_data())))

        self._set_default_headers(req)

    def http_response(self, request, response):
        if (response.code // 100) == 2:
            event = 'on_response'
        else:
            event = 'on_error_response'

        request = getattr(request, '_orig_request', request)
        self.event(event, request, response)

    def preprocess_request(self, req):
        for handler in  [self] + list(self.http_handlers):
            preprocess = getattr(handler, 'http_request', None)
            if preprocess is not None:
                preprocess(req)

    def postprocess_response(self, request, response):
        action = obj = pp_result = None
        for handler in  list(self.http_handlers) + [self]:
            for name in ('http_response_%3d' % response.code, 'http_response'):
                postprocess = getattr(handler, name, None)
                if postprocess is not None:
                    pp_result = postprocess(request, response)
                    if type(pp_result) is tuple and len(pp_result) == 2:
                        try:
                            action, obj = pp_result
                        except ValueError:
                            continue
                        else:
                            break
            else:
                if action is not None:
                    break

        if action is None:
            return

        if action == 'request':
            new_request = obj
            new_request._orig_request = getattr(request, '_orig_request', request)
            self.needs_request(request, new_request)
        else:
            raise ValueError("Don't know about this action: %r", action)

    @Events.event
    def needs_request(self, old_request, new_request):
        '''
        This event is used when a request has been modified by handlers and
        a new request must be performed.

        old_request: the original request
        new_request: the new request, (usually) constructed by the handlers
        '''

    def _handle_response(self, socket, request, status, headers, body):
        response = httptypes.HTTPResponse(status, headers, body, url = request.get_full_url())
        self.postprocess_response(request, response)
        self._requesting = False
        self._process() # , callnow = False)

    def _set_default_headers(self, req):
        if req.get_method() == 'POST':
            dicts = (self.default_headers, self.default_post_headers)
        else:
            dicts = (self.default_headers,)

        for _dict in dicts:
            for k in _dict:
                if k not in req.headers:
                    req.headers[k] = _dict[k]

class AsyncHttpSocket(AsyncSocket, Events.EventMixin):
    _http_vsn_str = AsyncHttpConnection._http_vsn_str
    CRLF = '\r\n'
    events = Events.EventMixin.events | set((
            "on_connect",          # args = socket
            "on_connection_error", # args = socket, error
            "on_close",            # args = socket
            "on_http_error",       # args = socket, error

            "on_request",          # args = socket, request (Request object)
            "on_request_error",    # args = socket, request (Request object), error
            "on_status_line",      # args = socket, (httpver, code, reason)
            "on_headers",          # args = socket, headers (list of tuples)
            "on_body",             # args = socket, request (Request object), (httpver, code, reason), headers (list of tuples), body (file-like object)
            ))

    def __init__(self, conn = None):
        self._connected = False

        Events.EventMixin.__init__(self)
        AsyncSocket.__init__(self, conn)

        self.buffer = []

        self.status_line = ''
        self.status = None
        self.chunk_header = ''
        self.current_request = None
        self.current_body = stringio()
        self.current_chunk = stringio()
        self.current_headers = ''
        self.body_length = 0

        self.waiting_for = 'request'
        self.set_terminator(self.CRLF)

        self.ssl = False
        self.ssl_want = None
        self.lastbuffer = None
        self._sent_data = False

    def _repr(self):
        return 'connected=%r' % self._connected

    def close(self):
        log.info('%r closing, has sent data? %r. waiting_for = %r, terminator = %r', self, self._sent_data, self.waiting_for, self.terminator)
        if self.status is not None:
            log.info('\tstatus = %r', self.status)
        AsyncSocket.close(self)

    def setup_ssl(self, ssl_cb=None):
        '''
        Note: this method is blocking. However, the connection is already
        established and we're on the net thread. Shouldn't be too bad if we
        block it for the duration of the SSL handshake.
        '''
        log.debug('setting up ssl on socket (waiting_for=%r): %r', self.waiting_for, self)
        self.ssl = True

        self.socket = ssl.wrap_socket(self.socket,
                cert_reqs=ssl.CERT_NONE,
                do_handshake_on_connect=False)

        self.socket.setblocking(0)

        self.ssl_want = 'write'
        self.ssl_cb = ssl_cb
        log.debug('wrap_socket completed')

    def _call_do_handshake(self):
        s = self.socket

        try:
            log.debug('calling do_handshake()')
            log.debug('sock.gettimeout() is %r', s.gettimeout())
            s.do_handshake()
        except ssl.SSLError, err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                log.debug('SSL_ERROR_WANT_READ')
                self.ssl_want = 'read'
            elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                log.debug('SSL_ERROR_WANT_WRITE')
                self.ssl_want = 'write'
            else:
                raise
        else:
            log.debug('handshake finished.')
            self.ssl_want = None
            ssl_cb, self.ssl_cb = self.ssl_cb, None
            if ssl_cb is not None:
                ssl_cb()

    def handle_read(self):
        if self.ssl_want is not None:
            self._call_do_handshake()
        else:
            return super(AsyncHttpSocket, self).handle_read()

    def handle_write(self):
        if self.ssl_want is not None:
            self._call_do_handshake()
        else:
            return super(AsyncHttpSocket, self).handle_write()

    def readable(self):
        return self.ssl_want != 'write' and (self.ssl_want == 'read' or AsyncSocket.readable(self))

    def writable(self):
        return self.ssl_want != 'read' and (self.ssl_want == 'write' or AsyncSocket.writable(self))

    def recv(self, buffer_size=4096):
        self.ssl_want = None
        try:
            return super(AsyncHttpSocket, self).recv(buffer_size)
        except ssl.SSLError, e:
            if e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                log.warning("read_want_write")
                self.ssl_want = 'write'
                return ""
            elif e.args[0] == ssl.SSL_ERROR_WANT_READ:
                log.warning("read_want_read")
                self.ssl_want = 'read'
                return ""
            else:
                raise socket.error(e)

    def send(self, buf):
        self.ssl_want = None

        if not self.ssl:
            return super(AsyncHttpSocket, self).send(buf)

        r = None
        if not self.lastbuffer:
            try:
                r = self.socket.send(buf)
            except ssl.SSLError, e:
                if e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    log.warning("write_want_write")
                    self.ssl_want = 'write'
                    self.lastbuffer = buf # -1: store the bytes for later
                    return len(buf)       # consume from asyncore
                elif e.args[0] == ssl.SSL_ERROR_WANT_READ:
                    log.warning("write_want_read")
                    self.ssl_want = 'read'
                    return 0
                else:
                    raise socket.error(e, r)
            else:
                if r < 0:
                    raise socket.error('unknown -1 for ssl send', r)
                return r
        else:
            try:
                # we've got saved bytes--send them first.
                r = self.socket.send(self.lastbuffer)
            except ssl.SSLError, e:
                if e.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                    log.warning("write_want_write (buffer)")
                    self.ssl_want = 'write'
                elif e.args[0] == ssl.SSL_ERROR_WANT_READ:
                    log.warning("write_want_read (buffer)")
                    self.ssl_want = 'read'
                else:
                    raise socket.error(e, r)
            else:
                if r < 0:
                    raise socket.error('unknown -1 for ssl send (buffer)', r)
                elif r < len(self.lastbuffer):
                    self.lastbuffer = self.lastbuffer[r:]
                else:
                    self.lastbuffer = ''
            return 0

    def initiate_send(self):
        #if there's nothing else in the socket buffer, the super class initiate_send won't call send
        # and self.lastbuffer won't be flushed.
        if self.lastbuffer:
            assert self.ssl_want == 'write'
            self.send(None)
            return
        return super(AsyncHttpSocket, self).initiate_send()

    def request(self, request):
        if not self.waiting_for == 'request':
            raise Exception('Socket not ready for a request', self, self.waiting_for)
        else:
            self.current_request = request
            self._send_request()

    def _send_request(self):

        self.waiting_for = 'status'
        self.set_terminator(self.CRLF)

        r = self.current_request

        self._push_start_line(r)
        self._push_headers(r)
        self._push_body(r)

    def _format_headers(self, req):
        buf = stringio()
        write = buf.write

        header_dicts = [req.headers, req.unredirected_hdrs]

        for d in header_dicts:
            for key, value in d.items():
                write(key);   write(': ')
                write(value); write('\r\n')

        write('\r\n')

        return buf.getvalue()

    def _push_start_line(self, req):

        if self._is_proxy:
            selector = req.get_full_url()
        else:
            selector = req.get_selector()

        if not selector:
            selector = '/'

        start_line = '%s %s %s\r\n' % (req.get_method(), selector.encode('ascii'), self._http_vsn_str)
        self.push(start_line)
        self._sent_data = True
        #_log.debug('pushed start line: %r', start_line)

    def _push_headers(self, req):
        data = self._format_headers(req)
        self.push(data)
        #_log.debug('pushed headers: %r', data)

    def _push_body(self, req):
        if req.has_data():
            data = req.get_data()
        else:
            data = ''

        # As soon as the producer's .more returns '', the callback will go off, signalling that the request has been sent.
        # With no data, this happens immediately. With data, it happens at the end.
        prod = producer_cb(data, success = lambda: self.on_request(), error = lambda e: self.on_request_error(e))
        self.push_with_producer(prod)
        #_log.debug('pushed body: %r', data)

    # ------ AsyncSocket methods

    def handle_connect(self):
        if not self._connected:
            self._connected = True
            self.on_connect()

    def handle_close(self):
        log.debug('handle_close for %r', self)
        self._connected = False
        self.close()

        if self.get_terminator() in (None, 0) and self.waiting_for == 'body':
            self.on_body()

        if self._sent_data:
            self.on_close()
        else:
            self.on_connection_error('socket closed before data sent')

    def handle_error(self, e=None):
        log.debug('handle_error for %r', self)
        if e is None:
            e = sys.exc_info()[1]

        if isinstance(e, socket.error):
            errno, _errmsg = e.args
            if errno in _ok_errors:
                return

        log.info('Socket error: %r', e)

        if sys.exc_info() != (None, None, None):
            traceback.print_exc()

        self._connected = False
        self.close()
        self.on_connection_error(e)

    def handle_expt(self):
        log.debug('handle_expt for %r', self)
        self.handle_error(OOB_Exception("OOB data"))

    def collect_incoming_data(self, data):
        if self.waiting_for == 'status':
            self.status_line += data
        elif self.waiting_for == 'headers':
            self.buffer.append(data)
        elif self.waiting_for == 'body':
            if self.buffer:
                old_data = ''.join(self.buffer)
                self.collect_body_data(old_data)
                self.set_terminator(self.terminator - len(old_data))
                del self.buffer[:]
                if self.terminator == 0: # Unlikely, but just in case
                    self.found_terminator()
            self.collect_body_data(data)
        elif self.waiting_for == 'chunk-header':
            self.collect_chunk_header(data)
        elif self.waiting_for == 'chunk-body':
            self.collect_chunk_data(data)
        elif self.waiting_for == 'request':
            log.error("Received data when no response was expected. This is an error and the socket will close. The data was: %r", data)
            self.handle_error(Exception("Unexpected data received: %r" % data))
        else:
            raise AssertionError("Shouldn't be waiting for this: %r" % self.waiting_for)

    def found_terminator(self):
        #_log.debug('Found terminator %r. Currently waiting for: %r', self.terminator, self.waiting_for)
        if self.waiting_for == 'status':
            status_line = self.status_line
            if status_line == '':
                new_term = self.CRLF
            else:
                new_term = self.on_status_line()
            self.set_terminator(new_term)
        elif self.waiting_for == 'headers':
            data = ''.join(self.buffer)
            del self.buffer[:]
            self.on_headers(data) # Changes 'waiting_for' to 'body' or 'request' or 'chunk-header' and sets new terminator
        elif self.waiting_for == 'body':
            if self.body_length:
                self.on_body() # Changes 'waiting_for' to 'request'
            else:
                log.warning('Received chunk for body of unknown size.')
                self.set_terminator(512)
        elif self.waiting_for == 'chunk-header':
            new_term = self.process_chunk_header()
            self.set_terminator(new_term)
        elif self.waiting_for == 'chunk-body':
            new_term = self.process_chunk_data()
            self.set_terminator(new_term)
        else:
            raise AssertionError("Unexpected 'waiting_for' for found_terminator: %r. Current buffer is: %r", self.waiting_for, self.buffer)

    # ------- End AsyncSocket methods


    # ------- Helper methods
    def collect_body_data(self, data):
        self.current_body.write(data)

    def collect_chunk_header(self, data):
        self.chunk_header += data

    def collect_chunk_data(self, data):
        self.current_chunk.write(data)

    def process_chunk_header(self):
        hdr, self.chunk_header = self.chunk_header, ''

        if hdr == '':
            # This happens every odd time this function is called. protocol states that
            # the header /includes/ a newline even though the next thing to read is a
            return self.CRLF

        #log.debug('Got chunk header: %r', hdr)
        hdr_parts = hdr.split(';', 1)
        sz, _rest = hdr_parts[0], hdr_parts[1:]
        chunk_size = int(sz, 16)

        self.waiting_for = 'chunk-body'
        if chunk_size == 0:
            return self.CRLF
        else:
            return chunk_size

    def process_chunk_data(self):
        chunk = self.current_chunk.getvalue()
        self.current_chunk = stringio()

        if len(chunk) == 0:
            self.waiting_for = 'request'
            self.on_body()
            return self.CRLF
        else:
            header = self.chunk_header
            self.chunk_header = ''
            self.waiting_for = 'chunk-header'
            return self.decode_chunk(header, chunk)

        # TODO: return new terminator ("\r\n" ?)

    @property
    def original_request(self):
        return getattr(self.current_request, '_orig_request', self.current_request)

    def decode_chunk(self, header, chunk):
        if chunk[:2] == '\r\n':
            chunk = chunk[2:]

        req = self.original_request
        req.on_chunk(chunk)
        if req.accumulate_body:
            self.current_body.write(chunk)
        return self.CRLF

    # --------- End helpers

    # --------- Events
    @Events.event
    def on_connect(self):
        '''
        on_connect: this event is thrown when this socket connects.
        the socket is the only event argument.
        '''
        #self._connected_host, self._connected_port = self.getpeername()
        return self

    @Events.event
    def on_close(self):
        '''
        on_close: this event is thrown when this socket is closed normally.
        the socket is the only event argument.
        '''
        return self

    @Events.event
    def on_connection_error(self, e):
        '''
        on_connection_error: this event is thrown when a connection related (but non-HTTP) error occurs.
        the event arguments are this socket and the error object.
        '''
        return self, e

    @Events.event
    def on_http_error(self, e):
        '''
        on_http_error: this event is thrown when a HTTP error occurs.
        the event arguments are this socket and the error object.
        '''
        return self, e

    @Events.event
    def on_request(self):
        '''
        the request has been sent.
        event args: this socket and the request that was sent.
        '''
        req = self.current_request
        return self, req

    @Events.event
    def on_request_error(self, e):
        '''
        there was an error sending the request

        event args: this socket, the request, and the error.
        '''
        req, self.current_request = self.current_request, None
        self.waiting_for = 'request'
        return self, req, e

    def on_status_line(self):
        match = status_line_re.match(self.status_line)
        if not match:
            raise ValueError("Unexpected data for status line: %r", self.status_line)

        (version, code, reason) = match.groups()
        code = int(code) # Will raise value error if something is terribly wrong.

        self.status = (version, code, reason)

        #_log.debug('Got status: %r', self.status)

        # If the response is 100/Continue, ignore it.
        if code == 100:
            self.waiting_for = 'status'
            self.status = None
            self.status_line = ''
            return self.CRLF
        else:
            self.waiting_for = 'headers'
            self.event('on_status_line', self, self.status)
            return self.CRLF*2

    def on_headers(self, header_data):
        '''
        response headers have been received. Returns new terminator, and throws
        'on_headers' event if appropriate.
        '''

        header_data = _fix_headers(header_data)

        self.current_headers = email.message_from_string(header_data)

        tenc = self.current_headers.get('Transfer-Encoding', None)
        clen = self.current_headers.get('Content-Length', None)
        if clen is not None:
            clen = int(clen)

        #_log.debug('Got headers: %r', dict(self.current_headers))

        if tenc is not None and tenc.lower() == 'chunked':
            self.waiting_for = 'chunk-header'
            term = self.CRLF
        elif self.status[1] == 204 or self.current_request.get_method() == 'HEAD': # No content
            self.event('on_headers', self, self.current_headers)
            return self.on_body()
        elif clen == 0:  # empty content
            self.waiting_for = 'request'
            term = self.CRLF
        elif clen:
            self.waiting_for = 'body'
            self.body_length = term = clen
        elif (self.current_headers.get('Connection', self.current_headers.get('Proxy-Connection', None)) == 'close') or (self.current_headers.get('Location', None) is not None):
            term = 0
            self.waiting_for = 'body'
        else:
            raise ValueError("Not sure how to proceed. status = %r, headers = %r", self.status, self.current_headers.items())
            term = None

        self.set_terminator(term)

        self.event('on_headers', self, self.current_headers)

        if self.waiting_for == 'request':
            self.on_body()

    def on_body(self):
        request = self.current_request
        self.current_request = None

        status = self.status
        self.status = None
        self.status_line = ''

        self.chunk_header = ''
        self.current_chunk = stringio()

        headers = self.current_headers or {}
        self.current_headers = ''

        body = self.current_body
        body.seek(0)
        #_log.debug('Got body: %r', body.getvalue())
        self.current_body = stringio()

        self.waiting_for = 'request'

        self.event('on_body', self, request, status, headers, body)

        if headers.get('Connection', headers.get('Proxy-Connection')) == 'close':
            log.debug('got "Connection: %s", "Proxy-Connection: %s", closing',
                      headers.get('Connection'), headers.get('Proxy-Connection'))
            self.close()
            self.on_close()

    # -------- End Events

    def __getattr__(self, attr):
        try:
            val = AsyncSocket.__getattr__(self, attr)
        except AttributeError, e:
            try:
                val = Events.EventMixin.__getattr__(self, attr)
            except AttributeError:
                raise e

        return val

class HttpPersister(Events.EventMixin):
    '''
    Wraps an HTTP connection and re-connects if necessary.
    '''
    MAX_ERROR = 6

    events = Events.EventMixin.events | set((
            'on_fail',
            'redirect',
            'on_close',
            ))

    connection_cls = AsyncHttpConnection

    def __init__(self, hostport):
        self.host, self.port = hostport
        self.conn = None
        self.pending = False
        self._err_count = 0
        self._request_q = None
        self.has_failed = False
        Events.EventMixin.__init__(self)

    def __repr__(self):
        conn_str = 'host=%r, port=%r' % (self.host, self.port)
        return '<%s %s, id=0x%x>' % (type(self).__name__, conn_str, id(self))

    def is_connected(self):
        return self.conn is not None and self.conn.is_connected()

    def _make_connection(self):
        cls = self.connection_cls
        log.info('Creating new %r', cls)
        conn = cls(self.host, self.port)
        if hasattr(self, 'password_mgr'):
            conn.password_mgr = self.password_mgr
        return conn

    def connect(self):
        if self._request_q is None:
            self._request_q = []

        if self.conn is None:
            self.conn = self._make_connection()
            self.bind_events()

        AsyncoreThread.call_later(self._do_connect)

    def _do_connect(self):
        if self.conn is None:
            # Some sort of error occurred and our connection object has been removed.
            return

        if not self.conn.is_connecting() and not self.conn.is_connected():
            self.conn.connect()

    @util.callsback
    def request(self, req, callback=None):
        err  = callback.error
        succ = callback.success
        def error(*a):
            assert len(a) == 2
            return err(*a)
        def success(*a):
            assert len(a) == 2
            return succ(*a)

        callback.error = error
        callback.success = success

        req.callback = callback

        if self._request_q is None:
            self._request_q = []

        self._request_q.append(req)
        self._process_one_request()

    def _on_connect(self, conn):
        if not self.pending:
            self._process_one_request()

    def _process_one_request(self):
        if self.pending:
            return

        if not self._request_q:
            log.info('no requests, closing HTTP connection %r', self)
            self.close()
            return

        if not self.is_connected():
            self.connect()
            return

        request = None
        while request is None and self._request_q:
            request = self._request_q[0]
            setattr(request, 'attempts', getattr(request, 'attempts', 0) + 1)
            if request.attempts > getattr(request, 'max_attempts', 5):
                log.error('This request has been attempted too many times, calling it\'s error callbacks: %r', request)
                try:
                    request.callback.error(Exception("too many failed attempts"))
                except Exception, e:
                    log.error('Error calling request\'s error callback: %r', e)
                    del e
                try:
                    self._request_q.pop(0)
                except AttributeError:
                    assert self._request_q is None

        if request is None:
            return

        assert not self.pending, 'request already pending'
        assert self.is_connected(), 'httpconnection not connected'

        self.pending = True
        self.conn.request(request)

    def bind_events(self):
        bind = self.conn.bind_event
        bind('on_connect', self._on_connect)
        bind('on_close', self._conn_closed)
        bind('on_connect_fail', self._conn_fail)
        bind('on_connect_lost', self._conn_lost)
        bind('on_response', self._handle_response)
        bind('on_error_response', self._handle_error_response)
        bind('needs_request', self._handle_new_request)

    def unbind_events(self):
        if self.conn is None:
            return
        unbind = self.conn.unbind
        unbind('on_connect', self._on_connect)
        unbind('on_close', self._conn_closed)
        unbind('on_connect_fail', self._conn_fail)
        unbind('on_connect_lost', self._conn_lost)
        unbind('on_response', self._handle_response)
        unbind('on_error_response', self._handle_error_response)
        unbind('needs_request', self._handle_new_request)

    def _handle_new_request(self, orig, req):
        #_log.debug('New request')

        try:
            self._request_q.remove(orig)
        except ValueError:
            pass

        # This event comes from the socket, usually for a redirect or authorization, so the previous request must be done
        self.pending = False

        self.redirect(req)
        self._process_one_request()

    @Events.event
    def redirect(self, req):
        '''
        The request has been redirected.

        event args: the request being redirected.
        '''

    def _conn_closed(self, conn = None, try_again = True):
        #_log.info('httppersister: Connection closed')
        self.unbind_events()
        if self.conn is not None:
            self.conn.close()
            self.conn = None

        self.pending = False

        if try_again:
            self._process_one_request()

    def _conn_fail(self, conn = None, fatal = False):
        log.info('_conn_fail for %r', self)
        self._conn_closed(try_again = not fatal)

        self._err_count += 1
        if self._err_count < self.MAX_ERROR and not fatal:
            self.connect()
        elif (self._err_count >= self.MAX_ERROR or fatal) and not self.has_failed:
            self.has_failed = True
            try:
                current_req = self._request_q[0]
            except (ValueError, IndexError):
                current_req = None

            if fatal:
                log.info('Fatal error occured, calling error callbacks for all requests. (current request = %r)', current_req)
            else:
                log.info('Error count for %r is too high (%r/%r). Calling error callbacks for all requests. (current request = %r)',
                         self, self._err_count, self.MAX_ERROR, current_req)
            q = self._request_q[:]
            while q:
                req = q.pop(0)
                try:
                    req.callback.error(req, Exception('conn_fail'))
                except Exception, e:
                    log.error('Error calling callback for req=%r: error=%r', req, e)

            self.event('on_fail', self)

    def _conn_lost(self, conn):
        if self.pending:
            self._conn_fail()  # Will increment + check error count.
        else:
            self._conn_closed(try_again = True)

    def _handle_response(self, req, resp):
        self._cleanup_request(req, resp, 'success')

    def _handle_error_response(self, req, resp):
        self._cleanup_request(req, resp, 'error')

    def _cleanup_request(self, req, resp, cb_attr):
        #_log.debug('httppersister: Got response, cleaning up')
        self._err_count = 0
        _req = self._request_q.pop(0)
        self.pending = False
        cb, _req.callback = _req.callback, None

        if hasattr(_req, '_orig_request'):
            log.info('%sful redirect: %r to %r. response = %r', cb_attr, _req._orig_request, _req, resp)
            req = _req._orig_request

        if cb is not None:
            f = getattr(cb, cb_attr)
            try:
                f(req, resp)
            except Exception, e:
                log.error('Error calling callback (%r) for req (%r): error=%r', cb_attr, req, e)
            else:
                #_log.info('Called %r (%r) with args=(%r, %r)', cb_attr, f, req, resp)
                pass
        else:
            log.warning('No callback for this request: %r', req)

        if req is not _req and req is not getattr(_req, '_orig_request', False):
            # XXX: this may be the case due to redirects
            #self._request_q.insert(0, _req)
            try:
                self._request_q.remove(req)
            except ValueError: # req not in list
                pass
            log.warning("Removed the wrong request! Things are messed up in asynchttp. (%r, %r)", req, _req)

        if self._request_q:
            self._process_one_request()

    def close(self):
        if self.conn is not None:
            self.unbind_events()
            self.conn.close()
            self.conn = None
            del self._request_q[:]
            self._request_q = None

        self.on_close()

    @Events.event
    def on_close(self):
        '''Closed intentionally (i.e., not an error)'''
        return self
