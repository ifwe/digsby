""" Utility functions and classes to deal with low level bytes, formatting, etc in the MySpace IM protocol. """
import logging
import path
import lxml.etree as etree
import util
from util import odict, this_list, try_this
from util.primitives.bits import rol
from hashlib import sha1
from base64 import b64decode
log = logging.getLogger('msim.util')
KEYLEN = 128


def escape(s):
    if isinstance(s, unicode):
        s = s.encode('utf8')
    return s.replace('/', '/1').replace('\\', '/2')


unescape = lambda s: s.replace('/2', '\\').replace('/1', '/')
from M2Crypto.RC4 import RC4


def crypt(nc, password, data=''):
    key, salt1 = make_key(nc, password)
    return RC4(key).update(salt1 + data)


def make_key(nc, password):
    salt = b64decode(nc)
    salt1, salt2 = salt[:32], salt[32:]
    key = sha1(sha1(password.encode('utf-16-le')).digest() + salt2).digest()
    key, rest = key[:KEYLEN / 8], key[KEYLEN / 8:]
    return key, salt1


def decrypt(nonce, password, data):
    key, salt1 = make_key(nonce, password)
    return RC4(key).update(b64decode(data))[len(salt1):]


def roflcopter(chlnum, sesskey, uid):
    return rol(sesskey, 5) ^ rol(uid, 9) ^ chlnum


class msmsg(odict):

    class CMD(object):

        Get = 1
        Set = 2
        Delete = 3
        Reply = 0x100
        Action = 0x200
        Error = 0x400

    def __init__(self, d_or_s='', **k):
        from_string = False
        if isinstance(d_or_s, basestring):
            self._orig = d_or_s
            d = self.parse(d_or_s)
            from_string = True
        else:
            d = d_or_s
        odict.__init__(self, d, **k)
        if from_string:
            for key in ('body', 'msg'):
                if key in self:
                    self[key] = unescape(str(self[key]))
        for key in self:
            if try_this(lambda: '\x1c' in self[key], False) or key == 'body':
                self[key] = msdict(self[key])
            for key in self:
                if isinstance(self[key], basestring):
                    try:
                        self[key] = eval(self[key], {}, {})
                    except Exception:
                        pass

    @property
    def mtype(self):
        return self._keys[0]

    @classmethod
    def parse(self, s):
        assert isinstance(s, basestring)
        if not s:
            return {}
        assert s.endswith('\\final\\')
        data = s.strip('\\').split('\\')
        return zip(data[::2], data[1::2])

    def serialize(self):
        return '\\%s\\final\\' % '\\'.join('\\'.join((str(k), str(v))) for (k, v) in self.iteritems())


class msdict(list):

    """ A list, masquerading as a dictionary. Can be turned into a string suitable for inclusion in an msmsg """

    delim1 = '\x1c'
    delim2 = '='

    def __init__(self, _s='', **k):
        if isinstance(_s, msdict):
            list.__init__(self)
            self[:] = _s[:]
        elif k:
            list.__init__(self, k.items())
        elif _s:
            list.__init__(self, (entry.strip().split(self.delim2, 1) for entry in _s.split(self.delim1)))
        else:
            list.__init__(self)

    def __getitem__(self, key):
        try:
            return list.__getitem__(self, key)[1]
        except Exception:
            r = filter(lambda x: x[0] == key, self)
            if not r:
                raise KeyError(key)
            elif len(r) == 1:
                return r[0][1]
            else:
                return [x[1] for x in r]

    def __setitem__(self, key, val):
        prevs = filter(lambda x: x[0] == key, self)
        if prevs:
            prev = prevs[0]
            prev[1] = val
        else:
            self.append([key, val])

    def __str__(self):
        try:
            return self.delim1.join('%s%s%s' % (k, self.delim2, escape(v)) for (k, v) in self.items())
        except Exception:
            print repr(self)
            raise

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def items(self):
        return self[:]

    def keys(self):
        return [x[0] for x in self if x not in this_list()]

    def values(self):
        return [x[1] for x in self]


class pipe_list(list):

    delim = '|'

    def __init__(self, s=''):
        if s:
            if isinstance(s, basestring):
                parts = [unescape(x) for x in s.split('|')]
            else:
                parts = s
            list.__init__(self, parts)
        else:
            list.__init__(self)

    def __str__(self):
        return self.delim.join(escape(x) for x in self)


class pipe_dict(msdict):

    delim = '|'

    def __init__(self, s=''):
        if s:
            parts = pipe_list(s)
            keys = parts[0::2]
            vals = parts[1::2]
            list.__init__(self, zip(keys, vals))
        else:
            list.__init__(self)

    def __str__(self):
        try:
            return self.delim.join(escape(str(x)) for x in util.flatten(self.items()))
        except Exception:
            print 'couldnt str(%r)' % repr(self)
            raise


def obj_list_from_msdict(d):
    if not d:
        return []
    _start_key = d.keys()[0]
    all_objs = []
    for k, v in d.items():
        if k == _start_key:
            this_obj = {k: v}
            all_objs.append(this_obj)
            continue
        else:
            this_obj[k] = v
    return all_objs


def int_to_status(i):
    '''
    0 means invisible.
    1 means online
    2 means idle
    5 means away
    '''

    s = {0: 'offline',
         1: 'available',
         2: 'idle',
         5: 'away', }.get(i)

    return s


def status_to_int(s):
    i = {'available': 1,
         'online': 1,
         'idle': 2,
         'away': 5,
         'invisible': 0,
         'offline': 0, }.get(s, 5)
    return i


def minihtml_to_html(message):
    try:
        doc = etree.fromstring(message)
    except Exception, e:
        log.error('Error parsing message as xml. message = %r, error = %r', message, e)
        return message
    xslt_doc = etree.parse(_get_mini_xslt_file_path())
    transform = etree.XSLT(xslt_doc)
    return etree.tostring(transform(doc))


def _get_mini_xslt_file_path():
    return path.path(__file__).parent / 'res' / 'mini_to_html.xsl'


def html_to_minihtml(message, format):
    from lxml.builder import E
    parts = [message]
    bg_color_tuple = format.get('backgroundcolor')
    if bg_color_tuple is None:
        bg_color = 'transparent'
    else:
        bg_color = 'rgba(%s, %s, %s, %s)' % tuple(bg_color_tuple)

    doc = \
    E.p(
        E.f(
            E.c(
                E.b(

                    *parts,

                    v=bg_color),
                v='rgba(%s, %s, %s, %s)' % tuple(format.get('foregroundcolor', (0, 0, 0, 255)))),
            f=format.get('face', 'Times'),
            h=str((int(format.get('size', '16')) * 96) / 72),
            s=str(format.get('bold', False) | (format.get('italic', False) << 1) | (format.get('underline', False) << 2)),
        )
    )

    log.info('message format: %r', format)
    return etree.tostring(doc)
