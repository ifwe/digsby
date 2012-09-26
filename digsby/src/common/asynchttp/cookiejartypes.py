from .connection import HttpPersister#, AsyncHttpConnection
from .requester import HttpMaster
import urllib2
import cookielib

class CookieJarHttpPersister(HttpPersister):

    def __init__(self, *a, **k):
        self.jar = k.pop('jar', None)
        return super(CookieJarHttpPersister, self).__init__(*a, **k)

    def _make_connection(self):
        conn = super(CookieJarHttpPersister, self)._make_connection()
        conn.add_handler(urllib2.HTTPCookieProcessor(self.jar))
        return conn

class CookieJarHTTPMaster(HttpMaster):
    persister_cls = CookieJarHttpPersister

    def __init__(self, *a, **k):
        self.jar = k.pop('jar', None)
        if self.jar is None:
            self.jar = cookielib.CookieJar()
        return super(CookieJarHTTPMaster, self).__init__(*a, **k)

    @classmethod
    def key(cls, thing):
        return super(CookieJarHTTPMaster, cls).key(thing)

    def _make_connection(self, key):
        conn = super(CookieJarHTTPMaster, self)._make_connection(key)
        conn.jar = self.jar
        return conn
