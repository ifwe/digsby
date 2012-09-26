from __future__ import division
import digsbysite
import sys
import util
import util.threads.threadpool as threadpool
import util.primitives.bits as bits

from tlslite.utils.rijndael.py_rijndael import encrypt as py_encrypt, decrypt as py_decrypt, rijndael as py_rijndael
from c_rijndael import encrypt as c_encrypt, decrypt as c_decrypt, rijndael as c_rijndael

TRIALS = 10000

print '0', '-'*46, '50', '-'*46, '100'

def try_once(i):
    key = bits.getrandbytes(16)
    bytes = bits.getrandbytes(16)
    py_e = py_encrypt(key, bytes)
    c_e = c_encrypt(key, bytes)

    assert py_e == c_e

    py_d   = py_decrypt(key, py_e)
    c_d    = c_decrypt(key, c_e)
    py_d_c = py_decrypt(key, c_e)
    c_d_py = c_decrypt(key, py_e)

    assert py_d_c == bytes
    assert py_d == bytes
    assert c_d == bytes
    assert c_d_py == bytes

    if ((i*100)/TRIALS) == ((i*100)//TRIALS):
        sys.stdout.write('|')

threadpool.ThreadPool(15)

#print '\nthreaded'
#for i in range(TRIALS):
#    util.threaded(try_once)(i)
#
#print 'sequential'
#for i in range(TRIALS):
#    try_once(i)

key = bits.getrandbytes(16)
c_crypter = c_rijndael(key)
py_crypter = py_rijndael(key)

py_encrypt = lambda _key, x: py_crypter.encrypt(x)
py_decrypt = lambda _key, x: py_crypter.decrypt(x)
c_encrypt = lambda _key, x: c_crypter.encrypt(x)
c_decrypt = lambda _key, x: c_crypter.decrypt(x)

print '\nsequential stateful'
for i in range(TRIALS):
    try_once(i)

#import time
#time.sleep(TRIALS//1000 * 5)
