import socket
from util.primitives.funcs import do
from util.primitives.synchronization import lock
from common.timeoutsocket import iptuples, TimeoutSocket

class HydraSocket(object):

    def tryconnect(self, ips, on_connect, on_fail, timeout=2.0, cls=TimeoutSocket):
        self._ips       = iptuples(ips)
        self.on_connect = on_connect
        self.on_fail    = on_fail
        self.timetowait = timeout
        self.numfails   = 0
        self.success    = False
        self.socks = [cls(False) for __ in self._ips]
        self.connected_sock = None
        [sock.tryconnect(ip,
                         self.on_success,
                         self.singlefail,
                         timeout=self.timetowait)
        for sock, ip in zip(self.socks, self._ips)]

    @lock
    def on_success(self, sock):
        if self.success:
            sock.do_disconnect()
        else:
            sock.cancel_timeout()
            do(sock_.do_disconnect() for sock_ in self.socks if sock_ is not sock)
            self.success = True
            self.connected_sock = sock
            self.on_connect(sock)

    @lock
    def singlefail(self):
        self.numfails += 1
        if self.numfails >= len(self._ips):
            self.on_fail()

    def send(self, *a, **k):
        if self.connected_sock is None:
            raise socket.error('HydraSocket is not connected')
        self.connected_sock.send(*a, **k)


