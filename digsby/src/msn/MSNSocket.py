import socket
import threading
import logging
import collections

import common
import util
import util.Events as Events

log = logging.getLogger('msn.sock')
#log.setLevel(1)

import msn
import msn.Msnifier

dummy = lambda *a, **k: None

def trid(max=0x7FFFFFFF, i=0):
    while True:
        i += 1
        yield i
        if i == max: i = 0

class MSNSocketBase(Events.EventMixin):
    events = Events.EventMixin.events | set((
        'on_connect',
        'on_send',
        'on_conn_error',
        'on_close',
        'on_message',

    ))

    delim = '\r\n'

    def __init__(self):
        Events.EventMixin.__init__(self)

        self.trid = trid()
        self.callbacks = collections.defaultdict(list)
        if not hasattr(self, '_lock'):
            self._lock = threading.RLock()

        self.timeouts = {}

    def is_payload_command(self, dlist):
        import msn.MSNCommands as MSNC
        return MSNC.is_payload_command(dlist)

    def set_trid(self, msgobj, trid):
        if trid is True:
            msgobj.trid = self.trid.next()
        elif type(trid) is int:
            msgobj.trid = trid

    def set_callbacks(self, msgobj, callback):
        if callback is sentinel:
            callback = None

        if msgobj.is_trid:
            self.set_timeout(msgobj)
            self.callbacks[msgobj.trid].append(callback)
        else:
            self.callbacks[msgobj.cmd].append(callback)

    def set_timeout(self, msgobj):
        timeout = getattr(msgobj, 'timeout', None)
        if timeout is not None and common.pref('msn.socket.use_timeout', type = bool, default = False):
            log.info('Starting timeout for %r', msgobj)
            timer = util.Timer(timeout, self.timeout_handler(msgobj))
            self.timeouts[msgobj.trid] = timer
            timer.start()

    def timeout_handler(self, msgobj):
        def handler():
            log.debug('This message has timed out: %r', msgobj)
            msgcopy = msgobj.copy()
            msgcopy.timeout = msgobj.timeout
            msgcopy.retries = msgobj.retries - 1
            msgcopy.trid = 0
            if msgcopy.retries == 0: # yes, this does mean you can retry infinitely with a negative number
                return

            log.debug('Retrying this message that timed out: %r', msgcopy)
            with self._lock:
                callback = self.callbacks.pop(msgobj.trid, None)
            self.send(msgcopy, trid = True, callback = callback)

        return handler

    def unset_timeout(self, msgobj, include_previous = True):
        if not msgobj.is_trid:
            return

        if include_previous:
            for i in range(msgobj.trid):
                self.unset_timeout_single(i)

        self.unset_timeout_single(msgobj.trid)

    def unset_timeout_single(self, key):
        try:
            timer = self.timeouts.pop(key, None)
            if timer is not None:
                timer.stop()
        except (IndexError, KeyError):
            pass

    def pause(self):
        return
    def unpause(self):
        return

    @Events.event
    def on_connect(self):
        return self

    @Events.event
    def on_send(self, data):
        "'data' has been sent"

    @Events.event
    def on_conn_error(self, e=None, **k):
        log.info('%r had a connection error: %r', self, e)
        return self, e

    @Events.event
    def on_close(self):
        return self

    @util.lock
    def unset_callbacks(self, msg):
        callback = None
        try:
            callback = self.callbacks[msg.trid or msg.cmd][0]
        except (KeyError, IndexError), e:
            pop = False
        else:
            pop = True

        if pop:
            if msg.is_trid:
                self.unset_timeout(msg, include_previous = False)
                self.callbacks.pop(msg.trid, None)

            elif not msg.trid:
                self.callbacks[msg.cmd].pop(0)

        return callback

    def adjust_message(self, msg):
        if msg.cmd == 'QNG':
            msg.cmd = 'PNG'
            msg.trid = 0

        return msg

    def on_message(self, msg):
        self.event('on_message', msg)

        msg = self.adjust_message(msg)
        callback = self.unset_callbacks(msg)
        if callback is None:
            return

        try:
            if msg.is_error:    f = callback.error
            else:               f = callback.success
        except AttributeError, e:
            log.error('AttributeError in msnsocket.on_message: %r\ncallback was: %r', e, callback)

        log.debug('MSNSocket calling %r', f)

        try:
            f(self,msg)
        except Exception, e:
            log.error('Error in callback')
            import traceback; traceback.print_exc()

    def close(self):
        while self.timeouts:
            try:
                k,v = self.timeouts.popitem()
            except KeyError:
                break
            else:
                if v is not None:
                    v.stop()

class MSNSocket(MSNSocketBase, common.socket):
    speed_limit = None
    speed_limit = 1
    speed_window = .150

    ac_in_buffer_size       = 16384
    ac_out_buffer_size      = 16384

    #@callsback
    def __init__(self,
                 #processor,
                 #server,
                 #callback=None
                 ):
        common.socket.__init__(self)
        MSNSocketBase.__init__(self)

#        assert isinstance(processor, CommandProcessor)
#        self.processor = processor
        self.set_terminator(self.delim)
        self.data = ''
        self.expecting = 'command'

        #self.connect_cb = callback

        self._server = None

        self.rater = msn.Msnifier.Msnifier(self)
        self.rater.start()

        self._bc_lock = threading.RLock()
        self.bytecount = [(0, util.default_timer())]

        log.debug('%r created', self)

    def get_local_sockname(self):
        return self.socket.getsockname()

    def connect_args_for(self, type, addr):
        return type, addr

    def connect(self, type, host_port):
        self._scktype = type
        try:
            host, port = host_port
        except (ValueError, TypeError):
            raise TypeError('%r address must be <type \'tuple\'> (host, port) not %r (%r)',
                            type(self).__name__, type(host_port), host_port)

        if self._server is not None:
            raise ValueError("Don't know which server to use! self._server = %r, host_port = %r.",
                             self._server, host_port)
        self._server = host_port
        log.info('connecting socket to %r', self._server)
        try:
            common.socket.connect(self, self._server,
                                  error=self.on_conn_error,
                                  )
        except Exception, e:
            self.on_conn_error(e)
            return

        self.bind_event('on_message', lambda msg, **k: log.debug('Received %r', msg))

    _connect = connect

    def _disconnect(self):
        self.close_when_done()

    @property
    def _closed(self):
        return not (getattr(self.socket, 'connected', False))

    def __repr__(self):

        try:
            s = 'connected to %r' % (self.socket.getpeername(),)
        except socket.error:
            s = 'not connected'

        return "<%s %s>" % (type(self).__name__, s,)

    @util.callsback
    def test_connection(self, callback=None):
        if self._scktype == 'NS':
            self.send(msn.Message('PNG'), callback=callback)
        else:
            log.info('Not testing connection because this is not an NS socket.')
            callback.success()

    def handle_connect(self):
        log.debug("connection established")
        self.on_connect()

    def handle_expt(self):
        log.warning('OOB data. self.data = %r', self.data)
        self.close()

    @util.lock
    def collect_incoming_data(self, data):
        self.data += data

    def set_terminator(self, term):
        assert term
        common.socket.set_terminator(self, term)

    def found_terminator(self):

        self.data += self.delim
        try:
            with self._lock:
                self.data, data = '', self.data

                dlist = data.split(' ')
                cmd = dlist[0]

                if self.expecting == 'command' and self.is_payload_command(dlist):
                    self.expecting, self.data = 'payload', data

                    try:
                        new_term = int(dlist[-1])
                    except ValueError:
                        new_term = 0

                    if not new_term:
                        self.found_terminator()
                        new_term = self.delim

                    return self.set_terminator(new_term)
                elif self.expecting == 'payload':
                    self.expecting = 'command'
                    data = data[:-len(self.delim)] # strip off newline that was appended
                    payload = True
                else:
                    assert self.expecting == 'command'
                    payload = False

                self.set_terminator(self.delim)
                if True or len(data) < 5000:
                    log.info_s('IN  : %r', data)
                msg = msn.Message.from_net(data, payload)
            # Release lock
        except Exception, e:
            log.info('error parsing message, testing connection\nError was %r', e)
            self.test_connection(success=self.conn_ok, error=self.conn_error)
            import traceback
            traceback.print_exc()
        else:
            self.on_message(msg)

    def handle_close(self):
        log.warning('socket closed, self.data = %r', self.data)
        if self.rater is not None:
            self.rater.stop()
            self.rater = None
#        self.processor.close_transport(self)

        self.close()

    def close(self):
        log.warning('socket closing, self.data = %r', self.data)
        MSNSocketBase.close(self)
        common.socket.close(self)
        self.on_close()

    def send_gen(self, gen, priority=5):
        if self.rater is not None:
            self.rater.send_pkt(gen, priority)
        else:
            log.error('Can\'t send generator after rater has been stopped')

    def send(self, msgobj, trid=sentinel, callback=None, **kw):
        if isinstance(msgobj, buffer):
            try:
                data = str(msgobj)
                if True or len(data) < 5000:
                    log.info_s("OUT : %r" % (data,))
                retval = common.socket.send(self, data)
            except Exception as e:
                raise e
            else:
                getattr(callback, 'after_send', lambda:None)()
                return retval

        self.set_trid(msgobj, trid)
        self.set_callbacks(msgobj, callback)
        log.debug('Sending %r', msgobj)
        if self.rater is not None:
            self.rater.send_pkt(str(msgobj), callback = callback, **kw)
        else:
            if not self._send(str(msgobj)):
                callback.error("Message dropped")
            else:
                log.warning("Calling after_send: %r", callback.after_send)
                callback.after_send()

    send = util.callsback(send, ('success', 'error', 'after_send'))

    def conn_ok(self):
        log.info('connection test passed')

    def conn_error(self):
        log.warning('connection test failed')
        self.close_when_done()
        self.on_conn_error()

    def _send(self, data, *a, **k):
        log.log_s(0,'sent: %s' % data)
        message_sent = False
        with self._lock:
            try:

                common.socket.push(self, data, *a, **k)
                message_sent = True
#                if common.socket.send(self, data, *a, **k):
#                    message_sent = True
#                else:
#                    log.critical('Message dropped in %r, data = %r', self, data)

            except Exception, e:
                log.critical('Error sending message in %r. error was %r, data = %r', self, e, data)

                try:
                    if data == "OUT\r\n":
                        e.verbose = False
                except Exception:
                    pass

                self.handle_error(e)
                if self.connected:
                    self.close()
                return

        if message_sent:
            self.on_send(data)

            now = util.default_timer()
            with self._bc_lock:
                self.bytecount.append((len(data), now))
        else:
            log.info("recursively calling _send... watch out!")
            self._send(data, *a, **k)

        return message_sent

    def time_to_send(self, data):
        if self.speed_limit is None:
            return 0

        now = util.default_timer()
        with self._bc_lock:
            self.bytecount = filter(lambda t:(now-t[1])<self.speed_window,
                                    self.bytecount)

        send_rate = sum(b[0] for b in self.bytecount)
        if send_rate < self.speed_limit: return 0

        log.debug('sending too fast')
        bytes = dlen = 1 #len(data)
        for size, tstamp in reversed(self.bytecount):
            bytes += size
            interval = now - tstamp
            if (bytes/interval*self.speed_window) > self.speed_limit: break

        tts = (bytes/self.speed_limit*self.speed_window) + interval
        #tts = 0 if tts < .005 else tts
        log.log(5, 'currently sending at %d bytes/sec', send_rate)
        log.debug('sleeping for %r seconds' % tts)
        return tts

    def close_when_done(self):
        '''
        close_when_done()

        sends the 'OUT' command and then closes itself (when done!)
        '''
        if self.rater is not None:
            self.rater.stop()
            self.rater = None

        if getattr(self, 'closed', False):
            return
        self.closed = True

        try:
            self.send(msn.Message('OUT'))
        except socket.error:
            pass

        try:
            self.close()
        except socket.error:
            pass

#class MSNSSL(MSNSocket):
#
#    @lock
#    def make_socket(self):
#        MSNSocket.make_socket(self)
#        from socket import ssl
#        self.socket = ssl(self.socket)
