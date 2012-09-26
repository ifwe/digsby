
import os.path
from hashlib import sha1

thisdir = os.path.abspath(os.path.dirname(__file__))

def file_contents(f):
    return open(f, 'rb').read()

class DiskCache(object):
    def __init__(self, cachedir=None):
        if cachedir is None:
            cachedir = os.path.join(thisdir, '.cache')
        self.cachedir = cachedir
        if not os.path.isdir(cachedir):
            os.makedirs(cachedir)

    def cachepath(self, key):
        pth = os.path.abspath(os.path.join(self.cachedir, key))
        return pth

    def get(self, key):
        cachepath = self.cachepath(key)
        if os.path.isfile(cachepath):
            return file_contents(cachepath)

    def set(self, key, value):
        cachepath = self.cachepath(key)
        ensure_dir_exists(cachepath)
        open(cachepath, 'wb').write(value)

def ensure_dir_exists(path):
    dirname = os.path.dirname(path)
    assert not os.path.isfile(dirname)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    assert os.path.isdir(dirname)

_disk_cache = DiskCache()

def sha(*elems):
    return sha1(''.join(elems)).hexdigest()

def _make_cachekey(dirname, hashelems, filename=None):
    path = os.path.join(dirname,
        sha(*hashelems))

    if filename is not None:
        path = os.path.join(path, filename)

    return path


def cache(val_func, dirname, hashelems, filename=None):

    assert callable(val_func)

    cachekey = _make_cachekey(dirname, hashelems, filename)
    val = _disk_cache.get(cachekey)
    if val is None:
        val = val_func()
        _disk_cache.set(cachekey, val)

    pth = _disk_cache.cachepath(cachekey)
    return dict(val=val, path=pth)

