import sys
import config
import util.callbacks as callbacks

@callbacks.callsback
def LoadPluginInfo(
                   feature_id = 'facebook',
                   plugin_id = 'fbchat',
                   site_path = 'http://s3.amazonaws.com/update.digsby.com/',
                   platform_version = 'digsby-1_0_0',
                   tag = 'release',
                   callback = None):

    import features.updatesite as US
    site = US.UpdateSite(site_path, platform_version, 'site.yaml')
    site.load(                                                  success = lambda site:
    site.get_feature_site(feature_id).load(                     success = lambda feature_site:
    feature_site.get_plugin_site(config.platform, sys.TAG).load(success = lambda plugin_site:
    plugin_site.get_plugin_info(plugin_id).load(                success = lambda plugin_info:
    plugin_info.get_best_distribution().load(                   callback = callback),

    error = callback.error),
    error = callback.error),
    error = callback.error),
    error = callback.error)

    return site

@callbacks.callsback
def LoadDigsbyInfo(site_path = 'http://s3.amazonaws.com/update.digsby.com/', callback = None):

    feature_name = 'digsby'

    import features.featuresite as FS
    import features.pluginresource as PR
    import util
    feature_site = FS.DigsbyFeatureSite(feature_name, 'update.yaml', site_path, 'digsby-1_0_0', feature_name,
                                        updatesite = site_path, localdir = util.program_dir())

    def _after_load_feature(*a):
        plugin_site = feature_site.get_plugin_site(config.platform, sys.TAG)

        def _after_load_plugin(*a):
            plugin_site.content = {'plugins':
                                   {feature_name:
                                    {'dist_types': ['manifest'],
                                     'manifest': {'location': plugin_site.remote.content_location},
                                     'meta' : ''}}}

            plugin_info = plugin_site.get_plugin_info(feature_name)
            distribution_info = plugin_info.get_best_distribution()

            #dist_info = feature_site.get_plugin_site('win', 'release').get_plugin_info('digsby').get_distribution('manifest')

            distribution_info.load(callback = callback)

        plugin_site.load(success = _after_load_plugin, error = callback.error)
    feature_site.load(success = _after_load_feature, error = callback.error)
    return feature_site

def find_features(where):
    import path, feature

    features = []
    where = path.path(where)
    for plat_dir in where.dirs():
        if plat_dir.name not in feature.compatible_platform_versions:
            continue

        for feat_dir in plat_dir.dirs():
            feat = feature.Feature(feat_dir.name, platform_version = plat_dir.name, dir = where)
            features.append(feat)

    return features

def find_all_features():
    import stdpaths
    features = []

    import feature
    features.append(feature.DigsbyFeature())

    features.extend(find_features(stdpaths.userdata / 'features'))
    features.extend(find_features(stdpaths.config / 'features'))

    return features

def find_feature_dirs():
    return [feature.local_path for feature in find_all_features()]
