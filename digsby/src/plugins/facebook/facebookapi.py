from __future__ import with_statement
from . import fberrors
from .fbutil import signature
from logging import getLogger
from util import AttrChain, default_timer
from util.callbacks import callsback, callback_adapter
from util.primitives.mapping import Ostorage
from util.xml_tag import tag
import common.asynchttp
from common import pref
import simplejson
import time
import traceback
import urllib
import urllib2
S = Ostorage
log = getLogger("facebook.api")

DIGSBY_APP_ID  =                 ''
WIDGET_APP_ID  =                 ''
DIGSBY_ACHIEVEMENTS_APP_ID     = ''
DIGSBY_APP_SECRET =              ''
WIDGET_APP_SECRET =              ''
DIGSBY_ACHIEVEMENTS_APP_SECRET = ''
DIGSBY_API_KEY =                 ''
WIDGET_API_KEY =                 ''
DIGSBY_ACHIEVEMENTS_API_KEY =    ''


class FacebookAPI(AttrChain):
    server_url        = 'http://api.facebook.com/restserver.php'
    secure_server_url = 'https://api.facebook.com/restserver.php'
    facebook_url      = 'http://www.facebook.com/'
    add_app_url       = facebook_url + 'add.php'

    request_limited_at = None

    def __init__(self, api_key, app_id, app_secret, session_key=None, secret=None, uid=None, format='JSON',
                 mode='async', name=None, **_k):
        self.api_key = api_key
        self.app_id = app_id
        self.app_secret = app_secret
        self.session_key = session_key
        self.secret = secret
        self.format = format
        self.mode = mode
        self.name = name

        self.uid = uid

        self.logged_in = bool(session_key and secret and uid)
        self.httpmaster = common.asynchttp.HttpMaster()
        AttrChain.__init__(self, 'facebook')

    def set_session(self, session_json_str):
        for f in (lambda s: s, lambda s: s.decode('url')):
            try:
                session_json_str_decoded = f(session_json_str)
                d = simplejson.loads(session_json_str_decoded)
            except ValueError as e:
                if e.args == ('No JSON object could be decoded',):
                    log.debug('%r', e)
                else:
                    traceback.print_exc()
            except Exception:
                traceback.print_exc()
            else:
                log.info('JSON object successfully decoded')
                log.info_s('%r', d)
                self.uid = int(d['uid'])
                self.session_key = d['session_key']
                self.secret = d['secret']

    def copy(self):
        ret = type(self)(**self.__dict__)
        ret.uid = self.uid
        return ret

    def console(self):
        new = self.copy()
        new.mode = "console"
        return new

    def query(self, query, **k):
        '''
        convenience method for executing fql queries
        '''
        return self.fql.query(query=query, **k)

    @callsback
    def multiquery(self, callback=None, prepare=False, **k):
        return self.fql.multiquery(callback=callback, prepare=prepare, queries=k)

    def set_status(self, status=u''):
        if status:
            assert isinstance(status, unicode)
            self.users.setStatus(status=status.encode('utf-8'),
                                     status_includes_verb = 1)
        else:
            self.users.setStatus(clear=1)

    def _call_id(self):
        return int(time.time()*1000)

    def prepare_call(self, method, **k):
        k['api_key'] = self.api_key.encode('utf-8') #should be ascii already
        k['method'] = method
        k['v'] = '1.0'
        format = self.format
        if format != 'XML':
            k['format'] = format

        k['session_key'] = self.session_key.encode('utf-8') #should be able to .encode('ascii'), but I'd rather not have that error
        k['call_id'] = str(int(self._call_id()))
        assert all(isinstance(val, bytes) for val in k.values())
        k['sig'] = signature(self.secret.encode('utf-8'), **k) # .encode same as session key, they come from webkit/json as unicode
        return urllib.urlencode(k)

    @callsback
    def __call__(self, method, callback=None, prepare=False, **k):
        k = prepare_args(k)
        data = self.prepare_call(method, **k)
        if prepare:
            return data

        if pref('facebook.api.https', False, bool):
            url = self.secure_server_url
        else:
            url = self.server_url
        log.info("calling method: %s", method)
        log.info_s("calling: %s with %r", url, k)
        callback.error += self.handle_error
        if self.mode == 'async':
            return self.call_asynchttp(url, data, callback=callback)
        elif self.mode == 'console':
            return call_urllib2(url, data)
        elif self.mode == 'threaded':
            from util.threads import threaded
            return threaded(call_urllib2)(url, data, callback=callback)
        else:
            return callback_adapter(call_urllib2)(url, data, callback=callback)
        log.info("called method: %s", method)

    def handle_error(self, error):
        if getattr(error, 'code', None) == 4:
            self.request_limited_at = default_timer()

    def request_limited(self):
        if self.request_limited_at is None:
            return False

    def __repr__(self):
        return "<{0.__class__.__name__!s} {0.name!r}>".format(self)

    @callsback
    def call_asynchttp(self, url, data, callback=None):
        return self.httpmaster.open(url, data=data,
                                         headers={'Accept-Encoding': 'bzip2;q=1.0, gzip;q=0.8, compress;q=0.7, identity;q=0.1'},
                                         success=(lambda *a, **k:
                                            callback_adapter(parse_response, do_return=False)(callback=callback, *a, **k)),
                                         error = callback.error,
                                         timeout = callback.timeout)

class DigsbyAPI(FacebookAPI):
    def __init__(self, session_key=None, secret=None, uid=None, format='JSON',
                 mode='async', name=None, **_k):

        FacebookAPI.__init__(self, DIGSBY_API_KEY, DIGSBY_APP_ID, DIGSBY_APP_SECRET,
                             session_key=session_key, secret=secret, uid=uid, format=format,
                             mode=mode, name=name, **_k)

class DigsbyAchievementsAPI(FacebookAPI):
    def __init__(self, session_key=None, secret=None, uid=None, format='JSON',
                 mode='async', name=None, **_k):

        FacebookAPI.__init__(self, DIGSBY_ACHIEVEMENTS_API_KEY, DIGSBY_ACHIEVEMENTS_APP_ID, DIGSBY_ACHIEVEMENTS_APP_SECRET,
                             session_key=session_key, secret=secret, uid=uid, format=format,
                             mode=mode, name=name, **_k)

class WidgetAPI(FacebookAPI):
    def __init__(self, session_key=None, secret=None, uid=None, format='JSON',
                 mode='async', name=None, **_k):

        FacebookAPI.__init__(self, WIDGET_API_KEY, WIDGET_APP_ID, WIDGET_APP_SECRET,
                             session_key=session_key, secret=secret, uid=uid, format=format,
                             mode=mode, name=name, **_k)


def call_urllib2(url, data):
    resp = urllib2.urlopen(url, data=data)
    return parse_response(resp)



PARSE_FUNCS = ((lambda s: simplejson.loads(s, object_hook=storageify)),)# tag_parse)
STR_FUNCS = ((lambda response: response), (lambda response: response.decode('z')))

def parse_response(req, resp=None):
    #call_asynchttp
    if resp is None:
        resp = req
    del req
    if hasattr(resp, 'read'):
        response = resp.read()
        #if not asynchttp:
        if hasattr(resp, 'close'):
            resp.close()
    else:
        #parsing a string directly
        response = resp
        assert isinstance(response, basestring)
    log.info("got response, len:%d", len(response))
    for parse_attempt in PARSE_FUNCS:
        for str_attempt in STR_FUNCS:
            try:
                s = str_attempt(response)
                log.info("string len:%d", len(s))
                if len(s) < 1024:
                    log.info("short response: %r" % s)
                assert log.info("zipped len:%d", len(s.encode('gzip'))) or True
                res = parse_attempt(s)
            except Exception:
                continue
            else:
                break
        else:
            continue
        break
    else:
        raise fberrors.FacebookParseFail('no idea what this data is: %r' % response)

    log.info("parsed response, checking for errors")
    try:
        if isinstance(res, list):
            to_check = res
        else:
            to_check = [res]
        map(check_error_response, to_check)
    except fberrors.FacebookError as e:
        log.debug_s("resp: %r", res)
        log.warning('FacebookError: %r, %r', e, vars(e))
        raise e
    except Exception, e:
        log.warning_s('resp: %r', res)
        log.warning('exception: %r, %r', e, vars(e))
        raise e
    log.info('\tsuccessful request')
    return res

def check_error_response(t):
    #does not simplify, 'in' doesn't work on ints
    if isinstance(t, tag):
        if 'error_code' in t:
            raise fberrors.FacebookError(t)
    elif getattr(t, 'error_code', False):
            raise fberrors.FacebookError(t)
    else:
        error_data = simplejson.loads(getattr(t, 'body', '{}')).get('error', None)
        if error_data is not None:
            raise fberrors.FacebookGraphError(error_data)

def storageify(d):
    if isinstance(d, dict):
        return S(d)
    return d

def prepare_args(d):
    assert type(d) is dict
    ret = dict(d)
    import simplejson as json
    for k,v in d.items():
        if isinstance(v, (list, dict, tuple)):
            ret[k] = json.dumps(v, sort_keys=False, use_speedups=False, separators=(',', ':'))
        else:
            ret[k] = v
    return ret

def simplify_multiquery(multi_result, keys=None):
    if keys is None:
        keys = {}

    assert (not keys) or (len(multi_result) == len(keys))
    res = S()
    for d in multi_result:
        name   = d['name']
        result = d.get('fql_result_set') or d.get('results') or []
        if keys and keys[name] is not None:
            result = db_rows_to_useful(result, keys[name])
        res[name] = result
    return res

def db_rows_to_useful(result, key):
    if key is list:
        return db_rows_to_list(result)
    else:
        return db_rows_to_dict(result, key)

def db_rows_to_list(result):
    res = []
    for row in result:
        assert len(row.values()) == 1
        res.append(row.values()[0])
    return res

def db_rows_to_dict(l, key):
    res = S()
    for row in l:
        row = type(row)(row) #copy
        res[row.pop(key)] = row
    return res
