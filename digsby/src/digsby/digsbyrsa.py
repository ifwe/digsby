import M2Crypto

RSA_size = len
def DIGSBY_RSA_blocksize(rsa, padding):
    '''
        int DIGSBY_RSA_blocksize(RSA *rsa, int padding){
            switch (padding){
            case RSA_PKCS1_PADDING:
            case RSA_SSLV23_PADDING:
                return RSA_size(rsa) - 11;
            case RSA_PKCS1_OAEP_PADDING:
                return RSA_size(rsa) - 42; //docs say 41, but 41 doesn't work.
            default:
                return RSA_size(rsa);
            }
        }
    '''
    return RSA_size(rsa) - {M2Crypto.RSA.pkcs1_padding:11, M2Crypto.RSA.pkcs1_padding:42}.get(padding, 0)

def DIGSBY_RSA_numblocks(flen, blocksize):
    '''
        int DIGSBY_RSA_numblocks(int flen, int blocksize) {
            div_t numblocks;
            if (!(flen && blocksize)){
                return -1;
            }
            numblocks = div(flen, blocksize);
            return numblocks.rem ? (numblocks.quot + 1) : numblocks.quot;
        }
    '''
    if flen <=0 or blocksize <= 0:
        raise ValueError("need both positive flen and blocksize")
    quot, rem = divmod(flen, blocksize)
    return quot + 1 if rem else quot

def DIGSBY_RSA_size(flen, rsa, padding):
    '''
        int DIGSBY_RSA_size(int flen, RSA *rsa, int padding) {
            int blocksize, numblocks;
            blocksize = DIGSBY_RSA_blocksize(rsa, padding);
            numblocks = DIGSBY_RSA_numblocks(flen, blocksize);
            if (numblocks <= 0) {
                return -1;
            }
            return numblocks * RSA_size(rsa);
        }
    '''
    blocksize = DIGSBY_RSA_blocksize(rsa, padding)
    numblocks = DIGSBY_RSA_numblocks(flen, blocksize)
    if (numblocks <= 0):
        raise ValueError('bad number of blocks')
    return numblocks * RSA_size(rsa)

def DIGSBY_RSA_size_inverse(flen, rsa, padding):
    '''
        int DIGSBY_RSA_size_inverse(int flen, RSA *rsa, int padding) {
            int blocksize, numblocks;
            blocksize = DIGSBY_RSA_blocksize(rsa, padding);
            numblocks = flen / RSA_size(rsa);

            if (numblocks <= 0) {
                return -1;
            }
            return numblocks * blocksize;
        }
    '''
    blocksize = DIGSBY_RSA_blocksize(rsa, padding)
    numblocks = flen / RSA_size(rsa)
    if (numblocks <= 0):
        raise ValueError('bad number of blocks')
    return numblocks * blocksize;

def DIGSBY_RSA_public_encrypt(from_, rsa, padding):
    '''
        int DIGSBY_RSA_public_encrypt(int flen, const unsigned char *from, unsigned char *to, RSA *rsa, int padding) {
            int m, c;
            int status;
            int blocksize, numblocks;
            int to_encrypt, left;
            blocksize = DIGSBY_RSA_blocksize(rsa, padding);
            numblocks = DIGSBY_RSA_numblocks(flen, blocksize);
            if (numblocks <= 0) {
                return -1;
            }
            m = 0;
            c = 0;
            while (m < flen) {
                left = flen - m;
                to_encrypt = blocksize > left ? left : blocksize;
                status = RSA_public_encrypt(to_encrypt, from + m, to + c, rsa, padding);
                if (status <= 0){
                    return -1;
                }
                c += status;
                m += blocksize;
            }
            return c;
        }
    '''
    blocksize = DIGSBY_RSA_blocksize(rsa, padding)
    numblocks = DIGSBY_RSA_numblocks(len(from_), blocksize)
    if (numblocks <= 0):
        raise ValueError('bad number of blocks')
    from StringIO import StringIO
    to_ = StringIO()
    from_ = StringIO(from_)
    while (from_.tell() < from_.len):
        to_.write(rsa.public_encrypt(from_.read(blocksize), padding))
    return to_.getvalue()

def DIGSBY_RSA_private_encrypt(from_, rsa, padding):
    blocksize = DIGSBY_RSA_blocksize(rsa, padding)
    numblocks = DIGSBY_RSA_numblocks(len(from_), blocksize)
    if (numblocks <= 0):
        raise ValueError('bad number of blocks')
    from StringIO import StringIO
    to_ = StringIO()
    from_ = StringIO(from_)
    while (from_.tell() < from_.len):
        to_.write(rsa.private_encrypt(from_.read(blocksize), padding))
    return to_.getvalue()

def DIGSBY_RSA_private_decrypt(from_, rsa, padding):
    blocksize = RSA_size(rsa)
    numblocks = DIGSBY_RSA_numblocks(len(from_), blocksize)
    if (numblocks <= 0):
        raise ValueError('bad number of blocks')
    from StringIO import StringIO
    to_ = StringIO()
    from_ = StringIO(from_)
    while (from_.tell() < from_.len):
        to_.write(rsa.private_decrypt(from_.read(blocksize), padding))
    return to_.getvalue()

def DIGSBY_RSA_public_decrypt(from_, rsa, padding):
    blocksize = RSA_size(rsa)
    numblocks = DIGSBY_RSA_numblocks(len(from_), blocksize)
    if (numblocks <= 0):
        raise ValueError('bad number of blocks')
    from StringIO import StringIO
    to_ = StringIO()
    from_ = StringIO(from_)
    while (from_.tell() < from_.len):
        to_.write(rsa.public_decrypt(from_.read(blocksize), padding))
    return to_.getvalue()

__all__ = [
           'DIGSBY_RSA_public_encrypt',
           'DIGSBY_RSA_public_decrypt',
           'DIGSBY_RSA_private_encrypt',
           'DIGSBY_RSA_private_decrypt'
           ]

def make_x509():
    import M2Crypto
    t = M2Crypto.ASN1.ASN1_UTCTIME()
    t.set_time(0)
    x = M2Crypto.X509.X509()
    rsa = M2Crypto.RSA.gen_key(512, 0x10001)
    pk = M2Crypto.EVP.PKey()
    pk.assign_rsa(rsa)
    del rsa
    x.set_pubkey(pk)
    x.set_not_after(t)
    x.set_not_before(t)
    x.sign(pk, 'sha1')
    return x
