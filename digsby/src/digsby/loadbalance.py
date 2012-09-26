import simplejson
import sys
import util.net as net
import urllib2
from util.primitives import funcs
from operator import itemgetter
import random
import util.callbacks as callbacks
import util.threads as threads
import common.asynchttp

from logging import getLogger
log = getLogger('loadbalance')

class DigsbyLoadBalanceAPI(object):
    __version__ = (1, 0)
    def __init__(self, profile, username, host="login1.digsby.org", port=80, mode='async', initial=None, **_k):
        self.profile = profile
        self.username = username
        self.host = host
        self.port = port
        self.mode = mode
        self.httpmaster = common.asynchttp.HttpMaster()
        self.initial = initial

    def copy(self):
        ret = type(self)(**self.__dict__)
        return ret

    @property
    def console(self):
        new = self.copy()
        new.mode = "console"
        return new

    @property
    def stringversion(self):
        return '.'.join(['%d']*len(self.__version__)) % self.__version__

    @callbacks.callsback
    def get(self, callback=None, **k):
        version = self.stringversion

        from gui.native.helpers import GetUserIdleTime
        from AccountManager import SECONDS_FOR_IDLE
        idle = GetUserIdleTime() > (1000 * SECONDS_FOR_IDLE)

        local_load_exc = getattr(self.profile, 'local_load_exc', None)
        log.debug('loaded: %s initial: %s', local_load_exc, self.initial)
        have_acct_data = not bool(local_load_exc)
        button_clicked = bool(self.initial)
        log.debug('have_data: %s button_clicked: %s', have_acct_data, button_clicked)
        if button_clicked and not have_acct_data:
            state = 'initial_nocache'
        elif button_clicked:
            state = 'initial'
        elif idle:
            state = 'reconnect_idle'
        else:
            state = 'reconnect'

        url = net.UrlQueryObject('http://%s:%s/load/all/json' % (self.host, self.port),
                                   revision = getattr(sys, 'REVISION', 'unknown'),
                                   tag      = getattr(sys, 'TAG',      'unknown'),
                                   username = self.username,
                                   version = version,
                                   state = state,
                                   v = version,
                                   **k)
        log.debug('calling loadbalance URL: %s', url)
        if self.mode == 'async':
            return self.call_async(url, callback=callback)
        elif self.mode == 'console':
            return self.get_urllib(url)
        elif self.mode == 'threaded':
            return threads.threaded(self.get_urllib)(url, callback=callback)
        else:
            return callbacks.callback_adapter(self.get_urllib)(url, callback=callback)

    def get_urllib(self, url):
        res = urllib2.urlopen(url)
        return self.clean(res.read())

    @callbacks.callsback
    def call_async(self, url, callback=None):
        return self.httpmaster.open(url,
                                 success=(lambda *a, **k:
                                 callbacks.callback_adapter(self.parse_response, do_return=False)(callback=callback, *a, **k)),
                                 error = callback.error,
                                 timeout = callback.timeout)

    def parse_response(self, _req, resp):
        if hasattr(resp, 'read'):
            response = resp.read()
            #if not asynchttp:
            if hasattr(resp, 'close'):
                resp.close()
        else:
            raise TypeError('failed to parse: %r', resp)
        return self.clean(response)

    def clean(self, val):
        log.debug("Got loadbalance result data: %r", val)
        info = simplejson.loads(val)
        if not isinstance(info, dict):
            return self.clean_0_0(val)
        return getattr(self, 'clean_%s' % info['version'].replace('.', '_'))(info)

    def clean_0_0(self, val):
        info = simplejson.loads(val)
        return DigsbyLoadBalanceInfo(nodes = info)

    def clean_1_0(self, info):
        info['version'] = map(int, info['version'].split('.'))
        return DigsbyLoadBalanceInfo(**info)


class DigsbyLoadBalanceInfo(object):
    def __init__(self, nodes = None, reconnect_strategy = None, version = (0, 0), **k):
        self.nodes = nodes
        self.state = k.get('state', None)
        self.reconnect_strategy = reconnect_strategy
        self.version = version

    @property
    def addresses(self):
        if not self.nodes:
            return None
        else:
            grouped = dict(funcs.groupby(self.nodes, itemgetter('load')))
            sorts   = sorted(grouped.items())
            addresses = []
            for _load, hosts in sorts:
                addys = []
                for host in hosts:
                    addys.extend(host.get('addresses', []))
                random.shuffle(addys)
                addresses.extend(addys)
            addresses = [a.encode('idna') for a in addresses]
            return addresses or None

    def __repr__(self):
        return "<%(name)s version:%(version)s state:'%(state)s' reconnect_strategy:%(reconnect_strategy)r nodes:%(nodes)r>" % dict(name = type(self).__name__, **self.__dict__)


class DigsbyLoadBalanceManager(object):
    def __init__(self, profile, username, servers, success, error, timeout=None, load_server=None, initial=None):
        self.servers = servers
        self.pos = 0
        self.success = success
        self.error = error
        self.timeout = timeout
        self.username = username
        self.load_server = load_server
        self.profile = profile
        self.initial = initial

    def process_one(self):
        if self.pos >= len(self.servers):
            return self.error(self)
        h,p = self.servers[self.pos]
        api = DigsbyLoadBalanceAPI(profile = self.profile, username=self.username, host=h, port=p, mode = 'async', initial = self.initial)
        api.get(success = self.response, error = self.api_error)

    def response(self, val):
        self.success(self, val)

    def api_error(self, *_a, **_k):
        self.pos += 1
        self.process_one()

if __name__ == '__main__':
    print DigsbyLoadBalanceAPI('foo', host='192.168.99.71', mode='console').get()
