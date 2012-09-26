from __future__ import with_statement

from struct import pack, unpack
from urllib2 import quote, unquote
from base64 import b64encode, b64decode
from string import zfill
from util import get_func_name, get_func, pythonize, to_storage, Timer, default_timer, fmt_to_dict
from util.auxencodings import fuzzydecode
from logging import getLogger

log = getLogger('msn.util')

from mail.passport import make_auth_envelope

msgtypes = \
{'text/x-msmsgsprofile'                   : 'profile',
 'text/x-msmsgsinitialmdatanotification'  : 'notification',
 'text/x-msmsgscontrol'                   : 'control',
 'text/plain'                             : 'plain',
 'text/x-msmsgsinitialemailnotification'  : 'init_email',
 'text/x-msmsgsemailnotification'         : 'new_email',
 'text/x-msmsgsinvite'                    : 'invite',
 'text/x-msnmsgr-datacast'                : 'datacast',
 'application/x-msnmsgrp2p'               : 'p2p',
 'text/x-clientcaps'                      : 'caps',
 'text/x-msmsgsoimnotification'           : 'oims',}

def utf8_encode(str):
    '''
    utf8_encode(str)

    function for lazy programmers to utf8 encode a string.
    '''
    return unicode(str, "utf-8")

def utf8_decode(str):
    '''
    utf8_decode(str)

    function for lazy programmers to utf8 decode a string.
    '''

    return str.encode("utf-8")

def url_encode(str):
    '''
    url_encode(str)

    function for lazy programmers to url encode a string.
    '''

    return quote(str)

def url_decode(str):
    '''
    url_decode(str)

    function for lazy programmers to url decode a string.
    '''
    return unquote(str)

def base64_encode(s):
    return s.encode('base64').replace('\n', '')

def base64_decode(s):
    return s.decode('base64')

def utf16_encode(str):
    try:
        return unicode(str, 'utf-16')
    except TypeError:
        if isinstance(str, unicode):
            return str.encode('utf-16')
        else:
            return fuzzydecode(s, 'utf-8').encode('utf-16')

def utf16_decode(str):
    return str.decode('utf-16')

mime_to_dict = fmt_to_dict(';','=')
csd_to_dict  = fmt_to_dict(',','=')

def mime_to_storage(str):
    '''
    turn mime headers into a storage object
    '''
    info = mime_to_dict(str)
    for k in info.keys():
        info[pythonize(k)] = info[k]

    return to_storage(info)

def csd_to_storage(str):
    '''
    turn mime headers into a storage object
    '''
    info = csd_to_dict(str)
    for k in info.keys():
        info[pythonize(k)] = info.pop(k)

    return to_storage(info)

def gen_msg_payload(obj, socket, trid, msg, src_account, src_display, *params):
    """
    MSG (MeSsaGe) with a payload.
    There are different payload types, so the appropriate function is called
    to handle that type of payload.
    """
    type = msg.get('Content-Type', None)
    if type:
        type = type.split(';')[0]
    if type not in msgtypes:
        log.critical("Can't handle type %s", type)
        return
    func = get_func(obj, get_func_name(2) + '_%s' % msgtypes[type])
    if func: func(socket, msg, src_account, src_display, *params)
    else: assert False

def dict_to_mime_header(d):
    hdr = ['MIME-Version: 1.0']
    ctype = 'Content-Type'
    ctype_val = d.pop(ctype, 'text/plain; charset=UTF-8')
    hdr.append('%s: %s' % (ctype,ctype_val))

    for k,v in d.items():
        if isinstance(v, dict):
            v = dict_to_mime_val(v)
        hdr.append('%s: %s' % (k,v))

    return '\r\n'.join(hdr) + '\r\n'

def dict_to_mime_val(d):
    s = []
    for k,v in d.items():
        s.append( (('%s=' % k) if k else '') + '%s' % v)

    return '; '.join(s)

def bgr_to_rgb(c):
    assert len(c) <= 6
    s = ('0'*6+c)[-6:]
    b,g,r = [a+b for a,b in zip(s[::2], s[1::2])]
    return r+g+b

def rgb_to_bgr(s):
    assert len(s) == 6
    r,g,b = [a+b for a,b in zip(s[::2], s[1::2])]
    s = b+g+r
    while s.startswith('0'): s = s[1:]
    return s

class FuncProducer(object):
    def __init__(self, f):
        object.__init__(self)
        self.f = f
    def more(self):
        try:     v = self.f()
        except:  v = None
        finally: return v


#
#class MSNTimer(ResetTimer):
#
#    def start(self):
#        Timer.start(self)
#        #self.set_time(self._interval)
#
#    def compute_timeout(self):
#        if self.done_at == None:
#            self._last_computed = default_timer() + 5
#            return self._last_computed
#        else:
#            return Timer.compute_timeout(self)
#
#    def process(self):
#        self.done_at = None
#        self._func(*self._args, **self._kwargs)
#
#    def set_time(self, t):
#        import threading
#        print 'msntimer:', threading.currentThread().getName()
#        with self._cv:
#            self.done_at = default_timer() + t
#            self._cv.notifyAll()
#
#        print 'msntimer out'

def q_untilready(func):
    def wrapper(self, *a, **k):

        if self.state == 'ready' and self.session_id == None and self.type == 'sb':
            print "ERROR STATE DETECTED: CALLING DISCONNECT", self
            self.disconnect()

        print 'in quntilready -- %r' % self

        if self.state != 'ready':
            self._q.append((func, (self,)+a, k))

            if self.state == 'disconnected':
                self.connect()
            elif self.state != 'calling':
                self.invite(self.buddy)
        else:
            return func(self, *a, **k)

    return wrapper

import functools
def dispatch(f):
    @functools.wraps(f)
    def wrapper(self,*a,**k):
        print 'DISPATCH type:',self.type
        fname = '_%s_%s' %(f.func_name.lstrip('_'), self.type)
        if f(self, *a,**k):
            print 'dispatch: calling %s' %fname
            return getattr(self,fname)(*a,**k)
        else:
            print 'dispatch: not calling %s' %fname
            return False
    return wrapper

def HashNonce(nonce):
    import hashlib
    hash = hashlib.sha1(nonce.bytes_le).digest()
    return CreateGuidFromData(2, hash)

def CreateGuidFromData(ver, data):
    import uuid
    import msn.P2P as P2P

    if ver == P2P.Version.V1:
        return uuid.UUID(bytes_le = data[-16:])
    else:
        return uuid.UUID(bytes_le = data[:16])
