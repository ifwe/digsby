'''
Registers auxillary encodings in the codecs module.

>>> 'x\x9cK\xc9L/N\xaa\x04\x00\x08\x9d\x02\x83'.decode('zip')
'digsby'
'''
from peak.util.imports import lazyModule

sys            = lazyModule('sys')
warnings       = lazyModule('warnings')
locale         = lazyModule('locale')
collections    = lazyModule('collections')
urllib         = lazyModule('urllib')
urllib2        = lazyModule('urllib2')
codecs         = lazyModule('codecs')
StringIO       = lazyModule('StringIO')
zipfile        = lazyModule('zipfile')
gzip           = lazyModule('gzip')
htmlentitydefs = lazyModule('htmlentitydefs')
base64         = lazyModule('base64')
#pylzma         = lazyModule('pylzma')

HAVE_LZMA = False #until proven otherwise

ENCODE_LZMA = False

__simplechars_enc = {
                 ord('<') : 'lt',
                 ord('>') : 'gt',
                 #ord("'") : 'apos',
                 ord('"') : 'quot',
                 ord('&') : 'amp',
                 }

__simplechars_dec = dict((v, unichr(k)) for k,v in __simplechars_enc.items())
__simplechars_dec['apos'] = unichr(ord("'"))


_encodings = [
    lambda: locale.getpreferredencoding(),
    lambda: sys.getfilesystemencoding(),
    lambda: sys.getdefaultencoding(),
]

_to_register = [
                ]

def register_codec(name, encode, decode):
    'An easy way to register a pair of encode/decode functions with a name.'
    global _to_register
    def _search(n):
        if n == name:
            return codecs.CodecInfo(name=name, encode=encode, decode=decode)
    _to_register.append(_search)

def install():
    global _to_register
    to_register, _to_register[:] = _to_register[:], []
    for codec in to_register:
        codecs.register(codec)

def fuzzydecode(s, encoding = None, errors = 'strict'):
    '''
    Try decoding the string using several encodings, in this order.
     - the one(s) you give as "encoding"
     - the system's "preferred" encoding
    '''

    if isinstance(s, unicode):
        import warnings; warnings.warn('decoding unicode is not supported!')
        return s

    encodings = [enc() for enc in _encodings]

    if isinstance(encoding, basestring):
        encodings.insert(0, encoding)
    elif encoding is None:
        pass
    else:
        encodings = list(encoding) + encodings

    assert all(isinstance(e, basestring) for e in encodings)

    for e in encodings:
        try:
            res = s.decode(e, errors)
        except (UnicodeDecodeError, LookupError), _ex:
            # LookupError will catch missing encodings
            import warnings; warnings.warn("Exception when fuzzydecoding %r: %r" % (s, _ex))
        else:
            return res

    return s.decode(encoding, 'replace')

def fuzzyencode(s, errors='strict'):
    raise NotImplementedError

def _xml_encode(input, errors='simple'):
    simple   = 'simple' in errors
    origtype = type(input)

    if simple:
        chars = __simplechars_enc
    else:
        chars = htmlentitydefs.codepoint2name
    res = []
    append = res.append
    for ch in input:
        och = ord(ch)
        if och in chars:
            append('&%s;' % chars[och])
        else:
            append(ch)

    return origtype(''.join(res)), len(input)

def _xml_decode(input, errors='strict'):
    data = collections.deque(input)
    res = []
    append = res.append
    popleft = data.popleft
    extendleft = data.extendleft
    name2codepoint = htmlentitydefs.name2codepoint
    while data:
        ch = popleft()
        if ch == '&':
            curtoken = ''
            is_ref = False
            is_num = False
            is_hex = False
            while len(curtoken) < 10 and data: # so we don't loop to the end of the input
                nch = popleft()

                if nch == '#':
                    is_num = True

                if is_num and len(curtoken) == 1 and nch == 'x':
                    is_hex = True

                if nch == ';':
                    is_ref = True
                    break

                curtoken += nch

                if nch == '&':
                    break

            if not is_ref:
                extendleft(reversed(curtoken)) # put it back
                append('&')      # this should not have been here, but we're nice so we'll put it back
                continue

            else:
                if is_num:
                    try:
                        curtoken = curtoken[1:]  # chop the #
                        if is_hex:
                            curtoken = curtoken[1:] # chop the x
                            och = int(curtoken, 16)
                        else:
                            och = int(curtoken, 10)
                        append(unichr(och))
                    except (UnicodeError, ValueError, TypeError):
                        pass
                    else:
                        continue

                if curtoken in name2codepoint:
                    append(unichr(name2codepoint[curtoken]))
                elif curtoken in __simplechars_dec:
                    append(__simplechars_dec[curtoken])
                else:
                    append('&%s;' % (curtoken))
        else:
            append(ch)

    return u''.join(res), len(input)

register_codec('xml', _xml_encode, _xml_decode)


def _pk_decode(input, errors='strict'):
    li = len(input)
    input = StringIO.StringIO(input)
    z = zipfile.ZipFile(input, mode='r')
    zi = z.filelist[0]
    return z.read(zi.filename), li

def _pk_encode(input, errors='strict'):
    li = len(input)
    s = StringIO.StringIO();
    z = zipfile.ZipFile(s, mode='wb', compression=zipfile.ZIP_DEFLATED)
    z.writestr('file', input)
    z.close()
    return s.getvalue(), li

def _gzip_decode(input, errors='strict'):
    li = len(input)
    input = StringIO.StringIO(input)
    g = gzip.GzipFile(mode='rb', fileobj=input)
    return g.read(), li

def _gzip_encode(input, errors='strict'):
    li = len(input)
    s = StringIO.StringIO()
    g = gzip.GzipFile(mode='wb', fileobj=s)
    g.write(input)
    g.close()
    return s.getvalue(), li

def search(name):
    if name == 'gzip':
        name = 'gzip'
        return codecs.CodecInfo(name = name, encode = _gzip_encode, decode = _gzip_decode)
_to_register.append(search)
del search

def _fuzzyzip_decode(input, errors='strict'):
    magic_num = input[:2]
    if magic_num == 'PK':
        return _pk_decode(input, errors=errors)
    elif magic_num == 'BZ':
        return input.decode('bz2'), len(input)
    elif magic_num == '\x1f\x8b':
        return _gzip_decode(input, errors=errors)
    else:
        global HAVE_LZMA
        if HAVE_LZMA:
            try:
                return pylzma.decompress(input), len(input)
            except ImportError:
                HAVE_LZMA = False
            except Exception:
                pass
        return input.decode('zip'), len(input)

def _fuzzyzip_encode(input, errors='strict'):
    li = len(input)
    funcs = [
#             lambda: _pk_encode(input)[0],
#             lambda: _gzip_encode(input)[0],
             lambda: input.encode('bz2'),
             lambda: input.encode('zlib'),
             ]
    if HAVE_LZMA and ENCODE_LZMA:
        funcs.append(lambda: pylzma.compress(input))
    shortest_val = None
    shortest_len = -1
    for func in funcs:
        newval = func()
        newlen = len(newval)
        assert newlen > 0
        if shortest_len < 0 or newlen < shortest_len:
            shortest_len = newlen
            shortest_val = newval
    return shortest_val, li

def search(name):
    if name == 'z' or name == 'fuzzyzip':
        name = 'fuzzyzip'
        return codecs.CodecInfo(name = 'fuzzyzip', encode = _fuzzyzip_encode, decode = _fuzzyzip_decode)

_to_register.append(search)
del search

def search(name):
    if name.startswith('fuzzy'):
        if name == 'fuzzyzip': return None

        encoding = name[len('fuzzy'):] or None

    elif name.endswith('?'):
        encoding = name[:-1] or None

    else:
        return None

    name = 'fuzzy'
    encode = fuzzyencode

    def decode(s, errors='strict'):
        if encoding:
            encs = filter(bool, encoding.split())
        else:
            encs = None
        return fuzzydecode(s, encs, errors), len(s)

    return codecs.CodecInfo(name=name, encode=encode, decode=decode)

_to_register.append(search)
del search

__locale_encoding = lambda: locale.getpreferredencoding()
register_codec('locale',
               lambda s, errors = 'strict': (s.encode(__locale_encoding()), len(s)),
               lambda s, errors = 'strict': (s.decode(__locale_encoding()), len(s)))

__filesysencoding = lambda: sys.getfilesystemencoding()

def _filesys_encode(s, errors = 'strict'):
    if isinstance(s, str):
        return s, len(s)
    else:
        return s.encode(__filesysencoding()), len(s)

def _filesys_decode(s, errors = 'strict'):
    if isinstance(s, unicode):
        return s, len(s)
    else:
        return s.decode(__filesysencoding()), len(s)

register_codec('filesys',
               _filesys_encode,
               _filesys_decode)

del _filesys_encode
del _filesys_decode

def _url_encode(input, errors='strict'):
    return urllib2.quote(input), len(input)

def _url_decode(input, errors='strict'):
    return urllib.unquote_plus(input), len(input)

register_codec('url', _url_encode, _url_decode)

# codec: utf8url
#  encode = utf8 encode -> url encode
#  decode = url decode -> utf8 decode
def _utf8url_encode(input, errors='strict'):
    output = input.encode('utf-8', errors)
    output = urllib2.quote(output)
    return output, len(input)

def _utf8url_decode(input, errors='strict'):
    output = input.encode('ascii', errors)
    output = urllib.unquote_plus(output)
    output = output.decode('utf-8', errors)
    return output, len(input)

register_codec('utf8url', _utf8url_encode, _utf8url_decode)

b64_codecs = {}

b64_names = frozenset(('b64', 'b32', 'b16'))

def make_funcs(encode, decode):
    def _encode(input, errors='strict'):
        return encode(input), len(input)
    def _decode(input, errors='strict'):
        return decode(input), len(input)
    return dict(encode=_encode, decode=_decode)

def search_base64(name):
    if name not in b64_names:
        return
    try:
        return b64_codecs[name]
    except KeyError:
        if name == 'b64':
            codec = b64_codecs[name] = codecs.CodecInfo(name = name, **make_funcs(base64.b64encode, base64.b64decode))
        if name == 'b32':
            codec = b64_codecs[name] = codecs.CodecInfo(name = name, **make_funcs(base64.b32encode, base64.b32decode))
        if name == 'b16':
            codec = b64_codecs[name] = codecs.CodecInfo(name = name, **make_funcs(base64.b16encode, base64.b16decode))
        return codec

_to_register.append(search_base64)
del search_base64

def _binary_encode(input, errors='strict'):
    def align(s):
        return '0'*(8-len(s)) + s
    output = ''.join((align(bin(ord(x))[2:]) for x in input))
    return output, len(input)

def _binary_decode(input, errors='strict'):
    assert not (len(input) % 8)
    #if using for serious work, fix the eval
    output = ''.join((chr(eval('0b' + input[x:x+8])) for x in range(0, len(input), 8)))
    return output, len(input)

register_codec('binary', _binary_encode, _binary_decode)

__all__ = []


if __name__ == '__main__':
    install()

    def gen_rand_str(length = 5000):
        from random import randint, choice as randchoice
        from string import ascii_letters

        ents = list(__simplechars_dec)

        data = []
        append = data.append
        for x in xrange(length):
            r = randint(0, 10)
            if r == 0:
                append('&%s;' % randchoice(ents))
            elif r == 1:
                append('&%d;' % randint(0, 65535))
            elif r == 2:
                append('&%x;' % randint(0, 65535))
            if r > 3:
                append(randchoice(ascii_letters))

        return ''.join(data)

    strings = [gen_rand_str() for x in xrange(100)]
    results1 = []
    results2 = []

    from time import clock

    def timeit(func):
        before = clock()
        func()
        return clock() - before

    def foo(encoding, res):
        for s in strings:
            res.append(s.decode(encoding))

    print 'xml',  timeit(lambda: foo('xml', results1))
    print 'xml2', timeit(lambda: foo('xml2', results2))
    assert results1 == results2
