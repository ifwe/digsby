from logging import getLogger; log = getLogger('tagged.realtime')
from util import AttrChain
import simplejson
import common.asynchttp as AsyncHttp
from util.callbacks import callsback
from util.net import WebFormData
import TaggedUtil as TU

class TaggedRealtime(AttrChain):
    @property
    def REALTIME_URL(self):
        return 'http://dpush01.tag-dev.com:8001' if TU.TAGGED_DOMAIN() == '.tag-local.com' else 'http://push' + TU.TAGGED_DOMAIN()

    def __init__(self, opener, session_token, user_id):
        AttrChain.__init__(self)
        self.opener = opener
        self.session_token = session_token
        self.user_id = user_id
        log.info('Tagged realtime initialized')

    @callsback
    def __call__(self, method, callback = None, **kwds):
        callargs = {'session_token' : self.session_token,
                    'user_id'       : self.user_id}
        callargs.update(method = method)
        if 'event_types' in kwds:
            kwds['event_types'] = simplejson.dumps(kwds['event_types'])
        callargs.update(kwds)

        req = AsyncHttp.HTTPRequest(self.REALTIME_URL, WebFormData(**callargs), {'X-T-Uid': self.user_id})

        def success(req, resp):
            resp = resp.read()

            # TODO temporary until prod nodeServer gets updated
            if resp.startswith('undefined'):
                resp = resp[10:-2]

            json = simplejson.loads(resp)
            data = json['data']

            if method == 'query_event_id':
                if json['status'] == 'ok':
                    log.info('Realtime initialization successful')
                    callback.success(data)
                else:
                    log.warning('Realtime initialization failed')
                    callback.error()

            elif method == 'register_client':
                if 'success' in json:
                    log.info('Realtime pushed data %r', data)
                    callback.success(data)
                elif data['message'] == 'Authentication failed: Bad session token.':
                    log.warning("We're likely active on a browser, hop on their userObj")
                    callback.error()
                else:
                    log.warning('Realtime register failed %r', data)
                    callback.error()

        self.opener.open(req, success = success, error = callback.error)
