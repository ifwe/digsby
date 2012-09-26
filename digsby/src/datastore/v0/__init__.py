import sys
import os
import logging
import stdpaths
import sysident

log = logging.getLogger('datastore.v0')

from ..common import Datastore, FileDatastore, EncryptingDatastore, YAMLDatastore

## TODO: make this ;)
#class LocalPrefs(FileDatastore):
#    """Data access for local prefs stored in an INI file"""
#    def __init__(self, **kwds):
#        super(LocalPrefs, self).__init__(**kwds)


class LoginInfo(EncryptingDatastore, YAMLDatastore):
    """Login info stored in YAML"""
    def __init__(self, encrypted_properties=(('password',), 'password',), **kwds):
        filepath = kwds.pop('filepath', None)

        if filepath is None:
            if sys.REVISION == 'dev':
                filename = 'logininfodev.yaml'
            else:
                filename = 'logininfo.yaml'

            filepath = stdpaths.userlocaldata / filename
            if not filepath.parent.isdir():
                filepath.parent.makedirs()

        super(LoginInfo, self).__init__(
            filepath=filepath,
            encrypted_properties=encrypted_properties,
            **kwds
        )

#    # TODO: if setting username, re-encrypt password
#    def set(self, key, value):
#        pass

    def _encrypt(self, val):
        encrypted = self.simple_crypt(val.encode('utf8'), keymat=self.get('username', '').encode('utf8'))
        return encrypted

    def _decrypt(self, val):
        decrypted = self.simple_crypt(val, keymat=self.get('username', '').encode('utf8'))
        return decrypted.decode('utf8')

    def simple_crypt(self, s, k=None, keymat=''):
        from M2Crypto.RC4 import RC4
        if k is None:
            k = self._get_key(keymat)
        return RC4(k).update(s)

    def _get_key(self, keymat=''):
        keys = getattr(self, '_keys', None)
        if keys is None:
            keys = self._keys = {}

        key = keys.get(keymat, None)
        if key is not None:
            return key

        self._keys[keymat] = sysident.sysident(append=keymat)

        return self._keys[keymat]

    def load_from_disk(self):
        users = self.get('users', None)
        if users is None:
            self.set('users', {})
            users = self.get('users')
        return self.get('last', ''), users

    def save_to_disk(self, last, info):
        self.set('last', last)
        for k, v in info.items():
            if type(v) is object:
                raise Exception(list(info.items()))
            self.set(('users',) + k, v)

        return True
