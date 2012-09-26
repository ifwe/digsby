from common.filetransfer import IncomingFileTransfer
from util.primitives import Storage
from httplib import HTTPConnection
from urllib import quote
from util.net import FileChunker
from path import path
from urlparse import urlparse
from util.threads.threadpool2 import threaded
from common.filetransfer import OutgoingFileTransfer
from random import choice
from traceback import print_exc
from .yfiletransfer import OutgoingYHTTPXfer
import dns
import logging

log = logging.getLogger('yahoo.peerft'); info = log.info; error = log.error


class YahooPeerFileTransfer(IncomingFileTransfer):
    def __init__(self, yahoo, buddy, **kws):
        IncomingFileTransfer.__init__(self)
        self.yahoo = yahoo
        self.buddy = buddy
        self.name = kws['filename']
        self.packet = Storage(**kws)
        self.numfiles = 1
        self.size = int(kws['filesize'])

        self.on_get_buddy(self.buddy)

    @property
    def protocol(self):
        return self.yahoo

    def decline(self):
        self.yahoo.send('peerrequest', 'available',
                        ['frombuddy', self.packet.to,
                         'to', self.packet.buddyname,
                         'p2pcookie', self.packet.p2pcookie,
                         'acceptxfer', '4'])
        self.state    = self.states.CANCELLED_BY_YOU
        IncomingFileTransfer.decline(self)

    def accept(self, openfile):
        self.packet.acceptxfer = '3'
        self.openfile = openfile
        self.yahoo.send('peerrequest', 'available', [
            'frombuddy', self.packet.to,
            'to', self.packet.buddyname,
            'p2pcookie', self.packet['p2pcookie'],
            'acceptxfer', '3',
        ])
        self.state    = self.states.CONNECTING

    @threaded
    def connect(self, buddy, filename, peer_path, p2pcookie, peerip, transfertype):
        myname = self.yahoo.self_buddy.name
        if transfertype == '1':
            u = urlparse(peerip)
            url = u.path + '?' + u.query
            peerip = u.netloc
        else:
            url = '/relay?token=%s&sender=%s&recver=%s' % (quote(peer_path), myname, buddy)
        # connect to them
        if peerip:
            info( 'Got a relay IP; connecting...' )

            info( 'HTTP HEAD: %s', peerip)
            relayconn = HTTPConnection(peerip)
            headers = {'User-Agent':'Mozilla/4.0 (compatible; MSIE 5.5)',
                       'Accept':'*/*',
                       'Cache-Control':'no-cache',
                       'Cookie': self.yahoo.cookie_str }

            relayconn.request('HEAD', url, headers = headers)

            # Check for OK
            response = relayconn.getresponse()
            status = response.status
            if status != 200:
                return log.error('ERROR: HEAD request returned a status of %d', status)
            print "resp1 in"
            print response.read()
            print "resp1 out"

            # Now make a GET to the same host/url
            relayconn.request('GET', url, headers = headers)

            if transfertype != '1':
                self.yahoo.send('peerinit', 'available',
                  frombuddy    = myname,
                  to           = buddy,
                  p2pcookie    = p2pcookie,
                  filename     = filename,
                  transfertype = '3',
                  peer_path     = peer_path
                )

            response = relayconn.getresponse()
            status = response.status
            if status != 200:
                return log.error('ERROR: GET req returned %d status', status)

            response.info = lambda: dict(response.getheaders())

            headers = response.info()

            bytecounter = lambda: 0

            if self.state != self.states.CANCELLED_BY_YOU:
                self.state    = self.states.TRANSFERRING
                self.filepath = path(self.openfile.name)
                gen = FileChunker.tofile_gen(response, self.openfile, self.progress,
                                                   bytecounter=bytecounter)
                self.chunker = gen.next()
                try:
                    gen.next()
                except StopIteration:
                    pass
                if self.bytes_read != self.size:
                    self.state = self.states.CONN_FAIL_XFER

            if self.state != self.states.CANCELLED_BY_YOU:
                self._ondone()


        else: # not peerip
            log.warning('No peer IP, buddy will connect to me. NOT IMPLEMENTED')

    def progress(self, bytes_read):
        self._setcompleted(bytes_read)
        self.bytes_read = bytes_read

    def cancel(self, me=True, state=None):
        if me:
            self.yahoo.send('peerinit', 'cancel',
                            ['frombuddy', self.packet.to,
                             'to', self.packet.buddyname,
                             'p2pcookie', self.packet.p2pcookie,
                             'error', '-1'])

            if state is None:
                state = self.states.CANCELLED_BY_YOU
            self.state = state
        else:
            self.state = self.states.CANCELLED_BY_BUDDY
        try:
            self.chunker.cancelled = True
        except Exception:
            print_exc()
        self._ondone()

    def _ondone(self):
        try:
            self.yahoo.file_transfers.pop((self.packet.buddyname, self.packet.p2pcookie))
        except Exception:
            log.warning('_ondone pop failed')
        try:
            IncomingFileTransfer._ondone(self)
        except Exception:
            log.warning('_ondone call failed')

class YahooOutgoingPeerFileXfer(OutgoingYHTTPXfer):

#    conn_host = 'relay.

    def __init__(self, protocol, buddy = None, fileinfo = None):
        OutgoingYHTTPXfer.__init__(self, protocol, buddy=buddy, fileinfo=fileinfo, initiate=False)
        self.yahoo = protocol

    def send_offer(self):
        log.critical('send_offer')
        import string
        letters = string.ascii_letters + string.digits
        cookie = []
        for _i in xrange(22):
            cookie.append(choice(letters))
        self.cookie = cookie = ''.join(cookie) + '$$'

        self.yahoo.file_transfers[(self.buddy.name, self.cookie)]  = self

        self.yahoo.send(
            'peerrequest', 'available',
            ['frombuddy', self.yahoo.self_buddy.name,
            'to',         self.buddy.name,
            'p2pcookie',  self.cookie,
            'acceptxfer',   '1',
            '266',   '1',
            'begin_mode', '268',
            'begin_entry', '268',
            'filename', self.name,
            'filesize', str(self.size),
            'end_entry', '268',
            'end_mode', '268'])
        self.state = self.states.WAITING_FOR_BUDDY

    def do_setup(self, buddy, p2pcookie, filename = None, peer_path=None, **k):
        log.critical('do_setup')
        self.state = self.states.CONNECTING
        assert p2pcookie == self.cookie
        @threaded
        def get_ip():
            for ip in dns.resolver.query('relay.msg.yahoo.com', 'A'):
                return str(ip)
            raise Exception, 'no ip for relay transfer'

        def send_later(ip):
            self.host = ip
            self.conn_host = ip
            self.yahoo.send(
                    'peersetup', 'available',
                    ['frombuddy', self.yahoo.self_buddy.name,
                    'to',         self.buddy.name,
                    'p2pcookie', self.cookie,
                    'filename', self.name,
                    'transfertype',   '3',
                    'peerip', ip])

        get_ip(success = send_later)

    def go(self, buddy, p2pcookie, filename, transfertype, peer_path, **k):
        log.critical('go')
        peer_path = quote(peer_path)
        self.http_path = '/relay?token=' + peer_path + '&sender=' + self.yahoo.self_buddy.name + '&recver=' + buddy
        self.state = self.states.TRANSFERRING
        try:
            filesize = self.filepath.size
            fileobj = file(self.filepath, 'rb')
        except Exception, e:
            print_exc()
            self.state = self.states.CONN_FAIL
            self.on_error()
        else:
            self._post_file('', self.yahoo.cookie_str, fileobj = fileobj, filesize = filesize)

    def cancel(self, me=True):
        self.cancelled = True
        if me:
            self.yahoo.send(
                    'peersetup', 'cancel',
                    ['frombuddy', self.yahoo.self_buddy.name,
                    'to',         self.buddy.name,
                    'p2pcookie', self.cookie,
                    '66', '-1'])
            self.state = self.states.CANCELLED_BY_YOU
        else:
            self.state = self.states.CANCELLED_BY_BUDDY
        try:
            self.conn.close()
            del self.conn
        except:
            pass



