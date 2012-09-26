import protocols
import gui.skin
import path
import hooks
import time
import stdpaths
import gui.infobox.interfaces as gui_interfaces
from traceback import print_exc
from util.introspect import memoize
from gettext import ngettext
import logging
log = logging.getLogger('infobox.providers')

class FileContext(object):
    resdirs = {}
    def __init__(self, basepath, name):
        self._context_dirs = {}
        self.name = name
        self.base = path.path(basepath).abspath()

    def resource(self, resname, context = 'base'):
        for path in hooks.each('infobox.content.resource', resname):
            if path is not None:
                return path

        dir = self.get_res_dir(context)
        file = dir / resname
        return file.abspath()

    def resourceurl(self, resname, context = 'base'):
        return self.resource(resname, context).url()

    def get_res_dir(self, context):
        '''context can be 'base', 'local', or 'user'''
        return self.get_dir(context)

    def get_dir(self, context):
        '''context can be 'base', 'local', or 'user'''
        if context == 'base':
            pth = self.base

        elif context == 'local':
            pth = stdpaths.config

        elif context == 'user':
            pth = stdpaths.userdata

        else:
            pth = self._context_dirs[context]

        return pth / self.name

    def add_file_context(self, context, dir):
        path_dir = path.path(dir)
        self._context_dirs[context] = path_dir

class AppFileContext(FileContext):
    def get_res_dir(self, context):
        return FileContext.get_res_dir(self, context) / self.resdirs.get(context, 'res')

template_engine = 'tenjin'


if template_engine == 'mako':
    class MakoTemplate(object):
        def __init__(self, dir, fname):
            self.dir = dir
            self.fname = fname

        def generate(self, **context):
            self.context = context
            return self

        def get_template(self, fname):
            import mako.lookup as L
            import mako.template as T
            dirs = [str(self.dir)]
            lookup = L.TemplateLookup(directories = dirs)
            return lookup.get_template(fname or self.fname)

        def render(self, **kwds):
            return self.get_template(self.fname).render_unicode(**self.context)

elif template_engine == 'tenjin':
    import tenjin
    class SafeIncludeEngine(tenjin.Engine):
        def include(self, template_name, *a, **k):
            import sys
            if isinstance(template_name, bytes):
                try:
                    template_name = template_name.decode('utf8')
                except UnicodeDecodeError:
                    template_name = template_name.decode('filesys')

                template_name = template_name.encode('filesys')

            frame = sys._getframe(1)
            locals  = frame.f_locals
            globals = frame.f_globals
            assert '_context' in locals
            _context = locals['_context']
            _buf = locals.get('_buf', None)

            try:
                return tenjin.Engine.include(self, template_name, *a, **k)
            except IOError, e:
                log.error("error performing tenjin include: template_name = %r, a = %r, k = %r, e = %r", template_name, a, k, e)
                return ''

    class TenjinTemplate(object):
        e = None
        def __init__(self, dir, fname):
            self.dir = dir
            self.fname = fname

        def generate(self, **context):
            self.context = context
            return self

        def render(self, **kwds):
            import tenjin
            import tenjin.helpers
            if not self.e:
                self.e = SafeIncludeEngine(preprocess = True, cache = None)
            self.context.update(vars(tenjin.helpers))
            p = self.dir/self.fname
            try:
                return self.e.render(p.encode('filesys'), self.context) #str(path object) == encode filesys, not str+path() (ascii, sometimes)
            except IOError:
                print 'Error loading: %r' % unicode(p)
                return ''

    def get_tenjin_template(dir, file):
        return TenjinTemplate(dir, file)

class InfoboxProviderBase(object):
    javascript_libs = [
                       'jquery',
                       'jquery.hotkeys',
                       'jquery.fullsize',
                       'jquery.lightbox',
                       'jquery.jgrow-singleline',
                       'json',
                       'dateformat',
                       'utils',
                       ]

    protocols.advise(instancesProvide=[gui_interfaces.ICacheableInfoboxHTMLProvider])
    def get_html(self, *a, **k):
        try:
            context = self.get_context()
            context.update(k.get('context', {}))
            self.load_files(context)
            a = time.clock()
            context.setdefault('ngettext', ngettext)
            stream = self.get_template(file=k.get('file'),
                                       loader=k.get('loader'),
                                       dir=k.get('dir'),
                                       ).generate(**context)
            ret = stream.render(method='xhtml', strip_whitespace=context.get('strip_whitespace', True))
            if hasattr(self, 'acct'):
                b = time.clock()
                self.acct.last_gen_time = b - a
#                setattr(self.acct, 'gens', getattr(self.acct, 'gens', []) + [self.acct.last_gen_time])
            return ret
        except Exception:
            print_exc()
            raise

    def load_files(self, context):
        self.platform = context.get('platform')
        self.lib = context.get('lib')
        self.app = context.get('app')

    if template_engine == 'mako':
        def get_template(self, file=None, loader=None, dir=None):
            return MakoTemplate(dir or self.get_dir(), file or 'infobox.mako')

    elif template_engine == 'tenjin':
        def get_template(self, file = None, loader = None, dir = None):
            dir = dir or self.get_dir()
            file = file or 'infobox.tenjin'
            return get_tenjin_template(dir, file)

    elif template_engine == 'genshi':
        def get_template(self, file=None, loader=None, dir=None):
            dir = dir or self.get_dir()
            loader = loader or self.get_loader(dir)
            return loader.load(file or 'infobox.xml')

    def get_dir(self, ):
        if self.platform is None:
            dir = path.path('.').abspath()
        else:
            dir = self.platform.get_res_dir('base')
        return dir

    def get_loader(self, dir=None):
        if dir is None:
            dir = self.get_dir()
        from genshi.template import TemplateLoader
        loader = TemplateLoader(dir)

        return loader

    def get_context(self):
        import util
        platform = FileContext(gui.skin.resourcedir() / 'html', 'infobox') # digsby/infobox stuff
        lib = FileContext(gui.skin.resourcedir(), 'html')
        app = self.get_app_context(AppFileContext) # stuff for the component using the infobox

        ctx = dict(app = app,
                   lib = lib,
                   platform = platform,

                   gui = gui,
                   util = util,
                   javascript_libs = self.javascript_libs)

        hooks.notify('infobox.content.context', ctx, getattr(self, 'acct', None))

        return ctx

