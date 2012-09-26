'''
Functions for transforming HTML
'''

import lxml.html
import re
import traceback

__all__ = [
    'render_contents', 'to_xhtml',
    'remove_tags',
    'remove_attrs',
    'remove_styles',
    'transform_text',
]

def render_contents(doc, encode_text_as_xml=True):
    tohtml = lambda d: lxml.html.tostring(d, encoding = unicode)

    try:
        t = doc.text
        if encode_text_as_xml and t is not None:
            t = t.encode('xml') # .text "converts" entities like &gt; to >
        return (t or '') + ''.join(map(tohtml, doc.getchildren()))
    except ValueError:
        return tohtml()

def make_xhtml_fragment(s):
    # ignore all whitespace
    if not s.strip():
        return s

    html = lxml.html.document_fromstring(s)

    body = html.body
    bgcolor = html.body.get('bgcolor')

    s = render_contents(body)
    if bgcolor is not None:
        return '<span style="background-color: %s;">%s</span>' % (bgcolor, render_contents(body))
    else:
        return s

def to_xhtml(s):
    s = make_xhtml_fragment(s)

    # lxml.html.document_fromstring will wrap bare text in <p></p> tags; remove
    # them
    if s.startswith('<p>') and s.endswith('</p>'):
        return s[3:-4]

    return s

def remove_tags(tree, tagnames):
    '''
    given an lxml tree, remove all tags named by tagnames
    '''

    for tagname in tagnames:
        assert isinstance(tagname, basestring)

        xpath = './/' + tagname
        tag = tree.find(xpath)

        while tag is not None:
            tag.drop_tag()
            tag = tree.find(xpath)

    return tree

def remove_attrs(tree, attrs):
    '''
    given an lxml tree and a sequence of attribute names, removes all occurences
    of those attributes
    '''

    find = tree.getroottree().iterfind
    for attr in attrs:
        assert isinstance(attr, basestring)

        # find all tags with an attribute "attr"
        for tag in find('//*[@%s]' % attr):
            del tag.attrib[attr]

def remove_style(s, style):
    search  = re.compile(r'\s*' + style + ' *:([^;]*)').search
    removed = []

    match = search(s)
    while match:
        # grab the value of (^;]*) in the above regex
        removed.append(match.groups(1)[0].strip())

        # cut out the matched expression.
        i, j = match.span()
        s = s[:i] + s[j+1:]

        match = search(s)

    return s.strip(), removed

def remove_styles(tree, styles):
    '''
    removes all given styles from the given lxml tree
    '''

    for tag in tree.getroottree().iterfind('//*[@style]'):
        for style in styles:
            attrib = tag.attrib
            attrib['style'], removed = remove_style(attrib['style'], style)

def transform_text(tree, func, raise_exceptions=False):
    '''
    replaces each text child in tree with the result of func(text)

    without raise_exceptions=True (False is default) any tracebacks will be
    printed with traceback.print_exc
    '''
    
    for textelem in tree.getroottree().xpath('//*/text()'):
        try:
            newtext = func(textelem)
        except Exception:
            if raise_exceptions:
                raise
            else:
                traceback.print_exc()
        else:
            textelem.getparent().text = newtext

