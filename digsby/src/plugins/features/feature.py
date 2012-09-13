import syck
import stdpaths

current_platform_version = DIGSBY_1_0_0 = 'digsby-1_0_0'

compatible_platform_versions = (
    current_platform_version,
)

digsby_update_site = 'http://update.digsby.com/'

class Feature(object):
    def __init__(self, feature_id,
                 feature_name = None,
                 platform_version = current_platform_version,
                 updatesite = None,
                 dir = None,
                 **kw):

        self.feature_id = feature_id
        self.feature_name = feature_name
        self.platform_version = platform_version
        self.__dir__ = dir

        for k in kw:
            setattr(self, k, kw[k])

        self._updatesite = updatesite

        self.__fs__ = None

    @property
    def local_path(self):
        p = self.local_root / self.feature_id
        if not p.isdir():
            p.makedirs()

        return p

    @property
    def local_root(self):
        p = (self.__dir__ or stdpaths.userdata) / self.platform_version
        if not p.isdir():
            p.makedirs()
        return p

    @property
    def remote_path(self):
        return self.remote_root + self.feature_id + '/'

    @property
    def remote_root(self):
        us = self.updatesite
        if us.endswith('/'):
            joiner = ''
        else:
            joiner = '/'
        return us + joiner + self.platform_version + '/'

    @property
    def updatesite(self):
        if self._updatesite is None:
            try:
                self._updatesite = syck.load((self.local_path / 'index.yaml').open())['source']
            except Exception:
                raise Exception('Unknown source site for %r', self)

        return self._updatesite

    def get_feature_site(self):
        if self.__fs__ is None:
            import features.featuresite as FS
            if self.feature_id == 'digsby':
                cls = FS.DigsbyFeatureSite
            else:
                cls = FS.FeatureSite
            self.__fs__ = cls.for_feature(self)
        return self.__fs__

    def get_feature_plugins(self):
        import wx

        found_paths = set()

        plugins = []
        for plugin in wx.GetApp().plugins:
            relpath = self.local_path.relpathto(plugin.path)
            split = relpath.splitpath()
            if (len(split) == 2 and split[0] == '') :
                if plugin.path in found_paths:
                    # Some plugins are "multi plugins" that may manifest as several entries in
                    # app.plugins, but we only need to know about them once.
                    continue

                found_paths.add(plugin.path)

                plugin_id = str(relpath.namebase)
                plugins.append(FeaturePlugin(self, plugin_id, plugin.name))

        return plugins

    def __repr__(self):
        return '%s(id = %r, local_path = %r)' % (type(self).__name__, self.feature_id, self.local_path)

class DigsbyFeature(Feature):
    def __init__(self):
        import util
        super(DigsbyFeature, self).__init__('digsby', 'digsby', updatesite = digsby_update_site, dir = util.program_dir())

    def get_feature_plugins(self):
        return [DigsbyFeaturePlugin(self, 'digsby', 'digsby')]

    @property
    def local_path(self):
        return self.local_root

    @property
    def local_root(self):
        p = (self.__dir__ or stdpaths.userdata)
        if not p.isdir():
            p.makedirs()
        return p

class FeaturePlugin(object):
    def __init__(self, feature, plugin_id, plugin_name = None):
        self.feature = feature
        self.plugin_id = plugin_id
        self.plugin_name = plugin_name

    @property
    def feature_id(self):
        return self.feature.feature_id

    @property
    def updatesite(self):
        return self.feature.updatesite

    @property
    def local_path(self):
        return self.feature.local_path / self.plugin_id

    def __repr__(self):
        return '%s(id = %r, feature = %r, local_path = %r)' % (type(self).__name__, self.plugin_id, self.feature_id, self.local_path)

class DigsbyFeaturePlugin(FeaturePlugin):
    @property
    def local_path(self):
        return self.feature.local_path
