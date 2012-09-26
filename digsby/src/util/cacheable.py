'''

Easy property caching.


'''

from __future__ import with_statement
__metaclass__ = type

from .introspect import base_classes
import stdpaths
import httplib2
from logging import getLogger; log = getLogger('cacheable'); info = log.info

from os.path import split as pathsplit, exists as pathexists

import os
import sys
import traceback
from zlib import compress, decompress
import cPickle
import simplejson
import syck

try:
    sentinel
except NameError:
    class Sentinel(object):
        def __repr__(self):
            return "<Sentinel (%r backup) %#x>" % (__file__, id(self))
    sentinel = Sentinel()

_cacheattr = '__cached'

def save_cache_object(name, obj, user=False, json=False):
    dumps = simplejson.dumps if json else cPickle.dumps
    croot = get_cache_root(user)
    if not croot.isdir():
        croot.makedirs()

    with open(croot / name, 'wb') as f:
        f.write(compress(dumps(obj)))

def load_cache_object(name, user=False, json=False):
    p = get_cache_root(user) / name

    if not p.isfile():
        return None

    loads = simplejson.loads if json else cPickle.loads
    with open(p, 'rb') as f:
        return loads(decompress(f.read()))

cache_formats = dict(
    json = (simplejson.dumps, simplejson.loads),
    pickle = (cPickle.dumps, simplejson.loads),
    yaml = (syck.dump, syck.load),
)
cache_formats[None] = (lambda x: x, lambda x: x),


class DiskCache(object):
    def __init__(self, name, user = True, format = 'json', compression = 'zip', validator = None):
        self.dumps, self.loads = cache_formats[format]
        self.filename = get_cache_root(user) / name
        self.format = format
        self.compression = compression

        assert validator is None or hasattr(validator, '__call__')

        self.validator = validator

    def remove(self):
        try:
            if self.exists():
                self.filename.remove()
        except Exception:
            traceback.print_exc()

    def exists(self):
        try:
            return self.filename.isfile()
        except Exception:
            traceback.print_exc()
            return False

    def safe_load(self, default_func=lambda:None):
        assert hasattr(default_func, '__call__'), "safe_load takes a callable that should produce a fallback"

        try:
            if self.exists():
                return self.load()
        except Exception:
            traceback.print_exc()

        return default_func()

    def load(self):
        with open(self.filename, 'rb') as f:
            val = f.read()
        try:
            val = val.decode('z')
        except Exception:
            if self.compression is not None: #.decode('z') should be a superset.
                val = val.decode(self.compression)

        obj = self.loads(val)

        if self.validator is not None:
            obj = self.validator(obj)

        return obj

    def save(self, obj):
        try:
            assert self.format is not None or isinstance(obj, bytes)
            val = self.dumps(obj)
            if self.compression is not None:
                val = val.encode(self.compression)
            with open(self.filename, 'wb') as f:
                f.write(val)
        except Exception:
            traceback.print_exc()
            return False
        else:
            return True

        # TODO: validate on save?

    def __repr__(self):
        return '<%s at %r, format=%s>' % (self.__class__.__name__, self.filename, self.format)

def get_cache_root(user=False, username = None):
    root = stdpaths.userlocaldata / 'cache'

    if user:
        from common import profile

        if username is not None:
            name = username
        elif profile:
            name = profile.username
        else:
            name = ''

        root = root / (name + '_cache')

    return root

def get_obj_cache_path(obj, user=False):
    ocp = getattr(obj, 'cache_path', '')
    if not ocp:
        import warnings
        warnings.warn('%r does not have a cache path, you really should give it one.' % obj)

    return get_cache_root(user) / ocp

def clear_file_cache(obj, user=False):
    return os.remove(get_obj_cache_path(obj, user=user))

def load_file_cache(obj, user=False):
    cache_path = get_obj_cache_path(obj, user)

    # If this object has never been cached, return an empty dict
    if not pathexists(cache_path):
        return None

    # Read in, decompress, unpickle, and return.
    with file(cache_path, 'rb') as f:
        return f.read()

def save_file_cache(obj, data, user=False):
    if not getattr(obj, '_disk_cacheable', True):
        return
    cache_path = get_obj_cache_path(obj, user)

    # Ensure that the location for the cache file exists.
    cache_head = pathsplit(cache_path)[0]
    if not pathexists(cache_head):
        os.makedirs(cache_head)

    # Pickle, compress, and write out.
    with file(cache_path, 'wb') as f:
        f.write(data)

class cproperty:
    '''
    A property that saves and loads its value from file.
    '''

    def __init__(self, default = sentinel, box = None, unbox = None, user=False):
        '''
        default becomes this property's default value

        box and unbox, if specified, are one argument functions that serialize
        and unserialize the objects assigned to this attribute.
        '''
        self.default = default

        if box is not None:
            assert unbox is not None
            self.box, self.unbox  = box, unbox
        else:
            self.box = self.unbox = lambda o: o

        self.usermode = user


    def load_cache(self, obj):
        data = load_file_cache(obj, self.usermode)
        if hasattr(obj, 'cache_crypt'):
            if data is not None:
                try:
                    data = obj.cache_crypt[1](data)
                except Exception, e:
                    traceback.print_exc()
                    print repr(data), repr(e)

        try:
            boxed = cPickle.loads( decompress(data) ) if data is not None else {}
        except Exception, e:
            traceback.print_exc()
            boxed = {}

        cache = {}
        error = False
        for k, v in boxed.iteritems():
            try:
                cache.update({k: self.cacheprop(obj, k).unbox(v)})
            except Exception:

                traceback.print_exc()
                error = True

        if error:
            log.warning('error retreiving cache for %s', obj)
            #clear_file_cache(obj, self.usermode)

        #cache = dict((k, self.cacheprop(obj, k).unbox(v)) for k, v in boxed.iteritems())
        setattr(obj, _cacheattr, cache)
        return cache

    def save_cache(self, obj):
        cache = getattr(obj, _cacheattr)
        boxed = dict((k, self.cacheprop(obj, k).box(v)) for k, v in cache.iteritems())
        compressed = compress(cPickle.dumps(boxed))
        if hasattr(obj, 'cache_crypt'):
            compressed = obj.cache_crypt[0](compressed)
        save_file_cache( obj, compressed, self.usermode)

    def __get__(self, obj, objtype):
        cache = getattr(obj, _cacheattr, sentinel)
        if cache is sentinel:
            try: cache = self.load_cache(obj)
            except Exception:
                traceback.print_exc()
                msg = 'error when getting cached attribute %s of %r' % (self.name(objtype), obj)
                print >> sys.stderr, msg
                cache = {}
                #clear_file_cache(obj, self.usermode)

        name = self.name(objtype)
        try:
            val   = cache[name]
        except KeyError:
            try:
                val = self.default()
            except (AttributeError,TypeError):
                val = self.default

            if val is not sentinel:
                cache[name] = val

        if val is sentinel:
            raise AttributeError
        return val


    def name(self, objtype):
        try:
            return self._name
        except:
            bases = [objtype] + base_classes(objtype)

            for clz in bases:
                assert isinstance(clz, type), str(type(clz))
                for k, v in clz.__dict__.iteritems():
                    if v is self:
                        self._name = k
                        return k

        raise AssertionError, str(bases)

    @classmethod
    def cacheprop(cls, objtype, name):
        objtype = objtype.__class__

        try:
            return vars(objtype)[name]
        except:
            bases = base_classes(objtype)

            for base in bases:
                assert isinstance(base, type), str(type(base))
                try:
                    return vars(base)[name]
                except KeyError:
                    pass

        raise AssertionError, 'cannot find %s in %s' % (name, objtype)


    def __set__(self, obj, value):
        cache = getattr(obj, _cacheattr, sentinel)
        if cache is sentinel:
            try:
                cache = self.load_cache(obj)
            except Exception, e:
                traceback.print_exc()
                print >> sys.stderr, 'error loading cache for %r while setting value %s' % (obj, self.name(obj.__class__))
                cache = {}

        cache[self.name(obj.__class__)] = value
        try:
            self.save_cache(obj)
        except Exception, e:
            traceback.print_exc()
            print >> sys.stderr, 'error saving cache for %r while setting value %s' % (obj, self.name(obj.__class__))


    def __delete__(self, obj):
        self.fdel(obj)

def urlcacheopen(url, *a,**k):

    http = httplib2.Http(cache = unicode(get_cache_root() / 'webcache'))
    resp, content = http.request(url, *a, **k)

    log.debug('%s for %s', resp.status, url)

    return resp, content

