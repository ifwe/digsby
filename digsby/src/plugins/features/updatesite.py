import path
import util.callbacks as callbacks
import common.asynchttp as asynchttp

import features.resources as resources

class UpdateSite(resources.YamlResource):
    index_fname = 'site.yaml'

    def __init__(self, site_root, version, index_fname = None):
        if index_fname is not None:
            self.index_fname = index_fname

        self.version = version
        self.site_root = site_root

        super(UpdateSite, self).__init__(site_root, version+'/', self.index_fname)
        self.features = {}
        self.feature_sites = {}

    def feature_list(self):
        if self.content is None:
            return None
        return self.content['features'].keys()

    def get_feature(self, fname):
        feature = self.features.get(fname)
        if feature is None:
            feature_info = self.content['features'].get(fname)
            if feature_info is None:
                return None
            import feature as F
            feature = F.Feature(fname,
                                feature_info.get('name', None),
                                self.version,
                                updatesite = self.site_root,
                                **feature_info)
            self.features[fname] = feature

        return feature

    def get_feature_site(self, fname):
        fs = self.feature_sites.get(fname)
        if fs is None:
            import featuresite
            feature_info = self.content['features'].get(fname)
            fs = featuresite.FeatureSite(root = self.content_location,
                                         version = self.version,
                                         feature_id = fname,
                                         updatesite = self.site_root,
                                         **feature_info)
#            fs = featuresite.FeatureSite.for_feature(feature, feature.url, remote_root = self.content_location)
            self.feature_sites[fname] = fs

        return fs
