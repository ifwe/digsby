from socket import SocketType as socket
from hashlib import sha1, md5
from struct import pack, unpack
from common.timeoutsocket import TimeoutSocketOne
from functools import partial
from common.timeoutsocket import TimeoutSocketMulti
from util import Timer
from util import lock
from traceback import print_exc

from logging import getLogger
log = getLogger('loginutil')

'''
Works with java server
maybe.
'''
POLL_SLEEP_TIME = 3.5 # Server polling sleep interval is 3 seconds

class DigsbyLoginError(Exception):
    def __init__(self, reason):
        self.reason = reason
        Exception.__init__(self,
        {
         'auth'     : 'Incorrect username or password.',
         'server'   : 'Server is unable to authenticate you at this time.',
         'client'   : 'Could not contact remote server. Check your internet connection.',
         'connlost' : 'The connection to the server was unexpectedly terminated.',
        }.get(reason, 'Unknown error: %r' % reason)
        )

def send_pstring(sck, str):
    sck.sendall(pack('!I', len(str)))
    sck.sendall(str)

def recv_pstring(sck):
    i = unpack('!I',sck.recv(4))[0]
    v = sck.recv(i)
    return v

def login(srv, cid, un, password):
    s = socket()
    s.connect(srv)
    send_pstring(s, cid)
    send_pstring(s, un)
    send_pstring(s, password)
    try:
        code = recv_pstring(s)
        if code == 'success':
            cookie = recv_pstring(s)
            servers = recv_pstring(s)
            servers = servers.split(' ')
            return cookie, servers
        elif code == 'error':
            reason = recv_pstring(s)
            raise DigsbyLoginError(reason)
        else:
            raise DigsbyLoginError('client')
    except DigsbyLoginError, e:
        raise e
    except Exception, e:
        print_exc()
        raise DigsbyLoginError('client')

def custom_crypt(c):
    return str(int(c)+1)

def hash_cookie(cookie, password):
    return sha1(custom_crypt(cookie)+password).hexdigest().lower()

def connect(host, jid, password):
    raise NotImplementedError

def digsby_login(srv, cid, un, password):
    password = md5(password).hexdigest()
    cookie, host = login(srv, cid, un, password)
    password = hash_cookie(cookie, password)
    connect(host, un, password)

def make_pstring(s):
    assert isinstance(s, str)
    l = len(s)
    format_str = '!I%ds' % l
    return pack(format_str, l, s)

class DigsbyConnect(TimeoutSocketOne):
    _SERVERTIMEOUT = 8

    def stale_connection(self):

        if getattr(self, '_triumphant', False):
            log.info('stale_connection was called but i already won! yayayay')
        else:
            log.info('%r had a stale connection. Calling do_fail (%r) with a connlost error', self, self.do_fail)
            self.do_fail(DigsbyLoginError('connlost'))

    def succ(self):
        generator = self.do_login()

        self._timeouttimer = Timer(self._SERVERTIMEOUT, self.stale_connection)
        self._timeouttimer.start()
        self.run_sequence( generator )

    @lock
    def handle_error(self, e=None):
        if hasattr(self, '_timeouttimer'):
            self._timeouttimer.stop()
        TimeoutSocketOne.handle_error(self)

    @lock
    def handle_expt(self):
        if hasattr(self, '_timeouttimer'):
            self._timeouttimer.stop()
        TimeoutSocketOne.handle_expt(self)

    @lock
    def handle_close(self):
        if hasattr(self, '_timeouttimer'):
            self._timeouttimer.stop()
        TimeoutSocketOne.handle_close(self)

    def do_login(self):
        login_str = make_pstring(self.cid) + make_pstring(self.un) + make_pstring(self.password)
        codelen = yield (4, login_str)
        codelen = unpack('!I', codelen)[0]
        if codelen <= 0:
            raise DigsbyLoginError('client')
        code = yield (codelen, '')

        try:
            if code == 'success':
                cookielen = unpack('!I', (yield (4, '')))[0]
                cookie = yield (cookielen, '')
                log.debug('Got cookie: %r', cookie)
                serverslen = unpack('!I', (yield (4, '')))[0]
                servers = yield (serverslen, '')
                log.debug('Got servers: %r', servers)
                servers = servers.split(' ')
                self.cookie  = cookie
                self.servers = servers
                self._triumphant = True
                return
            elif code == 'error':
                log.debug('Got error!')
                reasonlen = unpack('!I', (yield (4, '')))[0]
                reason = yield (reasonlen, '')
                log.debug('Got error reason: %r', reason)
                raise DigsbyLoginError(reason)
            else:
                log.debug('Unknown error occurred! blaming the client!')
                raise DigsbyLoginError('client')
        except DigsbyLoginError, e:
            if e.reason == 'server':
                log.debug('Got "upgrading digsby" error code. Sleeping.')
                import time; time.sleep(POLL_SLEEP_TIME)
            raise e
        except Exception, e:
            print_exc()
            raise DigsbyLoginError('client')
        finally:
            self._timeouttimer.stop()

    def run_sequence(self, generator):
        try:
            to_read, out_bytes = generator.send(self.data)
        except StopIteration:
            #win
            self.close()
            self._timeouttimer.stop() #just for good measure.
            return TimeoutSocketOne.succ(self)
        except DigsbyLoginError, e:
            self._timeouttimer.stop()
            self.do_fail(e)
            return
        except Exception, e:
            self._timeouttimer.stop()
            self.do_fail(e)
            return

        bytes = str(out_bytes)
        if out_bytes:
            log.info('Sending %r', bytes)
            self.push(bytes)
        self.data = ''
        self.found_terminator = partial(self.run_sequence, generator)
        if isinstance(to_read, int):
            self.set_terminator(to_read)
        else:
            self.set_terminator(to_read._size())

def connected(sock):
    pass

def youfail():
    pass


class DigsbyLoginMulti(TimeoutSocketMulti):
    def lose(self, e=None):
        if e and getattr(e,'reason',None) == 'auth' or self.attempts >= len(self._ips):
            self.on_fail(e)
        else:
            self.try_connect()

def new_digsby_login(addrtuples, cid, un, password, win, lose):
    def provide(self):
        self.cid = cid
        self.un  = un
        self.password  = password
    t = DigsbyLoginMulti()
    t.tryconnect(addrtuples,
                 win, lose, timeout=20, cls=DigsbyConnect, provide_init=provide)

if __name__ == "__main__":
    password = md5('password2').hexdigest()
    new_digsby_login([('129.21.160.40', 5555), ('129.21.160.41', 5555)], "foo", 'chris', password,
                     connected, youfail)
