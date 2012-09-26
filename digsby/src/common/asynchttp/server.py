import io
import rfc822
import common
import urlparse
import logging
import util.Events as events

log = logging.getLogger('httpserver')
import collections
from common.asynchttp.httptypes import HTTPRequest

CRLF = '\r\n'

def is_re(x):
    return False

class HTTPServerManager(object):
    def __init__(self):
        self.resources = collections.defaultdict(list)
        self.clients = collections.defaultdict(list)
        self.servers = {}
    
    def serve(self, pattern, handler_factory, host = '', port = 80):
        self.resources[(host, port)].append((pattern, handler_factory))
        shost, sport = self.bind(host, port)

        log.info('Now serving: http://%s:%s%s -> %r', shost or 'localhost', sport or 80, pattern, handler_factory)
        return shost, sport
        
    def stop_serving(self, pattern, host, port):
        p = hf = None
        for p, hf in self.resources[(host, port)]:
            if p == pattern:
                break
        else:
            p = hf = None
            
        if not (p is hf is None):
            try:
                self.resources[(host, port)].remove((p, hf))
            except ValueError:
                pass
        
        log.info('No longer serving http://%s:%s%s', host or 'localhost', port or 80, pattern)
        self._check_resources()

    def _check_resources(self):
        for hostport in self.resources.keys():
            if not self.resources[hostport]:
                self.resources.pop(hostport)
                self.shutdown_server(self.servers.pop(hostport))
                
        if not self.servers:
            log.info('Shutting down http server, nothing left to serve!')
            self.shutdown()

    def bind(self, host = '', port = 80):
        if (host, port) not in self.servers:
            srv = HTTPServerSocket()
            srv.bind_event('on_connection', self.on_client)
            srv.bind(host, port)
            self.servers[(host,port)] = srv
            
            srv.listen(5)
            
        return self.servers[(host, port)].getsockname()
            
    def shutdown(self):
        log.info('Shutting down all servers')
        for addr in self.servers.keys():
            self.shutdown_server(self.servers.pop(addr))
            
        for cli in self.clients.keys():
            clients = self.clients.pop(cli)
            while clients:
                self.shutdown_client(clients.pop(0))
                
        self.resources.clear()
                
    def shutdown_server(self, srv):
        srv.unbind('on_connection', self.on_client)
        
        srv.close()
        
    def shutdown_client(self, cli):
        cli.unbind('on_request', self.process_request)
        cli.unbind('on_close', self.on_client_close)
        
        cli.close()
        
    def on_client(self, srvaddr, client_address, conn):
        client = HTTPRequestGatherer(conn, client_address, srvaddr)
        client.bind_event('on_request', self.process_request)
        client.bind_event('on_close', self.on_client_close)
        self.clients[(srvaddr, client_address)].append(client)
        client.can_process = True
        
    def on_client_close(self, client):
        try:
            self.clients[(client.server_address, client.client_address)].remove(client)
        except ValueError:
            pass
        
        client.unbind('on_request', self.process_request)
        client.unbind('on_close', self.on_client_close)
        
    def process_request(self, srvaddr, client_address, client, request):
        for pattern, handler_factory in self.resources[srvaddr]:
            if not self.match(pattern, request):
                continue
            try:
                self.handle(handler_factory, srvaddr, client_address, client, request)
            except Exception as e:
                log.error('Error processing request %r: %r', request, e)
                return
            
    def handle(self, handler_factory, srvaddr, client_address, client, request):
        handler = handler_factory(srvaddr, client_address)
        handler.handle(client, request)
        
    def match(self, pattern, request):
        if isinstance(pattern, bytes):
            url = request.get_full_url()
            parsed = urlparse.urlparse(url)
            if parsed.path == pattern:
                return True
            
            dir = pattern
            if not dir.endswith('/'):
                dir = dir + '/'
            if parsed.path.startswith(dir):
                return True
            
        elif False and is_re(pattern):
            pass
        elif callable(pattern):
            return pattern(request)
        
        return False
    
class HTTPRequestGatherer(common.socket, events.EventMixin):
    events = events.EventMixin.events | set((
        'on_request',
        'on_close',
    ))

    def __init__(self, conn, client_address, server_address):
        events.EventMixin.__init__(self)
        common.socket.__init__(self, conn)
        self.can_process = False
        self.client_address = client_address
        self.server_address = server_address
        self.set_terminator(CRLF*2)
        self.buffer = []
        self.data = None
        self._request = None
        self._headers = None
        
    def readable(self):
        return self.can_process and common.socket.readable(self)
        
    def collect_incoming_data(self, data):
        self.buffer.append(data)
        
    def found_terminator(self):
        self.data = ''.join(self.buffer)
        self.buffer[:] = []
        if self.terminator == CRLF*2:
            self.headers_complete()
        else:
            self.body_complete()
        
    def headers_complete(self):
        header_fp, self.data = io.BytesIO(self.data), None
        
        start_line = header_fp.readline()
        self.method, self.path, self.version = self._parse_start_line(start_line)
        
        self._headers = headers = rfc822.Message(header_fp)
        self._normalize_headers()
        clen = headers.getheader('Content-Length')
        if clen is not None:
            if clen != 0:
                self.set_terminator(clen)
                return
        
        self.body_complete()
        
    def _parse_start_line(self, line):
        return line.split()
    
    def _normalize_headers(self):
        d = {}
        for key in self._headers.keys():
            d[key] = '; '.join(self._headers.getheaders(key))
        
        self._headers = d

    def body_complete(self):
        uri = urlparse.urlparse(self.path)
        d = uri._asdict()
        if not uri.netloc:
            d.update(netloc = '%s:%s' % self.server_address)
        if not uri.scheme:
            d.update(scheme = 'http')
            
        uri = urlparse.ParseResult(**d).geturl()
        body, self.data = self.data, ''

        request = HTTPRequest(uri, body, self._headers, method = self.method)
        self.path = self.method = self.version = self._headers = None
        
        self.event('on_request', self.server_address, self.client_address, self, request)
        
    def close(self):
        common.socket.close(self)
        self.event('on_close', self)
        
class HTTPServerSocket(common.socket, events.EventMixin):
    events = events.EventMixin.events | set((
        'on_connection',
    ))
    def __init__(self):
        events.EventMixin.__init__(self)
        common.socket.__init__(self)
        self.socket = None
        
    def bind(self, host = '', port = 80):
        self._hostport = (host, port)
        self.make_socket(proxy = False)
        common.socket.bind(self, (host, port))
        return self.getsockname()
    
    def getsockname(self):
        return self.socket.getsockname()
        
    def handle_accept(self):
        conn, address = self.accept()
        self.event('on_connection', self._hostport, address, conn)
        

class DefaultHandler(object):
    def __init__(self, srv_addr, client_addr):
        self.srv_addr = srv_addr
        self.client_addr = client_addr
    def handle(self, client, request):
        log.info('Got request! %r', request)
        client.push(
                    'HTTP/1.1 200 OK\r\n'
                    'Connection: close\r\n'
                    'Content-Length: 5\r\n'
                    '\r\n'
                    'byeee'
                    )
        
        client.close()
        
_default_server_manager = None
def serve(pattern, handler_factory, host = '', port = 0):
    global _default_server_manager
    if _default_server_manager is None:
        import atexit
        _default_server_manager = HTTPServerManager()
        atexit.register(_default_server_manager.shutdown)
        
    return _default_server_manager.serve(pattern, handler_factory, host, port)

def stop_serving(pattern, host, port):
    if _default_server_manager is None:
        return
    return _default_server_manager.stop_serving(pattern, host, port)

def shutdown():
    global _default_server_manager
    if _default_server_manager is None:
        return
    _default_server_manager.shutdown()
    _default_server_manager = None
    
if __name__ == '__main__':
    logging.basicConfig()
    import AsyncoreThread as AT
    AT.start()
    
    srv = HTTPServerManager()
    
    class ClosingHandler(DefaultHandler):
        def handle(self, client, request):
            print 'closing!'
            client.push('HTTP/1.1 200 OK\r\n'
                        'Connection: close\r\n'
                        '\r\n'
                        'server has been shutdown')
            client.close()
            srv.shutdown()
        
    
    host, port = srv.serve('/close', ClosingHandler, host = '', port = 0)
    srv.serve(lambda *a: True, DefaultHandler, host = '', port = 0)

    print AT.net_thread.map
    import time; time.sleep(1)
    import urllib2
    try:
        for url in ('http://localhost:{port}/foo/bar', 
                    'http://localhost:{port}/close',
                    'http://localhost:{port}/blah',
                    ):
            x  = urllib2.urlopen(url.format(**locals()))
            print x.read()
            x.close()
    except Exception, e:
        print 'urlopenerror:', e
    time.sleep(1)
    AT.join()
    