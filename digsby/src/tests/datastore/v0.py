import path
import unittest
import hashlib
import sysident
from datastore.v0 import LoginInfo
from tests.datastore.common import YAMLDatastoreTests

data = '''
---
last: !python/unicode username
users:
  ? !python/unicode username
  :
    password: !binary |
      /3m/lJnajX0=

    autologin: False
    save: True
    username: !python/unicode username

  ? !python/unicode veryreactive1
  :
    username: !python/unicode veryreactive1
    save: False
    autologin: False
    password: ""

  ~:
    status: ""
  pos: !python/tuple
    - 136
    - 106

  "":
    pos: !python/tuple
      - 200
      - 200
    password: ""
    autologin: False
    save: False
    username: ""
'''

## Old classes for compatibility testing
import syck
import os.path
import stdpaths
import traceback
import cPickle


class SplashDiskStorage(object):
    info_default = {'': dict(username='',
                             password='',
                             save=False,
                             autologin=False,
                             pos=(200, 200)),
                    None: dict()}
    last_default = ''

    def get_conf_dir(self):
        'Returns (and makes, if necessary) the user application directory.'
        c_dir = stdpaths.userdata
        try:
            return c_dir
        finally:
            if not os.path.exists(c_dir):
                os.mkdir(c_dir)

    def get_splash_data_path(self):
        return os.path.join(self.get_conf_dir(), self.data_file_name %
                            ('dev' if sys.REVISION == 'dev' else ''))

    def crypt_pws(self, info, codec):
        for user in info:
            if 'password' in info[user]:
                if codec == 'encode':
                    encrypted_password = self.simple_crypt(
                                             info[user]['password'].encode('utf8'),
                                             keymat=user.encode('utf8')
                                         )
                    info[user]['password'] = encrypted_password
                elif codec == 'decode':
                    decrypted_password = self.simple_crypt(
                                             info[user]['password'],
                                             keymat=user.encode('utf8')
                                         )
                    info[user]['password'] = decrypted_password.decode('utf8')
                else:
                    raise AssertionError

    def simple_crypt(self, s, k=None, keymat=''):
        raise NotImplementedError

    def save_to_disk(self, last, info):
        raise NotImplementedError

    def load_from_disk(self):
        raise NotImplementedError

    def can_write(self):

        fname = os.path.join(self.get_conf_dir(), '__test__')
        test_data = "test"
        try:
            with open(fname, 'wb') as f:
                f.write(test_data)

            with open(fname, 'rb') as f:
                if f.read() == test_data:
                    return True

            return False
        except Exception:
            return False
        finally:
            try:
                if os.path.exists(fname):
                    os.remove(fname)
            except Exception:
                pass


class NewSplashDiskStorage(SplashDiskStorage):
    data_file_name = 'logininfo%s.yaml'

    def __init__(self):
        SplashDiskStorage.__init__(self)

    def get_conf_dir(self):
        'Returns (and makes, if necessary) the user application directory.'

        c_dir = stdpaths.userlocaldata
        try:
            return c_dir
        finally:
            if not os.path.exists(c_dir):
                os.makedirs(c_dir)

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
        path = self.get_splash_data_path()
        try:
            with open(path, 'rb') as f:
                all_info = syck.load(f)

            if not isinstance(all_info, dict):
                all_info = {}

            info = all_info.get('users', self.info_default)
            last = all_info.get('last', self.last_default)
            self.crypt_pws(info, 'decode')
        except Exception, _e:
            traceback.print_exc()

        return last, info

    def save_to_disk(self, last, info):
        path = self.get_splash_data_path()

        self.crypt_pws(info, 'encode')
        for_yaml = {'users': info,
                    'last': last}
        try:
            with open(path, 'wb') as f:
                syck.dump(for_yaml, f)
        except Exception:
            traceback.print_exc()
        self.crypt_pws(info, 'decode')
        return True

## End old classes


class _LoginInfoTests(object):
    '''
    Base class for tests in common for old "NewSplashDiskStorage"
    and LoginInfo
    '''

    _filepath = path.path(__file__).parent / 'test.yaml'

    def create_datastore(self):
        raise NotImplementedError

    def setUp(self):
        # Part of the key to encrypt passwords is sysident, which is
        # (designed to be) machine specific. In order for tests to be
        # machine-independent, we're replacing it with something predictable.
        def new_sysident(prepend='', append=''):
            return hashlib.sha1(prepend + append).digest()
        self._old_sysident = sysident.sysident
        sysident.sysident = new_sysident

        self.datastore = self.create_datastore()
        self.flat_data = dict([
            (('last',), u'username'),
            (('users', u'username', 'username'), u'username'),
            (('users', u'username', 'save'), True),
            (('users', u'username', 'password'), 'password'),
            (('users', u'username', 'autologin'), False),
            (('users', '', 'username'), ''),
            (('users', '', 'save'), False),
            (('users', '', 'password'), ''),
            (('users', '', 'pos'), (200, 200)),
            (('users', '', 'autologin'), False),
            (('users', u'veryreactive1', 'username'), u'veryreactive1'),
            (('users', u'veryreactive1', 'password'), ''),
            (('users', u'veryreactive1', 'save'), False),
            (('users', u'veryreactive1', 'autologin'), False),
            (('users', None, 'status'), ''),
            (('users', 'pos'), (136, 106)),
        ])

    def tearDown(self):
        sysident.sysident = self._old_sysident
        del self.datastore
        self._filepath.remove()

    def test_load_from_disk(self):
        last, allinfo = self.datastore.load_from_disk()
        self.assertEqual(last, self.flat_data.get(('last',)))

        for key in self.flat_data:
            if key[0] == 'users':
                key = key[1:]
            else:
                continue

            val = reduce(lambda a, b: a.get(b), key, allinfo)
            self.assertEqual(val, self.flat_data.get(('users',) + key))

    def test_change_password(self):
        other_datastore = self.create_datastore()
        _last, allinfo = self.datastore.load_from_disk()
        new_password = 'new password'
        username = 'veryreactive1'
        key = (username, 'password')
        allinfo[username]['password'] = new_password
        self.datastore.save_to_disk(username, allinfo)

        other_last, other_allinfo = other_datastore.load_from_disk()
        last, allinfo = self.datastore.load_from_disk()

        self.assertEqual(last, username)
        self.assertEqual(allinfo[username]['password'], new_password)

        self.assertEqual(other_last, username)
        self.assertEqual(other_allinfo[username]['password'], new_password)

    def test_add_new_user(self):
        other_datastore = self.create_datastore()
        _last, allinfo = self.datastore.load_from_disk()
        new_username = 'new name'
        self.assertEqual(None, allinfo.get(new_username, None))
        self.assertRaises(KeyError, lambda: allinfo[new_username])

        allinfo[new_username] = {}
        allinfo[new_username]['username'] = new_username
        allinfo[new_username]['password'] = 'a password'
        allinfo[new_username]['save'] = True
        allinfo[new_username]['autologin'] = False

        self.datastore.save_to_disk(new_username, allinfo)

        other_last, other_allinfo = other_datastore.load_from_disk()
        last, allinfo = self.datastore.load_from_disk()

        self.assertEqual(last, new_username)
        self.assertEqual(other_last, new_username)

        for key in ('username', 'password', 'save', 'autologin'):
            self.assertEqual(allinfo[new_username][key],
                             other_allinfo[new_username][key])

        self.assertEqual(allinfo[new_username]['username'], new_username)
        self.assertEqual(allinfo[new_username]['password'], 'a password')
        self.assertEqual(allinfo[new_username]['save'], True)
        self.assertEqual(allinfo[new_username]['autologin'], False)


class LoginInfoTests(_LoginInfoTests, YAMLDatastoreTests):
    '''
    All the tests for a YAMLDatastore (with some overrides, see notes
    in methods below) and those for NewSplashDiskStorage class.
    '''
    def create_datastore(self):
        with self._filepath.open('wb') as f:
            f.write(data)

        return LoginInfo(filepath=self._filepath)

    def test_clear(self):
        # Note: sorting them because LoginInfo requires a 'username' key in
        # order to decrypt the value of 'password'. If username gets cleared
        # first, password will throw an Invalid Key error
        for k, _v in sorted(self.datastore.items()):
            self.datastore.clear(k)
            self.assertRaises(KeyError, lambda: self.datastore.get(k))

    def test_file_write(self):
        new_dstore = self.create_datastore()
        self.test_set_new()
        ## This doesn't work because the password doesn't get re-encrypted when
        ## the username is changed. see note in LoginInfo.
        #self.test_set_existing()
        new_items = set(new_dstore.items())
        my_items = set(self.datastore.items())
        self.assertEqual(my_items, new_items)


class OldLoginInfoTests(_LoginInfoTests, unittest.TestCase):
    '''
    Tests for NewSplashDiskStorage.
    '''
    # Apologies for the naming - let this be a lesson to everyone, don't use
    # New, Old, etc in class names.

    def create_datastore(self):
        with self._filepath.open('wb') as f:
            f.write(data)

        datastore = NewSplashDiskStorage()
        datastore.get_splash_data_path = lambda: self._filepath
        return datastore


def suite():
    s = unittest.TestSuite()
    loader = unittest.TestLoader()
    tests = map(loader.loadTestsFromTestCase, [
        OldLoginInfoTests,
        LoginInfoTests,
    ])

    s.addTests(
        tests
    )
    return s

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
    #unittest.main()
