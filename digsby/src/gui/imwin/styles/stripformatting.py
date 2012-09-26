'''

Strips formatting and colors from strings.

'''
from __future__ import with_statement

from gui.imwin.emoticons import apply_emoticons
from util import traceguard, linkify, soupify

from traceback import print_exc
from collections import defaultdict
from re import compile

from logging import getLogger; log = getLogger('stripformatting')
LOG = log.debug

def prewrap(m):
    return '<span style="white-space: pre-wrap;">' + m + '</span>'

plaintext_transform_functions = [
    ('emoticons', apply_emoticons),
    ('links',     linkify),
    ('spaces',    prewrap),
]

def strip(html, formatting = True, colors = True, plaintext_transforms = None):
    '''
    Strips formatting and/or colors from a string.

    Returns (stripped_string, {stripped_values}])
    '''

    #LOG('before strip: %r', html)

    if plaintext_transforms is None:
        plaintext_transforms = {}

    # A dictionary of lists of things this function has stripped out.
    removed = defaultdict(list)

    try:
        soup = soupify(html, convertEntities = 'html')
        #LOG('strip: %r', html)

        if formatting:
            strip_formatting(soup, removed)
            # LOG('after stripping formatting: %r', soup.renderContents(None))

        remove_attrs(soup,  ['color', 'bgcolor'], removed, doremove = colors)

        if colors:
            remove_styles(soup, ['background', 'color'], removed)
            remove_attrs(soup, ['back'], removed)
        else:
            convert_back(soup, removed)

        #LOG('after colors: %r', soup.renderContents(None))

        remove_tags(soup, 'html')
        remove_tags(soup, 'body')

        #LOG('after removing color: %r', soup.renderContents(None))

        apply_plaintext_transforms(soup, plaintext_transforms)

        final = soup.renderContents(None)
        #LOG('after transformations: %r', final)

        return final, removed

    except Exception:
        # If any exceptions occur, just return the original string.
        print_exc()

        return html, removed

def strip_formatting(soup, removed):
    'Removes font formatting attributes.'

    remove_attrs(soup,  ['face', 'size'], removed)
    remove_tags(soup, 'small', 'big') #'b', 'i', 'strong', 'em', <- decision was made to not remove bold, etc.
    remove_styles(soup, ['font-family', 'font-size'], removed)
    remove_styles(soup, ['font'], removed) #<- will not do partial remove

def apply_plaintext_transforms(soup, plaintext_transforms):
    "Applies selected functions to each text node in 'soup.'"

    for textElem in soup(text=True):
        s = textElem

        # Functions are keyed by name in "plaintext_transform_functions"
        # above.
        for name, func in plaintext_transform_functions:
            res = plaintext_transforms.get(name, False)
            if res:
                with traceguard: # Guard each call for failures.
                    if res not in (False, True, None):
                        s = func(s, res)
                    else:
                        s = func(s)

        with traceguard:
            textElem.replaceWith(s)

def attr_match(tag, attrnames):
    tagattrs = set(attrName for attrName, attrValue in tag.attrs)
    return any((a in tagattrs) for a in attrnames)

def remove_attrs(soup, attrs, removed, doremove = True):
    for tag in soup.findAll(lambda t: attr_match(t, attrs)):
        for attrName, attrValue in list(tag.attrs):
            #LOG('%s in %s?', attrName, attrs)
            if attrName in attrs:
                removed[attrName].append(attrValue)
                if doremove:
                    del tag[attrName]


def remove_tags(soup, *tags):
    for tag in soup.findAll(name = tags):
        # TODO: don't use soupify to reparse HTML a lot
        tag.replaceWith(soupify(tag.renderContents(None)))

def remove_style(s, style):
    search  = compile(r'\s*' + style + ' *:([^;]*)').search
    removed = []

    match = search(s)
    while match:
        # grab the value of (^;]*) in the above regex
        removed.append(match.groups(1)[0].strip())

        # cut out the matched expression.
        i, j = match.span()
        s = s[:i] + s[j+1:]

        match = search(s)

    return s, removed

def remove_styles(soup, styles, removed):
    all_removed = []

    for tag in soup.findAll(style = True):
        for style in styles:
            stripped_style, removed_style = remove_style(tag['style'], style)
            removed[stripped_style].append(removed_style)
            tag['style'] = stripped_style

    return all_removed


def convert_back(soup, removed):
    'AIM <font back="#ff0000">'

    # Convert all <font back="#ff0000">
    for tag in soup.findAll(name = 'font', back = True):
        removed['back'].append(tag['back'])

        styles = ['background-color: %s' % tag['back']]

        if 'color' in dict(tag.attrs):
            removed['color'].append(tag['color'])
            styles.append('color: %s' % tag['color'])

        tag.replaceWith(soupify(('<span style="%s">' % '; '.join(styles)) + tag.renderContents(None) + '</span>'))

