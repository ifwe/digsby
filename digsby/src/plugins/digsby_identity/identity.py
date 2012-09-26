import time
import path
import random
import hashlib
import simplejson

import common
import stdpaths

import util.cryptography as crypto
import util.primitives.files as files
import digsby.blobs as blobs
import digsby.accounts as accounts
import digsby.digsbylocal as digsbylocal
from util.json import pyloads, pydumps


class Identity(object):
    softcrypt_salt = 'digsby-softcrypt'
    name = None
    password = None
    _active = None

    @classmethod
    def activate(cls, active):
        if not active.is_valid:
            raise digsbylocal.InvalidPassword
        if cls._active is not None:
            cls.deactivate()

        active.set('last_login', time.time())
        cls._active = active

    @classmethod
    def deactivate(cls):
        cls._active = None

    @classmethod
    def active(cls):
        return cls._active

    @classmethod
    def save_data(cls, key, value):
        active = cls.active()
        if active is None:
            return
        return active.set(key, value)

    @classmethod
    def load_data(cls, key, default = None):
        active = cls.active()
        if active is None:
            return default
        return active.get(key, default)

    @classmethod
    def delete(cls, name, password):
        if not cls.exists(name):
            # TODO: should this just cleanly return?
            # the expected post-conditions of this function are satisfied...
            raise digsbylocal.InvalidUsername

        identity = cls(name, password)
        if not identity.is_valid:
            raise digsbylocal.InvalidPassword

        identity.storage.rmtree()

    @classmethod
    def generate_salt(cls):
        return hex(random.getrandbits(256)).lstrip('0').lstrip('x').rstrip('L')

    @classmethod
    def exists(cls, name):
        return cls(name).storage.isdir()

    @classmethod
    def all(cls):
        '''
        Return all available profiles
        '''
        return iter(cls(unicode(pth.name)) for pth in cls._storage_dir().dirs())

    @classmethod
    def last(cls):
        all_identities = list(cls.all())
        return sorted(all_identities, key = lambda identity: identity.get('last_login', 0))[-1]

    @classmethod
    def _storage_dir(cls):
        '''
        Returns the location where all profiles are stored. Creates the directory if necessary.
        '''
        pth = path.path(common.pref('digsby.profiles.location', default=stdpaths.userdata / 'profiles'))
        if not pth.isdir():
            pth.makedirs()
        return pth

    @classmethod
    def create(cls, name, password):
        if cls.exists(name):
            raise Exception('Profile %r already exists', name)

        identity = cls(name, password)

        identity.set('accounts', [])
        identity.set('prefs', {})
        identity.set('sentinel', hashlib.sha256(identity.key).hexdigest())

        return identity

    def __init__(self, name, password=None):
        self.name = name
        self.password = password or self.get('saved_password', None)

    @property
    def is_valid(self):
        try:
            return self.get('sentinel', None) == hashlib.sha256(self.key).hexdigest()
        except Exception:
            return False

    def set(self, key, value):
        '''
        Put 'value' in '_storage' as 'key'
        '''
        if not self.storage.isdir():
            self.storage.makedirs()

        data = self.serialize(key, value)

        with files.atomic_write(self.storage / key, 'wb') as f:
            f.write(data)

    def get(self, key, default = None):
        '''
        Retrieve stored value associated with 'key' from '_storage'
        '''

        fname = self.storage / key
        if not fname.isfile():
            return default

        with open(fname, 'rb') as f:
            data = f.read()

        # TODO: what happens if deserialize fails?
        return self.deserialize(key, data)

    def keys(self):
        if self.storage.isdir():
            return (unicode(f.name) for f in self.storage.files())
        else:
            return iter()

    @property
    def storage(self):
        return type(self)._storage_dir() / self.name

    def serialize(self, key, value):
        serializer = getattr(self, 'serialize_%s' % key, self.serialize_default)
        return serializer(key, value)

    def deserialize(self, key, data):
        deserializer = getattr(self, 'deserialize_%s' % key, self.deserialize_default)
        return deserializer(key, data)

    def serialize_nojson(self, key, value):
        assert isinstance(value, bytes)
        return self.encrypt(value)
    serialize_icon = serialize_nojson

    def deserialize_nojson(self, key, data):
        value = self.decrypt(data)
        assert isinstance(value, bytes)
        return value
    deserialize_icon = deserialize_nojson

    def serialize_nocrypt(self, key, value):
        return simplejson.dumps(value)
    serialize_salt = serialize_nocrypt
    serialize_autologin = serialize_nocrypt
    serialize_save = serialize_nocrypt
    serialize_sentinel = serialize_nocrypt
    serialize_last_login = serialize_nocrypt

    def deserialize_nocrypt(self, key, data):
        return simplejson.loads(data)
    deserialize_salt = deserialize_nocrypt
    deserialize_autologin = deserialize_nocrypt
    deserialize_save = deserialize_nocrypt
    deserialize_sentinel = deserialize_nocrypt
    deserialize_last_login = deserialize_nocrypt

    def serialize_softcrypt(self, key, value):
        return self.serialize_default(key, value, self.softcrypt_key)
    serialize_saved_password = serialize_softcrypt

    def deserialize_softcrypt(self, key, data):
        return self.deserialize_default(key, data, self.softcrypt_key)
    deserialize_saved_password = deserialize_softcrypt

    def serialize_accounts(self, key, value):
        stored_value = digsbylocal.serialize_local(accts = value, order = [x.id for x in value])
        return self.serialize_default(key, stored_value)

    def deserialize_accounts(self, key, data):
        stored_value = self.deserialize_default(key, data)
        stored_value = digsbylocal.unserialize(stored_value)
        for a in stored_value['accts']:
            password = a['password']
            assert (isinstance(password, str) or password is None)
            if password is not None:
                password = password.decode('base64')
            a['password'] = password
        return accounts.Accounts.from_local_store(stored_value)

    def serialize_default(self, key, value, crypt_key = None):
        return self.encrypt(pydumps(value), crypt_key)

    def deserialize_default(self, key, data, crypt_key = None):
        return pyloads(self.decrypt(data, crypt_key))

    @property
    def softcrypt_key(self):
        return hashlib.sha256(self.softcrypt_salt + self.name).digest()

    @property
    def key(self):
        if self.password is None:
            raise Exception('identity.password cannot be None. set no password explicitly with emptystring ("")')

        salt = self.get('salt')
        if salt is None:
            salt = self.generate_salt()
            self.set('salt', salt)

        return hashlib.sha256(salt + self.password + salt + self.name + 'digsby').digest()

    def encrypt(self, plaintext, key = None):
        if key is None:
            key = self.key
        return crypto.encrypt(key, plaintext, mode = crypto.Mode.CBC)

    def decrypt(self, ciphertext, key = None):
        if key is None:
            key = self.key
        return crypto.decrypt(key, ciphertext, mode = crypto.Mode.CBC)
