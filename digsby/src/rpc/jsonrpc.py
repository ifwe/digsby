import simplejson
import time
import wx.webview
import traceback
from util.primitives.funcs import Delegate
from logging import getLogger
log = getLogger('jsonrpc')

class JSPythonBridge(object):
    def __init__(self, webview):
        self.id_count = 0
        self.callbacks = {} # TODO: expire timeouts
        self.webview = webview
        self.webview.Bind(wx.webview.EVT_WEBVIEW_RECEIVED_TITLE, self.on_before_load)
        self.specifiers = {}
        self.on_call = Delegate()

    def SetPageSource(self, source, baseurl):
        self._update_origin_whitelist(baseurl)
        return self.webview.SetPageSource(source, baseurl)

    def LoadURL(self, url):
        self._update_origin_whitelist(url)
        return self.webview.LoadURL(url)

    def _update_origin_whitelist(self, url):
        # in the future, we may want to whitelist URL for accessing "digsby:"
        # URLS. but for now we just use title changes as a communication channel
        pass

    def on_before_load(self, e):
        url = e.Title
        prefix = 'digsby://digsbyjsonrpc/'
        if not url.startswith(prefix):
            return
        if url == prefix + "clear":
            return

        url = url[len(prefix):]

        if not url.startswith('json='):
            return

        url = url[len('json='):]

        json_data = url.decode('utf8url')
        json_obj = simplejson.loads(json_data)
        self.json(json_obj)
        return True

    def Call(self, call, success = None, error = None, **k):
        assert success is None or hasattr(success, '__call__')
        assert error is None or hasattr(error, '__call__')

        id = self.gen_id()
        self.callbacks[id] = d = dict(success = success,
                                      error = error)
        self.Dcallback(call, id, **k)

    def gen_id(self):
        id = '%s_%s' % (int(time.time()*1000), self.id_count)
        self.id_count += 1
        return id

    def Dcallback(self, method, id, **k):
        args = simplejson.dumps({'params':[{'method':method, 'args':k}], 'method':'callbackCall', 'id':id})
        script = '''Digsby.requestIn(%s);''' % args
        self.evaljs(script)

    def evaljs(self, js):
        assert wx.IsMainThread()
        return self.webview.RunScript(js)

    def register_specifier(self, specifier, func):
        self.specifiers[specifier] = func

    def json(self, json_decoded):
        d = json_decoded
        if 'result' not in d:
            if not self.on_call:
                specifier = d.pop('specifier')
                s = self.specifiers.get(specifier)
                if s is not None:
                    try:
                        return s(d, self)
                    except AttributeError:
                        traceback.print_exc()
            return self.on_call(d)

        cbs = self.callbacks.pop(d.pop('id'))
        if not cbs:
            return
        elif d['error'] is not None:
            assert d['result'] is None
            if cbs['error'] is not None:
                cbs['error'](d['error'])
        elif d['result'] is not None:
            assert d['error'] is None
            if cbs['success'] is not None:
                cbs['success'](d['result'])

    def RunScript(self, script):
        wx.CallAfter(self.webview.RunScript, script)

def Dsuccess(id, webview, **k):
    if not wx.IsMainThread():
        raise AssertionError('subthread called Dsuccess')

    val = simplejson.dumps({'result':[k], 'error':None, 'id':id})
    script = '''Digsby.resultIn(%s);''' % val
    webview.RunScript(script)

def Derror(id, webview, error_obj=None, *a, **k):
    if not wx.IsMainThread():
        raise AssertionError('subthread called Derror')

    if error_obj is None:
        error_obj = "error" #need something, and None/null isn't something.

    val = simplejson.dumps({'result':None, 'error':error_obj, 'id':id})
    script = '''Digsby.resultIn(%s);''' % val
    webview.RunScript(script)


class RPCClient(object):
    _rpc_handlers = {}

    def json(self, rpc, webview):
        method = rpc.get('method')
        args = rpc.get('params')[0]

        if hasattr(args, 'items'):
            kwargs = dict((k.encode('utf8'), v) for k, v in args.items())
            args = ()
        else:
            args = tuple(rpc.get('params', ()))
            kwargs = {}

        try:
            getattr(self, self._rpc_handlers.get(method, '_default_rpc'), self._default_rpc)(rpc, webview, rpc.get('id'), *args, **kwargs)
        except Exception, e:
            import traceback; traceback.print_exc()
            self._rpc_error(rpc, webview, e)

    def _rpc_error(self, rpc, webview, e):
        self.Dexcept(webview, rpc.get('id', 0), "oh noes!")

    def _default_rpc(self, rpc, webview, *a, **k):
        raise Exception("Unknown RPC call: extra args = %r, extra kwargs = %r", rpc, a, k)

    def rpc_hook(self, rpc, webview, id, *args, **kwargs):
        #CAS: yes, this needs to be abstracted.
        import hooks
        hooks.notify(*args, **kwargs)

    def Dsuccess(self, webview, id, **k):
        Dsuccess(id, webview, **k)

    def Dexcept(self, webview, id, response=None, *a, **k):
        self.Derror(webview, id, *a, **k)

    def Derror(self, webview, id, *a, **k):
        Derror(id, webview, error_obj=k.pop('error', k))

