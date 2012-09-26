'''
Saves and loads accounts to and from disk.
'''

from __future__ import with_statement

import os.path
from hashlib import sha1
import base64
import util.cryptography as crypto
import util.primitives.files as files
import util.primitives.strings as strings
import util.cacheable as cache

from logging import getLogger
from BlobManager import BlobManager
from digsby.blobs import load_cache_from_data_disk
import os.path
log = getLogger('digsbylocal')

from util.json import pydumps, pyloads

#don't zip w/o considering pad character for encryption.
#default is \0, and that's not going to the be the last character of JSON.
serialize = pydumps
unserialize = pyloads

class InvalidUsername(Exception):
    pass
class InvalidPassword(Exception):
    pass

def cipher_functions(username, password):
    from sysident import sysident

    mach_key = sysident()
    digest   = sha1(username + password).digest()
    assert len(mach_key) == len(digest)
    key = strings.string_xor(digest, mach_key)
    return crypto.cipher_functions(key[-16:], mode = crypto.Mode.CBC)

def encrypt(username, password, data):
    _encrypter, _decrypter = cipher_functions(username, password)
    return _encrypter(data)

def decrypt(username, password, data):
    _encrypter, _decrypter = cipher_functions(username, password)
    return _decrypter(data)

def local_file(username):
    'Where to store account and local order data.'
    cache_path = cache.get_cache_root(user = True)
    return cache_path / 'local.accounts'

def server_file(username):
    'Where to store the server side account hash and server order'
    cache_path = cache.get_cache_root(user = True)
    return cache_path / 'server.accounts'

def dict_for_acct(acct):
    acct_dictionary = dict((attr, getattr(acct, attr))
                           for attr in ('id', 'protocol', 'username', 'password'))
    acct_dictionary['data'] = acct.get_options()
    password = acct_dictionary['password']
    assert (isinstance(password, str) or password is None)
    if password is not None:
        password = base64.b64encode(password)
    acct_dictionary['password'] = password
    return acct_dictionary

def serialize_local(accts, order):
    assert validate_order(order)

    return serialize(dict(order=order,
                          accts=[dict_for_acct(acct) for acct in accts]))

def serialize_server(accounts_hash, server_order):
    assert validate_order(server_order)

    return serialize(dict(accounts_hash = accounts_hash,
                          server_order = server_order))

def _load_data(username, password, filename):
    if not os.path.isfile(filename):
        # if there is not accounts file, then we haven't ever saved this
        # username
        raise InvalidUsername

    with open(filename, 'rb') as f:
        data = f.read()

    data = decrypt(username, password, data)

    try:
        return unserialize(data)
    except Exception, e:
        # if the data could not be unserialized, then it was decrypted with
        # the wrong password
        raise InvalidPassword(e)

def load_local(username, password):
    local_info = _load_data(username, password, local_file(username))

    assert 'order' in local_info
    assert 'accts' in local_info

    for a in local_info['accts']:
        password = a['password']
        assert (isinstance(password, str) or password is None)
        if password is not None:
            password = password.decode('base64')
        a['password'] = password
    log.debug_s('loaded local: %r', local_info)
    return local_info

def load_server(username, password):
    sever_info = _load_data(username, password, server_file(username))
    log.debug_s('loaded server: %r', sever_info)
    return sever_info

def save_local_info(username, password, accounts, local_order):
    assert isinstance(username, basestring)
    assert isinstance(password, basestring)
    log.debug_s('saving local: %r', serialize_local(accounts, local_order))
    data = encrypt(username, password, serialize_local(accounts, local_order))

    with files.atomic_write(local_file(username), 'wb') as f:
        f.write(data)

def save_server_info(username, password, server_account_hash, server_order):
    assert isinstance(username, basestring)
    assert isinstance(password, basestring)
    server_data = serialize_server(server_account_hash, server_order)
    log.debug_s('saving server: %r', server_data)
    data = encrypt(username, password, server_data)

    with files.atomic_write(server_file(username), 'wb') as f:
        f.write(data)

def validate_order(o):
    'Validate that an account order object is of the correct type.'

    return isinstance(o, list) and all(isinstance(e, int) for e in o)


def load_local_blob(username, blobname):
    cache_path = cache.get_cache_root(user = True, username=username) / BlobManager.CACHE_FOLDER
    try:
        pth = cache_path / blobname
        if not os.path.isfile(pth):
            return None
        data = pth.bytes()
        blob = load_cache_from_data_disk(blobname, data)
        return blob.data
    except Exception:
        return None




