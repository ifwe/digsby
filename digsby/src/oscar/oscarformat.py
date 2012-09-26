from util import Point2HTMLSize, Storage as S

DEFAULTS = S(FONT = 'Times New Roman',
             SIZE = 12,
             BACK = (255, 255, 255),
             FORE = (0, 0, 0))

def tohex(t, n = 3):
    return ''.join('%02x' % c for c in t[:n])


pointsize_map = {
    8: 1,
    10: 2,
    12: 3,
    14: 4,
    18: 5,
    24: 6,
    36: 7,
    38: 7
}

def aimsize(n):
    n = int(n)

    try:
        return pointsize_map[n]
    except KeyError:
        return Point2HTMLSize(n)


def to_aimhtml(s, fmt, body_bgcolor = False, replace_newlines=False):
    '''
    Given a string, and a fmt dictionary containing color and font information, returns "AIM" html.

    AIM html is a limited subset of HTML displayed by AIM clients.
    '''
    before, after = '', ''

    fontface = fontsize = fontfore = fontback = None

    face = fmt.get('face', DEFAULTS.FONT)
    if face != DEFAULTS.FONT: fontface = face

    size = fmt.get('size', DEFAULTS.SIZE)
    if size != DEFAULTS.SIZE: fontsize = size

    back = fmt.get('backgroundcolor', DEFAULTS.BACK)
    if back != DEFAULTS.BACK: fontback = back

    fore = fmt.get('foregroundcolor', DEFAULTS.FORE)
    if fore != DEFAULTS.FORE: fontfore = fore

    bodyattrs = None

    if fontface or fontsize or fontback or fontfore:
        if body_bgcolor and fontback and fontback != (255, 255, 255):
            bodyattrs = 'BGCOLOR="#%s"' % tohex(fontback)

        fontattrs = ' '.join(filter(lambda s: bool(s),
                                    [(('face="%s"'   % fontface)          if fontface else ''),
                                     (('size="%s"'   % aimsize(fontsize)) if fontsize else ''),
                                     (('color="#%s"' % tohex(fontfore))   if fontfore else ''),
                                     (('back="#%s"'  % tohex(fontback))   if (not body_bgcolor and fontback and
                                                                       fontback[:3] != (255, 255, 255)) else '')
                                     ]))

        fontattrs = fontattrs.strip()

        if fontattrs:
            before += '<FONT %s>' % fontattrs
            after  += '</FONT>'

    for a in ('bold', 'underline', 'italic'):
        if fmt.get(a, False):
            tag = a[0]
            before += '<%s>' % tag
            after   = '</%s>' % tag + after

    if bodyattrs:
        before = ('<BODY %s>' % bodyattrs) + before
        after  += '</BODY>'

    if replace_newlines:
        last = lambda _s: _s.replace('\n', '<br />')
    else:
        last = lambda _s: _s

    return last(''.join([before, s, after]))
