import time
import syck


class Datastore(object):
    sentinel = object()

    def __init__(self, **kwds):
        super(Datastore, self).__init__()

    def get(self, key, default=sentinel):
        raise NotImplementedError

    def __getitem__(self, key):
        return self.get(key)

    def __iter__(self):
        return iter(self.keys())

    def keys(self):
        raise NotImplementedError

    def items(self):
        raise NotImplementedError

    def set(self, key, val=sentinel):
        raise NotImplementedError

    def __setitem__(self, key, value):
        return self.set(key, value)

    def clear(self, key):
        return self.set(key, self.sentinel)

    def create_substore(self, key, data):
        props = vars(self).copy()
        props['data'] = data
        return type(self)(**props)


class DictDatastore(Datastore):
    def __init__(self, data = None, **kwds):
        self.data = data
        super(DictDatastore, self).__init__(data=data, **kwds)

    def get(self, key, default=Datastore.sentinel):
        try:
            super(DictDatastore, self).get(key, default)
        except NotImplementedError:
            pass

        value = self.data.get(key, default)
        if value is self.sentinel:
            raise KeyError(key)
        elif isinstance(value, dict):
            return self.create_substore(key, value)
        else:
            return value

    def set(self, key, val=Datastore.sentinel):
        try:
            super(DictDatastore, self).set(key, val)
        except NotImplementedError:
            pass
        if val is self.sentinel:
            self.data.pop(key)
        else:
            self.data[key] = val

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()


class FileDatastore(Datastore):
    def __init__(self, filepath, **kwds):
        self.filepath = filepath
        self._needsWrite = False
        self._lastRead = -1
        super(FileDatastore, self).__init__(filepath=filepath, **kwds)

    def set(self, key, val=Datastore.sentinel):
        mydefault = object()
        if val == self.get(key, mydefault):
            # Not changing the value, no need to set
            return

        if self._lastRead < self.get_mtime():
            raise Exception("Synchronization error: file was changed on disk and in memory")

        super(FileDatastore, self).set(key, val)
        self._needsWrite = True
        self.write()

    def get(self, key, default=Datastore.sentinel):
        mtime = self.get_mtime()
        if self._needsWrite and self._lastRead < mtime:
            raise Exception("Synchronization error: file was changed on disk and in memory")
        elif self._needsWrite:
            self.write()
        elif self._lastRead < mtime:
            self.read()

        return super(FileDatastore, self).get(key, default)

    def write(self):
        if not self.filepath:
            return
        if not self._needsWrite:
            return

        with open(self.filepath, 'wb') as f:
            self.serialize(f)
        self._lastRead = self.get_mtime()
        self._needsWrite = False

    def read(self):
        if not self.filepath:
            return

        if not self.filepath.isfile():
            self.data = {}
            self._needsWrite = True
            self.write()

        with open(self.filepath, 'rb') as f:
            self.deserialize(f)
        self._lastRead = self.get_mtime()

    def get_mtime(self):
        try:
            return getattr(self.filepath, 'mtime', None)
        except OSError:
            return 0

    def serialize(self, file):
        raise NotImplementedError

    def deserialize(self, file):
        raise NotImplementedError

    def items(self):
        if self._lastRead < self.get_mtime():
            self.read()

        return super(FileDatastore, self).items()

    def keys(self):
        if self._lastRead < self.get_mtime():
            self.read()

        return super(FileDatastore, self).keys()


class AuthenticatedDatastore(Datastore):
    def __init__(self, credentials, **kwds):
        self.credentials = credentials
        super(AuthenticatedDatastore, self).__init__(credentials=credentials, **kwds)


class EncryptingDatastore(Datastore):
    def __init__(self, encrypted_properties, **kwds):
        self.encrypted_properties = encrypted_properties
        super(EncryptingDatastore, self).__init__(encrypted_properties=encrypted_properties, **kwds)

    def get(self, key, default=Datastore.sentinel):
        value = super(EncryptingDatastore, self).get(key, default)
        if key in self.encrypted_properties and value is not default:
            try:
                value = self._decrypt(value)
            except UnicodeDecodeError:
                raise ValueError('Invalid Key')
        elif value is not Datastore.sentinel:
            value = value
        else:
            raise KeyError(key)

        return value

    def set(self, key, val=Datastore.sentinel):
        if key in self.encrypted_properties and val is not self.sentinel:
            val = self._encrypt(val)

        return super(EncryptingDatastore, self).set(key, val)

    def _encrypt(self, val):
        raise NotImplementedError

    def _decrypt(self, val):
        raise NotImplementedError


class DeepDatastore(Datastore):
    def __init__(self, sep='.', prefix=None, **kwds):
        self.sep = sep
        self.prefix = prefix
        super(DeepDatastore, self).__init__(sep=sep, prefix=prefix, **kwds)

    def get_keyparts(self, key):
        if hasattr(key, 'split'):
            keyparts = key.split('.')
        else:
            keyparts = key

        try:
            iter(keyparts)
        except:
            keyparts = (keyparts,)

        return tuple(keyparts)

    def get(self, key, default=Datastore.sentinel):
        keyparts = list(self.get_keyparts(key))

        firstkey = keyparts.pop(0)
        val = super(DeepDatastore, self).get(firstkey, default)
        if val is default:
            if default is Datastore.sentinel:
                raise KeyError
            return default

        if keyparts:
            val.prefix = (firstkey,)
            val = val.get(tuple(keyparts), default)

        return val

    def items(self):
        for k1 in super(DeepDatastore, self).keys():
            k1 = self.get_keyparts(k1)

            self.prefix = k1
            v1 = self.get(k1)
            if isinstance(v1, Datastore):
                for k2, v2 in v1.items():
                    if not isinstance(k2, tuple):
                        k2 = (k2,)
                    yield (k1 + k2, v2)
            else:
                yield (k1, v1)

    def keys(self):
        for k, _v in self.items():
            yield k

    def set(self, key, val=Datastore.sentinel):
        keyparts = list(self.get_keyparts(key))
        firstkey = keyparts.pop(0)

        mydefault = object()
        if keyparts:
            substore = self.get(firstkey, mydefault)
            if substore is mydefault:
                substore = self.create_substore(firstkey, {})

            substore.set(tuple(keyparts), val)
            super(DeepDatastore, self).set(firstkey, substore.data)
        else:
            super(DeepDatastore, self).set(firstkey, val)

    def create_substore(self, key, value):
        props = vars(self).copy()
        props['data'] = value
        props['prefix'] = key
        return type(self)(**props)


class NestedDictDatastore(DeepDatastore, DictDatastore):
    pass


class YAMLDatastore(FileDatastore, NestedDictDatastore):
    def serialize(self, f):
        syck.dump(self.data, f)

    def deserialize(self, f):
        self.data = syck.load(f)

    def create_substore(self, key, value):
        substore = super(YAMLDatastore, self).create_substore(key, value)
        substore.data = value
        #substore.read = self.read
        #substore.write = self.write
        substore.serialize = self.serialize
        substore.deserialize = self.deserialize

        return substore

