if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    sys.modules['__builtin__']._ = lambda s: s
    import Digsby

import urllib2
import util
import util.net as net
import util.apitools as apitools
import util.callbacks as callbacks

from contextlib import closing

class TwitPicAPI(object):
    BASE = 'http://twitpic.com/'

    @property
    def API_BASE(self):
        return net.httpjoin(self.BASE, 'api/')

    class TwitPicError(Exception):
        pass

    def get_response_handler(self, method_call, callback):
        def response_handler(resp):
            with closing(resp):
                data = resp.read()
            import lxml.etree as ET
            doc = ET.fromstring(data)
            status = doc.get('stat', doc.get('status'))
            if status == 'ok':
                result = dict((node.tag, node.text) for node in doc.getchildren())
                callback.success(dict((node.tag, node.text) for node in doc.getchildren()))

            else:
                errnode = doc.find('./err')

                ecode = emsg = None
                if errnode is not None:
                    ecode = errnode.get('code')
                    emsg = errnode.get('msg')
                callback.error(self.TwitPicError(ecode, emsg))
        return response_handler

    @callbacks.callsback
    def send_method(self, call, callback = None):
        req = urllib2.Request(call.get_endpoint(self.API_BASE),
                              dict((name, arg.value) for name, arg in call.bound_args.items()),
                              )

        util.threaded(urllib2.urlopen)(req, callback = callback)

    @apitools.apicall('image-noenc', 'data',   'data')
    def upload(self,   media,        username,  password):
        pass

    @apitools.apicall(     'image-noenc',  'data',   'data',     'data')
    def uploadAndPost(self, media,         username,  password,  message = None):
        pass

class YFrogAPI(TwitPicAPI):
    '''
    YFrog.com is literally the same API as twitpic. yay!
    '''
    BASE = 'http://yfrog.com/'

def main():
    tp = util.threadpool.ThreadPool(5)
    api = TwitPicAPI()
    username = u'blahdyblah\u2665'
    password = u'unicodepassword\u2665'
    username = u'digsby01'
    media = urllib2.urlopen('http://antwrp.gsfc.nasa.gov/apod/image/0904/aprMoon_tanga.jpg').read()
    message = u'testing image host thingy'

    def success(resp):
        print 'success'
        print resp

    def error(err):
        print 'ohnoes'
        print err

    api.upload(media, username, password, success = success, error = error)
    tp.joinAll()

if __name__ == '__main__':
    import digsbysite
    main()
