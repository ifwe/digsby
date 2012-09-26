import wx, string
from util.introspect import memoize
from util.primitives import Point2HTMLSize
from util.xml_tag import tag
from util.lrucache import LRU

def FindAny(s, chrs, start = None, end = None):
    chrs = set(chrs)

    for i in xrange(start or 0, end or len(s)):
        if s[i] in chrs:
            return i

    return -1

def rFindAny(s,chrs,start=None,end=None):
    chrs = set(chrs)

    for i in xrange(end-1 or len(s)-1, start or 0, -1):
        if s[i] in chrs:
            return i

    return -1


def ContainsNumbers(s):
    return FindAny(s, string.digits) != -1


rtlCharRanges = [(0x202B, 0x202B), #http://www.fileformat.info/info/unicode/char/202b/index.htm
                 (0x0590, 0x05FF),
                 (0x0600, 0x06FF),
                 (0x0750, 0x077F),
                 (0xFB1D, 0xFB40),
                 (0xFB50, 0xFDFF),
                 (0xFE70, 0xFEFF)]

def isRTL(char):
    charcode = ord(char)
    for charRange in rtlCharRanges:
        if charcode >= charRange[0] and charcode <= charRange[1]:
            return True
    return False

#
# A side effect of passing both font and dc parameters to the following
# functions makes that font active in the DC.
#


VISTA_SHELL_FONT = u'Segoe UI'
VISTA_SHELL_FONT_SIZE = 9

_return_default_font = None

def _find_default():
    global _return_default_font
    faces = GetFonts()

    # Until wxWidgets uses the correct font on Vista, fake it.
    try:
        import ctypes
        ctypes.windll.dwmapi
        vista = True
    except:
        vista = False


    if vista and VISTA_SHELL_FONT in faces:
        _return_default_font = lambda: \
            wx.Font(VISTA_SHELL_FONT_SIZE, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                    wx.FONTWEIGHT_NORMAL, False, VISTA_SHELL_FONT)
    else:
        _return_default_font = lambda: wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)

def default_font():
    'Returns the default system GUI font.'

    global _return_default_font
    if _return_default_font is None:
        _find_default()

    return _return_default_font()


def shorten_all_links(textctrl, ondone=None, timeoutms=5000):
    '''Disables the text control, shortens all of its links, then enables it.'''

    import sys
    from util.net import LinkAccumulator, get_short_url, is_short_url
    from util import threaded

    links = LinkAccumulator(textctrl.Value)

    # since we're using string.replace, make a set
    all_links = set(links.links)

    # don't shorten already shortened URLs
    all_links = [l for l in all_links if not is_short_url(l)]

    if not all_links: return

    links.count = len(all_links)

    links.finished = False
    def finish():
        @wx.CallAfter
        def after():
            if not links.finished:
                links.finished = True

                textctrl.Enable()
                if ondone is not None:
                    ondone()

    # re-enable the text control after a timeout.
    if timeoutms is not None:
        wx.CallLater(timeoutms, finish)

    textctrl.Disable()
    for link in all_links:
        def shorten(link=link): # close over link
            def one_link_shortened():
                links.count -= 1
                if links.count == 0:
                    finish()

            def success(short_url):
                @wx.CallAfter
                def after():
                    if links.finished: return
                    # TODO: use adjusting spans.
                    textctrl.SetValue(textctrl.Value.replace(link, short_url))
                    one_link_shortened()

            def error():
                print >> sys.stderr, 'error shortening link: %r' % link
                one_link_shortened()

            threaded(get_short_url)(link, success=success, error=error)

        shorten(link)

class VisualCharacterLimit(object):
    '''A "visual validator" that highlights any text in a wxTextCtrl that is
    over a specified limit.'''

    def __init__(self, textctrl, limit, length=None):
        self.ctrl = textctrl
        self.limit = limit
        self.length = length if length is not None else len

        # TODO: text controls' default styles are not always black-on-white
        self.default_style = wx.TextAttr(wx.BLACK, wx.WHITE)
        self.limit_style = wx.TextAttr(wx.WHITE, wx.RED)

        self.needs_style_update = False
        self.in_set_style = False

        self.ctrl.Bind(wx.EVT_TEXT, self._on_text)
        self._on_text()

    def SetLimit(self, limit, refresh=True):
        self.limit = limit
        if refresh: self._on_text()

    def _on_text(self, e=None):
        if e is not None: e.Skip()

        if self.in_set_style:
            return

        value = self.ctrl.Value
        limit = self.limit(value) if callable(self.limit) else self.limit

        if self.needs_style_update or self.length(value) > limit:
            self.needs_style_update = True

            self.in_set_style = True
            self.ctrl.SetStyle(0, limit, self.default_style)
            self.ctrl.SetStyle(limit, self.ctrl.LastPosition, self.limit_style)
            self.in_set_style = False
        else:
            self.needs_style_update = False

# plz see http://style.cleverchimp.com/font_size_intervals/altintervals.html
aimsizes= { 8:  1,
            10: 2,
            12: 3,
            14: 4,
            18: 5,
            24: 6,
            36: 7  }

#

def attrToHTML(textattr):
    font = textattr.Font

    attrs = {}
    if textattr.HasTextColour() and textattr.GetTextColour() != wx.BLACK:
        attrs['color'] = textattr.GetTextColour().GetAsString(wx.C2S_HTML_SYNTAX)

    attrs.update(size = str(aimsizes.get(font.PointSize // 15, 4)),
                 face = unicode(font.FaceName))

    start = tag('font', **attrs)._to_xml(self_closing = False, pretty = False)[:-7]
    end = '</font>'

    if font.Weight == wx.FONTWEIGHT_BOLD:
        start += '<b>'; end = '</b>' + end
    if font.Style == wx.FONTSTYLE_ITALIC:
        start += '<i>'; end = '</i>' + end
    if font.Underlined:
        start += '<u>'; end = '</u>' + end

    return start, end

def TagFont(string, fonttype, fonts):
    font = fonts[fonttype]
    color = fonts['%sfc'%fonttype]
    tag = u''.join(['<font face="',font.FaceName,
                    '" size="',str(Point2HTMLSize(fonts[fonttype].PointSize)),
                    '" color="',color,'">',
                    '<b>' if font.Weight == wx.BOLD else '',
                    '<i>' if font.Style == wx.ITALIC else '',
                    '<u>' if font.Underlined else '',
                    string if isinstance(string, unicode) else string.decode('utf-8'),
                    '</u>' if font.Underlined else '',
                    '</i>' if font.Style == wx.ITALIC else '',
                    '</b>' if font.Weight == wx.BOLD else '',
                    '</font>'])
    return tag

def tagfontxml(string, fonttype, fonts):
    from lxml.builder import E
    font = fonts[fonttype]
    color = fonts['%sfc'%fonttype]
    out = string
    if isinstance(out, str):
        out = out.decode('utf-8')
    conditions = ((font.Underlined, 'u'),
                  (font.Style == wx.ITALIC, 'i'),
                  (font.Weight == wx.BOLD, 'b'))
    for condition, tag in conditions:
        if condition:
            out = getattr(E, tag)(out)
    out = E.span(out,
                 style = 'font-family: %(facename)s; font-size: %(size)ipt; color: %(color)s;' %
                        {'facename': font.FaceName,
                         'size': font.PointSize,
                         'color': color})
    return out



font_init_args = ('pointSize', 'family', 'style', 'weight', 'underline', 'faceName', 'encoding')

def CopyFont(font, **kwargs):
    """
        pointSize
        family
        style
        weight
        underline
        faceName
        encoding
    """

    f=fontkwargs    = dict(
        pointSize = font.PointSize,
        family    = font.Family,
        style     = font.Style,
        weight    = font.Weight,
        underline = font.Underlined,
        faceName  = font.FaceName,
        encoding  = font.Encoding
    )
    fontkwargs.update(kwargs)

    if 'underlined' in fontkwargs:
        fontkwargs['underline'] = fontkwargs.pop('underlined')

    # FIXME: Remove workaround once everything moves to SIP or wx.Font.init_args
    # is available everywhere.
    init_args = font_init_args
    if hasattr(wx.Font, "init_args"):
        init_args = wx.Font.init_args

    return wx.Font(*(f.get(a) for a in init_args))

if 'wxMac' in wx.PlatformInfo:
    get_measuring_context = lambda: wx.ClientDC(wx.GetTopLevelWindows()[0])
else:
    get_measuring_context = wx.MemoryDC


_sizecache = LRU(100)
def GetMultilineTextSize(text, font = None, dc = None):
    assert font or dc

    dc = dc or get_measuring_context()

    if font: dc.SetFont(font)
    else: font = dc.Font

    nativeinfo = font.NativeFontInfoDesc + text
    try:
        ext = _sizecache[nativeinfo]
    except KeyError:
        _sizecache[nativeinfo] = ext = dc.GetMultiLineTextExtent(text)[:2]

    return wx.Size(*ext)

_widthcache = LRU(100)
def GetTextWidth(line, font = None, dc = None):
    assert font or dc

    dc = dc or get_measuring_context()

    if font: dc.SetFont(font)
    else:    font = dc.Font

    nativeinfo = font.NativeFontInfoDesc + line
    try:
        width = _widthcache[nativeinfo]
    except KeyError:
        _widthcache[nativeinfo] = width = dc.GetFullTextExtent(line)[0]

    return width


# fonts in a cache dictionary --> they need a __hash__ method
wx.Font.__hash__ = lambda f: hash(f.NativeFontInfoDesc)

_heightcache = LRU(100)
def GetFontHeight(font = None, dc = None, line_height = False, descent = False):
    'Calculates the height of a font in pixels.'

    assert font or dc

    dc = dc or get_measuring_context()

    if font: dc.SetFont(font)
    else:    font = dc.Font

    nativeinfo = font.NativeFontInfoDesc
    try:
        extents = _heightcache[nativeinfo]
    except KeyError:
        _heightcache[nativeinfo] = extents = dc.GetFullTextExtent(string.ascii_letters)

    if line_height:
        return extents[1]
    if descent:
        return extents[2]
    else:
        return extents[1] - extents[2] + extents[3]

wx.Font.GetHeight = GetFontHeight
wx.Font.Height     = property(lambda f: GetFontHeight(f))
wx.Font.LineHeight = property(lambda f: GetFontHeight(f, line_height = True))
wx.Font.Descent    = property(lambda f: GetFontHeight(f, descent  = True))

def GetTextExtent(text, font = None, dc = None):
    'Returns the width and hight of string text in supplied font.'

    dc = dc or get_measuring_context()

    if font: dc.SetFont(font)
    return dc.GetTextExtent(text)


def DeAmp(text):
    return text.replace('&', '', 1)

from cgui import truncateText as TruncateText

def dcDTTfunc(self, text, rect, alignment = wx.ALIGN_LEFT | wx.ALIGN_TOP, indexAccel = -1):
    self.DrawLabel(TruncateText(text, rect.width, None, self), rect, alignment, indexAccel)

wx.DC.DrawTruncatedText = dcDTTfunc

def dcDTTfuncInfo(self, text, rect, alignment = wx.ALIGN_LEFT | wx.ALIGN_TOP, indexAccel = -1):
    'Returns true if text was cut off.'
    txt = TruncateText(text, rect.width, None, self)
    self.DrawLabel(txt, rect, alignment, indexAccel)
    return txt == text

wx.DC.DrawTruncatedTextInfo = dcDTTfuncInfo

#from cgui import DrawTruncated
#wx.DC.DrawTruncatedText = DrawTruncated


@memoize
def GetFonts():
    return sorted(set(f.lstrip('@') for f in wx.FontEnumerator().GetFacenames()))

# wxFont's constructor takes the following arguments
fontattrs = ('PointSize', 'Family', 'Style', 'Weight', 'Underlined', 'FaceName')

from cgui import Wrap
