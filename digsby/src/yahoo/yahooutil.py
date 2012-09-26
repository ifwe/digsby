'''
Yahoo utilities.
'''

from __future__ import with_statement
import re
from urllib import unquote_plus
from itertools import izip
from struct import pack, calcsize
from httplib import HTTPConnection
from .yahoolookup import ykeys, commands
from logging import getLogger; log = getLogger('yahoo'); info = log.info
from util import odict, threaded
from pprint import pformat
from common.exceptions import LoginError

class YahooLoginError(LoginError):
    def __init__(self, protocol, message):
        if not isinstance(message, basestring):
            raise TypeError('message must be a string')

        self.protocol = protocol
        Exception.__init__(self, message)


_filematch = re.compile(r'.*/(.+)\?\w+')


def filename_from_url(url):
    '''
    Returns a normally formatted filename from a file transfer URL.

    >> filename_from_url("http://fs.yahoo.com/name/.tmp/filename.txt?adfadfa'")
    filename.txt
    '''

    return unquote_plus(_filematch.search(url).group(1))

# standard ymsg argument seperator that separates items in a Yahoo dictionary
# on the network: 0xc0 followed by 0x80
argsep = pack( 'BB', 0xc0, 0x80 )

def to_ydict(d, argsep=argsep):
    '''
    Makes a yahoo dictionary ready to be sent out on the network.

    Takes either a mapping object (specifically, one with an iteritems
    attribute), or a even-length sequence object of key-value pairs.
    '''
    if not d:
        return ''

    def to_ydict_entry(k, v):
        try: n = int(k)
        except ValueError:
            try:
                n = ykeys[k]
            except:
                log.warning('to_ydict got a dict with a non number key: %s', k)
                return ''

        if isinstance(v, bytes):
            pass
        elif isinstance(v, (int,long)):
            v = str(v)
        else:
            if not isinstance(v, unicode):
                import warnings
                warnings.warn("yahoo got argument %r of type %r, not unicode" % (v, type(v)))
                v = unicode(v)
            v = v.encode('utf-8')

        return ''.join([str(n), argsep, v, argsep])

    # find some way to iterate
    if hasattr(d, 'iteritems'):        item_iterator = d.iteritems()
    elif isinstance(d, (list, tuple)): item_iterator = izip(d[::2],d[1::2])

    return ''.join(to_ydict_entry(k,v) for k,v in item_iterator)

def from_ydict_iter(data, argsep=argsep):
    'Returns an iterable of key-value pairs from a yahoo dictionary.'

    if not data: return iter([])
    data = data.split(argsep)
    keys, values = data[::2], data[1::2]

    # utf8 is the defined wire protocol for values in these dictionaries.
    # convert them to unicode before they get to the upper layers
    values = [from_utf8(v) for v in values]

    return izip(keys, values)

def from_utf8(s):
    if isinstance(s, str): s = s.decode('fuzzy utf8')
    return s

def format_packet(data, maxlen = 500, sensitive = False):
    if sensitive:
        items = []
        append = items.append
        for k, v in from_ydict_iter(data):
            k = ykeys.get(k, k)
            if k == 'message':
                v = '<omitted>'
            append((k, v))
    else:
        items = [(ykeys.get(k, k), v)
                 for k, v in from_ydict_iter(data)]

    return pformat(items)

def yiter_to_dict(yiter):
    d = odict()

    for k, v in yiter:
        try: k = ykeys[k]
        except KeyError: pass
        d[k] = v

    return d

def from_ydict(data, argsep=argsep):
    '''Turns a special contact yahoo dictionary into [a] Python dictionar[y/ies].

    If duplicate keys are found, all subsequent keys get turned into seperate
    dicts.'''


    d = {}

    for k, v in from_ydict_iter(data, argsep=argsep):
        if k in d:
            log.warning('duplicate %s: %s', k, v)
            #raise AssertionError()

        d[k] = v

    return d

# the layout of a Yahoo packet header has the following binary layout:
header_pack = '!4sHHHHiI'

# the binary entries above correspond to the following names:
header_desc = (header_pack,
          'ymsg',               # 4
          'version',            # 2
          'zero',               # 2
          'size',               # 2
          'command','status',   # 2, 4
          'session_id')         # 4
header_size = calcsize(header_pack)

#TODO: use Packable in the above

def header_tostr(hdr):
    "Prints out a nice string representation of a YMSG header."
    try:
        sv = commands[hdr.command]
    except KeyError:
        log.error("No command string for %s", hdr.command)
        sv = str(hdr.command)

    try:
        st = commands[hdr.status]
    except KeyError:
        log.error("No status string for %s", hdr.status)
        st = str(hdr.status)

    return 'YMSG packet( srv:%s, st:%s, id:%d v:%d, sz:%d )' % \
        (sv, st, hdr.session_id, hdr.version, hdr.size)

@threaded
def yahoo_http_post(ydata, cookies, progress_cb = lambda x: None):
    conn = HTTPConnection('filetransfer.msg.yahoo.com')

    # Hack httplib to send HTTP/1.0 as the version
    conn._http_vsn_str = 'HTTP/1.0'
    conn._http_vsn = 10

    #conn.set_debuglevel(3)
    url = 'http://filetransfer.msg.yahoo.com:80/notifyft'
    conn.putrequest('POST', url, skip_host = True, skip_accept_encoding=True)

    conn.putheader ('Content-length', str(len(ydata)))
    conn.putheader ('Host', 'filetransfer.msg.yahoo.com:80')
    conn.putheader ('Cookie', cookies)
    conn.endheaders()

    log.info('putting %d bytes of data...', len(ydata))

    for x in xrange(0, len(ydata), 512):
        conn.send(ydata)
        progress_cb(x)

    progress_cb(len(ydata))

    # Check for OK
    response = conn.getresponse()
    respdata, status = response.read(), response.status

    log.info('response data %d bytes, status code %s', len(respdata), status)

    conn.close()

    if status != 200:
        log.error('ERROR: POST returned a status of %d', status)
        return False

    info('HTTP POST response status %d', status)
    return True

class Cookie(str):
    def __init__(self, s):
        str.__init__(s)
        info('Cookie string %s', s)
        self.params = odict()

        for pair in s.split('&'):
            key, val = pair.split('=')
            self.params[key] = val

    def val(self):
        return '&'.join('%s=%s' % (k,v) for k,v in self.params.items())

def add_cookie(jar, cookiestr):
    assert isinstance(jar, dict)

    spl = cookiestr.find('\t')
    assert spl != -1

    key, value = cookiestr[:spl], cookiestr[spl + 1:]

    value = value.split('; ')[0]
    log.info('adding cookie %s: %s', key, value)
    jar[key] = value

def y_webrequest(url, data, cookies):
    headers = {'Cookie': cookies['Y'] + '; ' + cookies['T'],
               'User-Agent': 'Mozilla/4.0 (compatible; MSIE 5.5)',
               'Cache-Control': 'no-cache'}

    import urllib2
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    return response.read()



if __name__ == '__main__':

    cookies = {'Y':'v=1&n=3lutd2l220eoo&l=a4l8dm0jj4hisqqv/o&p=m2l0e8v002000000&r=fr&lg=us&intl=us',
               'T':'z=3H2OGB3NLPGBQXPLeKgW24v&a=YAE&sk=DAAHHqpEue2zZY&d=YQFZQUUBb2sBWlcwLQF0aXABQldCb2lBAXp6ATNIMk9HQmdXQQ--'}

    data = '<validate intl="us" version="8.1.0.209" qos="0"><mobile_no msisdn="17248406085"></mobile_no></validate>'

    print y_webrequest('http://validate.msg.yahoo.com/mobileno?intl=us&version=8.1.0.209',
                       data, cookies)
