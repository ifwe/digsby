import util.primitives.functional as functional
import peak.util.addons
import hooks
import simplejson
from util import Storage

COMBINE_INFOBOX_CSS = False

class JScript(functional.AttrChain):
    def __init__(self):
        self.script = []

    def __call__(self, method, *a, **k):
        assert not k
        callstr = ''.join((method, '(', ', '.join(['%s'] * len(a)), ');'))
        self.script.append(callstr % tuple(simplejson.dumps(arg) for arg in a))

    def js(self):
        return '\n'.join(self.script)

mock_app_context = lambda **k: Storage(resource= lambda *a: Storage(url=lambda *a:''), **k)


def init_host(bridge, baseUrl = 'file:///infoboxapp', protocol=None):
    def get_plugin_head_content():
        return hooks.each('infobox.content.head', protocol)
    plugins = Storage(head=get_plugin_head_content)

    from .providers import InfoboxProviderBase
    class InfoboxAppProvider(InfoboxProviderBase):
        def get_context(self):
            context = InfoboxProviderBase.get_context(self)
            context['plugins'] = plugins
            return context
        def get_app_context(self, context):
            # TODO: fix head.tenjin to include all the permutations of
            # resource loading in a more intelligent way
            return mock_app_context(plugins=Storage(
                head=get_plugin_head_content))

    ip = InfoboxAppProvider()
    app_content = ip.get_html(file='infoboxapp.tenjin')
    bridge.SetPageSource(app_content, baseUrl)

def set_hosted_content(webview, account, infobox_js=None):
    script = JScript()
    key = u'%s_%s' % (account.protocol, account.username)

    from .interfaces import IInfoboxHTMLProvider
    ip = IInfoboxHTMLProvider(account)
    ip.load_files(ip.get_context())
    dir = ip.app.get_res_dir('base')

    dirty = account._dirty
    if dirty:
        new_content = ''
        account.loaded_count = getattr(account, 'loaded_count', 0) + 1
        if not getattr(account, '_did_load_head', False):
            account._did_load_head = True
            new_content += ip.get_html(file='head.tenjin', dir=dir)

        new_content += ip.get_html(file='content.tenjin', dir=dir)

        script.updateContent(key, new_content)
        account._dirty = False

    jsscript = 'callOnHide();\n'

    script.swapToContent(key)

    jsscript += script.js()

    jsscript = SkinMemoizedCssScript(webview).get_css(jsscript)

    # switch our <link rel="stylesheet"> tag to app's infobox.css file
    css_url = simplejson.dumps((dir / 'infobox.css').url())

    jsscript = ('document.getElementById("appCSS").setAttribute("href", %s);\n' % css_url) + jsscript

    # replace $ if we are initializing
    if dirty:

        jsscript += 'clearOnHide();\n'

        if infobox_js is None:
            ijs_file = dir / 'infobox.js'
            if ijs_file.isfile(): infobox_js = ijs_file.bytes()

        infobox_js = infobox_js or ''

        infobox_js += '\n'.join(hooks.each('infobox.content.infoboxjs', account))

        jsscript += ('(function() {if (window.DCallbacks !== undefined) {var D = new DCallbacks(%s);}; %s})();\n' % (simplejson.dumps(key), infobox_js))

        jsscript = 'callWithInfoboxOnLoad(function() {' + jsscript +'});'
        jsscript += '\ncallSwapIn(currentContentName);'

    account.last_script = jsscript
    webview.RunScript(jsscript)

class SkinMemoizedCssScript(peak.util.addons.AddOn):
    def get_css(self, script):
        from common import pref
        skin_tuple = getattr(self, 'skin_tuple', None)
        new_skin_tuple = pref('appearance.skin'), pref('appearance.variant')
        if skin_tuple != new_skin_tuple:
            self.skin_tuple = new_skin_tuple
            import gui
            print 'new css'
            gen_css = gui.skin.get_css()
            script = ('''$('#gen_css').html(%s);''' % simplejson.dumps(gen_css)) + script
        return script

