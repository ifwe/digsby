import threading
import traceback
import collections
import time
import logging
import httplib
import pprint
import threading

import util
import util.allow_once as once
import util.httplib2 as httplib2
import util.threads.threadpool as threadpool
import common
import common.asynchttp as asynchttp

log = logging.getLogger('msnhttp')

import msn

MIMEParse = msn.util.mime_to_dict

class MsnHttpSocket(msn.MSNSocketBase):
    POLLINTERVAL = 3
    proto = 'http'
    gateway_ip = 'gateway.messenger.hotmail.com'
    gateway_path = '/gateway/gateway.dll'
    gateway_port = 80

    def get_local_sockname(self):
        return ('localhost', 0)

    @property
    def endpoint(self):
        if self.gateway_port != httplib.HTTP_PORT:
            s = '%s://%s:%s%s' % (self.proto, self.gateway_ip, self.gateway_port, self.gateway_path)
        else:
            s = '%s://%s%s' % (self.proto, self.gateway_ip, self.gateway_path)

        return s

    def __init__(self, *a, **k):
        self._session_id = None
        msn.MSNSocketBase.__init__(self, *a, **k)
        self._q = []
        self._waiting = False
        self._poller = util.RepeatTimer(self.POLLINTERVAL, self._poll)
        self._poller._verbose = False
        self._closed = False
        self._poll_in_queue = False

        self._paused = False

    def connect(self, type_host):
        type, host = self._parse_addr(type_host)
        self.typehost = type_host
        self.type = type
        self.host = self._server = host
        self.on_connect()

    _connect = connect

    def _parse_addr(self, type_addr):
        try:
            type, addr = type_addr
        except (ValueError, TypeError):
            raise TypeError('%r.connect argument must be <type \'tuple\'> (type, addr) not %r (%r)', type(self).__name__, type(type_addr), type_addr)

        bad_addr = False
        port = None
        if len(addr) == 1:
            host, port = addr[0], 80
        elif isinstance(addr, basestring):
            host, port = util.srv_str_to_tuple(addr, 80)
        elif len(addr) == 2:
            host, port = addr
        else:
            bad_addr = True

        try:
            port = int(port)
        except ValueError:
            bad_addr = True

        if bad_addr:
            raise TypeError('%r.connect argument\'s second element must be either string ("srv" or "srv:port") or tuple (("srv", port) or ("srv",)).'\
                            "Got %r instead" % addr)

        return type, host

    def connect_args_for(self, type, addr):
        return (type.upper(), addr),

    def _poll(self):
        if not self._waiting and not self._poll_in_queue:
            self._poll_in_queue = True
            self.send(None)

    def pause(self):
        self._paused = True
    def unpause(self):
        self._paused = False
        common.netcall(self.process)

    @util.callsback
    def send(self, msgobj, trid=sentinel, callback=None, **kw):
        self._q.append((msgobj, trid, callback, kw))

        if not self._paused:
            common.netcall(self.process)

    def process(self):
        if not self._q or self._waiting:
            return

        self._waiting = True

        data = []
        sending = []
        queue, self._q[:] = self._q[:], []

        while queue:
            msgobj, trid, callback, kw = queue.pop(0)
            if msgobj is not None:
                self.set_trid(msgobj, trid)
                self.set_callbacks(msgobj, callback)
                data.append(str(msgobj))
            else:
                self._poll_in_queue = False

            sending.append(callback)

        if self._session_id is None:
            url_kws = dict(Action = 'open', Server = self.type, IP = self.host)
        elif len(data) == 0:
            url_kws = dict(Action = 'poll', SessionID = self._session_id)
        else:
            url_kws = dict(SessionID = self._session_id)

        data = ''.join(data)

        req = self.make_request(url_kws, data = data)
        #log.debug(req.get_selector())

        def _transport_error(_req = None, _resp = None):
            log.error('Transport error in MsnHttpSocket: req = %r, resp = %r', _req, _resp)

            if isinstance(_req, Exception):
                e = _req
            elif isinstance(_resp, Exception):
                e = _resp
            else:
                e = _resp

            for cb in sending:
                cb_error = getattr(callback, 'error', None)
                if cb_error is not None:
                    cb_error(self, e)

            try:
                del self.gateway_ip # reset to class default- maybe host is bad?
            except AttributeError:
                pass
            self._on_send_error(e)

        asynchttp.httpopen(req, success = self._on_response, error = _transport_error)

    def fix_session_id(self, sess):

        return sess

        #if sess is None:
        #    return None

        #parts = sess.split('.')
        #if len(parts) > 3:
        #    parts = parts[-3:]

        #return '.'.join(parts)

    def _on_response(self, request, response):
        if request.get_data():
            log.debug_s('OUT : %r', request.get_data())

        if self._session_id is None:
            self._poller.start()

        session_info = MIMEParse(response['x-msn-messenger'])
        self.gateway_ip = session_info.get('GW-IP', self.gateway_ip)
        self._session_id = self.fix_session_id(session_info.get('SessionID', None))
        close = session_info.get('Session', '').lower() == 'close'

        if self._session_id is None and not close:
            raise Exception("Didn't get a session ID!")

        self._waiting = False
        if not close:
            common.netcall(self.process)

        if close:
            # this way if the socket is closed from within "_process_data" it won't be counted as "unexpected"
            self._session_id = None

        data = response.body
        self._process_data(data)

        if close:
            self.on_close()

    def _process_data(self, data):
        line = data.readline()
        while line:
            payload = False
            line.rstrip('\r\n')
            dlist = line.split()

            if self.is_payload_command(dlist):
                payload = True

                try:
                    sz = int(dlist[-1])
                except ValueError:
                    sz = 0
                line += data.read(sz)

            try:
                msg = msn.Message.from_net(line, payload)
                self.on_message(msg)
            except Exception, e:
                log.error('Error handling %r. e = %r', line, e)
                traceback.print_exc()

            line = data.readline()

    def _on_send_error(self, e):
        log.error('Something bad happened in MsnHttpSocket: %r', e)
        self.on_conn_error(e)

    def make_request(self, url_kws, data = None):
        url = util.UrlQuery(self.endpoint, url_kws)

        headers = {
            'Accept'         : '*/*',
            'Content-Type'   : 'text/xml; charset=utf-8', # 'application/x-msn-messenger',

            # Don't switch this to util.net.user_agent()
            'User-Agent'     : 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; SIMBAR={0B74DA00-76D2-11DD-9ABA-0016CFF93348}; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506; .NET CLR 3.5.21022; .NET CLR 1.1.4322; Windows Live Messenger BETA 9.0.1407)',
            'Cache-Control'  : 'no-cache',
            "Accept-Language": "en-us",
            }

        req = asynchttp.HTTPRequest.make_request(url, data = data, headers = headers, method = 'POST')
        return req

    @once.allow_once
    def close(self):
        log.info('Closing %r', self)
        msn.MSNSocketBase.close(self)
        del self._q[:]
        if self._session_id is None:
            self.on_close()
        else:
            self.send(msn.Message('OUT'))

    def on_close(self):
        log.info('on_close: %r', self)
        self._closed = True
        self._poller.stop()
        self._on_response = Null
        self._on_send_error = Null
        self._session_id = None
        self.gateway_ip = type(self).gateway_ip
        del self._q[:]
        self.pause()

        msn.MSNSocketBase.on_close(self)

    _disconnect = close_when_done = close

    def __repr__(self):
        return '<%s session_id=%r gateway_ip=%r>' % (type(self).__name__, self._session_id, self.gateway_ip)

def main():
    scktype = MsnHttpSocket

    sck = scktype()
    args = sck.connect_args_for('NS', ('messenger.hotmail.com', 1863))
    print args

    sck.connect(*args)
    sck.send(msn.Message('VER', 'MSNP8', 'CVR0'), trid=True)

    app.toggle_crust()
    app.MainLoop()

if __name__ == '__main__':
    import digsbysite
    import netextensions
    from tests.testapp import testapp
    logging.getLogger('events').setLevel(1)

    app = testapp('.')
    threadpool.ThreadPool(5)
    main()
