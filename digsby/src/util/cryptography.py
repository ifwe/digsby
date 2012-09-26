from hashlib import sha1 as _DefaultHash

class Mode:
    ECB = 1
    CBC = 2
    CFB1 = 3
    CFB8 = 4
    CFB64 = 5
    CFB128 = 6
    OFB = 7
    CTR = 8
    DEFAULT = ECB

def _key_prep(key, hash=_DefaultHash, length=16):
    return hash(key).digest()[:length]

def pad(s, sz, padchar='\0'):
    extralen = (sz - (len(s) % sz)) % sz
#    if extralen:
#        print 'ENCRYPT: padding plaintext with %d bytes' % extralen
    return s + (extralen * padchar)

def unpad(s, padchar='\0'):
    return s.rstrip(padchar)

def _encrypt(key, plain, padchar='\x00'):
    '''
    encrypt the plain-text using Cipher, appending padchar if necessary
    '''
    from Crypto.Cipher import AES as Cipher
    cipher = Cipher.new(key)
    plain = pad(plain, cipher.block_size, padchar)
    return cipher.encrypt(plain)

def _decrypt(key, crypt, padchar='\x00'):
    '''
    decrypt the crypt-text using Cipher, stripping padchar from the result
    '''
    from Crypto.Cipher import AES as Cipher
    assert (len(crypt) % Cipher.block_size) == 0
    cipher = Cipher.new(key)
    return cipher.decrypt(crypt).rstrip(padchar)

def cipher_functions(key, padchar='\x00', mode = Mode.DEFAULT):
    def _encrypt(plain):
        return encrypt(key, plain, padchar=padchar, mode=mode)

    def _decrypt(crypt):
        return decrypt(key, crypt, padchar=padchar, mode=mode)

    return _encrypt, _decrypt

#from Crypto.Cipher import ARC4 as oldenc
#from Crypto.Cipher import AES as newenc

#def change_pw_encryption(new_password=None, old_encryption=oldenc, new_encryption=newenc, new_hash=_DefaultHash, keylen=16):
#    from common import profile as p
#    from hashlib import sha1
#
#    if new_password is None:
#        new_password = p.password
#
#    oldencrypt, olddecrypt = cipher_functions(sha1(p.password).digest(), Cipher=oldenc)
#    newencrypt, newdecrypt = cipher_functions(_key_prep(new_password, hash=new_hash, length=keylen), Cipher=newenc)
#
#    all_accounts = list(p.account_manager) #p.account_manager._all_accounts.em.accounts + p._all_accounts.so.accounts + p._all_accounts.im.accounts
#
#    p.password = new_password
#    p._encrypter, p._decrypter = newencrypt, newdecrypt
#
#    for acct in all_accounts:
#        try:
#            oldpw = olddecrypt(acct.password)
#            acct.password = newencrypt(oldpw)
#            p.update_account(acct)
#        except:
#            print repr(acct.password), len(acct.password)


def hash(s, raw=True, Hash=_DefaultHash):
    if raw:
        digest = lambda x: x.digest()
    else:
        digest = lambda x: x.hexdigest()
    return digest(Hash(s))

def encrypt(key, plain, iv=None, padchar='\0', mode = Mode.DEFAULT):
    if iv is None:
        iv = '\0' *16
    aes = OpenSSL_AES(key, mode, iv)

    if padchar is not None:
        plain = pad(plain, aes.block_size, padchar)
    return aes.encrypt(plain)

def decrypt(key, crypt, iv=None, padchar='\0', mode = Mode.DEFAULT):
    if iv is None:
        iv = '\0' * 16

    aes = OpenSSL_AES(key, mode, iv)
    if padchar is None:
        return aes.decrypt(crypt)
    else:
        return unpad(aes.decrypt(crypt), padchar)


# --------------
# Trying to replicate the functions above using only M2Crypto
#
#def encrypt(key, plain):
#    '''
#    encrypt the plain-text using Cipher, appending padchar if necessary
#    '''
#    from M2Crypto import m2, encrypt, BIO
#    blocksize = m2.AES_BLOCK_SIZE
#    iv = '\0' * blocksize
#
#
#
#    from M2Crypto import BIO
#    buf = BIO.MemoryBuffer()
#    strm = BIO.CipherStream(buf)
#    strm.set_cipher('aes_128_cbc', key, iv, encrypt)
#    strm.write(plain)
#    strm.write_close()
#    result = buf.read()
#    strm.close()
#    buf.close()
#
#    return result
#
#def decrypt(key, crypt):
#    '''
#    decrypt the crypt-text using AES, and fix old PyCrypto strings as well
#    '''
#    from M2Crypto import m2, decrypt, BIO
#    blocksize = m2.AES_BLOCK_SIZE
#    iv = '\0' * blocksize
#
#    def __tryit(text):
#        buf = BIO.MemoryBuffer(text)
#        strm = BIO.CipherStream(buf)
#        strm.set_cipher('aes_128_cbc', key, iv, decrypt)
#        strm.write_close()
#        result = strm.read()
#        strm.close()
#        return result
#
#    plaintext = __tryit(crypt)
#    if len(plaintext) <= (len(crypt)-blocksize): # Was encrypted with pycrypto, needs fixin'
#        crypt = PyCrypto_to_M2Crypto(key, crypt)
#        plaintext = __tryit(crypt).rstrip('\0')
#
#    return plaintext
#
#def PyCrypto_to_M2Crypto(key, enc_string, iv=None):
#    from M2Crypto import m2, encrypt, BIO
#    blocksize = m2.AES_BLOCK_SIZE
#
#    iv = '\0' * blocksize
#
#    result = ''
#    while enc_string:
#        chunk, enc_string = enc_string[:blocksize], enc_string[blocksize:]
#        buf = BIO.MemoryBuffer(chunk)
#        strm = BIO.CipherStream(buf)
#        strm.set_cipher('aes_128_cbc', key, iv, encrypt)
#        strm.flush()
#        strm.write_close()
#        result += buf.read()
#        strm.close()
#        buf.close()
#
#    return result

try:
    from M2Crypto import m2
except ImportError:
    has_AES = False
    has_DES3 = False
else:
    has_AES = True
    has_DES3 = True

class OpenSSL_AES(object):
    '''
    thanks tlslite
    '''

    # WARNING: This operates in ECB mode (to be compatible with the implementation it replaces).
    # ECB mode is insecure. (see: http://en.wikipedia.org/wiki/Block_cipher_modes_of_operation#Electronic_codebook_.28ECB.29 )
    # DO NOT use it anymore. In the future, use CBC mode. A simple wrapper for this has not yet been implemented.

    def __init__(self, key, mode, IV):
        if len(key) not in (16, 24, 32):
            raise AssertionError()
        if mode < 1 or mode > 9:
            raise AssertionError()
        if len(IV) != 16:
            raise AssertionError()
        self.mode = mode
        self.isBlockCipher = True
        self.block_size = 16
        self.implementation = 'openssl'
        if len(key)==16:
            self.name = "aes128"
        elif len(key)==24:
            self.name = "aes192"
        elif len(key)==32:
            self.name = "aes256"
        else:
            raise AssertionError()
        self.key = key
        self.IV = IV

    def _createContext(self, encrypt):
        context = m2.cipher_ctx_new()
        keybits = len(self.key) * 8
        mode = [None, 'ecb', 'cbc', 'cfb1', 'cfb8', 'cfb64', 'cfb128', 'ofb', 'ctr'][self.mode]
        if mode is None:
            raise AssertionError

        ciph_type_name = 'aes_%d_%s' % (keybits, mode)
        cipherType = getattr(m2, ciph_type_name)()

        m2.cipher_init(context, cipherType, self.key, self.IV, encrypt)
        return context

    def encrypt(self, plaintext):
        assert(len(plaintext) % 16 == 0)

        if not plaintext:
            return ''

        context = self._createContext(1)
        ciphertext = m2.cipher_update(context, plaintext)
        m2.cipher_ctx_free(context)
        self.IV = ciphertext[-self.block_size:]
        return ciphertext

    def decrypt(self, ciphertext):
        assert(len(ciphertext) % 16 == 0)

        if not ciphertext:
            return ''

        context = self._createContext(0)
        #I think M2Crypto has a bug - it fails to decrypt and return the last block passed in.
        #To work around this, we append sixteen zeros to the string, below:
        plaintext = m2.cipher_update(context, ciphertext+('\0'*16))

        #If this bug is ever fixed, then plaintext will end up having a garbage
        #plaintext block on the end.  That's okay - the below code will discard it.
        plaintext = plaintext[:len(ciphertext)]
        m2.cipher_ctx_free(context)
        self.IV = ciphertext[-self.block_size:]
        return plaintext

AES = OpenSSL_AES


class OpenSSL_TripleDES(object):
    '''
    thanks tlslite
    '''

    def __init__(self, key, mode, IV):
        if len(key) != 24:
            raise ValueError()
        if mode != 2:
            raise ValueError()
        if len(IV) != 8:
            raise ValueError()
        self.isBlockCipher = True
        self.block_size = 8
        self.implementation = 'openssl'
        self.name = "3des"
        self.key = key
        self.IV = IV

    def _createContext(self, encrypt):
        context = m2.cipher_ctx_new()
        cipherType = m2.des_ede3_cbc()
        m2.cipher_init(context, cipherType, self.key, self.IV, encrypt)
        return context

    def encrypt(self, plaintext):
        assert(len(plaintext) % 8 == 0)

        if not plaintext:
            return ''

        context = self._createContext(1)

        ciphertext = m2.cipher_update(context, plaintext)
        m2.cipher_ctx_free(context)
        self.IV = ciphertext[-self.block_size:]
        return ciphertext

    def decrypt(self, ciphertext):
        assert(len(ciphertext) % 8 == 0)

        if not ciphertext:
            return ''

        context = self._createContext(0)
        #I think M2Crypto has a bug - it fails to decrypt and return the last block passed in.
        #To work around this, we append sixteen zeros to the string, below:

        plaintext = m2.cipher_update(context, ciphertext+('\0'*16))

        #If this bug is ever fixed, then plaintext will end up having a garbage
        #plaintext block on the end.  That's okay - the below code will ignore it.
        plaintext = plaintext[:len(ciphertext)]
        m2.cipher_ctx_free(context)
        self.IV = ciphertext[-self.block_size:]
        return plaintext

DES3 = OpenSSL_TripleDES

def nonce(len_=16):
    return m2.rand_bytes(len_)

def _main():
    key = _key_prep('this is my key')
    plaintext = 'abcd'*80

    old = encrypt(key, plaintext)
    new = _encrypt(key, plaintext)

    print (old, new), old == new
    print (decrypt(key, new), _decrypt(key, old))
    print 'yay'



if __name__ == '__main__':
    _main()
