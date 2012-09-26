from contextlib import closing
import urllib2

import util
import util.net as net
import util.apitools as apitools
import util.callbacks as callbacks

class TrimApi(object):
    # OPENSOURCE: api key?
    api_key = 'R36NaKwgl6sSnbUePimqMZNC25hTeD2QZ6EEdf7u7zddq6kD'
    BASE = 'http://api.tr.im/'

    @property
    def API_BASE(self):
        return net.httpjoin(self.BASE, 'api/')

    @apitools.apicall('data', name = 'picim_url.json', format = 'json')
    def picim_url(self, media):
        pass

    def get_response_handler(self, method_call, callback):
        if method_call.spec.format == 'json':
            def response_parser(data):
                import simplejson as json
                return json.loads(data)
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
                res = dict((keyval(doc),)).get('trim', {})
                print res
                return res

        def response_handler(resp):
            with closing(resp):
                data = resp.read()

            api_response = response_parser(data)

            callback.success(api_response)

        return response_handler

    @callbacks.callsback
    def send_method(self, call, callback = None):
        url = net.UrlQuery(call.get_endpoint(self.API_BASE), api_key = self.api_key)
        req = urllib2.Request(url,
                              dict((name, arg.value) for name, arg in call.bound_args.items()),
                              )

        util.threaded(urllib2.urlopen)(req, callback = callback)

def main():
    tp = util.threadpool.ThreadPool(5)
    api = TrimApi()
    media = urllib2.urlopen('http://antwrp.gsfc.nasa.gov/apod/image/0904/aprMoon_tanga.jpg').read()

    def success(resp):
        print 'success'
        print resp

    def error(err):
        print 'ohnoes'
        print err

    api.picim_url(media, success = success, error = error)
    tp.joinAll()

if __name__ == '__main__':
    import digsbysite
    main()
