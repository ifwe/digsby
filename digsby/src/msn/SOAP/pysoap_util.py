import uuid
import simplejson as json
import logging

import util
log = logging.getLogger('msn.storage')

import msn.SOAP.services as SOAPServices

def extract_zsi_properties(zsiobj):
    return dict((k[1:], v) for k, v in vars(zsiobj).items())

class Serializer(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Serializable):
            d = vars(o).copy()

            for k in d.keys():
                if k in getattr(o, 'nonserialize_attributes', []) or k in ("nonserialize_attributes", "serialize_attributes"):
                    d.pop(k)

            sentinel = object()
            for k in getattr(o, 'serialize_attributes', []):
                if k not in d:
                    v = getattr(o, k, sentinel)
                    if v is not sentinel:
                        d[k] = v

            return d

        if isinstance(o, set):
            return list(o)

        try:
            return json.JSONEncoder.default(self, o)
        except Exception, e:
            log.error("error json encoding %r", o)
            raise e
        return {}

class Serializable(object):
    def __init__(self, **k):
        if not hasattr(self, 'nonserialize_attributes'):
            self.nonserialize_attributes = []
        if not hasattr(self, 'serialize_attributes'):
            self.serialize_attributes = []

        util.autoassign(self, k)

        selfvars = vars(self)
        typevars = vars(type(self))
        for k in typevars:
            if k in selfvars and selfvars.get(k, None) == typevars.get(k, None):
                setattr(self, k, None)

    def serialize(self):
        return json.dumps(self, cls = Serializer)

    @classmethod
    def deserialize(cls, s):
        if isinstance(s, basestring):
            loaded = json.loads(s)
        else:
            loaded = s

        self_dict = {}
        for k, v in loaded.items():
            valtype = vars(cls).get(k, None)
            if valtype is not None:
                v = deserialize_item(valtype, v)

            self_dict[k] = v
        return cls(**self_dict)

    def copy(self):
        return type(self).deserialize(self.serialize())

    def __repr__(self):
        return '%s(**%r)' % (type(self).__name__, json.loads(self.serialize()))

    @classmethod
    def from_zsi(cls, obj, **kwds):
        if obj is None:
            if kwds:
                return cls(**kwds)
            return None

        attrs = extract_zsi_properties(obj)
        attrs.update(kwds)
        return cls(**attrs)

def deserialize_item(valtype, v):
    if v is None:
        return None
    if type(v) in (bool, int, basestring):
        return v
    if type(valtype) is type and issubclass(valtype, Serializable):
        return valtype.deserialize(v)
    elif type(valtype) is list:
        if len(valtype) == 1:
            return [deserialize_item(valtype[0], x) for x in v]
    elif type(valtype) is dict:
        if len(valtype) == 1:
            return dict((k,deserialize_item(valtype[''], v[k])) for k in v)

    return v

class DateAttr(object):
    def __init__(self, attrname):
        self.attrname = attrname

    def __get__(self, obj, objtype = None):
        return getattr(obj, '_' + self.attrname, 0)

    def __set__(self, obj, val):
        if self.attrname not in obj.serialize_attributes:
            obj.serialize_attributes.append(self.attrname)
        if '_' + self.attrname not in obj.nonserialize_attributes:
            obj.nonserialize_attributes.append('_' + self.attrname)

        if isinstance(val, basestring):
            val = SOAPServices.strptime_highres(val)

        setattr(obj, '_' + self.attrname, val)
