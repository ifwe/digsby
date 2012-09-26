'''
Created on Apr 9, 2012

@author: Christopher
'''

from util.net import UrlQuery
from facebook.facebookapi import DIGSBY_APP_ID
from facebook.fbconnectlogin import LOGIN_SUCCESS_PAGE
from util.primitives.functional import AttrChain
from util.callbacks import callsback, callback_adapter
import common.asynchttp
from facebookapi import parse_response
from facebook.facebookapi import prepare_args
from facebook.facebookapi import call_urllib2
from logging import getLogger
import time
import urllib
log = getLogger("graphapi")


def build_oauth_dialog_url(perms=None):
    params = dict(client_id=DIGSBY_APP_ID,
                  redirect_uri=LOGIN_SUCCESS_PAGE,
                  response_type='token',
                  display='popup')
    if perms is not None:
        params['scope'] = ','.join(perms)
    return UrlQuery('https://www.facebook.com/dialog/oauth/?',
                    **params)


class GraphAPI(AttrChain):
    graph_http = 'https://'
    graph_endpoint = 'graph.facebook.com'
    legacy_endpoint = 'api.facebook.com/method'

    def __init__(self, access_token=None, *a, **k):
        self.access_token = access_token
        self.logged_in = False
        self.mode = 'async'
        self.httpmaster = common.asynchttp.HttpMaster()
        super(GraphAPI, self).__init__(*a, **k)

    def copy(self):
        ret = type(self)(**self.__dict__)
        ret.uid = self.uid
        return ret

    def console(self):
        new = self.copy()
        new.mode = "console"
        return new

    @callsback
    def _do_call(self, endpoint, method, callback=None, **k):
        k = prepare_args(k)
        if self.access_token:
            k['access_token'] = self.access_token.encode('utf8')
        url = UrlQuery(self.graph_http + endpoint + '/' + method, **k)
        log.info("calling method: %s", method)
        log.info_s("calling: %s with %r", url, k)
        if self.mode == 'async':
            return self.call_asynchttp(url, None, callback=callback)
        elif self.mode == 'console':
            return call_urllib2(url, None)
        elif self.mode == 'threaded':
            from util.threads import threaded
            return threaded(call_urllib2)(url, None, callback=callback)
        else:
            return callback_adapter(call_urllib2)(url, None, callback=callback)

    def _call_id(self):
        return int(time.time() * 1000)

    @callsback
    def batch(self, *a, **k):
        callback = k.pop('callback')
        k['batch'] = list(a)
        k = prepare_args(k)
        if self.access_token:
            k['access_token'] = self.access_token.encode('utf-8')
        url = UrlQuery(self.graph_http + self.graph_endpoint)
        data = self.prepare_values(k)
        if self.mode == 'async':
            return self.call_asynchttp(url, data, callback=callback)
        elif self.mode == 'console':
            return call_urllib2(url, data)
        elif self.mode == 'threaded':
            from util.threads import threaded
            return threaded(call_urllib2)(url, data, callback=callback)
        else:
            return callback_adapter(call_urllib2)(url, data, callback=callback)

    def prepare_call(self, method, **k):
        k['api_key'] = DIGSBY_APP_ID
        k['method'] = method
        k['v'] = '1.0'
        #new
        k['access_token'] = self.access_token.encode('utf-8')
        k['call_id'] = str(self._call_id())
        k = prepare_args(k)
        return self.prepare_values(k)

    def prepare_values(self, k):
        assert all(isinstance(val, bytes) for val in k.values())
        return urllib.urlencode(k)

    @staticmethod
    def GET(relative_url):
        return dict(method='GET', relative_url=relative_url)

    @callsback
    def __call__(self, method, callback=None, **k):
        #TODO: make this not a hack
        if method.endswith('legacy'):
            method = method[:-(len('legacy') + 1)]
            endpoint = self.legacy_endpoint
        else:
            endpoint = self.graph_endpoint
        return self._do_call(endpoint=endpoint,
                             method=method,
                             callback=callback,
                             **k)

    def query(self, query, **k):
        '''
        convenience method for executing fql queries
        '''
        return self.fql.query(query=query, **k)

    @callsback
    def multiquery(self, callback=None, **k):
        assert self.access_token
        return self.fql.multiquery(callback=callback, queries=k)

    @callsback
    def call_asynchttp(self, url, data, callback=None):
        return self.httpmaster.open(url, data=data,
                                         headers={'Accept-Encoding': 'bzip2;q=1.0, gzip;q=0.8, compress;q=0.7, identity;q=0.1'},
                                         success=(lambda *a, **k:
                                            callback_adapter(parse_response, do_return=False)(callback=callback, *a, **k)),
                                         error = callback.error,
                                         timeout = callback.timeout)


class LegacyRESTAPI(GraphAPI):

    @callsback
    def __call__(self, method, callback=None, **k):
        k['format'] = 'JSON'
        endpoint = self.legacy_endpoint
        return self._do_call(endpoint=endpoint,
                             method=method,
                             callback=callback,
                             **k)
