from __future__ import with_statement
from .callbacks import callsback
from .threads import threaded
from .threads.timeout_thread import Timer
from .net import build_opener, build_cookie
from common.asynchttp.cookiejartypes import CookieJarHTTPMaster
import contextlib

import re
import traceback
import StringIO
import cookielib
import urlparse
import urllib2
import logging
import lxml.etree as ET
import lxml.html as HTML
import operator
from contextlib import closing

itemgetter0 = operator.itemgetter(0)

log = logging.getLogger('httptools')

class RequestOpener(object):
    max_redirects = 5
    retries = 3
    pause_for_attempts = 1

    js_redirect_res = (
                       (re.compile(r'window\.location\.replace\("(.*?)"\);'), 1),
                       #'http\x3a\x2f\x2fwww.hotmail.msn.com\x2fcgi-bin\x2fsbox\x3fn\x3d123456789'
                       )

    request_cls = urllib2.Request

    def __init__(self, opener, request, data = None, **kwds):
        self.openfunc = getattr(opener, 'open', opener)

        retries = kwds.pop('retries', None)
        if retries is not None:
            self.retries = retries

        if isinstance(request, basestring):
            request = self.request_cls.make_request(request, data, **kwds)

        self.request = request
        self._sub_requester = None

        self.callback = None

    @callsback
    def open(self, callback = None):
        if self.callback is not None:
            raise Exception("Request already in progress")

        self.callback = callback
        self._attempt_open()

    def _attempt_open(self):
        self.openfunc(self.request,
                      success = self._check_success,
                      error = self._check_error)

    def preprocess_response(self, resp):
        with closing(resp):
            data = resp.read()

        c_encoding = resp.headers.get('Content-Encoding', 'identity')

        # TODO: create pluggable infrastructure for (en|de)coders (or maybe for asynchttp?)
        if c_encoding == 'gzip':
            data = data.decode('gzip')

        sio = StringIO.StringIO(data)
        for attr in ('read', 'seek', 'close', 'tell'):
            setattr(resp, attr, getattr(sio, attr))

        resp._stringio = sio
        resp.content = data

        return resp

    def _check_success(self, resp):
        try:
            resp = self.preprocess_response(resp)
        except Exception, e:
            self._on_error(e)
            return
        redir = self.can_redirect(resp)
        if redir:
            return self.redirect(redir)
        else:
            error = self.check_resp_for_errors(resp)
            if error is None:
                self.finish('success', resp)
            else:
                self._on_error(error)

    def _redirect_success(self, resp):
        self._sub_requester = None
        self.finish('success', resp)

    def _redirect_error(self, err = None):
        self._sub_requester = None
        self._on_error(err)

    def can_redirect(self, resp):
        if getattr(self, '_redirect_count', 0) > self.max_redirects:
            return False
        if self._sub_requester is not None:
            return False
        return self.make_redirect_request(resp)

    def redirect(self, redirect):
        new = self._sub_requester = type(self)(self.openfunc, redirect)

        setattr(new, '_redirect_count', getattr(self, '_redirect_count', 0) + 1)

        new.open(success = self._redirect_success,
                 error = self._redirect_error)

    def make_redirect_request(self, resp):
        # construct a redirect request from the resp and current self.request.

        # TODO: or maybe leave this for subclasses. some things that aren't handled by anything else:
        # * <head><meta http-equiv="refresh" content="0;url=http://www.spam.com" /></head>
        # * <script type="text/javascript">window.location.href='http://www.eggs.com';</script>
        # * <body onload="javascript:setTimeout(function(){window.location.href='http://www.ham.com'},2000);">
        # etc.

        for redirecter in (self._find_http_redirect, self._find_js_redirect):
            redirect = redirecter(resp)
            if redirect is not None:
                if not redirect.startswith('http'):
                    if not redirect.startswith('/'):
                        redirect = '/' + redirect
                    redirect = self.request.get_type() + '://' + self.request.get_host() + redirect

                parsed = urlparse.urlparse(redirect)
                if parsed.path == '':
                    d = parsed._asdict()
                    d['path'] = '/'
                    redirect = urlparse.urlunparse(type(parsed)(**d))

                log.debug('got redirect: %r', redirect)
                return redirect

        return None

    def _find_http_redirect(self, resp):
        if resp.code in (301, 302):
            return resp.headers.get('Location', None)

    def _find_js_redirect(self, resp):
        for redirect_re, url_group_id in self.js_redirect_res:
            match = redirect_re.search(resp.content)
            if match:
                new_url = match.group(url_group_id)
                if new_url:
                    return new_url

    def check_resp_for_errors(self, resp):
        # TODO: or maybe leave this for subclasses
        return None

    def _check_error(self, err = None, resp = None):
        if resp is not None:
            self._on_error((err, resp))
        else:
            self._on_error(err)

    def _on_error(self, e = None):
        self.retries -= 1
        if self.retries:
            if self.pause_for_attempts > 0:
                Timer(self.pause_for_attempts, self._attempt_open).start()
            else:
                self._attempt_open()
        else:
            self.finish('error', e)

    def finish(self, result, *args):
        cb, self.callback = self.callback, None
        self._sub_request = self.request = self.openfunc = None
        getattr(cb, result, lambda * a: None)(*args)

def dispatcher(what, arg_getter):
    def dispatch(self, *args, **req_options):
        name = arg_getter(args)
        handler = getattr(self, '%s_%s' % (what, name), getattr(self, '%s_default' % what, None))

        if handler is not None:
            return handler(*args, **req_options)
        else:
            log.error('No default handler for %r', what)
    return dispatch

class WebScraperBase(object):
    CookieJarFactory = cookielib.CookieJar # I almost called it "CookieCutter".
    HttpOpenerFactory = staticmethod(build_opener) # TODO: use asynchttp here
    RequestFactory = staticmethod(urllib2.Request.make_request)
    @classmethod
    def RequestOpenerFactory(cls, open, req, **kwds):
        return RequestOpener(threaded(open), req, **kwds)
    domain = None # 'www.hotmail.com' or something like that.

    urls = {} # Convenience for mapping of names to urls so you don't have to implement lots of build_request_* methods.

    def __init__(self):
        self._waiting = set()

        self._callbacks = {}
        self.init_http()
        self._batching = False
        self._batchqueue = []

    def init_http(self):
        self._jar = self.CookieJarFactory()
        self.http = self.HttpOpenerFactory(urllib2.HTTPCookieProcessor(self._jar))

    def get_cookie(self, key, default = sentinel, domain = None, path='/'):
        if domain is None:
            domain = self.domain

        val = default

        try:
            with self._jar._cookies_lock:
                val = self._jar._cookies[domain][path][key].value
        except (AttributeError, KeyError), e:
            if val is sentinel:
                raise e
            else:
                return val
        else:
            return val

    def set_cookie(self, key, value, domain = None, path = '/'):
        if domain is None:
            domain = self.domain

        with self._jar._cookies_lock:
            domain_dict = self._jar._cookies.setdefault(domain, {})
            path_dict = domain_dict.setdefault(path, {})

            cookie = path_dict.get(key, None)
            if cookie is None:
                cookie = build_cookie(key, value, domain = domain, path = path)
                path_dict[key] = cookie
            else:
                cookie.value = value

    def set_waiting(self, *things):
        self._waiting.update(things)

    def clear_waiting(self, *things):
        self._waiting -= set(things)

        if not self._waiting:
            self.done_waiting()

    def done_waiting(self):
        pass

    @contextlib.contextmanager
    def batch(self):
        if self._batching:
            raise Exception('Can\'t do more than one batch of requests at a time.')
        self._batching = True

        try:
            yield self
        finally:
            self._batching = False

            while self._batchqueue:
                name, req, req_options = self._batchqueue.pop(0)
                self.perform_request(name, req, **req_options)

    @callsback
    def request(self, name, callback = None, **req_options):
        if name in self._waiting:
            log.warning('already waiting for %r', name)
            return

        self._callbacks[name] = callback
        req = self.build_request(name, **req_options)

        if self._batching:
            self.set_waiting(name)
            self._batchqueue.append((name, req, req_options))
            return

        self.perform_request(name, req, **req_options)

    def perform_request(self, name, req, **req_options):
        self.set_waiting(name)

        if req is None:
            return self.error_handler(name, req_options)(Exception("No request created for %r" % name))

        reqopen = self.RequestOpenerFactory(self.http.open, req, **req_options)

        reqopen.open(success = self.success_handler(name, req_options),
                     error   = self.error_handler(name, req_options))

    def error_handler(self, name, req_options):
        def handler(e = None):
            try:
                e = self.preprocess_resp(name, e, **req_options)
            except Exception, exc:
                if not req_options.get('quiet', False):
                    traceback.print_exc()
#                self.error_handler(name, req_options)(exc)
#                return

            self.clear_waiting(name)
            cb = self._callbacks.pop(name, None)
            retval = self.handle_error(name, e, **req_options)

            if cb is not None:
                cb.error(e)

            return retval

        return handler

    def success_handler(self, name, req_options):
        def handler(resp):
            try:
                resp = self.preprocess_resp(name, resp, **req_options)
            except Exception, exc:
                traceback.print_exc()
                self.error_handler(name, req_options)(exc)
                return

            try:
                newresp = self.handle_success(name, resp, **req_options)
            except Exception, exc:
                traceback.print_exc()
                self.error_handler(name, req_options)(exc)
                return

            if newresp is not None:
                resp = newresp

            cb = self._callbacks.pop(name, None)
            if cb is not None:
                cb.success(resp)
            self.clear_waiting(name)

            return newresp

        return handler

    build_request  = dispatcher('build_request',   itemgetter0)
    handle_error   = dispatcher('handle_error',    itemgetter0)
    preprocess_resp= dispatcher('preprocess_resp', itemgetter0)
    handle_success = dispatcher('handle_success',  itemgetter0)

    def build_request_default(self, name, **req_options):
        link = self.urls[name]

        if callable(link):
            link = link()

        return self.RequestFactory(link, **req_options)

    def handle_error_default(self, name, e, **req_options):
        log.error("Error requesting %r (options = %r): %r", name, req_options, e)

    def handle_success_default(self, name, resp, **req_options):
        if resp.document is not None:
            log.debug_s("document body: %r", HTML.tostring(resp.document, pretty_print = True))
        else:
            log.info('Got None for lxml doc. code/status= %r', resp.code, resp.msg, str(resp.headers))

    def preprocess_resp_default(self, name, resp, **req_options):
        data = resp.content
        # Since this is primarily for use with HTML screen-scraping, we're going
        # to use lxml's HTML parser.

        if data:
            document = HTML.fromstring(data, base_url = resp.geturl())
            document.make_links_absolute()
            resp.document = document
        else:
            resp.document = None

        return resp

class AsyncRequestOpener(RequestOpener):
    request_cls = CookieJarHTTPMaster.request_cls
    def _check_success(self, req, resp):
        return super(AsyncRequestOpener, self)._check_success(resp)
    def _check_error(self, req, resp=None):
        if resp == None:
            resp=req
        return super(AsyncRequestOpener, self)._check_error(resp)

class AsyncWebScraper(WebScraperBase):
    HttpOpenerFactory = CookieJarHTTPMaster
#    RequestFactory = staticmethod(CookieJarHTTPMaster.request_cls.make_request)
#    @classmethod
    def RequestOpenerFactory(self, open, req, **kwds):
        return AsyncRequestOpener(open, req, **kwds)

    def init_http(self):
        self._jar = self.CookieJarFactory()
        self.http = self.HttpOpenerFactory(jar=self._jar)

    def RequestFactory(self, *a, **k):
        headers = dict(getattr(self.http, 'addheaders', {}))
        headers.update(k.get('headers', {}))
        k['headers'] = headers
        ret = self.http.request_cls.make_request(*a, **k)
        return ret

WebScraper = AsyncWebScraper

if __name__ == '__main__':
    pass
