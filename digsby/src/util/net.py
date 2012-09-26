from __future__ import with_statement

import sys, traceback, re, struct, logging, random, StringIO
import calendar, time, rfc822
import socks, socket, asynchat
import urllib, urllib2, urlparse
import httplib, httplib2
import cookielib
import simplejson
import itertools

from httplib import HTTPConnection
from httplib import NotConnected

import primitives.funcs
import proxy_settings
from Events import EventMixin
from callbacks import callsback

try:
    sentinel
except NameError:
    class Sentinel(object):
        def __repr__(self):
            return "<Sentinel (%r backup) %#x>" % (__file__, id(self))
    sentinel = Sentinel()

log = logging.getLogger('util.net')

default_chunksize = 1024 * 4

def get_ips_s(hostname = ''):
    '''
    returns the ip addresses of the given hostname, default is '' (localhost)
    @param hostname: hostname to get the ips of
    @return ips as list of string
    '''
    # gethostbyname_ex returns tuple: (hostname, aliaslist, ipaddr_list)
    return socket.gethostbyname_ex(hostname or socket.gethostname())[2]

def get_ips(hostname = ''):
    '''
    returns the ip addresses of the given hostname, default is '' (localhost)
    @param hostname: hostname to get the ips of
    @return ips as list of int
    '''
    return [socket.inet_aton(ip) for ip in get_ips_s(hostname)]

myips = get_ips

def myip():
    'Returns the IP of this machine to the outside world.'
    return myips()[0]

def ip_from_bytes(bytes):
    """
    Converts a long int to a dotted XX.XX.XX.XX quad string.
    thanks U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66517}
    """


    return socket.inet_ntoa(bytes)

class FileChunker(object):
    'asynchat producer to return chunks of a file'

    def __init__(self, fileobj, chunksize = default_chunksize, close_when_done = False,
                 progress_cb = lambda bytes: None, bytecounter = None):

        self.fileobj         = fileobj
        self.chunksize       = chunksize
        self.close_when_done = close_when_done
        if bytecounter is None:
            bytecounter = fileobj.tell
        self.total           = bytecounter()
        self.progress_cb     = progress_cb
        self.cancelled       = False

    def more(self):
        try:
            data_read = self.fileobj.read(self.chunksize)
        except ValueError:
            try: self.fileobj.close() #make sure it's good and dead
            except: pass
            return '' #same as what happens at end of file
        sz = len(data_read)

        if sz == 0 and self.close_when_done:
            self.fileobj.close()

        self.total += sz
        self.progress_cb(self.total)

        return data_read

    @classmethod
    def tofile(cls, sourcefile, outfile, progress_callback = lambda *a: None,
               bytecounter = None):
        gen = cls.tofile_gen(sourcefile, outfile, progress_callback, bytecounter)
        gen.next()
        try:
            gen.next()
        except StopIteration:
            pass

    @classmethod
    def tofile_gen(cls, sourcefile, outfile, progress_callback = lambda *a: None,
               bytecounter = None):
        fc = cls(sourcefile, close_when_done = True, bytecounter = bytecounter)
        yield fc
        chunk = fc.more()
        bytes_written = 0

        # localize for speed
        write, tell, more = outfile.write, outfile.tell, fc.more

        while chunk and not fc.cancelled:
            write(chunk)
            bytes_written += len(chunk)
            progress_callback(tell())
            chunk = more()

        outfile.close()

class NoneFileChunker(FileChunker):
    def more(self):
        return super(NoneFileChunker, self).more() or None

def httpjoin(base, path, keepquery=False):
    if path.startswith('http'):
        # path is already absolute
        return path
    else:
        joined = urlparse.urljoin(base, path)
        if not keepquery:
            parsed = list(urlparse.urlparse(joined))
            parsed[4] = ''
            return urlparse.urlunparse(parsed)
        else:
            return joined

class UrlQuery(str):
    @classmethod
    def form_encoder(cls):
        return WebFormData

    @classmethod
    def parse(cls, url, parse_query = True, utf8=False):
        '''
        Return a mapping from a URL string containing the following keys:

        scheme://netloc/path;parameters?query#fragment

        If parse_query is True, "key=value&done" becomes
        {'key':'value', 'done':True} instead. Otherwise query is just a string.
        '''
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)

        if parse_query:
            query = cls.form_encoder().parse(query, utf8=utf8)

        return dict(scheme = scheme, netloc = netloc, path = path,
                    params = params, query = query, fragment = fragment)

    @classmethod
    def unparse(cls, scheme = '', netloc = '', path = '', params = '', query = None, fragment = ''):
        if query is None:
            query = {}

        if isinstance(query, dict):
            query = cls.form_encoder()(query)

        return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

    def __new__(cls, link, d={}, **kwargs):
        '''
        Splat **kwargs (and d) as URL parameters into the given url.

        The url must not already contain parameters (but may end with a
        question mark.)
        '''
        if not (d or kwargs):
            return str.__new__(cls, link)

        if link.endswith('?'):
            link = link[:-1]

        if '?' in link:
            joiner = '&' if (d or kwargs) else ''
        else:
            joiner = '?'

        return str.__new__(cls, ''.join([link, joiner, cls.form_encoder()(d = d, **kwargs)]))

class WebFormData(str):
    @classmethod
    def encoder(cls):
        return urllib.urlencode

    def __new__(cls, d={}, **kwargs):
        if d and kwargs:
            kwargs.update(d)
        else:
            kwargs = kwargs or d
        base = cls.encoder()(kwargs)
        return str.__new__(cls, base)

    @classmethod
    def parse(cls, s, utf8=False):
        querymap = {}
        if not s:
            return querymap
        encoding = 'utf8url' if utf8 else 'url'
        for elem in s.split('&'):
            if '=' in elem:
                key, value = elem.split('=', 1)
                querymap[key] = value.decode(encoding)
            else:
                querymap[elem] = True

        return querymap

class WebFormObjectData(WebFormData):
    @classmethod
    def encoder(cls):
        return urlencode_object

class UrlQueryObject(UrlQuery):
    @classmethod
    def form_encoder(cls):
        return WebFormObjectData

def urlencode_object(query):
    return urllib.urlencode(param(query))

def param(a):
    s = list()
    def add(key, value):
        s.append((key, value))
    for prefix in a:
        buildParams( prefix, a[prefix], add );
    return s

def buildParams(prefix, obj, add):
    if isinstance(obj, dict) and obj:
        for k,v in obj.items():
            buildParams( prefix + "[" + k +  "]", v, add );
    elif isinstance(obj, list):
        for k, v in enumerate(obj):
            if not isinstance(v, (list,dict)):
                k = ''
            buildParams( prefix + "[" + str(k) +  "]", v, add );
    else:
        add(prefix, obj)

def int_to_ip(s, byteorder='<'):
    '''
    turns an int (or string as int) into a dotted IP address.
    ex: int_to_ip('580916604') --> '124.21.160.34'

    default byteorder is little-endian (for msn)
    '''
    return '.'.join(str(ord(c)) for c in struct.pack(byteorder+'I', int(s)))


# matches two or more spaces in a row
spacify_pattern = re.compile('( {2,})')

def spacify_repl(m):
    l = len(m.group())

    if l == 2:
        return '  ' # "word joiner" unicode character is &#2060; but we're not using that anymore.
    else:
        # for more than two spaces use <SPACE><series of nbsp;s><SPACE>
        return ' ' + ''.join(['&nbsp;'] * (l-2)) + ' '

def spacify(s):
    'Turns consecutive spaces into a series of &nbsp; entities.'

    return spacify_pattern.sub(spacify_repl, s)

#
# a url for matching regexes
#
urlregex = re.compile(r'([A-Za-z][A-Za-z0-9+.-]{1,120}:[A-Za-z0-9/]'
                       '(([A-Za-z0-9$_.+!*,;/?:@&~=-])|%[A-Fa-f0-9]{2}){1,333}'
                       "(#([a-zA-Z0-9][a-zA-Z0-9$_.+!*,;/?:@&~=%-']{0,1000}))?)"
                       '[^\. <]')


#
# thanks http://en.wikipedia.org/wiki/List_of_Internet_top-level_domains
#
TLDs = \
['arpa', 'root', 'aero', 'asia', 'biz', 'com', 'coop', 'edu', 'gov', 'info', 'int',
 'museum', 'name', 'net', 'org', 'pro', 'ac', 'ad', 'ae', 'af', 'ag', 'ai', 'al', 'am',
 'an', 'ao', 'aq', 'ar', 'as', 'at', 'au', 'aw', 'ax', 'az', 'ba', 'bb', 'bd',
 'be', 'bf', 'bg', 'bh', 'bi', 'bj', 'bm', 'bn', 'bo', 'br', 'bs', 'bt', 'bv',
 'bw', 'by', 'bz', 'ca', 'cc', 'cd', 'cf', 'cg', 'ch', 'ci', 'ck', 'cl', 'cm',
 'cn', 'co', 'cr', 'cu', 'cv', 'cx', 'cy', 'cz', 'de', 'dj', 'dk', 'dm', 'do',
 'dz', 'ec', 'ee', 'eg', 'er', 'es', 'et', 'eu', 'fi', 'fj', 'fk', 'fm', 'fo',
 'fr', 'ga', 'gb', 'gd', 'ge', 'gf', 'gg', 'gh', 'gi', 'gl', 'gm', 'gn', 'gp',
 'gq', 'gr', 'gs', 'gt', 'gu', 'gw', 'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu',
 'id', 'ie', 'il', 'im', 'in', 'io', 'iq', 'ir', 'is', 'it', 'je', 'jm', 'jo',
 'jp', 'ke', 'kg', 'kh', 'ki', 'km', 'kn', 'kp', 'kr', 'kw', 'ky', 'kz', 'la',
 'lb', 'lc', 'li', 'lk', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'mc', 'md',
 'me', 'mg', 'mh', 'mk', 'ml', 'mm', 'mn', 'mo', 'mp', 'mq', 'mr', 'ms', 'mt',
 'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'nc', 'ne', 'nf', 'ng', 'ni', 'nl',
 'no', 'np', 'nr', 'nu', 'nz', 'om', 'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl',
 'pm', 'pn', 'pr', 'ps', 'pt', 'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw',
 'sa', 'sb', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sj', 'sk', 'sl', 'sm', 'sn',
 'so', 'sr', 'st', 'su', 'sv', 'sy', 'sz', 'tc', 'td', 'tf', 'tg', 'th', 'tj',
 'tk', 'tl', 'tm', 'tn', 'to', 'tp', 'tr', 'tt', 'tv', 'tw', 'tz', 'ua', 'ug',
 'uk', 'um', 'us', 'uy', 'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn', 'vu', 'wf',
 'ws', 'ye', 'yt', 'yu', 'za', 'zm', 'zw'
]


domains = '(?:%s)' % '|'.join(TLDs)

'''
 the one true email regex(tm)

 complicated case and simple case:
     this_email-user.name+mylabel@bbc.co.uk
     name@domain
'''

email_regex_string = r'(?:([a-zA-Z0-9_][a-zA-Z0-9_\-\.]*)(\+[a-zA-Z0-9_\-\.]+)?@((?:[a-zA-Z0-9\-_]+\.?)*[a-zA-Z]{1,4}))'

email_regex             = re.compile(email_regex_string)
email_wholestring_regex = re.compile('^' + email_regex_string + '$')

is_email = primitives.funcs.ischeck(lambda s:bool(email_wholestring_regex.match(s)))

class EmailAddress(tuple):
    def __new__(cls, addr, default_domain=sentinel):

        try:
            name, label, domain = parse_email(addr)
        except:
            if default_domain is sentinel:
                raise
            else:
                name, label, domain = parse_email(addr + '@' + default_domain)

        return tuple.__new__(cls, (name, label, domain.lower()))

    @property
    def name(self):
        return self[0]

    @property
    def label(self):
        return self[1]

    @property
    def domain(self):
        return self[2]

    def __str__(self):
        if self.label:
            return '%s+%s@%s' % self
        else:
            return '%s@%s' % (self.name, self.domain)

    def __repr__(self):
        return '<EmailAddress %s>' % (self,)

def parse_email(s):
    match = email_wholestring_regex.match(s)

    if match is None:
        raise ValueError('Not a valid email address: %r', s)

    user, lbl, dom = match.groups()
    if lbl:
        lbl = lbl.strip('+')
    else:
        lbl = ''
    return user, lbl, dom


protocols = 'ftp|https?|gopher|msnim|icq|telnet|nntp|aim|file|svn|svn+(?:\w)+'

# for these TLDs, only a few have ever been allowed to be registered.
single_letter_rule_tlds = frozenset(('net', 'com', 'org'))
allowed_single_letter_domains = frozenset(('i.net', 'q.com', 'q.net', 'x.com', 'x.org', 'z.com'))

linkify_url_pattern = re.compile(
  # thanks textile
  r'''(?=[a-zA-Z0-9])                             # Must start correctly
      ((?:                                        # Match the leading part (proto://hostname, or just hostname)
          (?:(?P<protocol>%s)                     #     protocol
          ://                                     #     ://
          (?:                                     #     Optional 'username:password@'
              (?P<username>\w+)                   #         username
              (?::(?P<password>\w+))?             #         optional :password
              @                                   #         @
          )?)?                                    #
          (?P<hostname>                           # hostname (sub.example.com). single-letter
          (?:[iqxz]|(?:[-\w\x7F-\xFF]+))          # domains are not allowed, except those listed:
          (?:\.[\w\x7F-\xFF][-\w\x7F-\xFF]*)*)    # http://en.wikipedia.org/wiki/Single-letter_second-level_domains
      )?                                          #
      (?::(?P<port>\d+))?                         # Optional port number
      (?P<selector>
        (?:                                       # Rest of the URL, optional
          /?                                      #     Start with '/'
          [^.!,?;:"<>\[\]{}\s\x7F-\xFF]+          #     Can't start with these
          (?:                                     #
              [.!,?;:]+                           #     One or more of these
              [^.!,?;:"<>{}\s\x7F-\xFF]+          #     Can't finish with these
              #'"                                 #     # or ' or "
          )*)                                     #
      )?)                                         #
   ''' % protocols, re.VERBOSE)


def isurl(text):
    m = linkify_url_pattern.match(text)
    if not m: return False

    protocol, host = m.group('protocol'), m.group('hostname')

    if host is not None:
        # only allow links without protocols (i.e., www.links.com)
        # if the TLD is one of the allowed ones
        if protocol is None:
            myTLDs = (host.split('.') if '.' in host else [host])
            if len(myTLDs) < 2 or myTLDs[-1] not in TLDs:
                return False

    return True

class LinkAccumulator(object):
    def __init__(self, s=None):
        self.links = []
        self.spans = []

        if s is not None:
            linkify_url_pattern.sub(self.repl, s)

    def repl(self, m):
        url, protocol, after = _url_from_match(m)
        if url is None:
            return ''
        href = ('http://' + url) if protocol is None else url
        self.links.append(href)
        self.spans.append(m.span())
        return ''

    def __iter__(self):
        return itertools.izip(self.links, self.spans)

def find_links(text):
    return LinkAccumulator(text).links

def _url_from_match(m):
    protocol, host = m.group('protocol'), m.group('hostname')
    url = m.group()

    # fix urls (surrounded by parens)
    after = ''
    if url.endswith(')') and '(' not in url:
        url = url[:-1]
        after = ')'

    if host is not None:
        myTLDs = (host.split('.') if '.' in host else [host])
        # only allow links without protocols (i.e., www.links.com)
        # if the TLD is one of the allowed ones
        if protocol is None:
            if len(myTLDs) < 2 or myTLDs[-1] not in TLDs:
                return None, None, None

        if len(myTLDs) >= 2:
            # don't allow single letter second level domains unless they are in the list
            # of allowed ones above
            second_level_domain = myTLDs[-2]
            top_level_domain = myTLDs[-1]
            if (len(second_level_domain) == 1
                and '.'.join((second_level_domain, top_level_domain)) not in allowed_single_letter_domains
                and top_level_domain in single_letter_rule_tlds):
                # "cancel" the replacement
                return None, None, None

        return url, protocol, after

    return None, None, None

def _dolinkify(text):
    def repl(m):
        url, protocol, after = _url_from_match(m)

        if url is None:
            i, j = m.span()
            return text[i:j]

        href = ('http://' + url) if protocol is None else url

        return '<a href="%s">%s</a>' % (href, url) + after # TODO: add 'target="_blank"' ?

    #text = email_regex.sub(r'<a href="mailto:\1">\1</a>', text)
    text = linkify_url_pattern.sub(repl, text)
    return text

def linkify(text):
    if isinstance(text, unicode):
        return _linkify(text.encode('utf-8')).decode('utf-8')
    else:
        return _linkify(text)

def _linkify(text):
    # Linkify URL and emails.

    # If there is no html, do a simple search and replace.
    if not re.search(r'''<.*>''', text):
        return _dolinkify(text)

    # Else split the text into an array at <>.
    else:
        lines = []
        prev_line = ''
        for line in re.split('(<.*?>)', text):
            if not re.match('<.*?>', line) and not prev_line.startswith('<a'):
                line = _dolinkify(line)

            prev_line = line
            lines.append(line)

        return ''.join(lines)

class QueueableMixin(object):
    def __init__(self):
        object.__init__(self)
        self._on_queue = False

    def queue(self):
        # Adds this object to its socket's queue
        # if it's not already there.
        if not self._on_queue:
            self._queue()
            self._on_queue = True

    def unqueue(self):
        if self._on_queue:
            self._unqueue()
            self._on_queue = False

class ProducerQueuable(QueueableMixin):
    def __init__(self, sck):
        QueueableMixin.__init__(self)
        self.sck = sck

    def _queue(self):
        self.sck.push_with_producer(self)
    def _unqueue(self):
        try:
            self.sck.producer_fifo.remove(self)
        except ValueError:
            pass

class RoundRobinProducer(ProducerQueuable):
    def __init__(self, sck):
        ProducerQueuable.__init__(self, sck)
        self.list = []

    def add(self, prod):
        # Adds a producer to our list, and checks that it has
        # a callable "more" attribute.
        try:
            if not callable(prod.more):
                raise AssertionError('Producers must have a "more" method')
        except:
            traceback.print_exc()
            raise

        self.unqueue()
        self.list.append(prod)
        self.queue()

    def more(self):
        # If this is getting called, we *must* be on the queue
        self._on_queue = True

        d = None
        l = self.list
        prod = None
        while (not d) and l:
            prod = l.pop(0)
            d = prod.more()

            # if we got data, loop will break
            # if not, the "bad" producer is gone

        # end loop

        if d:
            # that producer is still good -- put it on the end.
            l.append(prod)
        else:
            # Didn't get any data. We're going to be removed
            # from the socket FIFO

#            if prod is None and not self.list:
#                print 'List of producers was empty, returning None'
#            else:
#                print 'Didn\'t get any data from %r' % prod

            self.unqueue()
            if self.list:
                self.queue()

        return d


class PriorityProducer(ProducerQueuable):
    def __init__(self, sck):
        ProducerQueuable.__init__(self, sck)

        self.high = []
        self.mid = []
        self.low = []

    def add(self, prod, pri='mid'):
        assert callable(prod.more)
        assert pri in ('high', 'mid', 'low')
        self.unqueue()
        getattr(self, pri).append(prod)
        self.queue()

    def more(self):
        # If this is getting called, we *must* be on the queue
        self._on_queue = True

        d = None
        for l in (self.high, self.mid, self.low):
            if not l: continue

            while not d and l:
                prod = l.pop(0)
                d = prod.more()

            if d:
                # Put the producer back where we got it
                l.insert(0, prod)
                break

#        if not d:
#            self.unqueue()

        return d

class HTTPConnProgress(HTTPConnection):
    'Subclass of HTTPConnection which sends a file object, reporting progress.'

    def send_file_cb(self, fileobj, progress_cb, blocksize = default_chunksize, progressDelta = 0):
        'Sends the contents of fileobj (a .read-able object) to server.'

        if self.sock is None:
            if self.auto_open:
                self.connect()
            else:
                raise NotConnected()

        if self.debuglevel > 0:
            print "sending contents of", fileobj

        try:
            read    = fileobj.read
            sendall = self.sock.sendall

            chunk   = read(blocksize)
            total   = 0

            while chunk:
                total += len(chunk)
                sendall(chunk)
                progress_cb(total - progressDelta)
                chunk = read(blocksize)

        except socket.error, v:
            if v[0] == 32:      # Broken pipe
                self.close()
            raise

class SocketEventMixin(EventMixin):
    events = EventMixin.events | set(("connected",
                                  "connection_failed",
                                  "socket_error",
                                  "socket_closed",
                                  ))

    def post_connect_error(self, e=None):
        self.event("socket_error")
        self.post_connect_disconnect()

    def post_connect_expt(self):
        self.event("socket_error")
        self.post_connect_disconnect()

    def post_connect_disconnect(self):
        self.close()
        self.event("socket_closed")

    def post_connect_close(self):
        self.close()
        self.event("socket_closed")

    def reassign(self):
        self.handle_expt = self.post_connect_expt
        self.handle_error = self.post_connect_error
        self.handle_close = self.post_connect_close
        self.do_disconnect = self.post_connect_disconnect

def build_cookie(name, value,
                   version = 0,
                   domain = sentinel,
                   port = sentinel,
                   path = sentinel,
                   secure = False,
                   expires = None,
                   discard = False,
                   comment = None,
                   comment_url = None,
                   rest = {'httponly' : None},
                   rfc2109 = False):

    if domain is sentinel:
        domain = None
        domain_specified = False
        domain_initial_dot = False
    else:
        domain_specified = True
        domain_initial_dot = domain.startswith('.')

    if port is sentinel:
        port = None
        port_specified = False
    else:
        port_specified = True

    if path is sentinel:
        path = None
        path_specified = False
    else:
        path_specified = True
    return cookielib.Cookie(**locals())


def GetSocketType():
    d = GetProxyInfo()
    if d:
        #socks.setdefaultproxy(**GetProxyInfo())
        return socks.socksocket
    else:
        return socket.socket

NONE = 'NONPROX'
SYSDEFAULT = 'SYSPROX'
CUSTOM = "SETPROX"

def GetProxyInfo():
    ps = proxy_settings

    try:
        pd = ps.get_proxy_dict()
    except Exception, e:
        print >>sys.stderr, 'No proxies because: %r' % e
        pd = {}

    get = pd.get
    proxytype= get('proxytype')
    port     = get('port')

    try:
        port = int(port)
    except:
        port = None

    addr     = get('addr')
    username = get('username')
    password = get('password')
    override = get('override')
    rdns     = get('rdns', False)

    try:
        override = int(override)
    except:
        if override not in (SYSDEFAULT, CUSTOM, NONE):
            override = SYSDEFAULT
    else:
        # Hack for old proxy code that only had 2 options
        if override:
            override = CUSTOM
        else:
            override = SYSDEFAULT

    if override == NONE:
        return {}
    elif override == SYSDEFAULT:
        px = urllib._getproxies()
        if not px: return {}

        url = px.get('http', None)
        if url is None: return {}

        url = urlparse.urlparse(url)

        addr = url.hostname or ''
        if not addr: return {}

        port = url.port or 80
        username = url.username or username or None
        password = url.password or password or None
        proxytype = 'http'

#    d = {}
#    if all((addr, port)):
#        d.update(addr=addr, port=port, proxytype=proxytype)
#
#        if all((username, password)):
#            d.update(username=username, password=password)

    if all((type, port, addr)):
        proxytype=getattr(socks, ('proxy_type_%s'%proxytype).upper(), None)
        return dict(addr=addr, port=port, username=username, password=password, proxytype=proxytype, rdns = rdns)
    else:
        return {}

def GetProxyInfoHttp2():
    i = GetProxyInfo()
    if not i:
        return None
    return httplib2.ProxyInfo(proxy_type = i['proxytype'],
                              proxy_host = i['addr'],
                              proxy_port = i['port'],
                              proxy_user = i['username'],
                              proxy_pass = i['password'],
                              proxy_rdns = i.get('rdns', False),
                              )

def getproxies_digsby():
    '''
    A replacement for urllib's getproxies that returns the digsby app settings.
    the return value is a dictionary with key:val as:
      'http' : 'http://user:pass@proxyhost:proxyport'

    the dictionary can be empty, indicating that there are no proxy settings.
    '''

    pinfo = GetProxyInfo()

    proxies = {}
    if pinfo.get('username', None) and pinfo.get('password', None):
        unpw = '%s:%s@' % (pinfo['username'], pinfo['password'])
    else:
        unpw = ''

    if pinfo.get('port', None):
        port = ':' + str(pinfo['port'])
    else:
        port = ''

    host = pinfo.get('addr', None)
    if not host:
        return proxies # empty dict

    all = unpw + host + port

    proxies = urllib.OneProxy()
    proxies._proxyServer = all

    if pinfo['proxytype'] != socks.PROXY_TYPE_HTTP:
        proxy_url = ('socks%d://' % (4 if pinfo['proxytype'] == socks.PROXY_TYPE_SOCKS4 else 5)) + all
        return dict(socks=proxy_url, http=proxy_url, https=proxy_url)

    proxies['https'] = 'http://' + all
    proxies['http'] = 'http://' + all
    proxies['ftp'] = 'http://' + all

    return proxies


class SocksProxyHandler(urllib2.ProxyHandler):
    '''
    Handles SOCKS4/5 proxies as well as HTTP proxies.
    '''
    handler_order = 100
    def proxy_open(self, req, type):
        try:
            req._proxied
        except AttributeError:
            proxyinfo = self.proxies.get(type, '')
            proxytype = urllib2._parse_proxy(proxyinfo)[0]
            if proxytype is None:
                req._proxied = False
                return urllib2.ProxyHandler.proxy_open(self, req, type)
            else:
                req._proxytype = proxytype
                req._proxied = True

                if proxytype == 'http' and type != 'https': # Http proxy
                    return urllib2.ProxyHandler.proxy_open(self, req, type)
                else:
                    return None
        else:
            # Already proxied. skip it.
            return None

    def socks4_open(self, req):
        return self.socks_open(req, 4)

    def socks5_open(self, req):
        return self.socks_open(req, 5)

    def socks_open(self, req, sockstype):

        orig_url_type, __, __, orighostport = urllib2._parse_proxy(req.get_full_url())
        req.set_proxy(orighostport, orig_url_type)

        endpoint = req.get_host()
        if ':' in endpoint:
            host, port = endpoint.rsplit(':', 1)
            port = int(port)
        else:
            host, port = endpoint, 80
        req._proxied = True

        return self.parent.open(req)

try:
    import ssl
except ImportError:
    pass
else:
    class SocksHttpsOpener(urllib2.HTTPSHandler):
        handler_order = 101
        def https_open(self, req):
            if getattr(req, '_proxied', False) and getattr(req, '_proxytype', None) is not None:
                return urllib2.HTTPSHandler.do_open(self, SocksHttpsConnection, req)
            else:
                return urllib2.HTTPSHandler.https_open(self, req)

    class SocksHttpsConnection(httplib.HTTPSConnection):
        _sockettype = socks.socksocket
        def connect(self):
            "Connect to a host on a given (SSL) port."

            pd = urllib.getproxies().get('https', None)
            if pd is None:
                sockstype = ''
            else:
                sockstype, user, password, hostport = urllib2._parse_proxy(pd)


            assert ':' in hostport # if we don't have a port we're screwed
            host, port = hostport.rsplit(':', 1)
            port = int(port)

            sock = self._sockettype(socket.AF_INET, socket.SOCK_STREAM)
            sock.setproxy(proxytype=getattr(socks, 'PROXY_TYPE_%s' % sockstype.upper()), addr=host, port=port, rdns=True, username=user, password=password)
            sock.connect((self.host, self.port))
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file)


class SocksHttpOpener(urllib2.HTTPHandler):
    handler_order = 101
    def http_open(self, req):
        proxytype = getattr(req, '_proxytype', None)
        if getattr(req, '_proxied', False) and proxytype not in ('http', None):
            return urllib2.HTTPHandler.do_open(self, SocksConnection, req)
        else:
            return urllib2.HTTPHandler.http_open(self, req)


class SocksConnection(httplib.HTTPConnection):
    _sockettype = socks.socksocket
    def connect(self):
        #- Parse proxies
        pd = urllib.getproxies().get('http', None)
        if pd is None:
            sockstype = ''
        else:
            sockstype, user, password, hostport = urllib2._parse_proxy(pd)

        if 'socks' not in sockstype:
            return httplib.HTTPConnection.connect(self)

        assert ':' in hostport # if we don't have a port we're screwed
        host, port = hostport.rsplit(':', 1)
        port = int(port)


        for res in socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM):

            af, socktype, proto, canonname, sa = res
            try:
                self.sock = self._sockettype(af, socktype, proto)
                self.sock.setproxy(proxytype=getattr(socks, 'PROXY_TYPE_%s' % sockstype.upper()), addr=host, port=port, rdns=False, username=user, password=password)
                #- The rest is the same as superclass

                if self.debuglevel > 0:
                    print "connect: (%s, %s)" % (self.host, self.port)
                self.sock.connect(sa)
            except socket.error, msg:
                if self.debuglevel > 0:
                    print 'connect fail:', (self.host, self.port)
                if self.sock:
                    self.sock.close()
                self.sock = None
                continue
            break
        if not self.sock:
            raise socket.error, msg

class DigsbyHttpProxyPasswordManager(urllib2.HTTPPasswordMgr):
    def find_user_password(self, realm, uri):
        pi = GetProxyInfo()
        return (pi['username'] or None), (pi['password'] or None)

if not hasattr(urllib, '_getproxies'):
    urllib._getproxies, urllib.getproxies = urllib.getproxies, getproxies_digsby

    urllib2.UnknownHandler.handler_order = sys.maxint # This should be last, no matter what


    # BaseHandler comes first in the superclass list, but it doesn't take any arguments.
    # This causes problems when initializing the class with an argument.
    urllib2.ProxyDigestAuthHandler.__bases__ = urllib2.ProxyDigestAuthHandler.__bases__[::-1]
    urllib2.ProxyBasicAuthHandler.handler_order = 499 # Make sure it comes before the 'default' error handler

    httplib2.ProxyInfo.get_default_proxy = staticmethod(GetProxyInfoHttp2)

def GetDefaultHandlers():
    handlers = [SocksProxyHandler, SocksHttpOpener]
    httpsopener = globals().get('SocksHttpsOpener', None)
    if httpsopener is not None:
        handlers.append(httpsopener)

    pwdmgr = DigsbyHttpProxyPasswordManager()

    for auth_handler_type in (urllib2.ProxyBasicAuthHandler, urllib2.ProxyDigestAuthHandler):
        handlers.append(auth_handler_type(pwdmgr))

    return handlers

def build_opener(*a, **k):
    if 'default_classes' not in k:
        k['default_classes'] = GetDefaultHandlers() + urllib2.default_opener_classes

    return urllib2.build_opener(*a, **k)

opener = urllib2.build_opener(*GetDefaultHandlers())
#    for handler in opener.handlers:
#        handler._debuglevel = 1
urllib2.install_opener(opener)


_hostprog = re.compile('^//([^/?]*)(.*)$')
def splithost(url):
    """splithost('//host[:port]/path') --> 'host[:port]', '/path'."""
    match = _hostprog.match(url)
    if match:
        groups = match.group(1, 2)
        # Check if we're throwing out a slash accidentally. if so, put it back and return.
        if groups[0] == '':
            return groups[0], '/' + groups[1]
        else:
            return groups
    return None, url

urllib.splithost = urllib2.splithost = splithost # urllib2 imports it "from" urllib so we have to replace its copy as well

def _HTTPError__repr(self):
    if not hasattr(self, 'content'):
        try:
            self.content = self.read()
            self.close()
        except Exception, e:
            self._error = e
            self.content = "error reading body: %r" % e
            self.read = lambda: ''
        else:
            self._stringio = StringIO.StringIO(self.content)
            self.read = self._stringio.read

    etxt = self.content
    return '<HTTPError headers = %r, body = %r>' % (str(getattr(self, 'hdrs', {})), etxt)

urllib2.HTTPError.__repr__ = _HTTPError__repr

def httpok(_code):
    return getattr(_code, 'status', _code)//100 == 2

class SimpleProducer(asynchat.simple_producer):
    def more(self):
        data = asynchat.simple_producer.more(self)
        if data == '':
            data = None

        return data

class CallbackProducerMixin(object):
    '''
    Simple mixin for producer classes that calls callback.success() when all data has been read from it (via more()).

    Must be listed before the producer type in the inheritance list, for method resolution to work correctly.
    '''
    def __init__(self):
        bases = self.__class__.__bases__
        found_self = False
        self._siblingClass = None
        for base in bases:
            if base is CallbackProducerMixin:
                found_self = True
            else:
                if hasattr(base, 'more') and found_self:
                    self._siblingClass = base
                    break

        if self._siblingClass is None:
            raise AssertionError("This mix-in requires there is a sibling class with a 'more' method. "
                                 "Additionally, CallbackProducerMixin must be *before* that class in the inheritance list "
                                 "(for method resolution reasons).")

    @callsback
    def set_callback(self, callback=None):
        self._callback = callback

    def more(self):
        if not hasattr(self, '_siblingClass'):
            result = None
        else:
            result = self._siblingClass.more(self)

        if result is None:
            if getattr(self, '_callback', None) is not None:
                self._callback.success()
            if getattr(self, '_callback', None) is not None:
                del self._callback
        return result

class SimpleCallbackProducer(CallbackProducerMixin, SimpleProducer):
    '''
    Subclass of asynchat.simple_producer that calls self._callback.success() when all data has
    been exhausted. Set callback after instantiation with set_callback() method.

    SimpleCallbackProducer(data, buffer_size=512)
    '''
    def __init__(self, data):
        SimpleProducer.__init__(self, data)
        CallbackProducerMixin.__init__(self)

## Add a 'remove' method to asynchat's fifo

def _fifo_remove(self, val):
    '''
    returns True if value was found + removed, false otherwise.
    '''
    # self.list is a deque
    try:
        self.list.remove(val)
    except Exception:
        return False
    else:
        return True

asynchat.fifo.remove = _fifo_remove

@callsback
def producer_cb(data, callback=None):
    '''
    producer(data, success=callable)

    Facade for SimpleCallbackProducer.
    '''
    prod = SimpleCallbackProducer(data)
    prod.set_callback(callback=callback)
    return prod

class GeneratorProducer(object):
    def __init__(self, gen):
        self.gen = gen

    def more(self):
        if self.gen is None:
            return None

        try:
            return self.gen.next()
        except StopIteration:
            self.gen = None
            return None

# from tr.im:
_short_domains = frozenset((
                  '2big.at', '2me.tw', '3.ly', 'a.gd', 'a2n.eu', 'abbrr.com',
                  'adjix.com', 'arunaurl.com', 'beam.to', 'bit.ly',
                  'bitly.com', 'bkite.com', 'blip.fm', 'bloat.me',
                  'budurl.com', 'burnurl.com', 'canurl.com', 'chilp.it',
                  'cli.gs', 'decenturl.com', 'digg.com', 'digs.by', 'dn.vc',
                  'doiop.com', 'durl.us', 'dwarfurl.com', 'easyuri.com',
                  'easyurl.net', 'ff.im', 'fon.gs', 'fyiurl.com', 'ginx.com',
                  'goo.gl', 'go2.me', 'hex.io', 'hopurl.com', 'hurl.ws', 'icanhaz.com',
                  'idek.net', 'is.gd', 'ix.it', 'jijr.com', 'jmp2.net',
                  'knol.me', 'krz.ch', 'kurl.us', 'last.fm', 'lin.cr',
                  'lnk.in', 'makeitbrief.com', 'memurl.com', 'micurl.com',
                  'minu.ws', 'moourl.com', 'myturl.com', 'notlong.com', 'ow.ly',
                  'pic.im', 'pikchur.com', 'ping.fm', 'piurl.com', 'poprl.com',
                  'qurlyq.com', 'r.im', 'refurl.com', 'rubyurl.com', 'rurl.org',
                  'rurl.us', 's7y.us', 'sai.ly', 'sbt.sh', 'shorl.com'
                  'short.ie', 'short.to', 'shortna.me', 'shrinkify.com',
                  'shw.com', 'si9.org', 'skocz.pl', 'smalur.com', 'sn.im',
                  'snipr.com', 'snipurl.com', 'snurl.com', 'spedr.com',
                  'starturl.com', 'three.ly', 'timesurl.at', 'tiny.cc', 'tiny.pl',
                  'tinyarro.ws', 'tinylink.co.za', 'tinyuri.ca', 'tinyurl.com',
                  'tnij.org', 'tr.im', 'turo.us', 'twitclicks.com', 'twitpic.com',
                  'twt.fm', 'twurl.cc', 'twurl.nl', 'u.nu', 'ub0.cc', 'uris.jp',
                  'urlb.at', 'urlcut.com', 'urlenco.de', 'urlhawk.com',
                  'urltea.com', 'vieurl.com', 'w3t.org', 'x.se', 'xaddr.com',
                  'xr.com', 'xrl.us', 'yep.it', 'zi.ma', 'zombieurl.com', 'zz.gd'))

def is_short_url(url, domains = _short_domains):
    parsed = urlparse.urlparse(url)
    if parsed.netloc in domains:
        return True

    return False

def get_snurl(url):
    return get_short_url(url, 'snurl')

def get_isgd(url):
    return get_short_url(url, 'isgd')

def get_tinyurl(url):
    return get_short_url(url, 'tinyurl')

class UrlShortenerException(Exception):
    pass

from .lrucache import LRU
_short_url_cache = LRU(10)
def cache_shortened_url(url, short_url):
    if short_url:
        _short_url_cache[short_url] = url

class UrlShortener(object):
    endpoint = None

    def build_request_url(self, url):
        return UrlQuery(self.endpoint, d = self.get_args(url.encode('utf-8')))

    def shorten(self, url):
        try:
            resp = urllib2.urlopen(self.build_request_url(url))
        except urllib2.HTTPError, e:
            resp = e

        short_url = self.process_response(resp)
        cache_shortened_url(url, short_url)
        return short_url

    def shorten_async(self, url, success, error=None):
        def async_success(req, resp):
            try:
                ret = self.process_response(resp)
            except Exception as e:
                if error is not None: error(e)
            else:
                cache_shortened_url(url, ret)
                success(ret)

        def async_error(req=None, resp=None):
            print req
            print resp
            if error is not None:
                error(None) # TODO: async interface for errors?

        import common.asynchttp as asynchttp
        asynchttp.httpopen(self.build_request_url(url), success=async_success, error=async_error)

    def get_args(self, url):
        raise NotImplementedError

    def process_response(self, resp):
        if resp.code != 200:
            body = resp.read()
            raise UrlShortenerException(body)

        ret = resp.read()
        return ret

class ResponseIsResultShortener(UrlShortener):
    def process_response(self, resp):
        ret = UrlShortener.process_response(self, resp)
        if not isurl(ret):
            raise UrlShortenerException(body)
        return ret

class isgd_shortener(ResponseIsResultShortener):
    endpoint = 'http://is.gd/api.php'
    def get_args(self, url):
        return dict(longurl=url)

class tinyurl_shortener(ResponseIsResultShortener):
    endpoint = 'http://tinyurl.com/api-create.php'
    def get_args(self, url):
        return dict(url=url)

class threely_shortener(UrlShortener):
    endpoint = 'http://3.ly/'
    def get_args(self, url):
        return dict(api = 'em5893833',
                    u = url)

    def process_response(self, resp):
        ret = UrlShortener.process_response(self, resp)
        if not ret.startswith(self.endpoint):
            raise UrlShortenerException(ret)

        return ret

class snipr_shortener(UrlShortener):
    endpoint = 'http://snipr.com/site/snip'
    def get_args(self, url):
        return dict(r='simple', link=url.encode('url'))
    def process_response(self, resp):
        ret = UrlShortener.process_response(self, resp)
        if not ret.startswith('http'):
            raise UrlShortenerException('bad url: %r' % ret, ret)
        return ret

class shortname_shortener(UrlShortener):
    endpoint = 'http://shortna.me/hash/'
    def get_args(self, url):
        return dict(snURL=url, api=0)

    def process_response(self, resp):
        ret = UrlShortener.process_response(self, resp)
        import lxml.html as HTML
        doc = HTML.fromstring(ret)
        links = doc.findall('a')
        for link in links:
            href = link.attrib.get('href')
            if href is not None and href.startswith('http://shortna.me/') and href != 'http://shortna.me':
                return href

        raise UrlShortenerException('short link not found in %r' % ret, ret)

# not currently used
class digsby_shortener(UrlShortener):
    endpoint = 'https://accounts.digsby.com/api/shorturl'
    def get_args(self, url):
        import common
        import hashlib
        username = common.profile.username.encode('utf8')
        password = hashlib.sha256(common.profile.password.encode('utf8')).digest()

        return {'user':username, 'pass':password, 'link' : url}

    def process_response(self, httpresp):
        ret = UrlShortener.process_response(self, httpresp)

        resp = simplejson.loads(ret)
        if resp['shorter']['status'] == 'error':
            raise UrlShortenerException(resp['shorter']['errormsg'])

        elif resp['shorter']['status'] == 'ok':
            import common
            url = resp['shorter']['shortURL']
            to_add = common.pref('urlshorteners.digsby.append_text', type = unicode, default = u'')
            return url + to_add

class bitly_shortener(UrlShortener):
    login = 'digsby'
    api_key = 'R_1fdb0bb8ce9af01f9939c2ffdf391dc8'
    endpoint = 'http://api.bit.ly/shorten'

    def __init__(self, login=None, api_key=None):
        if login is not None:
            self.login = login
        if api_key is not None:
            self.api_key = api_key

    def get_args(self, url):
        return dict(longUrl=url, version='2.0.1', login=self.login, apiKey=self.api_key)

    def process_response(self, resp):
        ret = UrlShortener.process_response(self, resp)

        try:
            info = simplejson.loads(ret)
        except Exception:
            raise UrlShortenerException('expected JSON')
        else:
            if info['errorCode'] == 0:
                return self.extract_shorturl(info)
            else:
                raise UrlShortenerException(info['errorMessage'])

    def extract_shorturl(self, info):
        return info['results'].values()[0]['shortUrl']


class digsby_bitly_shortener(bitly_shortener):
    def extract_shorturl(self, info):
        return "http://digs.by/" + info['results'].values()[0]['userHash']


# TODO: add bit.ly, cli.gs, tr.im
_shorteners = {
   #'snipr'    : snipr_shortener,
   #'snurl'    : snipr_shortener,
   #'snipurl'  : snipr_shortener,      # has a new API we didn't implement yet
    'isgd'     : isgd_shortener,
    'tinyurl'  : tinyurl_shortener,
    'tiny'     : tinyurl_shortener,
    'threely'  : threely_shortener,
    '3ly'      : threely_shortener,
    'shortname': shortname_shortener,
    'digsby'   : digsby_bitly_shortener,
    }

def get_short_url(url, provider=None, choices = None):
    """
    Gets a shortened url from 'provider' through their api.

    Intended to be used with threaded:
    threaded(get_short_url)(url, 'tinyurl', success=func, error=func)

    @param url: The URL to be snipped
    @param provider: The shortening service to use.
    """
    if choices is None:
        choices = list(_shorteners.keys())
    choices = choices[:]
    random.shuffle(choices)

    if provider is not None:
        choices.append(provider)
    else:
        import common
        choices.append(common.pref("url_shortener.default", type = basestring, default = 'digsby'))

    e = None
    while choices:
        try:
            provider = choices.pop()
            shortener = _shorteners.get(provider)
            if shortener is None:
                raise Exception("UrlShortener provider %r not found", provider)

            return shortener().shorten(url)
#        except UrlShortenerException, e:
#            log.error('error getting short URL from %r: %r', provider, e)
#            raise e
        except Exception, e:
            log.error('error getting short URL from %r: %r', provider, e)
            shortener = provider = None

    if e is None:
        e = Exception('No shorteners found!')
    # none of them worked
    raise e


def wget(url, data=None):
    '''
    return urllib2.urlopen(url, data).read()
    '''
    from contextlib import closing
    import urllib2
    with closing(urllib2.urlopen(url, data=data)) as web:
        return web.read()

def long_url_from_cache(shorturl):
    try:
        return _short_url_cache[shorturl]
    except KeyError:
        return None

def unshorten_url(url, cb):
    longurl = long_url_from_cache(url)
    if url is not None:
        return cb(longurl)

    requrl = UrlQuery('http://untiny.me/api/1.0/extract',
                      url=url, format='json')

    def success(req, resp):
        json = resp.read()
        unshortened_url = simplejson.loads(json)['org_url']
        cb(unshortened_url)

    def error(req, resp):
        pass

    import common.asynchttp as asynchttp
    return asynchttp.httpopen(requrl, success=success, error=error)

def timestamp_to_http_date(ts):
    return rfc822.formatdate(timeval=ts)

def http_date_to_timestamp(date_str):
    if date_str is None:
        return None
    return calendar.timegm(rfc822.parsedate(date_str))

def user_agent():
    return 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.10) Gecko/20100914 Firefox/3.6.15'

if __name__ == '__main__':
    print get_snurl('http://www.google.com')


