from .yahooHTTPConnection import YahooHTTPConnection
from .yahoologinsocket import YahooLoginSocket

ALL_PORTS = (5050, 80, 25, 23, 20)

S1_PORTS = (5050, 80)
S3_PORTS = (25, 23, 20)

class ServerEndpoint(object):
    def __init__(self, server_address, port):
        self.address = server_address
        self.port    = port

    def __repr__(self):
        return '<ServerEndpoint %s:%d>' % (self.address, self.port)

    def __cmp__(self, other):
        if type(other) == HTTPEndpoint:
            if self.port in S3_PORTS:
                return 1
            return -1
        if self.port not in ALL_PORTS:
            if other.port in ALL_PORTS:
                return -1
            return 0
        if other.port not in ALL_PORTS:
            if self.port in ALL_PORTS:
                return 1
            return 0
        if other.port in S1_PORTS and self.port in S1_PORTS:
            return S1_PORTS.index(self.port) - S1_PORTS.index(other.port)
        if other.port in S1_PORTS and self.port in S3_PORTS:
            return 1
        if other.port in S3_PORTS and self.port in S1_PORTS:
            return -1
        if other.port in S3_PORTS and self.port in S3_PORTS:
            return S3_PORTS.index(self.port) - S3_PORTS.index(other.port)
        assert False

    def make_socket(self, y):
        return YahooLoginSocket(y, (self.address, self.port))

class HTTPEndpoint(object):
    def __init__(self, server_address):
        self.address = server_address
    def __repr__(self):
        return '<HTTPEndpoint %s>' % (self.address,)
    def make_socket(self, y):
        return YahooHTTPConnection(y, self.address)
