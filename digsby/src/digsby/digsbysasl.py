import traceback
import logging

from pyxmpp.utils import to_utf8
from pyxmpp.sasl.core import ClientAuthenticator
from pyxmpp.sasl.core import Success,Failure,Challenge,Response

import struct, hashlib

log = logging.getLogger('digsby.sasl')

import M2Crypto, util.cryptography, util.cacheable
import digsbyrsa

# OPENSOURCE: does this need to go? seems like it should be a
# public key sort of thing but we should double check.
ROOT_CERT_RAW = '''-----BEGIN CERTIFICATE-----
MIIEqjCCA5KgAwIBAgIJAIm6tjo3F7DQMA0GCSqGSIb3DQEBBQUAMIGUMQswCQYD
VQQGEwJVUzERMA8GA1UECBMITmV3IFlvcmsxEjAQBgNVBAcTCVJvY2hlc3RlcjEX
MBUGA1UEChMOZG90U3ludGF4LCBMTEMxDzANBgNVBAsTBkRpZ3NieTETMBEGA1UE
AxMKZGlnc2J5Lm9yZzEfMB0GCSqGSIb3DQEJARYQYWRtaW5AZGlnc2J5LmNvbTAe
Fw0xMDEyMTUyMDUwNTZaFw0xMTEyMTUyMDUwNTZaMIGUMQswCQYDVQQGEwJVUzER
MA8GA1UECBMITmV3IFlvcmsxEjAQBgNVBAcTCVJvY2hlc3RlcjEXMBUGA1UEChMO
ZG90U3ludGF4LCBMTEMxDzANBgNVBAsTBkRpZ3NieTETMBEGA1UEAxMKZGlnc2J5
Lm9yZzEfMB0GCSqGSIb3DQEJARYQYWRtaW5AZGlnc2J5LmNvbTCCASIwDQYJKoZI
hvcNAQEBBQADggEPADCCAQoCggEBALvRZBUWh9IhxNfajLc6gXA8OVArXp2XvxCf
hHR/CznE4bqNSs8kGlkXZzGZlhRXDpMM4ytlktYN6Bu+RwR1BzjQSt/GpnuxCL5X
+l9yukATrfBs/i7iHwmWREkvJXzgi3ToyZ/NsmjmA1CtzYn44D8Sc/lsui4EeGyb
slno/ZYpCIniaHPnA1+A8u6Fbq/DgZkpLY8ZA/lgKRwtQMa216eBEhROjJVLjdN3
GDenu/tGBIdKQLAJ1bLCswSamtmmTAIT4nqd5GH/p1PlZKpObn38+PV1Cth1ZA3R
SnIxFSRUO5s2OxWTR694hEufrLV3ccK5NSW1tuMYeDaWUfo3MIECAwEAAaOB/DCB
+TAdBgNVHQ4EFgQUq3dfcfI0E/07C6iZiyp1lwmdA24wgckGA1UdIwSBwTCBvoAU
q3dfcfI0E/07C6iZiyp1lwmdA26hgZqkgZcwgZQxCzAJBgNVBAYTAlVTMREwDwYD
VQQIEwhOZXcgWW9yazESMBAGA1UEBxMJUm9jaGVzdGVyMRcwFQYDVQQKEw5kb3RT
eW50YXgsIExMQzEPMA0GA1UECxMGRGlnc2J5MRMwEQYDVQQDEwpkaWdzYnkub3Jn
MR8wHQYJKoZIhvcNAQkBFhBhZG1pbkBkaWdzYnkuY29tggkAibq2OjcXsNAwDAYD
VR0TBAUwAwEB/zANBgkqhkiG9w0BAQUFAAOCAQEAJCsHm8osylNqfmNMTEL6Nczr
hD95jl1D3a3hKlKHYPkZ5/pmGHV4C/ZYteSm9yWtWNQp/ZGTS+XG4I9NFQ6s6Cr1
LLOoK52BVzal5LemAPyzXyIKuG2fwTMdBiL9fIoYDLWvjzp5SGHHc4K0mofetgxZ
TdqQr7qWXY62zdkKSgwo9HPqrhtUzyfvDBJPjzeRbGguV3jCvodgV5D7aK18K1gz
C9lIMQaWRzS80+a1dUtibwG4fTKSRaIrOmdhvI+YdTj4aNKcmq985CXD068hG09P
ArAEDrQEul9GOIqcx6RmtDSx1r+f1Iv+ef5boBu/04TZCCClDF7AYUwIErJCoQ==
-----END CERTIFICATE-----
'''

ROOT_CERT = M2Crypto.X509.load_cert_string(ROOT_CERT_RAW)

def _save_client_key_pem(key, uname, password):
    passfunc = lambda _dec_enc: hashlib.sha256(password + "digsby" + uname.encode('utf-8')).digest()
    key = key.as_pem(callback = passfunc)
    if key is not None:
        dec_key = key.decode('utf8')
    else:
        dec_key = key

    return util.cacheable.save_cache_object('client_priv_key.key', dec_key, json=True, user=True)

def _get_client_key_pem(uname, password):
    passfunc = lambda _dec_enc: hashlib.sha256(password + "digsby" + uname.encode('utf-8')).digest()
    key = util.cacheable.load_cache_object('client_priv_key.key', json=True, user=True)

    if key is not None:
        enc_key = key.encode('utf8')
        try:
            ret_key = M2Crypto.RSA.load_key_string(enc_key, callback=passfunc)
            if not ret_key.check_key():
                ret_key = None
        except Exception:
            ret_key = None
    else:
        ret_key = key

    return ret_key

def pstrI(s):
    return struct.pack('!I', len(s)) + s

def pstrIlist(l):
    return [pstrI(s) for s in l]

def pstrAES(key, s, iv=None):
    p = pstrI(s)
    return util.cryptography.encrypt(key, p, iv=iv, padchar = chr(256 + ~ord(p[-1])), mode = util.cryptography.Mode.CBC)

def unpackpstrlist(s):
    ret = []
    while s:
        l, s = struct.unpack('!I', s[:4])[0], s[4:]
        ret.append(s[:l])
        s = s[l:]
    return ret

def unpackpstr(s):
    l = struct.unpack('!I', s[:4])[0]
    return s[4:4+l], s[4+l:]

class DigsbyAESClientAuthenticator(ClientAuthenticator):

    def __init__(self,password_manager):
        ClientAuthenticator.__init__(self,password_manager)
        self.username=None
        self.password=None
        self.key = None
        self.step = 0
        self.authzid=None
        self.__logger=logging.getLogger("digsby.sasl.AES")

    def start(self,username,authzid):
        self.username=username
        if authzid:
            self.authzid=authzid
        else:
            self.authzid=""
        self.step = 0
        return self.challenge("")

    def challenge(self, challenge):
        if self.password is None:
            self.password,pformat=self.password_manager.get_password(self.username)
            if not self.password or pformat!="plain":
                self.__logger.debug("Couldn't retrieve plain password")
                return Failure("password-unavailable")
        if self.step == 0:
            self.step = 1
            return Response(''.join(pstrIlist([
                            to_utf8(self.authzid),
                            to_utf8(self.username)])))

        elif self.step == 1:
            self.step = 2
            srv_rsa_key = None
            self.__logger.critical("loading server certificate")
            try:
                srv_cert = M2Crypto.X509.load_cert_string(challenge)
                if srv_cert is not None:
                    self.__logger.critical("retrieving server pubkey")
                    srv_key = srv_cert.get_pubkey()
                    if srv_key is not None:
                        self.__logger.critical("retrieving server RSA pubkey")
                        srv_rsa_key = srv_key.get_rsa()
            except Exception:
                traceback.print_exc()

            if srv_rsa_key is None:
                return Failure("bad-server-cert")

            if not srv_cert.verify(ROOT_CERT.get_pubkey()):
                return Failure("bad-server-cert")

            self.srv_rsa_key = srv_rsa_key
            self.__logger.critical("generating Nonce")
            from M2Crypto import m2
            nonce = m2.rand_bytes(16)
            self.__logger.critical("encrypting Nonce")
            enonce = digsbyrsa.DIGSBY_RSA_public_encrypt(nonce, srv_rsa_key, M2Crypto.RSA.pkcs1_oaep_padding)

            self.__logger.critical("loading key")
            try:
                self.key = _get_client_key_pem(self.username, self.password)
            except Exception:
                self.key = None

            if self.key is None:
                self.__logger.critical("generating new key")
                self.key = M2Crypto.RSA.gen_key(2048, 0x10001)
                self.__logger.critical("saving new key")
                if not self.key.check_key():
                    raise ValueError("failed to generate key")
                try:
                    _save_client_key_pem(self.key, self.username, self.password)
                except Exception:
                    traceback.print_exc()
            self.__logger.critical("creating buffer")
            buff = M2Crypto.BIO.MemoryBuffer()
            self.__logger.critical("serializing client public key to buffer")
            self.key.save_pub_key_bio(buff)

            self.__logger.critical_s("Nonce: %r", nonce)
            genkey = buff.getvalue()
            self.__logger.critical_s("Key: %r", genkey)
            eKey = pstrAES(nonce, genkey)

            self.__logger.critical("returning response")

            return Response(''.join(pstrIlist([
                            enonce,
                            eKey

                            ])))
        elif self.step == 2:
            self.step = 3

            package_nonce_C_userpub, package_C_AES_C_serverpriv = unpackpstrlist(challenge)
            package_nonce = digsbyrsa.DIGSBY_RSA_private_decrypt(package_nonce_C_userpub, self.key, M2Crypto.RSA.pkcs1_oaep_padding)
            package_C_serverpriv = util.cryptography.decrypt(package_nonce, package_C_AES_C_serverpriv, padchar=None, mode = util.cryptography.Mode.CBC)

            nonce = digsbyrsa.DIGSBY_RSA_public_decrypt(package_C_serverpriv, self.srv_rsa_key, M2Crypto.RSA.pkcs1_padding)

            return Response(pstrAES(nonce, self.password))
        else:
            return Failure("extra-challenge")

    def finish(self,data):
        _unused = data
        return Success(self.username,None,self.authzid)
