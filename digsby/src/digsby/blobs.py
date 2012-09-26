from __future__ import with_statement
from digsby.abstract_blob import AbstractBlob
import cPickle
from pyxmpp.utils import to_utf8
from copy import deepcopy
from util import Storage
from logging import getLogger; log = getLogger('blobs'); info = log.info
from util.observe import ObservableDict, ObservableList
from struct import pack, unpack
import struct
from os.path import join as pathjoin
from zlib import compress, decompress
import util, syck
import prefs

import common.notifications as comnot

DIGSBY_PREFS_NS         = 'digsby:prefs'
DIGSBY_DEFAULT_PREFS_NS = 'digsby:defaultprefs'
DIGSBY_ICON_NS          = 'digsby:icon'
DIGSBY_EVENTS_NS        = 'digsby:events'
DIGSBY_STATUS_NS        = 'digsby:status'
DIGSBY_BUDDYLIST_NS     = 'digsby:blist'
DIGSBY_PROFILE_NS       = 'digsby:profile'

def to_primitive(thing):
    if isinstance(thing, ObservableDict):
        return dict(thing)
    elif isinstance(thing, ObservableList):
        return list(thing)
    return thing


def maybe_copy(thing):
    if isinstance(thing, (dict, list)):
        return deepcopy(thing)
    return thing

class NetData(AbstractBlob):

    timeout = 300

    @classmethod
    def pack(cls, data):
        return cPickle.dumps(data)

    @classmethod
    def unpack(cls, data):
        return cPickle.loads(data)

    def set_data(self, data):
        try:
            return AbstractBlob.set_data(self, self.pack(data))
        except:
            import sys
            print >> sys.stderr, 'Error pickling %r: %s' % (self, repr(data)[:200])
            print >> sys.stderr, '  %s' % type(data)
            raise

    def get_data(self):
        try:
            retval = self.unpack(AbstractBlob.get_data(self))
            return retval
        except Exception, e:
            import traceback
            traceback.print_exc()

            log.error('Could not unpickle %s', type(self).__name__)
            self.set_data(to_primitive(self.fallback()))
            return self.get_data()

    def del_data(self):
        self._data = None

    data = property(get_data, set_data, del_data)

    def fallback(self):
        return list()

class SerializableNetData(NetData):
    __VERSION = 3

    @classmethod
    def pack(cls, data):
        from util.json import pydumps
        d = pydumps(data).encode('z')
        v = cls.__VERSION
        log.info("packing version %d of %s", v, cls.__name__)
        return pack("!I", v) + d

    @classmethod
    def unpack(cls, data):
        if len(data) < 4:
            # profile strings less than 4 bytes long should be treated as
            # strings
            version = 0
        else:
            (version,) = unpack("!I", data[:4])

        if version not in (1,2,3):
            #assume it was really old and either v0 or had no version
            #(used for converting from NetData to SerializableNetData)
            log.info("unpacking version %d of %s", version, cls.__name__)
            data = pack("I", 1) + data
            version = 1
        if version == 1:
            log.info("unpacking version %d of %s", version, cls.__name__)
            data = data[4:]
            try:
                data = data.decode('z')
            except Exception: pass
        if version == 2:
            log.info("unpacking version %d of %s", version, cls.__name__)
            data = data[4:]
            data = data.decode('z')
        if version != 3:
            d = NetData.unpack(data)
            if isinstance(d, (SerializedDict, SerializedSet)):
                return unserialize(d)
            elif isinstance(d, cls.basetype):
                return d
            else:
                return cls.upgrade(d)
        if version == 3:
            log.info("unpacking version %d of %s", version, cls.__name__)
            from util.json import pyloads
            return pyloads(data[4:].decode('z'))

    @classmethod
    def upgrade(cls, d):
        return cls.basetype(d)

class ODictNetData(NetData):
    fallback = lambda self: ObservableDict()
    basetype = dict

class Prefs(ODictNetData, SerializableNetData):
    xml_element_namespace =  DIGSBY_PREFS_NS

class DefaultPrefs(NetData):
    xml_element_namespace =  DIGSBY_DEFAULT_PREFS_NS
    diskdata = None

    def complete_xml_element(self, xmlnode, _unused):
        xmlnode.newTextChild(None, "time", to_utf8(self.tstamp)) if self.tstamp is not None else None

    def set_data(self, data):
        pass

    def get_data(self):
        if self.diskdata is None:
            defaults = prefs.defaultprefs()
            self.diskdata = defaults
        return self.diskdata


    def del_data(self):
        pass

    data = property(get_data, set_data, del_data)

class BuddyList(ODictNetData, SerializableNetData):
    xml_element_namespace =  DIGSBY_BUDDYLIST_NS

class Statuses(SerializableNetData):
    xml_element_namespace =  DIGSBY_STATUS_NS

    fallback = lambda self: ObservableList()
    basetype = list

class Profile(SerializableNetData):
    xml_element_namespace =  DIGSBY_PROFILE_NS
    basetype = dict
    fallback = lambda self: dict(plaintext='')

    @classmethod
    def upgrade(cls, d):
        # allow upgrading from when profile blobs were just (pickled) strings
        # the code to handle this case is in _incoming_blob_profile
        if isinstance(d, basestring):
            return d

        return cls.basetype(d)

class Icon(NetData):
    xml_element_namespace =  DIGSBY_ICON_NS

    fallback = lambda self: ''

    @classmethod
    def pack(cls, data):
        return data

    @classmethod
    def unpack(cls, data):
        return data


class Notifications(ODictNetData, SerializableNetData):
    xml_element_namespace =  DIGSBY_EVENTS_NS

    fallback = lambda self: deepcopy(comnot.default_notifications)

#
#
#

#to be used for (developer) hacking only
def load_cache_from_data_disk(name, data):
    from StringIO import StringIO
    f = StringIO(data)

    try:
        plen = struct.unpack('!H', f.read(2))[0]
        tstamp = f.read(plen)
        data = f.read()
    except IOError:
        tstamp = '0001-01-01 00:00:00'
        data = None

    #print 'tstamp, data', tstamp, data
    return name_to_obj[name](tstamp, rawdata=data)

#to be used for (developer) hacking only
def load_cache_from_data_db(name, data):
    tstamp = '0001-01-01 00:00:00'
    #print 'tstamp, data', tstamp, data
    return name_to_obj[name](tstamp, rawdata=data)

class SerializedDict(list):
    def __init__(self, dict_):
        self[:] = sorted(dict_.iteritems())

class SerializedSet(list):
    def __init__(self, set_):
        self[:] = sorted(set_)

PrimitiveTypes = frozenset((int, bool, float, long, str, unicode, type(None), type))

def serialize(thing):
    t = type(thing)

    if t in PrimitiveTypes:
        return thing
    elif t is tuple:
        return tuple(serialize(foo) for foo in thing)
    elif t is list:
        return list(serialize(foo) for foo in thing)
    elif issubclass(t, dict):
        bar = SerializedDict(thing)
        bar[:] = [serialize(foo) for foo in bar]
        return bar
    elif t is set:
        bar = SerializedSet(thing)
        bar[:] = [serialize(foo) for foo in bar]
        return bar
    else:
        assert False, (t, thing)

def unserialize(thing):
    t = type(thing)

    if t is SerializedDict:
        return dict(unserialize(foo) for foo in thing)
    elif t is SerializedSet:
        return set(unserialize(foo) for foo in thing)
    elif t is tuple:
        return tuple(unserialize(foo) for foo in thing)
    elif t is list:
        return list(unserialize(foo) for foo in thing)
    elif t in PrimitiveTypes:
        return thing
    else:
        assert False, t

ns_to_obj = {DIGSBY_PREFS_NS : Prefs,
#     DIGSBY_DEFAULT_PREFS_NS : DefaultPrefs,
     DIGSBY_ICON_NS          : Icon,
     DIGSBY_EVENTS_NS        : Notifications,
     DIGSBY_STATUS_NS        : Statuses,
     DIGSBY_BUDDYLIST_NS     : BuddyList,
     DIGSBY_PROFILE_NS       : Profile}

name_to_ns = dict((value.__name__.lower(), key)
                  for (key, value) in ns_to_obj.iteritems())

name_to_obj = dict((name, ns_to_obj[name_to_ns[name]]) for name in name_to_ns)

from util import dictreverse
ns_to_name =dictreverse(name_to_ns)
