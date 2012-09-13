import stdpaths

import path

import util.net as net
import features.resources as resources

class FeatureSite(resources.YamlResource, resources.LocalOrRemote):

    def __init__(self, name, url, root, version, feature_id, updatesite,**kwds):
        self.id = feature_id
        self.name = name
        self.platform_version = version
        self._localdir = path.path(kwds.get('localdir', stdpaths.userdata / 'features')) / self.platform_version
        self.updatesite = updatesite
        super(FeatureSite, self).__init__(remote = (root, url),
                                          local  = (self._localdir, url))

        self.plugins = {}

    def _repr(self, d = None):
        d = super(FeatureSite, self)._repr(d)
        d['name'] = self.name
        d['platform_version'] = self.platform_version
        d['id'] = self.id

        return d

    def _get_plugin_site_type(self):
        import pluginsite
        return pluginsite.PluginSite

    def get_plugin_site(self, platform, tag):
        if self.content is None:
            return None

        if (platform, tag) in self.plugins:
            return self.plugins.get((platform, tag))

        platform_dict = self.content.get('all').copy()
        platform_dict.update(self.content.get(platform, {}))

        if tag not in platform_dict:
            tag = 'release'

        plugin = self._get_plugin_site_type()(root = self.remote.content_location,
                                              platform = platform,
                                              tag = tag,
                                              url = platform_dict[tag],
                                              platform_version = self.platform_version,
                                              updatesite = self.updatesite,
                                              feature_id = self.id)

        self.plugins[(platform, tag)] = plugin

        return plugin

    def local_dir(self):
        return self._localdir / self.platform_version / self.id

    def local_path(self):
        return self.local_dir() / self.content_location.name

    @classmethod
    def for_feature(cls, feat, meta_filepath = './update.yaml', remote_root = None):
        if feat.feature_id == 'digsby':
            import util
            assert cls is DigsbyFeatureSite
            remote_path = 'http://update.digsby.com/'
            local_path = util.program_dir()
        else:
            remote_path = feat.remote_path
            local_path = feat.local_path

        return cls(
                   feat.feature_id,
                   meta_filepath,
                   remote_path,
                   feat.platform_version,
                   feat.feature_id,
                   localdir = local_path,
                   updatesite = feat.updatesite,
                   )


class DigsbyFeatureSite(FeatureSite):
    def _get_plugin_site_type(self):
        import pluginsite
        return pluginsite.DigsbyPluginSite
