import mapping
import HTMLParser
import StringIO
import re
import string
import sys
import traceback

try:
    _
except NameError:
    _ = lambda x: x

def strftime_u(timeobj, fmt):
    '''
    strftime_u(datetime timeobj, str fmt) -> unicode
    Returns a unicode string of the date. Uses locale encoding to decode.
    '''

    if isinstance(fmt, unicode):
        fmt = fmt.encode('utf-8')
    return timeobj.strftime(fmt).decode('locale')

def strfileobj(writefunc):
    s = StringIO()
    writefunc(s)
    return s.getvalue()

def strincrement(s): return str(int(s)+1)

def tuple2hex(t):
    return ''.join('%02x' % c for c in t[:3])

def format_xhtml(s, f):
    'Turns "format storages" and a string into a <span> with css styles.'

    s = s.replace('\n', '<br />')

    font_attrs = filter(lambda e: bool(e),
                        ['bold'   if f.bold      else '',
                         'italic' if f.italic    else'',
                         ('%spt' % f.size) if f.size is not None else '',
                         f.face if f.face is not None else ''])

    style_elems = filter(lambda s: bool(s), [
        ('color: #%s' % tuple2hex(f.foregroundcolor)) if f.foregroundcolor is not None else '',
        ('background-color: #%s' % tuple2hex(f.backgroundcolor)) if f.backgroundcolor not in (None, (255, 255, 255, 255)) else '',
        'text-decoration: underline'  if f.underline else '',
        ('font: ' + ' '.join(font_attrs)) if font_attrs else ''])

    if style_elems:
        span_style = '; '.join(style_elems)
        return '<span style="%s;">%s</span>' % (span_style, s)
    else:
        return s

fontsizes = (
    lambda x: x < 8,
    lambda x: x == 8,
    lambda x: x in (9, 10),
    lambda x: x in (11, 12, 13),
    lambda x: x in (14, 15, 16),
    lambda x: x in (17, 18, 19),
    lambda x: x > 19,
)

def Point2HTMLSize(n):
    for i, f in enumerate (fontsizes):
        if f(n):
            return i + 1

    assert False

# html stripper...make sure to pay her well ;-)

class StrippingParser(HTMLParser.HTMLParser):

    # These are the HTML tags that we will leave intact
    from htmlentitydefs import entitydefs #@UnusedImport
    def __init__(self, valid_tags=()):
        HTMLParser.HTMLParser.__init__(self)
        self.valid_tags = valid_tags
        self.result = u""
        self.endTagList = []

    def handle_data(self, data):
        if data:
            self.result = self.result + data

    def handle_starttag(self, tag, attrs):
        if tag == 'br':
            self.result += '\n'

    def handle_charref(self, name):
        self.result += unichr(int(name))
        #self.result += "%s&#%s;" % (self.result, name)

    def handle_entityref(self, name):
        self.result += self.entitydefs.get(name,'')

    def unknown_starttag(self, tag, attrs):
        """ Delete all tags except for legal ones """
        if tag in self.valid_tags:
            self.result = self.result + '<' + tag
            for k, v in attrs:
                if string.lower(k[0:2]) != 'on' and string.lower(v[0:10]) != 'javascript':
                    self.result = u'%s %s="%s"' % (self.result, k, v)
            endTag = '</%s>' % tag
            self.endTagList.insert(0,endTag)
            self.result = self.result + '>'

    def unknown_endtag(self, tag):
        if tag in self.valid_tags:
            self.result = "%s</%s>" % (self.result, tag)
            remTag = '</%s>' % tag
            self.endTagList.remove(remTag)

    def cleanup(self):
        """ Append missing closing tags """
        for j in range(len(self.endTagList)):
                self.result = self.result + self.endTagList[j]

parser = StrippingParser()

def scrape_clean(text):
    '''
    Removes HTML markup from a text string.

    @param text The HTML source.
    @return The plain text.  If the HTML source contains non-ASCII
            entities or character references, this is a Unicode string.
    '''
    def fixup(m):
        text = m.group(0)
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        elif text[:1] == "&":
            import htmlentitydefs
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)

def strip_html(s, valid_tags=()):
    "Strip HTML tags from string s, leaving valid_tags."
    parser.valid_tags = valid_tags
    parser.feed(s)
    parser.close()
    parser.cleanup()
    result = parser.result
    parser.result = ""
    return result

def strip_html2(s):
    '''
    Strips out HTML with the BeautifulSoup library.

    >>> strip_html2('<html><body><b>Some <i>ugly</i></b> html.</body></html>')
    u'Some ugly html.'
    '''
    if not s: return s

    from util.BeautifulSoup import BeautifulSoup
    soup = BeautifulSoup(s)

    text_pieces = []
    for pc in soup.recursiveChildGenerator():
        if isinstance(pc, unicode):
            text_pieces.append(pc)
        elif pc.name == 'br':
            text_pieces.append('\n')

    return ''.join(text_pieces)

def strip_html_and_tags(s, invalid_tags):
    '''
    content between "invalid_tags" is removed
    '''
    if not s: return s

    from util.BeautifulSoup import BeautifulSoup
    soup = BeautifulSoup(s.replace('<br>','\n').replace('<br/>','\n').replace('<br />', '\n'))
    for tag in invalid_tags:
        for result in soup.findAll(name=tag):
            result.replaceWith("")

    return ''.join(e for e in soup.recursiveChildGenerator()
                   if isinstance(e,unicode))

def srv_str_to_tuple(address, default_port = None):
    if address.find(':') != -1:
        host, port = address.split(':')
        port = int(port)
    else:

        if default_port is None:
            raise ValueError('No port found in %r and no default port supplied.', address)

        host = address
        port = default_port

    return (host, port)

def get_between(s, start_str, end_str):
    '''
    Returns the portion of s between start_str and end_str, or None
    if
    '''

    start_i = s.find(start_str)
    end_i = s.find(end_str, start_i + len(start_str))

    if start_i > end_i or (-1 in (start_i, end_i)):
        return None
    else:
        return s[start_i+len(start_str):end_i]

def strlist(s):
    'Strips comments from a multiline string, then splits on whitespace.'

    lines = s.split('\n')
    for y, line in enumerate(lines):
        i = line.find('#')
        if i != -1: lines[y] = line[:i]
    return '\n'.join(lines).split()

# matches anything ${between} to group "expr"
_curlymatcher = re.compile(r'\$\{(?P<expr>.*?)\}', re.DOTALL)

def curly(s, frame = 2, source = None):
    def evalrepl(match, source = source):
        f = sys._getframe(frame)

        if source is None:
            source = {}
        elif isinstance(source, dict):
            source = source
        elif hasattr(source, '__dict__'):
            source = source.__dict__
        elif hasattr(source, '__slots__'):
            source = dict((x, getattr(source, x)) for x in source.__slots__)
        else:
            raise AssertionError('not sure what to do with this argument: %r' % source)

        locals = mapping.dictadd(f.f_locals, source)
        try:
            res = eval(match.group('expr'), f.f_globals, locals)
        #except NameError:
        except Exception, e:
            traceback.print_exc()
            #print >> sys.stderr, 'Error parsing string: ' + s
            #print >> sys.stderr, 'locals:'
            #from pprint import pformat
            #try: print >> sys.stderr, pformat(locals)

            return ''

            raise e
        return u'%s' % (res,)

    return _curlymatcher.sub(evalrepl, s)

def cprint(s):
    print curly(s, frame = 3)

def replace_newlines(s, replacement=' / ', newlines=(u"\n", u"\r")):
    """
    Used by the status message display on the buddy list to replace newline
    characters.
    """
    # turn all carraige returns to newlines
    for newline in newlines[1:]:
        s = s.replace(newline, newlines[0])

    # while there are pairs of newlines, turn them into one
    while s.find(newlines[0] * 2) != -1:
        s = s.replace( newlines[0] * 2, newlines[0])

    # replace newlines with the newline_replacement above
    return s.strip().replace(newlines[0], replacement)

SI_PREFIXES = ('','k','M','G','T','P','E','Z','Y')
IEC_PREFIXES = ('','Ki','Mi','Gi','Ti','Pi','Ei','Zi','Yi')

def nicebytecount(bytes):
    '''
    >>> nicebytecount(1023*1024*1024)
    '1,023 MB'
    >>> nicebytecount(0)
    '0 B'
    >>> nicebytecount(12.34*1024*1024)
    '12.34 MB'
    '''
    bytes = float(bytes)
    if not bytes:
        count = 0
    else:
        import math
        count = min(int(math.log(bytes, 1024)), len(SI_PREFIXES)-1)
    bytes = bytes / (1024 ** count)
    return '{bytes:.4n} {prefix}B'.format(bytes=bytes, prefix=SI_PREFIXES[count])

class istr(unicode):
    def __new__(self, strng):
        return unicode.__new__(self, _(strng))
    def __init__(self, strng):
        self.real = strng
    def __cmp__(self, other):
        if type(self) == type(other):
            return cmp(self.real, other.real)
        else:
            return unicode.__cmp__(self, other)
    def __eq__(self, other):
        return not bool(self.__cmp__(other))

def nicetimecount(seconds, max=2, sep=' '):

    seconds = int(seconds)

    if seconds < 0:
        return '-' + nicetimecount(abs(seconds), max=max, sep=sep)

    minutes, seconds = divmod(seconds, 60)
    hours, minutes   = divmod(minutes, 60)
    days, hours      = divmod(hours, 24)
    years, days      = divmod(days, 365) #@UnusedVariable

    i = 0
    res = []
    for thing in 'years days hours minutes seconds'.split():
        if not vars()[thing]:
            continue
        else:
            res.append('%d%s' % (vars()[thing], thing[0]))
            i += 1

        if i == max:
            break
    else:
        if not res:
            res = ['0s']

    return sep.join(res)

#pascal strings
def unpack_pstr(s):
    from struct import unpack
    l = unpack('B', s[0])[0]
    if l > (len(s) - 1):
        raise ValueError(s)
    return s[1:1+l], s[1+l:]

def pack_pstr(s):
    from struct import pack
    return pack('B', len(s)) + s

def preserve_newlines(s):
    return preserve_whitespace(s, nbsp=False)

_whitespace_pattern = re.compile(r'(\s{2,})')

def _whitespace_repl(match):
    return len(match.group(1)) * '&nbsp;'

def preserve_whitespace(s, nbsp=True):
    '''
    HTML condenses all spaces, tabs, newlines into a single space when rendered. This function
    replaces multiple space/tab runs into &nbsp; entitities and newlines with <br />

    Runs of whitespace are replaced with an equal number of &nbsp; - this means two spaces get
    converted to &nbsp;&nbsp; but a single space is left alone.
    '''
    s = s.replace('\r\n', '\n').replace('\n', '<br />')

    if not nbsp:
        return s

    return _whitespace_pattern.sub(_whitespace_repl, s)

class EncodedString(object):
    '''
    Attempt at making a new string type that keeps track of how it's encoded.
    Hopefully we'll be able to know that '<3' can't go into the IM window but
    '<font size=10>my text</font>' can.
    '''
    def __init__(self, s, encodings=None):
        if encodings is None:
            encodings = ()

        self.encodings = tuple(encodings)
        self._data = s

    def encode(self, encoding):
        '''
        Encode this string's data with encoding, returning a new EncodedString object.

        >>> x = EncodedString(u'<3').encode('xml')
        >>> x, type(x)
        (<EncodedString (u'&lt;3') encodings=('xml',)>, <class '__main__.EncodedString'>)
        '''
        return EncodedString(self._data.encode(encoding), self.encodings+(encoding,))

    def decodeAll(self):
        '''
        Decode this string down to its data. Just calls .decode() over and over again.

        >>> x = EncodedString(u'%26lt%3B%26gt%3B%26amp%3B', ['xml', 'url'])
        >>> unicode(x.decodeAll())
        u'<>&'
        '''
        s = self
        while s.encodings:
            s = s.decode()
        return s

    def decode(self):
        '''
        Decode a single encoding. Since this object tracks its codecs, specifying a codec
        is not allowed.

        >>> x = EncodedString(u'%26lt%3B%26gt%3B%26amp%3B', ['xml', 'url'])
        >>> y = x.decode()
        >>> z = y.decode()
        >>> map(unicode, (x,y,z))
        [u'%26lt%3B%26gt%3B%26amp%3B', u'&lt;&gt;&amp;', u'<>&']
        '''
        encoding = self.encodings[-1]
        newencodings = self.encodings[:-1]
        return EncodedString(self._data.decode(encoding), newencodings)

    def __getattr__(self, attr):
        '''
        Delegate to data's methods. Useful? maybe.
        '''
        if attr in ('encodings', '_data', 'encode', 'decode', 'decodeAll'):
            return object.__getattribute__(self, attr)
        else:
            return self._data.__getattribute__(attr)

    def __repr__(self):
        return '<%s (%s) encodings=%r>' % (type(self).__name__, repr(self._data), self.encodings)

    def __str__(self):
        if type(self._data) is str:
            return self._data
        else:
            raise TypeError('%r cannot be implicitly converted to str')

    def __unicode__(self):
        if type(self._data) is unicode:
            return self._data
        else:
            raise TypeError('%r cannot be implicitly converted to unicode')

estring = EncodedString

def try_all_encodings(s):
    '''
    You'd better have a good reason to use this.
    '''
    successes = []
    import encodings
    codecs = set(encodings.aliases.aliases.values())
    for c in codecs:
        try:
            decoded = s.decode(c)
        except (Exception,):
            continue
        else:
            if isinstance(decoded, unicode):
                try:
                    recoded = decoded.encode('utf8')
                except UnicodeEncodeError:
                    continue
            else:
                continue
            if isinstance(recoded, str) and isinstance(decoded, unicode):
                # we have a winner!
                codec = c
                successes.append((s,codec,decoded,recoded))
    else:
        decoded = recoded = codec = None

    return successes

def saferepr(obj):
    try:
        return repr(obj)
    except Exception:
        try:
            return '<%s>' % obj.__class__.__name__
        except Exception:
            return '<??>'

def wireshark_format(data):
    out = StringIO()

    safe = (set(string.printable) - set(string.whitespace)) | set((' '),)

    def hex(s):
        return ' '.join('%02X' % ord(ch) for ch in s)
    def safe_bin(s):
        return ''.join((ch if ch in safe else '.') for ch in s)

    def pad(s, l, ch=' '):
        return s + (ch * (l - len(s)))

    w = out.write
    space = ' ' * 4

    while data:
        chunk1, chunk2, data = data[:8], data[8:16], data[16:]
        w(pad(hex(chunk1), 24));      w(space)
        w(pad(hex(chunk2), 24));      w(space)
        w(pad(safe_bin(chunk1), 8));  w(space)
        w(pad(safe_bin(chunk2), 8));  w('\n')

    return out.getvalue()

#these next two came from introspect
def to_hex(string, spacer=" "):
    """
    Converts a string to a series of hexadecimal characters.

    Use the optional spacer argument to define a string that is placed between
    each character.

    Example:

    >>> print to_hex("hello!", ".")
    68.65.6C.6C.6F.21

    >>> print to_hex("boop")
    62 6F 6F 70

    """
    return spacer.join('%02X' % ord(byte) for byte in string)

def byte_print(string_, spacer=" "):
    import string as strng
    output = ''
    for i in range(len(string_)/16+1):
        line = string_[i*16: i*16 + 16]
        pline = ''.join(x if x in strng.printable else '.' for x in line)
        pline = pline.replace('\n', ' ')
        pline = pline.replace('\r', ' ')
        pline = pline.replace('\t', ' ')
        pline = pline.replace('\x0b', ' ')
        pline = pline.replace('\x0c', ' ')
        output += to_hex(line) + ' ' + pline + '\n'
    return output

def string_xor(x, y, adjustx=False, adjusty=False):
    assert isinstance(x, bytes) and isinstance(y, bytes)
    assert not (adjustx and adjusty)
    if adjusty:
        x, y, adjustx = y, x, True
    if adjustx:
        x = ((int(float(len(y))/float(len(x))) + 1)*x)[:len(y)]
    assert len(x) == len(y)
    return ''.join(chr(ord(a) ^ ord(b)) for a,b in zip(x, y))

def dequote(s):
    if isinstance(s, basestring):
        if (s.startswith('"') and s.endswith('"')) or \
           (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
    return s

def indefinite_article(s):
    # i18n ... help!
    if s.lower()[0] in _('aeiou'):
        article = _('an')
    else:
        article = _('a')

    return _('%(article)s %(s)s') % locals()


def abbreviate_dotted(dotted_string, desired_len=-1,
                      bias_left = 0,
                      bias_right = 0,
                      biases = None):
    '''
    abbreviates a string like:
    alpha.beta.gamma
    alpha.b.gamma
    a.b.gamma
    ab.gamma
    ab.g
    abg
    a

    bias determines which sections get shortened last(+)/first(-)
    left 1, right 1
    default.foo.com -> default.f.com
    left -1, right -1
    negative.foo.com -> n.foo.c

    if more fine grained control is desired, a sequence can be provided,
    of the form: [(position, weight)].  position is 0-based.
    with [(2, -5)]:
    weighted.foo.com -> weighted.foo.c
    when "biases" is provided, left and right will be ignored.
    otherwise, they determine the number of sections on each side for which
    it is desirable to keep (or get rid of).

    TODO: add an ellipsis mode, for "alpha.beta.g..."

    >>> print abbreviate_dotted("alpha.beta.gamma", 10)
    al.b.gamma
    >>> print abbreviate_dotted("alpha.beta.gamma", 4)
    ab.g
    >>> print abbreviate_dotted("alpha.beta.gamma", 8)
    a.b.gamm
    >>> print abbreviate_dotted("alpha.beta.gamma", 0)
    <BLANKLINE>
    '''

    if any((bias_left, bias_right, biases)):
        raise NotImplementedError

    remove = len(dotted_string) - desired_len

    split   = dotted_string.split('.')

    if len(split) >= desired_len:
        return ''.join([s[0] for s in split])[:desired_len]

    lengths = [len(section) for section in split]
    while remove and max(lengths) > 1:
        notone = [i for i in lengths if i != 1]
        val = min(notone)
        idx = lengths.index(val)
        if val > remove:
            newval = val - remove
        else:
            newval = 1
        lengths[idx] = newval
        remove -= val - newval

    return ''.join([s[:i] for s,i in zip(split[:remove+1], lengths[:remove+1])]) + \
           '.' + '.'.join([s[:i] for s,i in zip(split[remove+1:], lengths[remove+1:])])


def merge_xml(a, b, **opts):
    import lxml.etree as etree
    import lxml.objectify as objectify
    import copy

    if isinstance(a, objectify.ObjectifiedElement):
        # Objectify elements are not editable.
        a = etree.tostring(a)

    if isinstance(a, basestring):
        a = etree.fromstring(a)

    if isinstance(b, objectify.ObjectifiedElement):
        # Objectify elements are not editable.
        b = etree.tostring(b)

    if isinstance(b, basestring):
        b = etree.fromstring(b)

    if not isinstance(a, etree._Element):
        raise TypeError("Need string or lxml element!", a)

    if not isinstance(b, etree._Element):
        raise TypeError("Need string or lxml element!", b)

    if a.tag != b.tag:
        raise Exception("Tags don't match, can't merge!", a, b)

    text_replace = opts.get("text", 'replace') == 'replace'

    a.attrib.update(dict(b.attrib))
    if a.text is None or text_replace:
        a.text = b.text
    elif b.text is not None:
        a.text += b.text

    if a.tail is None or text_replace:
        a.tail = b.tail
    elif b.tail is not None:
        a.tail += b.tail

    merged_tags = []
    a_child = b_child = None
    for a_child in a.iterchildren():
        for b_child in b.iterfind(a_child.tag):
            merged_tags.append(a_child.tag)
            merge_xml(a_child, b_child)

    a_child = b_child = None
    for b_child in b.iterchildren():
        if b_child.tag in merged_tags:
            continue

        matches = 0
        for a_child in a.iterfind(b_child.tag):
            matches += 1
            merge_xml(a_child, b_child)

        if matches == 0:
            a.append(copy.deepcopy(b_child))

    return a

if __name__ == '__main__':
    import locale
    locale.setlocale(locale.LC_ALL, 'US')
    import doctest
    doctest.testmod(verbose=True)



