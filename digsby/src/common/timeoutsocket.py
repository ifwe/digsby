'''
Connects to a series of addresses, trying each one in sequence.
'''
from util.primitives import lock

import common
from logging import getLogger
from util import Timer
log = getLogger('common.timeoutsocket'); info = log.info;

class TimeoutSocket(common.socket):

    def tryconnect(self, ips, on_connect, on_fail, timeout=2.0):
        '''
        Setup for a new set of ips and start the connect routine

        @param ips:
        @param on_connect:
        @param on_fail:
        @param timeout:
        '''
        self.cancel_timeout()
        self.timetowait = timeout
        self.on_connect = on_connect
        self.on_fail    = on_fail
        self._ips       = iptuples(ips)
        self.attempts = 0
        self._accepting = False
        self.try_connect()

    def try_connect(self):
        'Do the connection routine.'

        addr = self._ips[self.attempts]
        log.warning('tryconnect: %r', (addr,))
        self.attempts += 1
        self.timeout = Timer(self.timetowait, lambda s=self.socket: self.handle_timeout(s))
        self.make_socket()
        if self.timeout is not None:
            self.timeout.start()
        def succ(*a, **k):
            log.info("WIN")
        def fail(*a, **k):
            log.info("FAIL")
        self.connect(addr, success=succ, error=fail)

    def tryaccept(self, addr, on_connect, on_fail, timeout = 1.5):
        self._accepting = True
        info('tryaccept Y=%r, N=%r', on_connect, on_fail)
        self.on_connect = on_connect
        self.on_fail    = on_fail

        info('listening for a connection at %r', (addr,))
        self.make_socket()
        common.socket.bind( self, addr )
        self.listen(1)

        if timeout:
            info('timeout in %r secs', timeout)
            self.timeout = Timer(timeout, lambda s=self.socket: self.handle_timeout(s))
            self.timeout.start()

    def handle_timeout(self, socket):
        info('TIMEOUT %r', socket)
        if socket is self.socket:
            self.do_disconnect()
        elif socket is not None:
            socket.close()

    def handle_expt(self):
        info('handle_expt in %r', self)
        self.do_disconnect()

    def handle_error(self, e=None):
        info('handle_error in %r', self)
        import traceback
        traceback.print_exc()
        self.do_disconnect()

    def do_disconnect(self):
        '''
        toss away the current connection
        will try the next address immediately
        '''

        log.warning('do_disconnect')
        self.cancel_timeout()
        self.close()

        if not self._accepting and self.attempts < len(self._ips):
            self.try_connect()
        else:
            self.on_fail()

    def handle_connect(self):
        info('connected!')
        self.cancel_timeout()
        self.on_connect(self)

    def handle_accept(self):
        self.cancel_timeout()
        conn, address = self.accept()
        info('%r connection accepted (%r), canceling timeout and calling %r', self, address, self.on_connect)
        self.on_connect(conn)

    def cancel_timeout(self):
        # Cancel any timeout.
        if hasattr(self, 'timeout') and self.timeout is not None:
            info('cancelling timeout')
            self.timeout.cancel()
        else:
            log.warning('there was no timeout to cancel')
        self.timeout = None

    def __repr__(self):
        if hasattr(self,'ips') and len(self.ips):
            return '<TimeoutSocket %s:%d>' % self.ips[0]
        else:
            pn = None
            try:     pn = self.socket.getpeername()
            finally: return "<%s connected to %r>" % (self.__class__.__name__,pn)

class TimeoutSocketOne(common.socket):
    '''
    single socket timeout socket
    '''

    @lock
    def try_connect(self, address, succ, fail, time_to_wait, provide_init):
        provide_init(self)
        self.real_success = succ
        self.fail = fail
        self.dead = False
        self.data = None
        #make new socket
        self.make_socket()
        self.timeoutvalid = True
        self.timeout = Timer(time_to_wait, self.handle_timeout)
        self.timeout.start()

        print '*'*40
        from util import funcinfo
        print funcinfo(self.connect)
        print '*'*40

        self.connect(address, error=self.do_fail)
        #do connect with callback
        #success indicates that the socket started, but guarantees nothing
        #error indicates that there was a problem, should try to close + do fail

    def succ(self):
        info('succ')
        self.real_success()

    @lock
    def do_fail(self, *a, **k):
        info('do_fail')
        if self.timeout is not None:
            self.timeout.cancel()
            self.timeout = None
        self.timeoutvalid = False
        self.close()
        print a, k
        self.fail(*a,**k)


    @lock
    def handle_connect(self):
        info('CONNECT')
        if self.timeout is not None:
            self.timeout.cancel()
            self.timeout = None
        self.timeoutvalid = False
        self.succ()
        #cancel timeout
        #success

    @lock
    def handle_timeout(self):
        info('TIMEOUT')
        #mark as dead
        if self.timeoutvalid:
            if self.timeout is not None:
                self.timeout.cancel()
                self.timeout = None
            self.timeoutvalid = False
            self.close()
            self.dead = True
            self.fail()

    @lock
    def collect_incoming_data(self, data):
        self.data += data

    @lock
    def __error(self):
        olddead = self.dead
        self.dead = True
        if self.timeout is not None:
            self.timeout.cancel()
            self.timeout = None
        self.timeoutvalid = False
        #cancel timeout
        self.close()
        if not olddead:
            self.fail()

    def handle_error(self, e=None):
        info('ERROR: %r', e)
        import traceback;traceback.print_exc()
        self.__error()

    def handle_expt(self):
        info('EXPT')
        self.__error()

    def handle_close(self):
        info('CLOSE')
        self.__error()

class TimeoutSocketMulti(object):

    def tryconnect(self, ips, on_connect, on_fail, timeout=2.0,
                   cls=TimeoutSocketOne, provide_init=lambda self: None):
        '''
        Setup for a new set of ips and start the connect routine

        @param ips:
        @param on_connect:
        @param on_fail:
        @param timeout:
        '''
        self.provide_init = provide_init
        self.cls = cls
        self.timetowait = timeout
        self.on_connect = on_connect
        self.on_fail    = on_fail
        self._ips       = iptuples(ips)
        self.attempts = 0
        self.try_connect()

    def try_connect(self):
        self.socket = self.cls(False)
        address = self._ips[self.attempts]
        log.warning('tryconnect: %r', address)
        self.attempts += 1
        self.socket.try_connect(address, self.win, self.lose, self.timetowait,
                                self.provide_init)

    def win(self):
        self.on_connect(self.socket)

    def lose(self, *a, **k):
        if self.attempts < len(self._ips):
            self.try_connect()
        else:
            self.on_fail(*a, **k)

def iptuples(ips):
    if not hasattr(ips, '__len__'):
        raise TypeError('ips must be (host, port) or [(host,port), (host,port)]')
    if isinstance(ips[0], basestring):
        ips = tuple([ips])

    # ips is now a sequence of (host, port) tuples
    assert all(isinstance(a, basestring) and isinstance(p, int) for a, p in ips)
    return ips
