from contextlib import closing
import urllib2

import util
import util.net as net
import util.apitools as apitools
import util.callbacks as callbacks

class ImgurApi(object):
    # OPENSOURCE: api key?
    api_key = '086876da7b51c619ffddb16eaca51400'
    BASE = 'http://imgur.com/'

    @property
    def API_BASE(self):
        return net.httpjoin(self.BASE, 'api/')

    @apitools.apicall('data', name = 'upload', format = 'json')
    def upload(self, image):
        pass

    def get_response_handler(self, method_call, callback):
        if method_call.spec.format == 'json':
            def response_parser(data):
                import simplejson as json
                return {'url' : json.loads(data)['rsp']['image']['imgur_page']}
        else:
            def response_parser(data):
                import lxml.etree as ET
                doc = ET.fromstring(data)

                def keyval(node):
                    if node.text and node.text.strip():
                        return (node.tag, node.text.strip())
                    elif node.getchildren():
                        return (node.tag, dict(map(keyval, node.getchildren())))
                    elif node.attrib:
                        return (node.tag, dict(node.attrib))

                print data
                res = dict((keyval(doc),)).get('rsp', {})
                print res
                return res

        def response_handler(resp):
            try:
                with closing(resp):
                    data = resp.read()
                api_response = response_parser(data)
            except Exception as e:
                return callback.error(e)
            else:
                callback.success(api_response)

        return response_handler

    @callbacks.callsback
    def send_method(self, call, callback = None):
        url = net.UrlQuery(call.get_endpoint(self.API_BASE) + '.' + call.spec.format)
        params = dict((name, arg.value) for name, arg in call.bound_args.items())
        params['key'] = self.api_key
        req = urllib2.Request(url, params)

        util.threaded(urllib2.urlopen)(req, callback = callback)
