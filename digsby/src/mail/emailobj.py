'''
Represents an email.
'''

from util import autoassign, strip_html_and_tags, replace_newlines, Storage
from util.lrucache import lru_cache
from util.auxencodings import fuzzydecode
from email.utils import parseaddr, parsedate
from email.header import decode_header
from datetime import datetime
import email.message
from common import pref
import sys, traceback

import logging
log = logging.getLogger('emailobj')

replace_newlines = lru_cache(100)(replace_newlines)

UnicodeErrors = (UnicodeEncodeError, UnicodeDecodeError)

def unicode_hdr(hdr, fallback=None):
    more_encs = [fallback] if fallback else []
    try:
        return u''.join(fuzzydecode(hdr, [encoding,]+more_encs) if encoding else hdr
                        for (hdr, encoding) in decode_header(hdr))
    except UnicodeErrors:
        # a unicode string with extended ascii characters gets into this function, this is what happens
        # because the stdlib's decode_header function calls str() on its argument.
        return fuzzydecode(hdr, more_encs+['utf-8'])
    except Exception:
        # an example header that raises ValueError (because of an int() call in email.header.decode_headers)
        # 'You=?UTF8?Q?=E2=80=99?=re HOT, brian@thebdbulls.com =?UTF8?Q?=E2=80=93?= See if Someone Searched for You'
        log.warning('decoding an email header failed: %r', hdr)
        return fuzzydecode(hdr, more_encs+['utf-8'])

def find_part(email, types):
    if not email.is_multipart():
        # Our work here is done!
        return email

    results = dict((part.get_content_type(), part)
                       for part in email
                       if part.get_content_type() in types)

    print results

    for ty in types:
        if ty in results:
            return results[ty]

    return None

def find_attachments(email):
    attachments = {}

    for part in email:
        if (('Content-Disposition' in part.keys()) and
            ('attachment' in part['Content-Disposition'])):
            attachments[part.get_filename()] = Storage(data = part.get_payload(decode=True),
                                                       content_type = part.get_content_type())

    return attachments

def parse_content(part):
    charset      = part.get_content_charset()
    content_type = part.get_content_type()
    payload      = part.get_payload(decode = True)

    html = (content_type == 'text/html')

    if payload is None:
        payload = ''

    try:
        content = payload.decode(charset or 'ascii')
    except (UnicodeDecodeError, LookupError):
        content = payload.decode('utf-8', 'replace')

    if html:
        content = strip_html_and_tags(content, ['style'])
    else:
        content = content

    return content


class Email(object):

    def __init__(self,
                 id          = None,
                 fromname    = None,
                 fromemail   = None,
                 sendtime    = None,
                 subject     = None,
                 content     = None,
                 attachments = None,
                 labels      = None,   ):
        autoassign(self, locals())

    def update(self, email):
        if isinstance(email, dict):
            attrs = email
        else:
            attrs = vars(email)

        autoassign(self, dict((k, v) for k, v in attrs.iteritems() if v is not None))

    @classmethod
    def fromEmailMessage(cls, id, email, sendtime_if_error = None):
        'Creates an Email from a Python email.message.Message object.'
        encoding = email.get_content_charset()
        # parse name, address
        realname, email_address = parseaddr(email['From'])
        realname = unicode_hdr(realname, encoding)

        # parse date

        _email = email

        try:
            datetuple = parsedate(email['Date'])
            sendtime = datetime(*datetuple[:7])
        except Exception:
            traceback.print_exc()
            print >> sys.stderr, 'using %s for "sendtime" instead' % sendtime_if_error
            sendtime = sendtime_if_error

        try:
            attachments = find_attachments(email)
        except:
            attachments = {}
        part = find_part(email, ('text/plain', 'text/html'))

        if part is None:
            content = u''

        else:
            content = parse_content(part)

        content = replace_newlines(content)

        prev_length = pref('email.preview_length', 200)
        if len(content) > prev_length:
            content = content[:prev_length] + '...'
        else:
            content

        email = cls(id, realname, email_address, sendtime, email['Subject'],
                     content = content, attachments=attachments)

        return email

    def __eq__(self, other):
        'Email equality is determined by its "id" attribute.'

        if not isinstance(other, Email):
            return False

        return self.id == other.id

    def __cmp__(self, other):
        'Makes emails.sort() newest -> oldest.'
        try:
            return -cmp(self.sendtime, other.sendtime)
        except TypeError:
            return -1

    @property
    def domain(self):
        f = self.fromemail
        if f is not None:
            return f[f.find('@')+1:]

#    disabled b/c of #3535
#
#    @property
#    def icon_badge(self):
#        from common.favicons import favicon
#        domain = self.domain
#        if domain is not None:
#            return favicon(self.domain)

    def __unicode__(self):
        'Returns a simple string representation of this email.'

        lines = [unicode('Subject: %s' % (self.subject or '<none>')).encode("utf-8")]

        if self.fromname:
            _fromstr = self.fromname
            if self.fromemail:
                _fromstr += ' <%s>' % self.fromemail
        elif self.fromemail:
            _fromstr = self.fromemail
        else:
            _fromstr = '<unknown>'
        lines.append('From: %s' % _fromstr)

        if self.sendtime:
            lines.append('Sent at %s' % self.sendtime)

        if self.content:
            lines.append('')
            lines.append(unicode(self.content))
        self.lines = lines
        return u''.join(lines)

    # Ascii representation...XML entities might be in here, so ignore
    # them for console (ASCII).
    __str__ = lambda self: self.__unicode__().decode('ascii', 'ignore')

    def __repr__(self):

        try:
            return u'<Email (Subject: %r, From: %r)>' % \
                        (self.subject[:30], self.fromemail or self.fromname)
        except Exception:
            return u'<Email from %r>' % self.fromemail


class DecodedEmail(email.message.Message):
    def __init__(self, myemail):
        self.email = myemail
        # Why does this line break things? gah.
        #email.message.Message.__init__(self)

    def __getattr__(self, attr, val = sentinel):
        result = getattr(self.email, attr, val)
        if result is sentinel:
            raise AttributeError
        else:
            return result

    def __getitem__(self, header):
        s = email.message.Message.__getitem__(self, header)

        if header == 'Content':
            return s
        else:
            return unicode_hdr(s, self.get_content_charset())

    __iter__ = email.message.Message.walk
