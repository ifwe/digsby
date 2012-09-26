'''
Tools to scan for, find, register, and setup plugins.
'''

from __future__ import with_statement
import traceback
import logging
import config

import util.primitives
import util.data_importer as importers
from contextlib import closing
from util.data_importer import zipopen
from babel.messages.pofile import read_po
from babel.messages.mofile import write_mo
from StringIO import StringIO
import peak.util.plugins as Plugins

from path import path

log = logging.getLogger('plugin_registry')

METAINFO_FILENAME = 'info.yaml'

type_handlers = {}

def register_plugin_default(name, metainfo):
    '''
    Default handler for a discovered plugin.
    '''
    log.error('Not registering type %r because of unknown "type" key (%r). its metainfo is: %r', name, metainfo.get('type', None), metainfo)

def register_type_handler(typename, handler):
    '''
    Sets 'handler' as the callable for plugins with type == typename. 'handler' should be a callable
    that takes two arguments, (str name, mapping metainfo)
    '''
    old_handler = type_handlers.get(typename, None)
    if old_handler is not None:
        log.warning('Overwriting handler for type %r: was %r, now %r', typename, old_handler, handler)

    type_handlers[typename] = handler

def get_type_handler(typename):
    '''
    Returns the handler for 'typename', or the default handler if none is registerd.
    '''
    try:
        return type_handlers[typename]
    except KeyError:
        return register_plugin_default

def type_handler(typename):
    '''
    Decorator to mark a function as the type handler for 'typename'
    '''
    def register_handler(f):
        register_type_handler(typename, f)
        return f
    return register_handler

def register_type(name, metainfo):
    '''
    str name:         name of the plugin, ex: 'oscar', 'nowplaying'
    mapping metainfo: information about the plugin, ex: {'type' : 'im', 'shortname' : 'aim'}
    '''
    # TODO: move protocolmeta.protocols to this module and get rid of protolmeta?
    # use this as a central hub for all protocol meta info.
    # XXX: what should we do with functions like is_compatible and things like that from
    # protocolmeta?

    a_type = metainfo.get('type', None)
    if a_type is None:
        log.error('Not registering type %r because it did not have a "type" key. its metainfo is: %r', name, metainfo)
        return
    else:
        platforms = metainfo.get('platforms', None)
        if platforms is None or config.platformName in platforms:
            PluginType = get_type_handler(a_type)

            # TODO: store these things somewhere?
            plugin = PluginType(metainfo.__file__.parent, metainfo)
            plugin.init()

            return plugin

class PluginLoader(object):
    def __init__(self, dirpath, metainfo):
        self.path = dirpath
        self.shortname = metainfo.get('shortname', self.path.name)
        self.info = metainfo


    def init(self):
        self.name = self.info.name

        self.init_skin()
        self.init_notifications()
        self.init_actions()

        log.info('registered plugin type: %r', self.name)

    def init_skin(self):
        # self.skin contains transformed data with paths made relative to the
        # plugin's directory, while
        # self.info.skin contains the "raw info" from the plugin's metadata.
        #
        # when looking up skin values, you should really use self.skin
        self.skin = self.resolve_paths(self.get_component('skin'))

    def resolve_paths(self, d):
        '''recursively transform any string leafs in a mapping into paths
        relative to this plugin's directory, if those paths exist.'''

        if not isinstance(d, dict):
            return d
        ret = {}
        for k,v in d.items():
            if isinstance(v, basestring):
                pth = self.path / v
                if pth.isfile() or pth.isdir():
                    v = pth
            elif isinstance(v, dict):
                v = self.resolve_paths(v)
            ret[k] = v
        return ret

    def init_actions(self):
        actions = self.get_component('actions')
        if actions is None:
            return

        import common.actions
        common.actions.add_actions(actions)

    def init_notifications(self):
        nots = self.get_component('notifications')

        if nots is None:
            return

        import common.notifications as n
        #import gui.skin.skintransform as gst
        #nots.notifications = map(lambda x: gst.transform(x, False), nots.notifications)

        defaults = {}
        for d in nots:
            for k in d:
                not_ = d[k]
                default = not_.get('default', {})
                default_reactions = [{'reaction' : reaction} for reaction in default.get('reaction', [])]
                defaults[k.replace('_','.')] = default_reactions

        n.add_notifications(nots)
        n.add_default_notifications(defaults)
        self.set_component('notifications', nots)

    def get_component(self, attr, yamlname = None):
        attempts = [
                    lambda: getattr(self, attr, None),
                    lambda: getattr(self.info, attr, None),
                    lambda: getattr(self.yaml_load(yamlname or attr), '__content__', None),
                    ]

        for attempt in attempts:
            thing = attempt()
            if thing is not None:
                break
        else:
            return None

        self.set_component(attr, thing)
        return thing

    def set_component(self, attr, thing):
        setattr(self, attr, thing)
        setattr(self.info, attr, thing)

    def yaml_load(self, yamlname):
        try:
            return importers.yaml_import(yamlname, loadpath = [self.path])
        except ImportError:
            return None

    def load_entry_points(self):
        """Connects plugin entry points defined in info.yaml"""

        import pkg_resources
        from .plugin_resources import PluginDistribution
        import config as digsbyconfig
        platforms = self.get_component('platforms')
        if platforms is None or digsbyconfig.platformName in platforms:
            pkg_resources.working_set.add(PluginDistribution(location = str(self.path.parent),
                                                             project_name = self.info.name,
                                                             ep_yaml = self.get_component('entry_points')))

    def __repr__(self):
        return "<%s %r>" % (type(self).__name__, self.name)

class ProtocolPluginLoader(PluginLoader):
    def init(self, dictnames = None):
        PluginLoader.init(self)
        self.init_info(dictnames)

    def init_info(self, dictnames = None):
        import common.protocolmeta as pm

        plugin_info = util.primitives.mapping.Storage(self.info)

        if dictnames is not None:
            for dictname in dictnames:
                d = getattr(pm, dictname, None)
                if d is not None:
                    d[self.shortname] = plugin_info

        pm.protocols[self.shortname] = plugin_info

@type_handler('im')
class IMProtocolPluginLoader(ProtocolPluginLoader):
    def init(self):
        return ProtocolPluginLoader.init(self, ['improtocols'])

@type_handler('email')
class EmailProtocolPluginLoader(ProtocolPluginLoader):
    def init(self):
        return ProtocolPluginLoader.init(self, ['emailprotocols'])

@type_handler('social')
class SocialProtocolPluginLoader(ProtocolPluginLoader):
    def init(self):
        result = ProtocolPluginLoader.init(self, ['socialprotocols'])
        self.load_entry_points()
        return result

@type_handler('meta')
class MetaProtocolPluginLoader(ProtocolPluginLoader):
    def init(self):
        return ProtocolPluginLoader.init(self)

@type_handler('platform')
@type_handler('pure')
class PurePluginLoader(PluginLoader):
    def init(self):
        self.load_entry_points()
        super(PurePluginLoader, self).init()

@type_handler('multi')
class MultiPluginLoader(PurePluginLoader):
    def init(self):
        self.plugins = []
        plugin_dicts = self.info['plugins']
        for name, plugin in plugin_dicts.items():
            plugin_obj = register_type(name, plugin)
            if plugin_obj is not None:
                self.plugins.append(plugin_obj)
        super(MultiPluginLoader, self).init()


@type_handler("service_provider")
class ServiceProviderPlugin(PurePluginLoader):
    def init(self):
        res = super(ServiceProviderPlugin, self).init()
        self.type = self.info.type
        self.name = self.info.name
        self.provider_id = self.info.provider_id

        return res

@type_handler("service_component")
class ServiceComponentPlugin(ProtocolPluginLoader):
    def init(self):
        pm_key = {
                  'social' : 'socialprotocols',
                  'email'  : 'emailprotocols',
                  'im'     : 'improtocols',
                  }.get(self.info.component_type, None)

        dictnames = []
        if pm_key is not None:
            dictnames.append(pm_key)
        result = ProtocolPluginLoader.init(self, dictnames)
        self.load_entry_points()
        self.service_provider = self.provider_id = self.info.service_provider
        self.component_type = self.info.component_type
        return result

@type_handler('lang')
class LangPluginLoader(PurePluginLoader):
    def init(self):
        super(LangPluginLoader, self).init()
#
    def get_catalog(self):
        if self.info.get('catalog_format') == 'po':
            return self.get_po_catalog()
        return self.get_mo_catalog()

    @property
    def file_base(self):
        return self.path / (self.info['domain'] + '-' + self.info['language'])

    def get_mo_catalog(self):
        with closing(zipopen(self.file_base + '.mo')) as f:
            return StringIO(f.read())

    def get_po_catalog(self):
        cat = StringIO()
        with closing(zipopen(self.file_base + '.po')) as f:
            po = read_po(f)
            write_mo(cat, po)
            cat.seek(0)
            return cat

pkg_dirs = set()

def scan(dirname):
    '''
    Search 'dirname' for .zip, .egg, or directories with an info.yaml.
    for each found, loads the plugin info and calls register_type with
    the discovered name and information.
    '''
    root = path(dirname)
    plugins = []
    for pkg_dir in root.dirs() + root.files('*.zip') + root.files('*.egg'):
        name = pkg_dir.namebase
        if exclude_dir(name):
            continue

#        sys.path.append(pkg_dir)
        try:
            plugin = _load_plugin_info_from_item(pkg_dir)

            if plugin is None:
    #            sys.path.remove(pkg_dir)
                log.info("No protocol info found in %r", pkg_dir)
            else:
                pkg_dirs.add(pkg_dir.abspath())
                ret = register_type(name, plugin)
                if ret is None:
                    continue

                plugins.append(ret)
                if hasattr(ret, 'plugins'):
                    plugins.extend(ret.plugins)
        except Exception:
            traceback.print_exc()

    return plugins

def exclude_dir(dirname):
    return dirname.startswith('.')

def _load_plugin_info_from_item(pkgdir):
    '''
    Tries really hard to load the plugin info from the specified item.
    '''

    try:
        return importers.yaml_import('info', loadpath = [pkgdir])
    except ImportError:
        try:
            return importers.yaml_load(pkgdir / 'info.yaml')
        except Exception:
            return None

def plugins_skintrees():
    'All info.yamls can define a "skin:" section that gets merged with the skin tree.'

    import wx
    plugins = wx.GetApp().plugins

    trees = []
    for plugin in plugins:
        skin = plugin.get_component('skin') or None
        if skin is not None:
            trees.append(skin)

    return trees

def plugins_skinpaths():
    'Returns paths images for plugins can be loaded from.'

    return list(pkg_dirs) # todo: limit skin lookups for plugins to their own res/ directory

Plugins.Hook('digsby.skin.load.trees', 'plugins_skin').register(plugins_skintrees)
Plugins.Hook('digsby.skin.load.skinpaths', 'plugins_skin').register(plugins_skinpaths)

if __name__ == '__main__':
    import wx
    a = wx.App()
    logging.basicConfig()
    log.setLevel(1)
    scan('c:\\workspace\\digsby\\src\\plugins')

