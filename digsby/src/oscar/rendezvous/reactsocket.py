from common.timeoutsocket import TimeoutSocketOne
from util.net import SocketEventMixin
import common, socket
from functools import partial
from logging import getLogger
from util import Timer

log = getLogger('oscar.reactsocket'); info = log.info;

class OscarTimeoutSocket(common.socket):
    def tryconnect(self, ips, on_connect, on_fail, timeout = 2.0):
        self._connectedonce = False
        info('tryconnect Y=%r, N=%r', on_connect, on_fail)
        self.ips = self.iptuples(ips)

        if not callable(on_connect) or not callable(on_fail):
            raise TypeError( 'on_connect and on_fail must be callables' )

        self.on_connect = on_connect
        self.on_fail = on_fail
        self.timetowait = timeout
        self._tryagain(timeout)

    def tryaccept(self, addr, on_connect, on_fail, timeout = 1.5):
        self._connectedonce = False
        info('tryaccept Y=%r, N=%r', on_connect, on_fail)
        self.ips = ()
        self.on_connect = on_connect
        self.on_fail    = on_fail

        info('listening for a connection at %s:%d', *addr)
        self.bind( addr )
        self.listen(1)

        if timeout:
            info('timeout in %r secs', timeout)

            def dotimeout():
                info('TIMEOUT. calling %r', self.on_fail)
                self.on_fail()

            self.timeout = Timer(timeout, dotimeout)
            self.timeout.start()

    def _tryagain(self, timetowait):
        # Try the next IP.
        addr = self.ips.pop(0)

        if len(self.ips) > 0:
            timeoutfunc = partial(self._tryagain, timetowait)
        else:
            # This is the last one.
            timeoutfunc = self.on_fail

        self.timeout = Timer(timetowait, timeoutfunc)
        info('%r attempting conn: %s:%d', self, *addr)

        self.make_socket()
        self.connect(addr, error=timeoutfunc)

        info('timeout is %r seconds...', timetowait)
        if self.timeout is not None:
            self.timeout.start()

    def handle_expt(self):
        info('handle_expt in %r', self)
        self.handle_disconnect()

    def handle_error(self, e=None):
        info('handle_error in %r', self)

        import traceback
        traceback.print_exc()

        if not self._connectedonce:
            self.handle_disconnect()
        else:
            self.close()

    def handle_disconnect(self):
        self.cancel_timeout()
        self.close()

        if len(self.ips) > 0:
            info('got an error, trying next ip immediately: ' + \
                 repr(self.ips[0]))
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self._tryagain(self.timetowait)
        elif not self._connectedonce:
            info('no more ips to attempt, calling on_fail (%r)', self.on_fail)
            self.on_fail()

    def handle_connect(self):
        info('connected!')
        self.cancel_timeout()
        #self.handle_disconnect = lambda: None
        self._connectedonce = True
        self.on_connect()
        self.on_fail = Sentinel

    def handle_accept(self):
        self.cancel_timeout()
        conn, address = self.accept()
        info('%r connection accepted (%r), canceling timeout and calling %r', self, address, self.on_connect)
        self._connectedonce = True
        self.on_connect(conn)

    def cancel_timeout(self):
        # Cancel any timeout.
        if hasattr(self, 'timeout') and self.timeout is not None:
            self.timeout.cancel()
            self.timeout = None

    def iptuples(self, ips):
        if not hasattr(ips, '__len__'):
            raise TypeError('ips must be (host, port) or [(host,port), (host,port)]')
        if not hasattr(ips[0], '__len__'):
            ips = tuple([ips])

        # ips is now a sequence of (host, port) tuples
        assert all(isinstance(a, basestring) and isinstance(p, int) for a, p in ips)
        return ips

    def __repr__(self):
        try:    pn = self.getpeername()
        except Exception: pn = None
        return '<TimeoutSocket peername=%r ips=%r at 0x%08x>' % (pn, getattr(self, 'ips', None), id(self))


class ReactSocket(OscarTimeoutSocket):
    'Wrapper for asynchat with packables.'

    def __init__(self, connected_socket = None, on_close = lambda: None):
        if connected_socket is None: OscarTimeoutSocket.__init__( self )
        else: OscarTimeoutSocket.__init__( self, connected_socket )

        self._connectedonce = True
        self.data = ''
        self.original_collector = self.collect_incoming_data
        self.collectors = []
        self.on_close = on_close

    def handle_close(self):
        log.info('%r handle_close', self)
        self.on_close()
        self.close()

    def collect_incoming_data(self, data):
        self.data += data

    def push_collector(self, collector):
        self.collectors.append(collector)
        self.collect_incoming_data = self.collectors[-1]

    def pop_collector(self):
        self.collectors.pop(-1)
        self.collect_incoming_data = \
            self.collectors[-1] if self.collectors else self.original_collector

    def receive_next(self, size, callable_func):
        # Pulls sizes out of packables
        if hasattr(size, '_struct'): size = size._struct.size
        assert isinstance(size, (int, long))
        assert callable(callable_func)

        self.found_terminator = lambda: callable_func(self.data)
        self.data = ''
        self.set_terminator( size )

class ReactSocketOne(TimeoutSocketOne, SocketEventMixin):
    def __init__(self, *a, **k):
        common.TimeoutSocketOne.__init__(self, *a, **k)
        SocketEventMixin.__init__(self)
        self.data = ''
        self.original_collector = self.collect_incoming_data
        self.collectors = []

    def collect_incoming_data(self, data):
        self.data += data

    def push_collector(self, collector):
        self.collectors.append(collector)
        self.collect_incoming_data = self.collectors[-1]

    def pop_collector(self):
        self.collectors.pop(-1)
        self.collect_incoming_data = \
            self.collectors[-1] if self.collectors else self.original_collector

    def receive_next(self, size, callable_func):
        # Pulls sizes out of packables
        if hasattr(size, '_struct'): size = size._struct.size
        assert isinstance(size, (int, long))
        assert callable(callable_func)

        self.found_terminator = lambda: callable_func(self.data)
        self.data = ''
        self.set_terminator( size )

    #in case we don't inherit this
    def __getattr__(self, attr):
        return getattr(self.socket, attr)

