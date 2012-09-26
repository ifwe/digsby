import atexit
import logging
import httplib
import urllib2

import util

_log = log = logging.getLogger('asynchttp')

import connection
import httptypes

__all__ = [
           'HttpMaster',
           'httpopen',
           ]

class HttpMaster(object):
    persister_cls = connection.HttpPersister
    request_cls   = httptypes.HTTPRequest

    @classmethod
    def key(cls, thing):
        if isinstance(thing, (cls.persister_cls, cls.persister_cls.connection_cls)):
            return '%s:%s' % (thing.host, thing.port)

        elif isinstance(thing, cls.request_cls):
            host, o_r_host = thing.get_host(), thing.get_origin_req_host()
            if o_r_host in host:
                if o_r_host != host:

                    pass
                else:
                    host = o_r_host
            url = thing.get_full_url()
            if ':' in host:
                host, port = host.split(':')
            elif url.startswith('https'):
                port = httplib.HTTPS_PORT
            else:
                port = httplib.HTTP_PORT

            return '%s:%s' %  (host, port)
        else:
            raise TypeError("Don't know how to key this object: %r", thing)

    @classmethod
    def host_port(cls, forkey):
        return forkey.split(':')[:2]

    def __init__(self):
        self._conns = {} # key(conn) -> HttpConnection

    def __repr__(self):
        return '<%s with %r active connections (id=0x%x)>' % (type(self).__name__, len(self._conns), id(self))

    @util.callsback
    def request(self, full_url, data=None, *a, **k):
        cb = k.pop('callback')
        if isinstance(full_url, basestring):
            req = self.request_cls.make_request(full_url, data, *a, **k)
        else:
            req = full_url

        self._do_request(req, cb)

    httpopen = open = request

    def _do_request(self, req, cb = None):
        if cb is None:
            cb = req.callback

        conn = self.get_connection(req)
        conn.request(req, callback = cb)

    def get_connection(self, forwhat):
        key = self.key(forwhat)
        try:
            conn = self._conns[key]
        except KeyError:
            conn = self._conns[key] = self._make_connection(key)

        return conn

    def _make_connection(self, key):
        log.info('Making new %r for key=%r', self.persister_cls, key)
        host, s_port = self.host_port(key)
        port = int(s_port)
        conn = self.persister_cls((host,port))
        if hasattr(self, 'password_mgr'):
            conn.password_mgr = self.password_mgr

        self.bind_events(conn)

        return conn

    def add_password(self, realm, uri, username, password):
        if not hasattr(self, 'password_mgr'):
            self.password_mgr = urllib2.HTTPPasswordMgr()

        self.password_mgr.add_password(realm, uri, username, password)

    def bind_events(self, conn):
        bind = conn.bind_event
        bind('on_fail', self._failed_connection)
        bind('redirect', self._handle_redirect)
        bind('on_close', self._handle_close)

    def unbind_events(self, conn):
        unbind = conn.unbind
        unbind('on_fail', self._failed_connection)
        unbind('redirect', self._handle_redirect)
        unbind('on_close', self._handle_close)

    def _handle_redirect(self, req):
        redirect_cb = getattr(req, 'redirect_cb', None)

        #Always call "on_redirect" for side-effects
        newreq = req.on_redirect(req)
        #redirect_cb will be a funciton or None.
        if redirect_cb is not None:
            if newreq is None:
                req.callback.error('redirect cancelled')
                return

            req = newreq

        self._do_request(req)

    def _failed_connection(self, conn):
        log.info('Removing failed connection: conn = %r, key(conn) = %r', conn, self.key(conn))
        self._cleanup(conn)

    def _handle_close(self, conn):
        self._cleanup(conn)

    def _cleanup(self, conn):
        self._conns.pop(self.key(conn), None)
        self.unbind_events(conn)

    def close_all(self):
        while self._conns:
            _key, conn = self._conns.popitem()
            self.unbind_events(conn)
            conn.close()

_httpmaster = HttpMaster()
atexit.register(_httpmaster.close_all)

@util.callsback
def httpopen(*a, **k):
    '''
    @util.callsback
    httpopen(full_url, data=None, callback=None)

    Also accepts (*a, **k) that is passed to the httpmaster's request method.
    '''
    cb = k.pop('callback')
    _httpmaster.request(callback = cb, *a, **k)

def main():
    def success(*a):
        print 'success', a
    def error(*a):
        print 'error', a

    httpopen('http://65.54.239.211/index.html', success = success, error = error)

if __name__ == '__main__':
    from tests.testapp import testapp
    a = testapp()
    main()
    a.MainLoop()

