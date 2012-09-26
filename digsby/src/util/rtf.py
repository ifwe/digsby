'''
Module for various RTF functions. Extremely limited.

Originally created for parsing simple RTF documents.
Example:

    {\rtf1\ansi\ansicpg1252\deff0\deflang1033{\fonttbl{\f0\fmodern\fprq1\fcharset0 Courier New;}}
    {\colortbl ;\red0\green255\blue64;}
    \viewkind4\uc1\pard\cf1\b\f0\fs32 this is the body\par
    }

    {\rtf1\ansi\ansicpg1251\deff0\deflang1026{\fonttbl{\f0\fnil\fcharset204{\*\fname Arial;}Arial CYR;}}
    {\colortbl ;\red0\green64\blue128;}
    \viewkind4\uc1\pard\cf1\f0\fs20\'e4\'e0\par
    }

'''
import string

symbols = {
            '\\': '\\',
            '~': ' ', # should really be non-breaking space- &nbsp; in html
            'tab' : '\t',
            "'7b" : '{',
            "'7d" : '}',
            }

rev_symbols = {}
for k,v in symbols.items():
    rev_symbols[v] = k

rtf_fcharsets = {
    0 : 'ANSI',
    1 : 'Default',
    2 : 'Symbol',
    3 : 'Invalid',
    77 : 'Mac',
    128 : 'shiftjis',
    130 : 'johab',
    134 : 'GB2312',
    136 : 'Big5',
    161 : 'Greek',
    162 : 'iso-8859-9', # Turkish
    163 : 'cp1258', # Vietnamese
    177 : 'Hebrew',
    178 : 'Arabic',
    179 : 'Arabic Traditional',
    180 : 'Arabic user',
    181 : 'Hebrew user',
    186 : 'Baltic',
    204 : 'Russian',
    222 : 'Thai',
    238 : 'Eastern European',
    254 : 'PC 437',
    255 : 'OEM',
}
def tokenize(string):
    '''
    input:
        {\rtf1\ansi\ansicpg1252\deff0\deflang1033{\fonttbl{\f0\fmodern\fprq1\fcharset0 Courier New;}}
        {\colortbl ;\red0\green255\blue64;}
        \viewkind4\uc1\pard\cf1\b\f0\fs32 this is the body\par
        }

    output:

      ['{', '\\', 'rtf1', '\\', 'ansi', '\\',
     'ansicpg1252', '\\', 'deff0', '\\',
     'deflang1033', '{', '\\', 'fonttbl',
     '{', '\\', 'f0', '\\', 'fmodern', '\\',
     'fprq1', '\\', 'fcharset0', ' ',
     'Courier', ' ', 'New;', '}', '}', '\n',
     '{', '\\', 'colortbl', ' ', ';', '\\',
     'red0', '\\', 'green255', '\\', 'blue64;',
     '}', '\n', '\\', 'viewkind4', '\\', 'uc1',
     '\\', 'pard', '\\', 'cf1', '\\', 'b', '\\',
     'f0', '\\', 'fs32', ' ', 'and', ' ', 'another',
     '\\', 'par\n', '}']
    '''
    tokens = []
    curr_token = ''

    for c in string:
        if c in '\\{} \r\n':
            if curr_token:
                tokens.append(curr_token)
                curr_token = ''
            if c == '\n' and tokens[-1] == '\r':
                tokens[-1] = c
            else:
                tokens.append(c)
        else:
            curr_token += c

    if curr_token:
        tokens.append(curr_token)


    return tokens

class TypedString(str):
    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, str.__repr__(self))

class TypedList(list):
    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, list.__repr__(self))

class ControlNode(TypedString):
    pass
class TextNode(TypedString):
    pass
class WhitespaceNode(TypedString):
    pass
class Group(TypedList):
    pass

def compress_text(doc):
    new = Group()
    cur_text = []
    while doc:
        node = doc.pop(0)
        if type(node) is WhitespaceNode:
            if cur_text:
                cur_text.append(node)
        elif type(node) is TextNode:
            cur_text.append(node)
        elif type(node) is Group:
            if cur_text:
                new.append(TextNode(''.join(cur_text)))
            new.append(compress_text(node))

    return new


def parse(tokens):
    doc = None

    while tokens:
        token = tokens.pop(0)

        if token == '{':  # start of group
            if doc is None:
                doc = Group()
            else:
                tokens.insert(0,'{')
                doc.append(parse(tokens))
        elif token == '}': # end of group
            return doc
        elif token == '\\': # control code or symbol follows
            next = tokens.pop(0)

            if len(next) == 1 and next not in (string.ascii_letters + string.digits):
                doc.append(TextNode(symbols.get(next, next)))
            else:
                if next.startswith("'"):
                    # Hex number for a character
                    hexchar = next[1:3]
                    tokens.insert(0, next[3:]) # put the rest back
                    doc.append(TextNode(chr(int(hexchar, 16))))
                else:
                    doc.append(ControlNode(token + next))

        elif token in string.whitespace: # whitespace. end of control code if applicable
            last = doc[-1]
            if type(last) is WhitespaceNode:
                doc[-1] = WhitespaceNode(last + token)
            else:
                doc.append(WhitespaceNode(token))
        else:
            last = doc[-1]
            if type(last) is TextNode:
                doc[-1] = TextNode(last + token)
            else:
                doc.append(TextNode(token))

    doc = compress_text(doc)

    return doc

def tree_to_plain(tree):

    ''' input:
<Group [
  <ControlNode 'rtf1'>,
  <ControlNode 'ansi'>,
  <ControlNode 'ansicpg1252'>,
  <ControlNode 'deff0'>,
  <ControlNode 'deflang1033'>,
  <Group [
    <ControlNode 'fonttbl'>,
    <Group [
      <ControlNode 'f0'>,
      <ControlNode 'fmodern'>,
      <ControlNode 'fprq1'>,
      <ControlNode 'fcharset0'>,
      <TextNode 'Courier New;'>
    ]>
  ]>,
  <Group [
    <ControlNode 'colortbl'>,
    <TextNode ';'>,
    <ControlNode 'red0'>,
    <ControlNode 'green255'>,
    <ControlNode 'blue64;'>
  ]>,
  <ControlNode 'viewkind4'>,
  <ControlNode 'uc1'>,
  <ControlNode 'pard'>,
  <ControlNode 'cf1'>,
  <ControlNode 'b'>,
  <ControlNode 'f0'>,
  <ControlNode 'fs32'>,
  <TextNode 'this is the body'>,
  <ControlNode 'par'>
]>

    output:
    'this is the body'
    '''
    tree = tree[:]

    if not tree:
        return ''

    if type(tree[0]) is ControlNode and str(tree[0]) in ('\\colortbl','\\fonttbl'):
        return ''

    res = []
    encoding = None
    last = None
    uni_replace_len = None
    while tree:
        node = tree.pop(0)

        if type(node) is Group:
            res.append(tree_to_plain(node))

        if type(node) is TextNode:
            s = str(node)
            if encoding is not None:
                s = s.decode(encoding)
            res.append(s)

        if type(node) is WhitespaceNode:
            s = str(node)
            if type(last) in (ControlNode, Group):
                s = s[1:]
            res.append(s)

        if type(node) is ControlNode:
            if str(node) == '\\par':
                res.append('\n')
            elif str(node).startswith('\\ansicpg'):
                try:
                    codepage = int(str(node)[len('\\ansicpg'):].strip())
                except (ValueError, IndexError), e:
                    pass
                else:
                    encoding = 'cp%d' % codepage

            elif str(node).startswith('\\u') and str(node)[2] in ('-' + string.digits):
                if tree:
                    put_back = True
                    replacement_charnode = tree.pop(0)
                else:
                    put_back = False
                    replacement_charnode = TextNode('')

                if type(replacement_charnode) is not TextNode:
                    if put_back:
                        tree.insert(0, replacement_charnode)
                    replacement_char = ' '
                else:
                    replacement_char = str(replacement_charnode)
                    if uni_replace_len is not None:
                        if len(replacement_char) > uni_replace_len:
                            replacement_char, rest = replacement_char[uni_replace_len:], replacement_char[:uni_replace_len]
                            if rest: # should be true, given previous if statements
                                tree.insert(0, TextNode(rest))

                try:
                    val = int(str(node)[2:])
                except ValueError:
                    val = ord(replacement_char)
                else:
                    val = abs(val) + ((val < 0) * 32767)

                try:
                    res.append(unichr(val))
                except ValueError:
                    res.append(replacement_char)
        last = node

    final = ''.join(res)
    return final

def rtf_to_plain(s):
        return tree_to_plain(parse(tokenize(s)))

def make_color_table(colors):
    table = Group()
    table.append(ControlNode('\\colortbl'))
    table.append(TextNode(';'))
    for color in colors:
        r,g,b,a = tuple(color)
        table.extend((ControlNode('\\red%d'   % r),
                      ControlNode('\\green%d' % g),
                      ControlNode('\\blue%d'  % b),
                      TextNode(';')))

    return table

def normalize_font_family(family):
    family = family.lower()
    if family not in set(('nil', 'roman', 'swiss', 'modern', 'script', 'decor', 'tech')):
        return 'nil'

    return family

def make_font_table(fonts):
    table = Group()
    table.append(ControlNode('\\fonttbl'))
    for i, (family, font) in enumerate(fonts):
        table.extend((ControlNode('\\f%d' % i),
                      ControlNode('\\' + normalize_font_family(family)),
                      TextNode(' ' + font + ';')))

    return table

def storage_to_tree(s):
    if s.get('backgrouncolor') and s.get('foregroundcolor'):
        color_table = make_color_table([s.backgroundcolor, s.foregroundcolor])
    else:
        color_table = TextNode('')

    if s.get('family') and s.get('font'):
        font_table = make_font_table([(s.family, s.font)])
    else:
        font_table = TextNode('')

    top_level = Group([
        ControlNode('\\rtf1'),
        ControlNode('\\ansi'),
        ControlNode('\\uc1'),
        color_table,
        font_table,
        ])

    format_group = Group([])
    if font_table:
        format_group.append(ControlNode('\\f1'))
    if color_table:
        format_group.append(ControlNode('\\cb1'))
        format_group.append(ControlNode('\\cf2'))

    if s.get('bold'):
        format_group.append(ControlNode('\\b'))
    if s.get('italic'):
        format_group.append(ControlNode('\\i'))
    if s.get('underline'):
        format_group.append(ControlNode('\\ul'))
    if s.get('size'):
        format_group.append(ControlNode('\\fs%d' % (s.size * 2)))

    top_level.append(format_group)

    return top_level, format_group.append

def storage_to_rtf(s, text):
    escaped = rtf_escape(text)
    doc, add_text = storage_to_tree(s)
    add_text(escaped)
    return tree_to_rtf(doc)

'''
{\rtf1\ansi\ansicpg1252\deff0\deflang1033
  {\fonttbl
    {\f0\fswiss\fcharset0 Arial;}
    {\f1\froman\fprq2\fcharset0 Bodoni;}}
  {\\colortbl ;\\red0\\green255\\blue64;}
  \viewkind4\uc1\pard\i\f0\fs20      first line\par\b second line\par\ul\i0 third line\par\b0 fourth line\par\ulnone\b bold\par\f1 newfont\ul\b0\f0\par}
'''

#Storage(
#            backgroundcolor = tuple(tc.BackgroundColour),
#            foregroundcolor = tuple(tc.ForegroundColour),

#            face = font.FaceName,
#            size = font.PointSize,
#            underline = font.Underlined,
#            bold = font.Weight == BOLD,
#            italic = font.Style == ITALIC)


def rtf_escape(node):
    if isinstance(node, unicode):
        s = unicode(node)
        try:
            s = s.encode('ascii')
        except UnicodeEncodeError:
            pass
    else:
        assert isinstance(node, str)
        s = str(node)

    return ''.join(rtf_escape_chr(c) for c in s)

def rtf_escape_chr(c):
    if c in rev_symbols:
        return '\\' + rev_symbols[c]
    elif isinstance(c, unicode):
        val = ord(c)
        negate, val = divmod(val, 32767)
        if negate:
            val = -abs(val)
        return '\\u%d ?' % val
    elif ord(c) > 127 and isinstance(c, str):
        return ('\\\'%x' % ord(c))
    else:
        return str(c)

def tree_to_rtf(tree):
    res = []
    res.append('{')
    for node in tree:
        t = type(node)
        if t is Group:
            res.append(tree_to_rtf(node))
        elif t is TextNode:
            res.append(rtf_escape(node))
        else:
            res.append(str(node))
    res.append('}')
    return ''.join(res)

def main():

    for test_string, test_plain in (
        (r'{\rtf1\ansi\ansicpg1252\deff0\deflang1033{\fonttbl{\f0\fmodern\fprq1\fcharset0 Courier New;}}{\colortbl ;\red0\green255\blue64;}\viewkind4\uc1\pard\cf1\b\f0\fs32 this is the body\par}', 'this is the body\n'),
        (r'{\rtf1\ansi\ansicpg1252\deff0\deflang1033{\fonttbl{\f0\fswiss\fcharset0 Arial;}{\f1\froman\fprq2\fcharset0 Bodoni;}}\viewkind4\uc1\pard\i\f0\fs20      first line\par\b second line\par\ul\i0 third line\par\b0 fourth line\par\ulnone\b bold\par\f1 newfont\ul\b0\f0\par}', '     first line\nsecond line\nthird line\nfourth line\nbold\nnewfont\n'),
        ('{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1033{\\fonttbl{\\f0\\fmodern\\fprq1\\fcharset0 Courier New;}}\n{\\colortbl ;\\red0\\green255\\blue64;}\n\\viewkind4\\uc1\\pard\\cf1\\b\\f0\\fs32 newline\\par\nbackslash\\\\ rawr end\\par\n}', 'newline\nbackslash\\ rawr end\n'),
        #(r'{\rtf1\ansi\ansicpg1252\deff0\deflang1033{\fonttbl{\f0\froman\fprq1\fcharset128 MS PGothic;}{\f1\fswiss\fprq2\fcharset0 Lucida Sans Unicode;}}\viewkind4\uc1\pard\f0\fs20\'93\'fa\'96\'7b\'8c\'ea\f1  / \f0\'82\'c9\'82\'d9\'82\'f1\'82\'b2\f1\par}', u'\u65e5\u672c\u8a9e / \u306b\u307b\u3093\u3054'),

        ):

        parsed = parse(tokenize(test_string))
        plain = tree_to_plain(parsed)
        print plain
        if not test_plain == plain:
            print repr(test_plain)
            print repr(plain)
            print
        if not test_string == tree_to_rtf(parsed):
            print repr(test_string)
            print repr(tree_to_rtf(parsed))
            print

if __name__ == '__main__':
    print main()
