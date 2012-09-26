import path
import features.resources as resources

distribution_priority = dict(zip = 100, manifest = 90)

class PluginInfo(resources.YamlResource):
    def __init__(self, root, dist_types, meta, id, feature_id, platform_version, updatesite, **kwds):
        self.id = id
        self.feature_id = feature_id
        self.metainfo = meta
        self.dist_types = dist_types
        self.platform_version = platform_version
        self.updatesite = updatesite

        super(PluginInfo, self).__init__(root, meta)

        for k in dist_types:
            setattr(self, k, self.get_di_type()(k, root,
                                                plugin_id = self.id,
                                                feature_id = feature_id,
                                                platform_version = platform_version,
                                                updatesite = updatesite,
                                                **kwds[k]))

    def get_di_type(self):
        return DistributionInfo

    def distribution_list(self):
        return self.dist_types
    def get_distribution(self, name):
        return getattr(self, name, None)

    def get_best_distribution(self):
        best_dist = None
        best_score = -1
        for dist in self.distribution_list():
            dist_score = distribution_priority.get(dist, best_score)
            if  dist_score > best_score:
                best_dist = dist
                best_score = dist_score

        if best_dist is None:
            return None
        return self.get_distribution(best_dist)

class DigsbyPluginInfo(PluginInfo):
    def get_best_distribution(self):
        return self.get_distribution('manifest')
    def get_di_type(self):
        return DigsbyDistributionInfo

class DistributionInfo(resources.RemoteOrLocalCached):
    def __init__(self, dist_type, root, location, plugin_id, feature_id, platform_version, updatesite, **kwds):
        self.dist_type = dist_type
        self._location = location
        self.feature_id = feature_id
        self.name = self.plugin_id = plugin_id
        self.platform_version = platform_version
        self.updatesite = updatesite
        super(DistributionInfo, self).__init__(remote = (root, location),
                                               cache  = self._cache_parts(temp = True),
                                               local  = self._cache_parts(temp = False))
        assert not self.cache.web

        for k in kwds:
            setattr(self, k, kwds[k])

    def _cache_parts(self, temp):

        if self.dist_type == 'zip':
            plugin_dist_file = self.plugin_id + '.zip'
        else:
            plugin_dist_file = self.plugin_id + '/' + path.path(self._location).name

        mypath = root = (resources.default_feature_location(),)
        if temp:
            mypath += ('temp',)

        return mypath + (
                self.platform_version,
                self.feature_id,
                plugin_dist_file,
        )

    def is_installed(self):
        if getattr(self, 'local', None) is None:
            return False

        return self.local.content_location.isfile()

    def update(self):
        getattr(self, 'update_%s' % self.dist_type)()

    def update_manifest(self):
        pass

    def update_zip(self):
        pass

class DigsbyDistributionInfo(DistributionInfo):
    def _cache_parts(self, temp):
        import util
        import digsby_updater.file_integrity as FI
        self._location = './manifest'
        if temp:
            return (FI.GetUserTempDir(), self._location)
        else:
            return (util.program_dir(), self._location)
