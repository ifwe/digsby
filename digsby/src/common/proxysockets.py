import util
from AsyncSocket import AsyncSocket as asocket  # our AsyncSocket
import socks                                    # socks module
from socket import _socket as socket            # original python socket module
from functools import wraps

import sys

import logging; log = logging.getLogger('proxysockets')

class ProxyType:
    SOCKS4 = socks.PROXY_TYPE_SOCKS4 # 1
    SOCKS5 = socks.PROXY_TYPE_SOCKS5 # 2
    HTTP   = socks.PROXY_TYPE_HTTP   # 3
    HTTPS  = socks.PROXY_TYPE_HTTPS  # 4

class ProxySocket(asocket):
    def __init__(self, proxy, conn, post):
        asocket.__init__(self, conn)

        self.callback = None
        self.post_negotiate = post
        self._negotiating = False
        if proxy is None:
            proxy = {}
        self._proxyinfo = proxy.copy()
        self.mid = (self._proxyinfo.get('addr', ''), self._proxyinfo.get('port',0))
        self.end = ('',0)

    @util.callbacks.callsback
    def connect(self, end, callback = None):
        self.callback = callback
        self.end = end
        self._pconnect()

    def _pconnect(self):
        asocket.connect(self, self.mid)

    def handle_close(self):
        log.info('ProxySocket.handle_close - calling callback.error')
        self.close()
        asocket.handle_close(self)

    def close(self):
        if getattr(self, 'socket', None) is not None:
            asocket.close(self)

        if self.callback is not None:
            self.callback, cb = None, self.callback
            cb.error()

    def handle_connect(self):

        if not self._negotiating:
            log.info('ProxySocket connected. starting negotiation... ')
            self._negotiating = True
            self._pnegotiate()

    def _pnegotiate(self):
        negs = {
               ProxyType.HTTP   :self._negotiatehttp,
               ProxyType.HTTPS  :self._negotiatehttps,
               ProxyType.SOCKS4 :self._negotiatesocks4,
               ProxyType.SOCKS5 :self._negotiatesocks5,
               }

        neg = negs.get(self._proxyinfo.get('proxytype', None), self._negotiation_done)

        neg()

    def _negotiatehttp(self):
        self._endhost_resolved = None
        endhost = self.end[0]
        endport = self.end[1]

        if not self._proxyinfo.get('rdns', True):
            try:
                endhost = self._endhost_resolved = socket.gethostbyname(self.end[0])
            except socket.gaierror:
                pass

        authstr = self._httpauthstring()
        http_connect = (('CONNECT %s:%d HTTP/1.1\r\n'
                        'Host: %s\r\n'
                        '%s\r\n') %
                        (endhost, endport,
                         self.end[0],            # use unresolved host here
                         authstr,
                         ))

        log.info('ProxySocket._negotiatehttp: sending proxy CONNECT%s. %r:%r',
                 (" and auth string" if authstr else ''),
                 self, (endhost, endport))

        self.push(http_connect)
        self.push_handler(self._httpfinish)
        self.set_terminator('\r\n\r\n')

    def _httpauthstring(self):
        username, password = self._proxyinfo.get('username', None), self._proxyinfo.get('password', None)

        if all((username, password)):
            raw = "%s:%s" % (username, password)
            auth = 'Basic %s' % ''.join(raw.encode('base-64').strip().split())
            return 'Proxy-Authorization: %s\r\n' % auth
        else:
            return ''

    def _httpfinish(self, data):
        self.pop_handler()
        statusline = data.splitlines()[0].split(" ",2)
        if statusline[0] not in ("HTTP/1.0","HTTP/1.1"):
            log.info("ProxySocket._httpfinish: Bad data from server, disconnecting: (%r)", data)
            return self.close()
        try:
            statuscode = int(statusline[1])
        except ValueError:
            log.info('ProxySocket._httpfinish: Got some bad data from the server, disconnecting: %r (%r)', statusline, data)
            return self.close()
        if statuscode != 200:
            log.info('ProxySocket._httpfinish: got HTTPError code %r, disconnecting (%r)', statuscode, data)
            return self.close()

        log.info('ProxySocket._httpfinish: success %r', self)

        self.__proxysockname = ("0.0.0.0",0)
        self.__proxypeername = (self._endhost_resolved or self.end[0],self.end[1])

        self._negotiation_done()

    def _negotiation_done(self):
        log.info('proxy negotiation complete')
        self._proxy_setup = True
        self.del_channel()

        self.finish(self.socket, 'handle_connect')
        if self.callback is not None:
            self.callback.success()

        self.callback = None
        self.socket = None

    def finish(self, sck, handler_name):
        sck = self.post_negotiate(sck)
        sck.connected = True
        sck._proxy_setup = True
        self.collect_incoming_data = sck.collect_incoming_data
        getattr(sck, handler_name)()

    def _negotiatehttps(self):
        raise NotImplementedError

    def _negotiatesocks4(self):
        from struct import pack
        destaddr = self.end[0]
        destport = self.end[1]
        rresolve = self._proxyinfo.get('rdns', True)

        def zstring(s):
            return s + '\0'

        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # Named server. needs to be resolved at some point
            if not rresolve:
                try:
                    ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                except socket.error:
                    ipaddr = pack('!I', 1)
                    rresolve = True

        req = pack('!BBH', 4, 1, destport) + ipaddr
        username = self._proxyinfo.get('username', '')

        req += zstring(username)

        if rresolve:
            req += zstring(destaddr)

        log.info('ProxySocket._negotiatesocks4: sending request')
        self.push(req)
        self.push_handler(self._socks4finish)
        self.set_terminator(8)

        if rresolve:
            self.__proxypeername = (socket.inet_ntoa(ipaddr),destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def _socks4finish(self, data):
        from struct import unpack
        self.pop_handler()
        log.info('ProxySocket._negotiatesocks4: received response')

        try:
            null, returncode, port, ip = unpack('!BBH4s', data)
        except Exception, e:
            log.info('ProxySocket._negotiatesocks4: bad data received from server. original exception is: %r', e)
            return self.close()

        ip = socket.inet_ntoa(ip)

        if null != 0:
            # Bad data
            log.info('ProxySocket._negotiatesocks4: Bad data from server- expected null byte, got %r', null)
            return self.close()
        if returncode != 0x5A:
            # Server returned an error
            log.info('ProxySocket._negotiatesocks4: received error code %r', returncode)
            return self.close()

        log.info('ProxySocket._negotiatesocks4: success')
        self.__proxysockname = (ip,port)
        self._negotiation_done()

    def _negotiatesocks5_gen(self):
        from struct import pack, unpack
        from util import Storage

        destaddr, destport = self.end
        uname, password = self._proxyinfo.get('username', ''), self._proxyinfo.get('password', '')

        this = Storage()
        this.errors = False
        this.authtype = 0
        this.incoming_host_type = 0

        def pstring(s):
            return chr(len(s)) + s

        def single_use_handler(f):
            @wraps(f)
            def wrapper(data):
                self.pop_handler()
                return f(data)
            return wrapper

        def if_errors_close(f):
            def wrapper(*a, **k):
                ok = not this.errors
                if ok:
                    try:
                        return f(*a, **k)
                    except Exception, e:
                        import traceback; traceback.print_exc()
                        log.info('ProxySocket._negotiatesocks5: there was an error calling %r(*%r, **%r). the exception was: %r',
                                 f, a, k, e)
                        this.errors = True
                        self.close()
                        return '',None
                else:
                    log.info('ProxySocket._negotiatesocks5: Previous errors prevented %r(*%r, **%r) from happening', f,a,k)
                    return '',None
            return wrapper

        sender = if_errors_close
        def recver(f):
            return if_errors_close(single_use_handler(f))

        @sender
        def _sendauthtype():
            if uname and password:
                data = pack('!BBBB', 5,2,0,2)
            else:
                data = pack('!BBB', 5,1,0)

            return data, 2

        @recver
        def _recvauthtype(data):
            status, authmethod = unpack('!BB', data)
            if status != 5:
                raise Exception("Bad data was received from the proxy server: %r", data)

            if authmethod in (0,2):
                this.authtype = authmethod
            elif authmethod == 0xFF:
                this.authtype = None
                raise Exception('All auth methods were rejected')

        @sender
        def _sendauth():
            return chr(1) + pstring(uname) + pstring(password), 2

        @recver
        def _recvauth(data):
            code, status = map(ord, data)
            if code != 1:
                raise Exception('Was expecting 1, got %r', code)

            if status != 0:
                raise Exception('authentication failed. bad uname/pword?')

        @sender
        def _sendproxysetup():
            request = pack('!BBB', 5, 1, 0)
            rresolve = self._proxyinfo.get('rdns', True)

            this.resolved_ip = None
            if rresolve:
                try:
                    this.resolved_ip = socket.inet_aton(destaddr)
                except socket.error:
                    try:
                        this.resolved_ip = socket.inet_aton(socket.gethostbyname(destaddr))
                    except:
                        rresolve = True

            if rresolve or (this.resolved_ip is None):
                request += chr(3) + pstring(destaddr)
            else:
                request += chr(1) + this.resolved_ip

            request += pack('!H', destport)

            return request, 4

        @recver
        def _recvproxysetup(data):
            five, null, _unused, status = map(ord, data)

            if five != 5:
                raise Exception('Was expecting 5, got: %r', five)

            if null != 0:
                raise Exception('Connection failed, reason code was: %r', null)

            if status in (1, 3):
                this.incoming_host_type = status
                return

            raise Exception('Unknown error occurred.')

        @sender
        def _sendpstringhost1():
            return '', 1
        @recver
        def _recvpstringhost1(data):
            this.hostlen = ord(data)
        @sender
        def _sendpstringhost2():
            return '', this.hostlen
        @recver
        def _recvpstringhost2(data):
            this.boundhost = data

        @sender
        def _sendiphost():
            return '', 4
        @recver
        def _recvhost(data):
            this.boundhost = socket.inet_ntoa(data)

        @sender
        def _getport():
            return '',2
        @recver
        def _recvport(data):
            this.boundport, = unpack('!H', data)

        #-----------

        steps = ((_recvauthtype,     _sendauthtype,     None),
                 (_recvauth,         _sendauth,         lambda: this.authtype),
                 (_recvproxysetup,   _sendproxysetup,   None),
                 (_recvhost,         _sendiphost,       lambda: this.incoming_host_type == 1),
                 (_recvpstringhost1, _sendpstringhost1, lambda: this.incoming_host_type == 3),
                 (_recvpstringhost2, _sendpstringhost2, lambda: this.incoming_host_type == 3),
                 (_recvport,         _getport,          None),
                )

        for recvr, sendr, check in steps:
            if check is None or check():
                recvr((yield sendr))

        #-----------
        self.__proxysockname = (this.boundhost, this.boundport)
        if this.resolved_ip is not None:
            self.__proxypeername = (socket.inet_ntoa(this.resolved_ip), destport)
        else:
            self.__proxypeername = (destaddr, destport)

        if not this.errors:
            self._negotiation_done()
        else:
            self.close()

    def _negotiatesocks5(self):
        gen = self._negotiatesocks5_gen()

        def handler(data):
            log.info('ProxySocket._negotiatesocks5: in =%r', data)
            try:
                next = gen.send(data)
            except StopIteration:
                # Done!
                return
            data, term = next()

            if data and ord(data[0]) == 1:
                logdata = '<authstring omitted>'
            else:
                logdata = data
            log.info('ProxySocket._negotiatesocks5: out=%r, terminator=%r', logdata, term)

            self.push(data); self.push_handler(handler); self.set_terminator(term)

        # Go!
        handler(None)

    def __repr__(self):
        parentrepr = asocket.__repr__(self).strip('<>')

        return '<%s, fileno=%r>' % (parentrepr, self._fileno)

def main():
    from tests.testapp import testapp
    from AsyncoreThread import end

    import wx; a = testapp('../..')
    a.toggle_crust()


    class HeadSocket(asocket):
        def __init__(self, *a, **k):
            asocket.__init__(self, *a, **k)
            self.set_terminator('\r\n\r\n')
            self.push('HEAD / HTTP/1.0\r\n\r\n')
            self.push_handler(lambda d: log.info(repr(d)))

        def GetProxyInfo(self):
            return {}

    h = HeadSocket()
    h.connect(('www.google.com', 80), success=lambda s=h: log.info('success! socket: %r',s))

    a.MainLoop(); end()
    return

if __name__ == '__main__':
    def GetProxyInfo():
        return dict(
                    proxytype=3,
                    username='digsby',
                    password='password',
                    addr='athena',
                    port=9999,
                    )

    print main()
