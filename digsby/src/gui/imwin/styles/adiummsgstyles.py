'''

Adium MessageStyles

http://trac.adiumx.com/wiki/CreatingMessageStyles

'''

CACHE_CSS = True

import config
from datetime import datetime
from traceback import print_exc
import re, sys, logging

from gui import skin
from gui.imwin.styles import MessageStyle, MessageStyleException

from util import strftime_u
from util.primitives.misc import fromutc
from util.xml_tag import plist
from path import path
from common import prefprop
from common.protocolmeta import protocols

from gui.buddylist.renderers import get_buddy_icon_url


from util import strip_html2
from gui.textutil import isRTL

log = logging.getLogger('adiummsgstyles')


from util import memoizedprop as memoizedprop_cache

if not CACHE_CSS:
    memoizedprop = lambda p: p
    print >>sys.stderr, 'WARNING: not caching CSS'
else:
    memoizedprop = memoizedprop_cache

# font alternatives, since PCs usually don't have some mac fonts

font_alternatives = {}

if config.platform == 'win':
    font_alternatives.update({
        'Lucida Grande': ['Arial', 'Lucida Sans Unicode', 'Lucida Sans', 'Lucida'],
        'Monaco':        ['Consolas', 'Lucida Console'],
        'Geneva':        ['Arial'],
        'Helvetica':     ['Arial'],
    })


# Not all of the strftime formatting options used by Adium skins have equivalents
# in Python's strftime. Replace them here.
strftime_replacements = [
    ('%1I', '%I'),
    ('%e', '%d')
]

# If key.html is missing, value.html will be tried also.
htmlfile_fallbacks = {
    'Context': 'Content',
    'NextContext': 'NextContent',
    'Incoming': 'Outgoing',
    'Outgoing': 'Incoming',
}

# pattern for finding adium message style %variables%
msgpattern = re.compile('(%([^{%\s]+)(\{([^}]+)\})?%)')

class AdiumMessageStyleBase(MessageStyle):
    def __init__(self, themepath):
        MessageStyle.__init__(self)

        self.path = path(themepath)
        self._cached_contents = {}

        if not (self.path / 'Contents').isdir():
            raise MessageStyleException('Adium MessageStyle has no "Contents" '
                                        'directory (%s)' % themepath)

    @property
    def baseUrl(self):
        return 'file:///%s/' % self.path.drive

    def _getcontent(self, *paths):
        p = paths[0]
        for elem in paths[1:]:
            if elem is not None:
                p = p / elem

        return self.cached_contents(p)

    @memoizedprop
    def resources(self):
        return self.path / 'Contents' / 'Resources'

    @property
    def plist(self):
        try:
            return self._plist
        except AttributeError:
            plistpath = self.path / 'Contents' / 'Info.plist'
            self._plist = {}
            if plistpath.isfile():
                try:
                    self._plist = plist(plistpath.text())
                except Exception:
                    print_exc()

        return self._plist

    @memoizedprop
    def default_css_styles(self):
        p = self.plist

        style = 'body {\n'

        try:
            fontfamily   = p['DefaultFontFamily']
            alternatives = font_alternatives.get(fontfamily, [])
            fontfamilies = u', '.join([fontfamily] + alternatives)

            style += '  font-family: %s;\n' % fontfamilies
        except KeyError:
            pass

        try:
            style += '  font-size: %spt;\n' % p['DefaultFontSize']
        except KeyError:
            pass

        style += '}\n'

        return style

    @memoizedprop
    def base(self):
        return self.resources.url() + '/'

    @property
    def css_file(self):
        return path('Variants') / self.variant + '.css' if self.variant else 'main.css'

    if CACHE_CSS:
        def cached_contents(self, path):
            # todo: make a selfmemoize
            try: return self._cached_contents[path]
            except KeyError: return self._cached_contents.setdefault(path, path.text())
    else:
        def cached_contents(self, path):
            return path.text()

    def get_variant(self):
        try:
            variants = self.resources / 'Variants'
            return self._variant
        except AttributeError:
            if variants.isdir():
                variants = variants.files('*.css')
                self._variant = self.plist.get('DefaultVariant', variants[0].namebase)
                if not self._variant:
                    self._variant = None
            else:
                # no variant specified.
                self._variant = None

        return self._variant

    def set_variant(self, variant):
        self._variant = variant

    variant = property(get_variant, set_variant)

    @property
    def variants(self):
        v = self.resources / 'Variants'
        variants = [p.namebase for p in v.files('*.css')] if v.isdir() else []

        try:
            novariant_name = self.plist['DisplayNameForNoVariant']
        except KeyError:
            return variants
        else:
            return [None] + variants


    @memoizedprop
    def novariant_name(self):
        return self.plist.get('DisplayNameForNoVariant', _('(none)'))

    @memoizedprop
    def theme_name(self):
        return self.path.namebase

    @memoizedprop
    def shows_background_colors(self):
        return '%textbackgroundcolor%' in self._getcontent(self.resources, 'Incoming', 'Content.html')

class AdiumMessageStyle(AdiumMessageStyleBase):

    def __init__(self, themepath, **options):
        'Represents the information, styles, and HTML in a AdiumMessageStyle directory.'

        AdiumMessageStyleBase.__init__(self, themepath)

    def initialContents(self, chatName, buddy, header = False, prevent_align_to_bottom=False):
        '''
        Return the initial HTML contents of this message style. Usually
        res/MessageStyles/Template.html, but can be overridden by an individual
        style by a file with the same name in its resource directory.
        '''

        self.options = dict(chatName = chatName)
        template     = self.resources     / 'Template.html'

        if template.isfile():
            s = template.text('utf-8')
        else:
            baseTemplate = skin.resourcedir() / 'MessageStyles' / 'Template.html'
            s = baseTemplate.text('utf-8')

        # the default Adium Template.html file includes several string
        # special substitution character sequences
        s = s.replace('%', '%%').replace('%%@', '%s')

        args = (self.base.replace('\\', '/'),
                self.default_css_styles,
                self.css_file.replace('\\', '/'),
                self.applySubstitutions(self.get_header(prevent_align_to_bottom=prevent_align_to_bottom), buddy = buddy),
                self.applySubstitutions(self.footer, buddy = buddy) + \
                    self.init_header_script(header))

        try:
            s = s % args
        except Exception:
            try:
                s = s % (args[:1] + args[2:])
            except Exception:
                print >> sys.stderr, s
                print_exc()

        return s

    def show_header_script(self, show):
        'Returns Javascript for showing or hiding the header.'

        display = '' if show else 'none'
        return "document.getElementById('header').style.display = '%s'" % display

    def init_header_script(self, show_header):
        'Returns CSS for the <head><script></head> tag.'

        if not show_header:
            return '<style type="text/css">#header { display: none; }</style>'
        else:
            return ''

    @property
    def header(self):
        return self.get_header()

    def get_header(self, prevent_align_to_bottom=False):
        headerPath = self.resources / 'Header.html'
        headerText = super(AdiumMessageStyleBase, self).header + (headerPath.text() if headerPath.isfile() else '')
        if prevent_align_to_bottom:
            headerText += "<script>window.preventAlignToBottom = true;</script>"
        return headerText

    @property
    def footer(self):
        footerPath = self.resources / 'Footer.html'
        return footerPath.text() if footerPath.isfile() else ''

    @property
    def allow_text_colors(self):
        return self.plist.get('AllowTextColors', True)

    def format_message(self, messagetype, messageobj, next = False, context = False, **extra):
        '''
        Applies a section of this theme's formatting template to the message
        object given.

        messagetype  'incoming' or 'outgoing' or 'status' or...more to come maybe!

        messageobj   a Digsby messageobj

        next         a boolean indicating if this is a "next" message (i.e.,
                     one to be appended to the previous block

        context      a boolean indicating if this message is "context"--the
                     history showed when you open an IM window
        '''
        if messagetype in ('incoming', 'outgoing'):
            direction = messagetype.title()
            content = '%s%s' % ('Next' if next else '',
                                'Context' if context else 'Content')
        else:
            direction = None
            content = messagetype.title()

        try:
            content = self._getcontent(self.resources, direction, '%s.html' % content)
        except IOError:
            #TODO: discovery these fallbacks once.
            if content in htmlfile_fallbacks:
                content = htmlfile_fallbacks[content]
                try:
                    content = self._getcontent(self.resources, direction, '%s.html' % content)
                except IOError:
                    return None, None
            else:
                return None, None

        self.apply_auto(messageobj, **extra)

        # apply magic variables
        msg = self.applySubstitutions(content, messageobj, getattr(messageobj, 'buddy', None), **extra)

        return 'append%sMessage' % ('Next' if next else ''), msg

    def apply_auto(self, mobj, autotext='{message}', **extras):
        if getattr(mobj, 'auto', False):
            mobj.message = autotext.format(message = mobj.message)

    def applySubstitutions(self, s, msgobj = None, buddy = None, **extra):
        '''
        Replace MessageStyle variables like %incomingIconPath% or
        %time{%H:%M}
        '''

        if not isinstance(s, basestring): raise TypeError

        def _repl(match):
            wholeMatch, attr, __, args = match.groups()
            return self.getMagicAttr(attr, args, wholeMatch, m = msgobj, b = buddy, **extra)

        if isinstance(s, str):
            s = s.decode('fuzzy utf-8')

        try:
            s = msgpattern.sub(_repl, s)
        except UnicodeDecodeError, e:
            log.critical('error substituting message style variables')
            log.critical('  s: %r', s)
            log.critical('  buddy: %r', buddy)
            if buddy is not None:
                log.critical('  buddy alias: %r\n', getattr(buddy, 'alias', '<no alias attribute>'))
            log.critical('  extra: %r', extra)
            log.critical('%r', e)

        return s


    def getMagicAttr(self, attr, args = None, originalString = '', m = None, b = None, **extra):
        try:
            attrs = self.magicattrs
        except AttributeError:
            self.setup_string_substitution()
            attrs = self.magicattrs

        try:
            try:
                return attrs[attr](m, b) if args is None else attrs[attr](m, b, args)
            except KeyError:
                return extra[attr]
        except Exception:
            #print_exc() #uncomment me to find out why there are %strayvariables% in your HTML
            return '%' + attr + '%'

    show_tstamp = prefprop('conversation_window.timestamp', True)
    tstamp_fmt  = prefprop('conversation_window.timestamp_format', '%#I:%M')

    def setup_string_substitution(self):
        # TODO: this should probably be done once, at the class level...not in a function

        icon = get_buddy_icon_url

        def strf(t, fmt = None):
            if not self.show_tstamp and not self.should_always_show_timestamp:
                return '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'

            fmt = self.tstamp_fmt if fmt is None else fmt

            for s, repl in strftime_replacements:
                fmt = fmt.replace(s, repl)

            return strftime_u(fromutc(t), fmt)

        def time(m, b, fmt = None):
            # %a %B %e %H:%M:%S %Y
            return strf(m.timestamp, fmt)

        def timeOpened(m, b, fmt = None):
            # TODO: this is wrong. have convos track their opened datetime
            return strf(datetime.utcnow(), fmt)

        def xml_or_None(s):
            if s is None:
                return None
            return s.encode('xml')

        self.magicattrs = dict(
            #
            # magic name        = lambda: message, buddy: "template substitution"
            #
            chatName            = lambda m, b: xml_or_None(self.options.get('chatName')),
            incomingIconPath    = lambda m, b: icon(b),
            userIconPath        = lambda m, b: icon(b),
            senderScreenName    = lambda m, b: xml_or_None(b.name),  # service screenname
            senderDisplayName   = lambda m, b: xml_or_None(b.remote_alias or b.alias),
            sender              = lambda m, b: xml_or_None(getattr(b, 'alias', b.name)),
            time                = time,
            timeOpened          = timeOpened,
            message             = lambda m, b: m.message,
            service             = lambda m, b: protocols[b.service].name if b is not None else '',
            messageDirection    = lambda m, b: 'rtl' if isRTL(strip_html2(m.message)[0]) else 'ltr',
        )

class DigsbyMessageStyle(AdiumMessageStyle):
    def setup_string_substitution(self):
        AdiumMessageStyle.setup_string_substitution(self)

        self.magicattrs.update(
           auto = lambda m,b: m.auto,
       )

