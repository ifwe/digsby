from logging import getLogger; log = getLogger('tagged.api')
from util import AttrChain
import simplejson
from util.callbacks import callsback
from util.net import WebFormData
import TaggedUtil as TU

class TaggedApi(AttrChain):
    @property
    def API_URL(self):
        return 'http://www' + TU.TAGGED_DOMAIN()  + '/api/?'

    def __init__(self, opener, session_token):
        AttrChain.__init__(self, 'tagged')
        self.opener = opener
        self.session_token = session_token
        log.info('Tagged api initialized')

    @callsback
    def __call__(self, method, callback = None, **kwds):
        callargs = {'session_token'  : self.session_token,
                    'application_id' : 'user',
                    'format'         : 'json'}
        callargs.update(method = method)
        callargs.update(kwds)

        def success(req, resp):
            resp = resp.read()
            json = simplejson.loads(resp)
            if json['stat'] == 'ok':
                callback.success(json['result'] if 'result' in json else json['results'])
            elif json['stat'] == 'fail':
                raise Exception('API call failed %r', json)
            elif json['stat'] == 'nobot':
                d = {'x*=' : (lambda x, y: x *y),
                     'x-=' : (lambda x, y: x -y),
                     'x+=' : (lambda x, y: x +y),
                     'x=x%' : (lambda x, y: x % y)}

                result = json['result']

                fnc = result['jsfunc'].replace('(function(){var ', '').replace('return x;})()', '')
                init = fnc.split(';')[0]
                rest = fnc.split(';')[1:]
                x = int(init[2:])
                for val in rest:
                    for key in d:
                        if val.startswith(key):
                            y = int(val[len(key):])
                            x = d[key](x, y)

                self.security.nobot.submitAnswer(answer = x,
                                                 origCallObj = simplejson.dumps(result['origCallObj']),
                                                 callback = callback)

        self.opener.open(self.API_URL, WebFormData(**callargs), success = success, error = callback.error)
