from .YahooSocket import YahooConnectionBase
from .yahoologinsocket import YahooLoginBase
from .yahoolookup import ykeys
from common import callsback
from hashlib import sha1
from itertools import izip
from logging import getLogger
from .yahooutil import from_utf8
from util.xml_tag import tag
from common.asynchttp.cookiejartypes import CookieJarHTTPMaster
from urllib2 import HTTPError
from httplib import HTTPResponse as libHTTPResponse
from common.asynchttp.httptypes import HTTPResponse as asyncHTTPResponse
RESPONSE_TYPES = (libHTTPResponse, asyncHTTPResponse)
import cookielib
import re
import string

log = getLogger('yahoohttp')

argsep = '^$'

ASCII_LETTERS = '@' + ''.join(sorted(string.ascii_letters))[:0x1f]

caret_split_re = re.compile('((?:\^.)|!(?:\^.))')

even_caret          = r'(?:(?:\^{2})*)'
single_caret_dollar = r'(?:\^\$)'

odd_caret_dollar_re    = re.compile(even_caret + single_caret_dollar)

parser_re = re.compile('(' + even_caret + (single_caret_dollar + '?') + ')')

def decode_caret(s):
    ss = caret_split_re.split(s)
    ret = []
    for s2 in ss:
        if s2 == '^^':
            s2 = '^'
        elif s2 == '^@':
            s2 = '\0'
        elif len(s2) == 2 and s2[0] == '^':
            ascii_pos = ASCII_LETTERS.find(s2[1])
            if ascii_pos >= 0: # != -1
                s2 = chr(ascii_pos)
        ret.append(s2)
    return ''.join(ret)

#TODO: use StringIO
def encode_caret(s):
    ret = []
    for char in s:
        if char == '^':
            ret.append('^^')
            continue
        if 0 <= ord(char) < len(ASCII_LETTERS): # < 0x20 (1 + 0x1f)
            ret.append('^' + ASCII_LETTERS[ord(char)])
        else:
            ret.append(char)
    return ''.join(ret)

class YahooHTTPConnection(YahooConnectionBase, YahooLoginBase):
    def __init__(self, yahoo, server):
        YahooConnectionBase.__init__(self, yahoo)
        YahooLoginBase.__init__(self, yahoo)
        self.server = server
        self.init_vars()
        self.handle_connect()

    def init_vars(self):
        self.ClientCounter = 0

        #I kid you not, an 8 digit integer string representation encoded in hex
        # from the last 8 digits of the string representation of the lower word
        # of GetSystemTimeAsFileTime.  Random seems just as good, since that value
        # in units of 100 nanoseconds, 8 digits will cycle every 10 seconds
        #http://forum.sharpdressedcodes.com/index.php?showtopic=589
        #wtfinterns?
        from random import randint
        self.secret = '%08d' % randint(0, int('9'*8))
        self.Secret = (self.secret).encode('hex')
        self.jar = cookielib.CookieJar()

        self.client_http_opener = CookieJarHTTPMaster(jar=self.jar)
        self.server_http_opener = CookieJarHTTPMaster(jar=self.jar)

    def close(self):
        self._close_server()
        #if we don't inform the server that we're leaving, we won't appear offline until
        # it decides we have timed-out.
        if self.client_http_opener is not None:
            self._push_cb(self.yahoo.yahoo_packet('logoff', 'available'),
                         success = self._close_client,
                         error   = self._close_client)

    def _close_server(self, *a):
        self.server_http_opener, sho = None, self.server_http_opener

        if sho is not None:
            sho.close_all()

    def _close_client(self, *a):
        self.client_http_opener, cho = None, self.client_http_opener

        if cho  is not None:
            cho.close_all()

    @classmethod
    def to_ydict(cls, d):
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

            try:
                v = str(v)
            except UnicodeEncodeError:
                v = unicode(v).encode('utf-8')

            return ''.join([str(n), argsep, encode_caret(v), argsep])

        # find some way to iterate
        if hasattr(d, 'iteritems'):        item_iterator = d.iteritems()
        elif isinstance(d, (list, tuple)): item_iterator = izip(d[::2],d[1::2])

        return ''.join(to_ydict_entry(k,v) for k,v in item_iterator)

    @classmethod
    def from_ydict(cls, data):
        d = {}
        for k, v in cls.from_ydict_iter(data):
            if k in d:
                log.warning('duplicate %s: %s', k, v)
                #raise AssertionError()
            d[k] = v
        return d

    @classmethod
    def from_ydict_iter(cls, data):
        rval = None
        retval = []
        for val in parser_re.split(data):
            if odd_caret_dollar_re.match(val) is not None:
                if rval is None:
                    retval.append(decode_caret(val[:-2]))
                else:
                    retval.append(decode_caret(rval+val[:-2]))
                rval = None
            else:
                if rval is None:
                    rval = val
                else:
                    rval += val

        keys, values = retval[::2], retval[1::2]

        # see note in yahooutil:from_ydict_iter
        values = [from_utf8(v) for v in values]

        return izip(keys, values)

    def ypacket_pack(self, command, status, version, data):
        data = self.to_ydict(data)
        return Ymsg(command, status, version, data, vendor_id='0', session=self)

    def push(self, packet, count=0):
        self._push_cb(packet,
                     success = self.recieve_response,
                     error = lambda *a: self.handle_client_stream_error(packet=packet, count=count, *a))

    @callsback
    def _push_cb(self, packet, callback=None):
        http, to_send = self.wrap_packet(packet)
        self._client_send(http, to_send, callback=callback)

    def wrap_packet(self, packet):
        is_auth = getattr(packet, '_yahoo_auth', False)
        http = 'http'
        if is_auth:
            http = 'https'
            assert self.ClientCounter == 0
            to_send = SessionWrapper(packet, self)
        else:
            to_send = SessionWrapper(packet, self)
        self.ClientCounter += 1
        return http, to_send

    @callsback
    def _client_send(self, http, to_send, callback=None):
        if self.client_http_opener is None:
            callback.error(Exception("Not connected"))
            if self.yahoo:
                self.yahoo.set_disconnected(self.yahoo.Reasons.CONN_LOST)
            return

        log.debug_s('yahoo sending\n%r', str(to_send))
        self.client_http_opener.open(http + '://' + self.server + '/', str(to_send),
                                     callback=callback)
        #if request already in progress, wait, let responses go first?  keep order separate until actually sending.

    def server_update(self):
        to_send = SessionWrapper(None, self, server=True)
        self.ClientCounter += 1
        log.debug_s('yahoo sending\n%r', str(to_send))
        self.server_http_opener.open('http://' + self.server + '/', str(to_send),
                                                success = self.server_response,
                                                error = self.handle_server_stream_error)
        #wait for list15 "online" to start this chain.
        #SessionWrapper(None, self, server=True), send on server connection.
        #wait for response, send again.

    def server_response(self, req, resp=None):
        try:
            self.recieve_response(req, resp)
        except Exception:
            pass
        self.server_update()

    def handle_server_stream_error(self, req, resp=None, *a, **k):
        log.error('handle_server_stream_error %r, %r, %r, %r', req, resp, a, k)
        if isinstance(resp, RESPONSE_TYPES):
            return self.server_response(req, resp)
        if isinstance(req, HTTPError) or isinstance(resp, HTTPError):
            return self.server_response(req, resp)
        import traceback;traceback.print_exc()
        self.close()
        if self.yahoo:
            self.yahoo.set_disconnected(self.yahoo.Reasons.CONN_LOST)

    def handle_client_stream_error(self, req, resp=None, packet=None, count=0, *a, **k):
        log.error('handle_client_stream_error %r, %r, %r, %r, %r, %r', req, resp, packet, count, a, k)
        if resp is None: #urllib compatibility
            resp = req
            del req
        #it's not going to be a 200 if we're in the error handler, no need to check that here.

        if isinstance(resp, RESPONSE_TYPES) or isinstance(resp, HTTPError):
            if count < 3:
                return self.push(packet, count + 1)

        self.close()
        if self.yahoo:
            self.yahoo.set_disconnected(self.yahoo.Reasons.CONN_LOST)

    def handle_connect(self):
        return self.async_proc(self.logon())

    def send_auth_req(self, user):
        cmd, wait, pkt = super(YahooHTTPConnection, self).send_auth_req(user)
        pkt._yahoo_auth = True
        return cmd, wait, pkt

    def recieve_response(self, req, resp=None):
        if resp is None: #urllib compatibility
            resp = req
            del req
        #should probably all be treated the same, who knows what can come back from where, nor should we care.
        data = resp.read()

        log.debug_s('yahoo recieved\n%r', data)

        Session = tag(data)
        #deal with sequence numbers
        if Session['Payload'] == 'yes':
            ymsg = Session.Ymsg
            if not isinstance(ymsg, list):
                ymsg = [ymsg]
            for pkt in ymsg:
                self.handle_packet(pkt, Session)
        try:
            self.ServerSeqno = Session['ServerSeqno']
        except KeyError:
            pass

    def handle_packet(self, pkt, session):
        from util import Storage
        header = Storage()
        header.command = int(pkt['Command'])
        header.status  = int(pkt['Status'])
        account_id, session_id = session['SessionId'].split('-', 1)
        self.account_id = account_id
        header.session_id = self.session_id = int(session_id)
        data = pkt._cdata.strip().encode('utf-8')
        YahooConnectionBase.handle_packet(self, header, data)
        if header.command == 241 and header.status == 0:
            self.server_update()

class Ymsg(object):
    def __init__(self, command, status, version, data='', vendor_id='0', session=None):
        self.Command = command
        self.Status = status
        self.Version = version
        self.data = data
        self.VendorId = vendor_id
        self.SessionId = getattr(session, 'session_id', '0')

    def _as_tag(self):
        t = tag('Ymsg')
        t['Command']  = self.Command
        t['Status']   = self.Status
        t['Version']  = self.Version
        t['VendorId'] = self.VendorId
        t['SessionId'] = self.SessionId
        t._cdata = self.data
        return t

    def __str__(self):
        t = self._as_tag()
        #should all be utf-8 already, but we don't want to accidently go back to unicode via ascii
        l = t._to_xml(pretty=False, self_closing=False, return_list=True)
        return ''.join((s if isinstance(s, bytes) else s.encode('utf-8')) for s in l)

class SessionWrapper(object):
    def __init__(self, payload=None, session=None, server=False):
        assert payload is None or isinstance(payload, Ymsg)
        self.payload = payload
        self.server  = server
        self.session = session
        self.cc = self.session.ClientCounter

    @property
    def Payload(self):
        return "yes" if self.payload else "no"

    @property
    def SessionId(self):
        return '%s-%s' % (self.session.account_id, self.session.session_id)

    @property
    def Channel(self):
        return "ServerPost" if self.server else "ClientPost"

    @property
    def ClientHash(self):
        return sha1(str(self.cc) + self.SessionId + self.session.secret + self.Channel).hexdigest().upper()

    def __str__(self):
        t = tag('Session')
        t['Payload'] = self.Payload
        t['Channel'] = self.Channel
        session_id = getattr(self.session, 'session_id', None)
        if session_id:
            t['ClientHash'] = self.ClientHash
            t['SessionId']  = self.SessionId
        else:
            t['Secret']     = self.session.Secret
        t['ClientCounter'] = self.cc
        t['ClientSeqno']   = self.cc
        if self.server:
            server_seqno = getattr(self.session, 'ServerSeqno', None)
            if server_seqno:
                t['ServerSeqno'] = server_seqno
        if self.payload:
            t.Ymsg = self.payload._as_tag()
        #should all be utf-8 already, but we don't want to accidently go back to unicode via ascii
        l = t._to_xml(pretty=False, self_closing=False, return_list=True)
        return ''.join((s if isinstance(s, bytes) else s.encode('utf-8')) for s in l)

