from pkg_resources import Distribution, EGG_DIST, PY_MAJOR, EntryPoint

class PluginDistribution(Distribution):
    def __init__(self,
        location=None, metadata=None, project_name=None, version=None,
        py_version=PY_MAJOR, platform=None, precedence = EGG_DIST,
        ep_yaml=None
    ):
        if ep_yaml is None:
            ep_yaml = {}
        self._ep_map = {}

        for group, impl in ep_yaml.items():
            i = {}
            for im, loc in impl.items():
                ep = EntryPoint.parse('%s=%s' % (im, loc), dist=self)
                i[ep.name] = ep
            self._ep_map[group] = i
        Distribution.__init__(self, location, metadata, project_name, version, py_version, platform, precedence)

