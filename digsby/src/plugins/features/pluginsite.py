import util.callbacks as callbacks
import features.resources as resources

class PluginSite(resources.CachedYamlResource):
    def _repr(self, d = None):
        d = super(PluginSite, self)._repr(d)
        d['platform'] = self.platform
        d['tag'] = self.tag

        return d

    def __init__(self, platform, tag, root, url, platform_version, updatesite = None, feature_id = None):
        self.platform = platform
        self.tag = tag
        self.feature_id = feature_id
        self.platform_version = platform_version
        self.root = root
        self.updatesite = updatesite

        super(PluginSite, self).__init__(remote = (root, url),
                                         local  = (resources.default_feature_location(),
                                                  self.platform_version,
                                                  self.feature_id,
                                                  url.rsplit('/', 1)[-1]))

        self.plugins = {}

    def process_data(self, fobj):
        content = super(PluginSite, self).process_data(fobj)
        if isinstance(content, dict):
            content['source'] = str(self.updatesite)
        self._cache(content, force = True)
        return content

    def plugin_list(self):
        if self.content is None:
            return None

        return self.content['plugins'].keys()

    def get_plugin_info(self, pname):
        plugin = self.plugins.get(pname)
        if plugin is None:
            if self.content is None:
                return None
            pdata = self.content['plugins'][pname]

            plugin = self.get_plugin_info_type()(id = pname,
                                                 root = self.remote.content_location,
                                                 feature_id = self.feature_id,
                                                 platform_version = self.platform_version,
                                                 updatesite = self.updatesite,
                                                 **pdata)

            self.plugins[pname] = plugin

        return plugin

    def get_plugin_info_type(self):
        import pluginresource
        return pluginresource.PluginInfo

class DigsbyPluginSite(PluginSite):
    def __init__(self, *a, **k):
        super(DigsbyPluginSite, self).__init__(*a, **k)

        self.content = {'plugins':
                        {'digsby':
                         {'dist_types': ['manifest'],
                          'manifest' : {'location': self.content_location},
                          'meta' : ''}}}

    @callbacks.callsback
    def load(self, callback = None):
        callback.success(self)
    def plugin_list(self):
        return ['digsby']

    def get_plugin_info(self, pname):
        assert pname == 'digsby'
        return super(DigsbyPluginSite, self).get_plugin_info(pname)

    def get_plugin_info_type(self):
        import pluginresource
        return pluginresource.DigsbyPluginInfo

def _main(*args):
    pass

if __name__ == '__main__':
    _main(*sys.args)
