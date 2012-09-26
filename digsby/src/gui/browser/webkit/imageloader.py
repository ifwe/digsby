'''
maintains a hidden webview for loading images

TODO: this could be replaced by exposing a webkit resource loader API to python.
'''

from util.primitives.funcs import Delegate
from util.primitives.refs import better_ref
from gui.browser.webkit.webkitwindow import WebKitWindow
from simplejson import dumps as jsenc
from rpc.jsonrpc import JSPythonBridge
import wx

_imageloader = None # global instance

class LazyWebKitImage(object):
    '''
    an object, given a url and a default image, which has a "lazy_load" function
    which will return a cached image, or start downloading the image, and return it
    at a later call.
    '''

    def __init__(self, url, default_image):
        self.url = url
        self.default_image = default_image

    def lazy_load(self, refresh_cb=None):
        img = None
        if self.url:
            img = load_image(self.url, refresh_cb)
        if img is None:
            img = self.default_image
        return img

def load_image(url, refresh_cb=None):
    global _imageloader
    if _imageloader is None:
        _imageloader = WebKitImageLoader()

    img = _imageloader.get_no_download(url)
    if img is not None:
        return img

    if refresh_cb is not None:
        refresh_cb = better_ref(refresh_cb)

        def unhook():
            _imageloader.on_load -= on_load
            _imageloader.on_error -= on_error

        def on_load(img, src):
            if src == url:
                unhook()
                refresh_cb.maybe_call()

        def on_error(src):
            if src == url:
                unhook()

        _imageloader.on_load += on_load
        _imageloader.on_error += on_error

    return _imageloader.get(url, check_cache=False)

class WebKitImageLoader(object):
    def __init__(self):
        self.webview = None
        self.on_load = Delegate()
        self.on_error = Delegate()

    def _webview_on_call(self, obj):
        method = obj['method']
        src = obj['params'][0]['src']

        if method == 'onLoad':
            img = self.webview.GetCachedBitmap(src)
            self.on_load(img, src)
        elif method == 'onError':
            self.on_error(src)
        else:
            from pprint import pformat
            raise AssertionError('unexpected JS call: ' + pformat(obj))

    def GetWebView(self):
        if self.webview is not None:
            return self.webview

        self.frame = wx.Frame(None)
        w = self.webview = WebKitWindow(self.frame)
        w.js_to_stderr = True

        self.bridge = bridge = JSPythonBridge(self.webview)
        bridge.on_call += self._webview_on_call

        import gui.skin
        jslib = lambda name: jsenc((gui.skin.resourcedir() / 'html' / name).url())

        html = '''<!doctype html>
<html>
    <head>
        <script type="text/javascript" src=%(utils)s></script>
        <script type="text/javascript" src=%(pythonbridgelib)s></script>
        <script type="text/javascript">
function onLoad(img) {
    img.load_state = 'loaded';
    D.notify('onLoad', {src: img.src});
}

function onError(img) {
    img.load_state = 'error';
    D.notify('onError', {src: img.src});
}

function cmp(a, b) {
    if (a < b) return -1;
    else if (b > a) return 1;
    else return 0;
}

function _byTime(a, b) {
    return cmp(a.lastAccessTime, b.lastAccessTime);
}

function evictOld() {
    // TODO: an insertion sort at access time would be more efficient, but this array is small so...eh
    allImages.sort(_byTime);
    var numToDelete = allImages.length - MAX_IMAGES;
    var deleted = allImages.slice(0, numToDelete);
    allImages = allImages.slice(numToDelete);

    for (var i = 0; i < deleted.length; ++i) {
        var img = deleted[i];
        img.parentNode.removeChild(img);
    }
}

window.allImages = [];
window.MAX_IMAGES = 30;

        </script>
    </head>
    <body>
    </body>
</html>''' % dict(pythonbridgelib=jslib('pythonbridge.js'),
                  utils=jslib('utils.js'))

        self.bridge.SetPageSource(html, 'file://imageloader')
        return self.webview

    def get_no_download(self, url):
        # first, see if the image is already in the cache. if so, just return it.
        webview = self.GetWebView()
        img = webview.GetCachedBitmap(url)
        if img.Ok():
            return img

    def get(self, url, check_cache=True):
        if check_cache:
            img = self.get_no_download(url)
            if img is not None:
                return img

        # otherwise, find an existing image tag loading this url, or create one.
        html = '''
(function() {

var img = document.getElementById(%(hashed_url)s);
if (!img) {
    img = document.createElement('img');
    document.body.appendChild(img);
    window.allImages.push(img);
    img.setAttribute('id', %(hashed_url)s);
    img.setAttribute('onLoad', 'onLoad(this);');
    img.setAttribute('onError', 'onError(this);');
    img.src = %(url)s;
} else {
    if (img.load_state === 'loaded')
        onLoad(img);
    else if (img.load_state === 'error')
        onError(img);
}

img.lastAccessTime = new Date().getTime();
if (window.allImages.length > window.MAX_IMAGES)
    evictOld();

})();
    ''' % dict(url = jsenc(url), hashed_url=jsenc(urlhash(url)))

        self.GetWebView().RunScript(html)


import hashlib
def urlhash(url, algo=hashlib.md5):
    return algo(url.encode('utf8')).hexdigest()

def main():
    from tests.testapp import testapp

    app = testapp()
    il = WebKitImageLoader()

    def test_onLoad(img, url):
        print 'onLoad', img, url

    def test_onError(url):
        print 'onError', url

    il.on_load += test_onLoad
    il.on_error += test_onError
    il.get('http://img.digsby.com/logos/digsby_196x196.png')
    il.frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    main()
