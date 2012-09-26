'''

Parses and creates Yahoo formatting codes.

  tohtml - returns valid XHTML from a Yahoo message with formatting codes
  format - returns a string with formatting codes from a message and a "format storage"

'''
import traceback
import re
from util import flatten
import util.primitives.bits as bits

color = lambda hex: ('font color="#' + hex + '"', 'font')

codes = {
    1: 'b',
    2: 'i',
    4: 'u',

    'l': '', # ignore link markers
}

color_codes = {
     30: '000000',
     31: '0000FF',
     32: '008080',
     33: '808080',
     34: '008000',
     35: 'FF0080',
     36: '800080',
     37: 'FF8000',
     38: 'FF0000',
     39: '808000',
}

rereplace = [
    # <font>
    ('&lt;font (.+?)&gt;', '<font %s>'),
    ('&lt;/font&gt;',      '</font>'),

    # <s>
    ('&lt;s&gt;',           '<s>'),
    ('&lt;/s&gt;',          '</s>'),

    # ignore alt and fade tags
    ('&lt;alt (?:.+?)&gt;', ''),
    ('&lt;/alt&gt;',      ''),
    ('&lt;fade (?:.+?)&gt;', ''),
    ('&lt;/fade&gt;',      ''),

]


def hexstr_to_tuple(hexstr):
    return tuple([ord(a) for a in bits.hex2bin(' '.join(''.join(x) for x in zip(hexstr[::2], hexstr[1::2])))])

color_lookup = dict((hexstr_to_tuple(v), str(k)) for k, v in color_codes.iteritems())

format_codes = {
     #
     # codes following \x1b bytes in the formatting stream
     #
     # code: (start tag, end tag)
     #
     '1':    ('b', 'b'),
     '2':    ('i', 'i'),
     '4':    ('u', 'u'),
     '#':    ((lambda hex: 'font color="#%s"' % hex),               'font'),
     'face': ((lambda face: 'font face="%s"' % face),               'font'),
     'size': ((lambda size: 'font style="font-size: %spt"' % size), 'font'),
}

format_lookup = {'b': '1',
                 'i': '2',
                 'u': '4'}

format_codes.update(dict((str(k), color(v)) for k, v in color_codes.iteritems()))

def flatten(s):
    for a in s:
        for e in a: yield e

def codepair(code, tag):
    if isinstance(tag, tuple):
        start, end = tag
    else:
        start = end = tag

    return [('\033[%sm' % code,   ('<%s>'  % start) if start else ''),
            ('\033[x%sm' % code,  ('</%s>' % end)  if end else '')]

color_re = re.compile('\033\\[#([^m]+)m')

codes.update(('' + str(code), ('font color="#%s"' % color, 'font')) for code, color in color_codes.iteritems())

replace = list(flatten(codepair(code, tag) for code, tag in codes.iteritems()))

rereplace = [(re.compile(txt, re.IGNORECASE), repl) for txt, repl in rereplace]

FADE_ALT_RE = r'<(?:(?:FADE)|(?:ALT))\s+(?:(?:#[a-f0-9]{6}),?\s*)+>'

BIT_DEFENDER_RE = r'<font (?:BDYENCID|BDPK|BDCH).*>'

STUPID_COMBINED_RE = r'((?:%s)|(?:%s))' % (FADE_ALT_RE, BIT_DEFENDER_RE)

tags_re = re.compile(r'''(</?\w+(?:(?:\s+\w+(?:\s*=\s*(?:".*?"|'.*?'|[^'">\s]+))?)+\s*|\s*)/?>)''', re.DOTALL | re.IGNORECASE)
entity_re = re.compile(r'''&(?:(?:(?:#(?:(?:x[a-f0-9]+)|(?:[0-9]+)))|[a-z]+));''', re.IGNORECASE)
stupid_tags_re = re.compile(STUPID_COMBINED_RE, re.DOTALL | re.MULTILINE | re.IGNORECASE)
stupid_tags = frozenset(('alt', 'fade'))
allowed_tags = frozenset(('b', 'i', 'u', 's', 'font'))

def is_ascii(s):
    '''
    sanity check only.
    '''
    return all(((32 <= ord(c) <= 126) or (ord(c) in (0x9, 0xA, 0xD))) for c in s)

def tohtml(s):
    #s = s.encode('xml')

    # normal replacements
    for txt, repl in replace:
        s = s.replace(txt, repl)

    # regex replacements
    for pattern, repl in rereplace:
        match = pattern.search(s)
        while match:
            i, j  = match.span()
            splat = [a.decode('xml') for a in match.groups()]

            if repl == '<font %s>':
                for k, e in enumerate(splat[:]):
                    splat[k] = fix_font_size(e)

            s = s[:i] + repl % tuple(splat) + s[j:]
            match = pattern.search(s)

    # custom colors
    match = color_re.search(s)
    while match:
        i, j = match.span()
        s = s[:i] + '<font color="#%s">' % match.group(1) + s[j:]
        match = color_re.search(s)

    # close tags as necessary
    exploded = tags_re.split(s)
    ret = []
    for chunk in exploded:
        if tags_re.match(chunk):
            if any(any(chunk.lower().startswith(s % tag) for s in ('<%s ', '<%s>', '</%s ', '</%s>')) for tag in allowed_tags):
                ret.append(chunk)
                continue
            elif any(any(chunk.lower().startswith(s % tag) for s in ('</%s ', '</%s>')) for tag in stupid_tags):
                continue
        elif stupid_tags_re.match(chunk):
            exp2 = filter((lambda arg: not stupid_tags_re.match(arg)), stupid_tags_re.split(chunk))
            for chunk2 in exp2:
                ret.append(chunk2.encode('xml'))
            continue
        ret.append(chunk.encode('xml'))
    s = ''.join(ret)

    #lxml turns everything into ascii w/ escaped characters.

    return s

def fix_font_size(e):
    # TODO: Get rid of the regex matching here. it affects non-markup text.
    # turn '<font size="10">' into '<font style="font-size: 10pt;">'
    return re.sub(r'size=["\']([^"\']+)["\']', lambda match: 'style="font-size: %spt"' % match.group(1), e)

def color2code(color):
    'returns the yahoo format code for color, where color is (r, g, b)'

    return ''.join([
        '\x1b[',
        color_lookup.get(color, '#' + ''.join('%02x' % c for c in color[:3])),
        'm'
    ])

def format(format, string):
    before, after = '<font face="%(face)s" size="%(size)s">' % format, ''

    try:
        foregroundcolor = format.get('foregroundcolor')
    except KeyError:
        pass
    else:
        before += color2code(foregroundcolor)

    for a in ('bold', 'italic', 'underline'):
        if format.get(a, False):
            before += '\x1b[' + format_lookup[a[0]] + 'm'

    return before + string + after


def main():
    tests = '''

<font size="10">\x1b[30mhey, who\'s this?
<font size="14">normal</font>
\033[1m<font size="14">bold</font>\033[x1m
\033[1m<font size="14">bold</font>\033[x1m<font size="14">notbold</font>
\033[1mbold\033[x1m\033[2mitalic\033[1mbolditalic\033[4mall\033[x1m\033[x2mjustunderline
<not html>
\033[38mred
\033[#ff3737moffre
<font face="Chiller" size="15">test</font>
<font face="Chiller" size='15'>test</font>
\033[#FF0000mhello\033[#000000m
\033[1m\033[4m\033[2m\033[#000000m<font face="Arial"><font size="20">\033[lmhttp://www.digsby.com\033[xlm\033[x2m\033[x4m\033[x1m

'''.strip().split('\n')

    #print decode(tests[0])

    for t in tests:
        print repr(t)
        print repr(tohtml(t))
        print


if __name__ == '__main__':
    main()
