import logging
log = logging.getLogger('features.resources')

import struct
import path
import common.asynchttp as asynchttp
import util.net as net
import util.callbacks as callbacks
import util.primitives.funcs as funcs

def default_feature_location():
    import stdpaths
    return stdpaths.userdata / 'features'

class Resource(object):
    def _repr(self, d = None):
        if d is None:
            d = {}
        d['content_location'] = self.content_location
        if self.has_loaded_content:
            r_content = repr(self.content)
            d['content'] = r_content.strip(r_content[0] if r_content[0] in '"\'' else '')[:250]
        if self._load_callback is not None:
            d['loading'] = True
        d['web'] = self.web

        return d

    def __repr__(self):
        info = self._repr({})
        return '%s(%s)' % (type(self).__name__, ', '.join('%s=%r' % i for i in info.items()))

    def __init__(self, *location_parts, **k):
        self.httpopen = k.pop('httpopen', asynchttp.httpopen)

        location_parts = list(location_parts)

        first = location_parts.pop(0)
        while len(location_parts) > 0:
            next = location_parts.pop(0)

            if next.startswith("http:"):
                first = next
            elif first.startswith("http:"):
                first = net.httpjoin(first, next)
            else:
                # path will handle relative vs. absolute
                first = path.path(first)
                if first.ext:
                    first = first.parent
                first = first / next
                first = first.normpath()

        self.web = first.startswith("http:")
        self.content_location = path.path(first)
        self.content = None
        self._load_callback = None
        self.meta = None

    @property
    def has_loaded_content(self):
        return self.content is not None

    def set_load_callback(self, callback):
        if self._load_callback is not None:
            self._load_callback.success += callback.success
            self._load_callback.error   += callback.error
        else:
            self._load_callback = callback

    @callbacks.callsback
    def load(self, callback = None):
        self.set_load_callback(callback)

        log.info("%r's content_location: %r", self, self.content_location)

        if self.web:
            self._httprequest(success = lambda req, resp: self._content_success(resp),
                              error   = lambda req, err: self._content_error(err))
        else:
            try:
                fobj = self.content_location.open()
            except Exception, e:
                print repr(e)
                self._content_error(e)
            else:
                self._content_success(fobj)

    @callbacks.callsback
    def _httprequest(self, *a, **k):
        self.httpopen(self.content_location, *a, **k)

    @callbacks.callsback
    def get_metadata(self, callback = None):
        if self.meta is not None:
            return callback.success(self.meta)

        if self.web:
            self._httprequest(method = 'HEAD',
                              success = lambda req, resp: self._create_filemeta_from_http(resp, callback = callback),
                              error   = callback.error)
        else:
            try:
                import digsby_updater.file_integrity as file_integrity
                self.meta = file_integrity.FileMeta(self.content_location.name,
                                                    hashes = dict(md5=self.content_location.read_md5().encode('hex')))
            except Exception, e:
                print repr(e)
                callback.error(e)
            else:
                callback.success(self.meta)

    def _create_filemeta_from_http(self, resp, callback):
        headers = resp.headers

        rmtime = headers.get('x-amz-meta-mtime', None)

        if rmtime is None:
            rmtime = headers.get('last-modified', None)
            if rmtime is not None:
                rmtime = net.http_date_to_timestamp(rmtime)

        if rmtime is not None:
            try:
                rmtime = int(rmtime)
            except (TypeError, ValueError):
                rmtime = None


        import digsby_updater.file_integrity as file_integrity
        mtime = file_integrity.MTime()
        mtime._val = rmtime or 0
        hashes = dict(mtime = mtime.hexdigest())

        self.meta = file_integrity.FileMeta(self.content_location.name, hashes = hashes)
        callback.success(self.meta)

    def _content_success(self, fobj):
        log.debug("Got content for %r", self)
        self.content = self.process_data(fobj)

        self._load_callback, cb = None, self._load_callback
        cb.success(self)

    def _content_error(self, e = None):
        log.debug("Got error retrieving content for %r: %r", self, e)
        self._load_callback, cb = None, self._load_callback
        cb.error(self)

    def process_data(self, fobj):
        if isinstance(fobj, basestring):
            return fobj
        else:
            assert hasattr(fobj, 'read')
            return fobj.read()

class YamlResource(Resource):
    def process_data(self, fobj):
        import syck
        return syck.load(super(YamlResource, self).process_data(fobj))

class XmlResource(Resource):
    def process_data(self, fobj):
        import lxml.objectify as objectify
        return objectify.fromstring(getattr(fobj, 'read', lambda:fobj)())

class MultiResource(Resource):
    priority = None
    def __init__(self,
                 **parts):

        for part in parts:
            setattr(self, part, Resource(*parts[part]))

        if self.priority is None:
            self.priority = parts.keys()

        self._load_callback = None

    @property
    def resource(self):
        first = None
        for pri in self.priority:
            res = getattr(self, pri, None)
            if res is None:
                continue
            else:
                if first is None:
                    first = res

            if res.has_loaded_content:
                return res

        return first

    @property
    def content_location(self):
        return self.resource.content_location

    @property
    def web(self):
        return self.resource.web

    def _set_content(self, value):
        self.resource.content = value

    def _get_content(self):
        return self.resource.content

    content = funcs.iproperty('_get_content', '_set_content')

    @property
    def has_loaded_content(self):
        return self.resource.has_loaded_content

    @callbacks.callsback
    def load(self, callback = None):
        self.set_load_callback(callback)
        self._load_pos = 0
        self._try_next_load()

    def _try_next_load(self, *a):
        if self._load_pos < len(self.priority):
            resource = getattr(self, self.priority[self._load_pos])
            self._load_pos += 1
            resource.load(success = self._content_success,
                          error   = self._try_next_load)
        else:
            self._content_error()

    def process_data(self, resource):
        return super(MultiResource, self).process_data(resource.content)

    @callbacks.callsback
    def get_metadata(self, callback = None):
        self._metadata_callback = callback
        self._meta_pos = 0
        self._try_next_meta()

    def _try_next_meta(self, *a):
        if self._meta_pos < len(self.priority):
            resource = getattr(self, self.priority[self._meta_pos])
            self._meta_pos += 1
            resource.get_metadata(success = self._metadata_success,
                                  error   = self._try_next_meta)
        else:
            self._metadata_error()

    def _metadata_success(self, meta):
        log.info("Got metadata for %r: %r", self, meta)
        self.meta = meta
        mcb, self._metadata_callback = self._metadata_callback, None
        if mcb is not None:
            mcb.success(meta)

    def _metadata_error(self, err = None):
        log.info("Error getting metadata for %r: %r", self, err)
        self.meta = None
        mcb, self._metadata_callback = self._metadata_callback, None
        if mcb is not None:
            mcb.error(err)

class LocalOrRemote(MultiResource):
    priority = ['local', 'remote']

class RemoteOrLocal(MultiResource):
    priority = ['remote', 'local']

class LocalOrRemoteYaml(LocalOrRemote, YamlResource):
    pass

class CachedResource(MultiResource):
    @callbacks.callsback
    def load(self, callback = None):
        self.set_load_callback(callback)
        self.get_metadata(success = self.check_metadata,
                          error   = self._content_error)

    def check_metadata(self, meta):
        cache_resource = getattr(self, 'cache', getattr(self, 'local', None))
        if cache_resource is not None:
            if meta.match_local(cache_resource.content_location):
                log.info("Meta info matches cached resource %r", cache_resource)
                self.priority = self.priority[:]
                if 'cache' in self.priority:
                    self.priority.remove('cache')
                self.priority.insert(0, 'cache')
                self.cache = cache_resource
                if cache_resource.has_loaded_content:
                    return self._content_success(cache_resource)
                else:
                    log.info("Loading cached resource %r", cache_resource)
                    return cache_resource.load(success = self._content_success,
                                               error   = self._content_error)

        log.info("Meta data (%r) doesn't match cached resource (%r), loading according to priority", meta, cache_resource)
        super(CachedResource, self).load()

    def process_data(self, content):
        content = super(CachedResource, self).process_data(content)
        self._cache(content)
        return content

    def _cache(self, content, force = False):
        save_resource = getattr(self, 'cache', getattr(self, 'local', None))
        if save_resource is None or save_resource.web:
            return content

        if force or not self.meta.match_local(save_resource.content_location):
            if not save_resource.content_location.parent.isdir():
                save_resource.content_location.parent.makedirs()

            with open(save_resource.content_location, 'wb') as f:
                self.write_content(save_resource.content_location, content)

            if 'mtime' in self.meta.hashes:
                mtime = struct.unpack('!I', self.meta.hashes['mtime'].decode('hex'))[0]
                if mtime is not None:
                    save_resource.content_location.utime((int(save_resource.content_location.atime), mtime))

        if save_resource is not self.local:
            if self.local.content_location.isfile():
                assert save_resource.content_location.read_md5() == self.local.content_location.read_md5()

    def write_content(self, fpath, content = None):
        with open(fpath, 'wb') as f:
            f.write(content or self.content)
#        assert self.meta.match_local(fpath)

class CachedYamlResource(YamlResource, CachedResource):
    def write_content(self, fpath, content = None):
        if isinstance((content or self.content), str):
            super(CachedYamlResource, self).write_content(fpath, content)
        else:
            with open(fpath, 'wb') as f:
                import syck
                syck.dump(content or self.content, f)

class CachedXmlResource(XmlResource, CachedResource):
    def write_content(self, fpath, content = None):
        if isinstance((content or self.content), str):
            super(CachedYamlResource, self).write_content(fpath, content)
        else:
            with open(fpath, 'wb') as f:
                import lxml.etree as etree
                f.write(etree.tostring(content or self.content))

class LocalOrRemoteCachedYaml(LocalOrRemote, CachedYamlResource):
    pass

class RemoteOrLocalCachedXml(RemoteOrLocal, CachedXmlResource):
    pass

class LocalOrRemoteCached(LocalOrRemote, CachedResource):
    pass
class RemoteOrLocalCached(RemoteOrLocal, CachedResource):
    pass

def _main():
    import stdpaths, digsby_updater.file_integrity as file_integrity
    remote = 'http://s3.amazonaws.com/update.digsby.com/update.yaml'
    local = 'c:\\program files (x86)\\digsby\\update.yaml'
    updateyaml = LocalOrRemoteYaml(local = (local,),
                                   remote = (remote,))

    resources = []
    finished = []
    def check_success(res):
        resources.remove(res)
        finished.append(res)
        res.local.content = None
        res.remote.content = None
        if not resources:
            print 'all done'

    def got_manifest(manifest):
        metas = map(file_integrity.FileMeta.from_xml, manifest.content.file)
        for meta in metas:
            res = RemoteOrLocalCached(remote  = (manifest.remote.content_location.parent+'/', meta.path.replace('\\', '/')),
                                      #local  = (manifest.local.content_location.parent, meta.path),
                                      #cache  = (manifest.cache.content_location.parent, meta.path),
                                      local   = (manifest.cache.content_location.parent, meta.path),
                                      )

            res.meta = meta
            if not res.meta.match_local(manifest.local.content_location.parent/meta.path):
                resources.append(res)

        for resource in resources:
            resource.load(success = check_success)

    def get_manifest(uyaml):
        manifest = RemoteOrLocalCachedXml(remote = (updateyaml.content.get('win').get('release'), ),
                                          local  = (updateyaml.local.content_location.parent, 'manifest'),
                                          cache  = (stdpaths.userlocaldata, 'temp', 'manifest'))
        manifest.load(success = got_manifest)

    updateyaml.load(success = get_manifest)

    return resources, finished

if __name__ == '__main__':
    _main()
