from jabber.filetransfer.s5b_proxy_sender import S5B_proxyConnect
from jabber.objects.bytestreams import ByteStreams, BYTESTREAMS_NS
from jabber.objects.si_filetransfer import Feature
from jabber.objects.si_filetransfer import SI_FileTransfer, SI_NS
from jabber.objects.si_filetransfer import File
from jabber.filetransfer.S5BFileXferHandler import ByteStream
import functools
import random
from jabber.filetransfer import supported_streams
from pyxmpp.all import Iq
from util.net import NoneFileChunker

from logging import getLogger
log = getLogger('jabber.file.send')

from common import pref
from common.filetransfer import OutgoingFileTransfer, FileTransfer

from path import path
from util import lock

done_states  = FileTransfer.states.CompleteStates | FileTransfer.states.FailStates

def if_not_done(f):
    @functools.wraps(f)
    def wrapper1(self,*args, **kw):
        if self.state not in done_states:
            return f(self, *args, **kw)
    return wrapper1


class SIsender(OutgoingFileTransfer):

    def __init__(self, jabber_protocol, jid, filestorage, message = None):
        OutgoingFileTransfer.__init__(self)

        self.j        = jabber_protocol
        self.jid      = jid
        self.filestor = filestorage
        self.message  = message
        self.sid      = 'si_' + str(id(self)) + str(random.randint(0,100))
        log.info('SIsender created for %r', jid)

        # to conform to the FileTransfer interface
        self.completed = 0
        self.size      = filestorage.size
        self.filepath  = path(self.filestor.path)
        self.buddy     = self.j.buddies[jid]
        self.name      = self.filestor.name

        self.on_get_buddy(self.buddy)

    @property
    def protocol(self):
        return self.j

    def send_offer(self):
        self.state = self.states.WAITING_FOR_BUDDY

        i = Iq(to_jid=self.jid, stanza_type='set')

        #CAS: id generator for streams
        si = SI_FileTransfer(self.sid)
        si.file = File(self.filestor.name, self.filestor.size)
        si.feature = Feature(possible_streams=supported_streams)
        si.as_xml(i.get_node())

        self.j.send_cb(i, success = self.handle_response,
                          error   = self.handle_error,
                          timeout = self.timed_out)

    @lock
    @if_not_done
    def handle_response(self, stanza):
        self.state = self.states.CONNECTING
        si = SI_FileTransfer.from_iq(stanza)
        self.stream = b = stream_connectors[si.feature.selected_stream](self)
        b.bind_event("stream_connected", self.transferring)
        b.bind_event("stream_connect_failed", self.stream_connect_failed)
        b.bind_event("stream_error", self.stream_error)
        b.bind_event("stream_closed", self.stream_closed)
        b.connect_stream()

    @lock
    @if_not_done
    def stream_connect_failed(self):
        self.unbind_all()
        self.state = self.states.CONN_FAIL
        self.on_error()

    @lock
    @if_not_done
    def handle_error(self, stanza):
        e = stanza.get_error()

        SI_NS_error = e.get_condition(SI_NS)
        if SI_NS_error is not None:
            SI_NS_error = SI_NS_error.name

        error = e.get_condition()
        if error is not None:
            error = error.name

        if SI_NS_error == 'no-valid-streams':
            #remote user didn't support our streams
            self.state = self.states.CONN_FAIL
        elif SI_NS_error == 'bad-profile':
            #remote user doesn't support file transfer, but does support SI
            self.state = self.states.CONN_FAIL
        elif error == 'forbidden':
            #remote user rejected the transfer
            reason = e.get_text()
            log.info('%r: handle_error. Setting state to CANCELLED_BY_BUDDY')
            self.state = self.states.CANCELLED_BY_BUDDY
        else:
            #user probably doesn't support SI, let alone file transfer
            self.state = self.states.CONN_FAIL

        if self.state == self.states.CONN_FAIL:
            self.on_error()

    @lock
    @if_not_done
    def timed_out(self):

        log.info('%r: Timed out. Setting state to CONN_FAIL, calling on_error')

        self.unbind_all()
        self.state = self.states.CONN_FAIL
        self.on_error()

    @lock
    @if_not_done
    def stream_error(self):

        log.info('%r: Stream error. Setting state to CONN_FAIL_XFER, calling on_error')

        self.unbind_all()
        self.close_file()
        self.state = self.states.CONN_FAIL_XFER
        self.on_error()

    @lock
    @if_not_done
    def stream_closed(self):

        log.info('%r: Stream closed. Setting state to CANCELLED_BY_BUDDY')

        self.unbind_all()
        self.close_file()

        self.state = self.states.CANCELLED_BY_BUDDY

    @lock
    def unbind_all(self):
        if hasattr(self, 'stream'):
            b = self.stream
            b.unbind("stream_connected", self.transferring)
            b.unbind("stream_connect_failed", self.stream_connect_failed)
            b.unbind("stream_error", self.stream_error)
            b.unbind("stream_closed", self.stream_closed)

    @lock
    @if_not_done
    def transferring(self):
        self.stream.unbind("stream_connected", self.transferring)
        self.state = self.states.TRANSFERRING
        #DON'T REACH INTO THE STREAM OBJECT
        self.chunker = NoneFileChunker(self.filestor.obj,
                                   close_when_done = True,
                                   progress_cb = self.on_progress)
        self.stream.conn.push_with_producer(self.chunker)
        self.stream.conn.close_when_done()

    @lock
    @if_not_done
    def cancel(self, state=None):
        self.unbind_all()
        if hasattr(self, 'stream'):
            self.stream.cancel()
            if hasattr(self, 'chunker'):
                self.chunker.cancelled = True
        self.close_file()

        if state is None:
            state = self.states.CANCELLED_BY_YOU
        self.state = state

    @lock
    @if_not_done
    def on_progress(self, bytes):
        self._setcompleted(bytes)
        if self.completed == self.size:
            self.unbind_all()
            self.stream.close()
            self.state = self.states.FINISHED
            self._ondone()
            #cleanup

    def close_file(self):
        try:    self.chunker.fileobj.close()
        except Exception: pass
        try:    self.filestor.obj.close()
        except Exception: pass

class SOCKS5OutBytestream(ByteStream):

    def __init__(self, sender):
        ByteStream.__init__(self)
        self.j        = sender.j
        self.jid      = sender.jid
        self.sid      = sender.sid
        self.conn     = None

    def connect_stream(self):
        try: #protection against None stream
            self.hash = self.j.s5bserver.conn_id(self.sid, self.j.stream.me, self.jid)
        except AttributeError:
            self.event("stream_connect_failed")
            return
        self.j.s5bserver.add_hash(self.hash)

        i = Iq(to_jid=self.jid, stanza_type='set')
        b = ByteStreams(sid = self.sid )
        if pref('jabber.use_direct_ft'):
            if not pref('jabber.use_faulty_localhost_ips'):
                [b.add_host(self.j.stream.me, h[0], h[1]) for h in self.j.s5bserver.hosts]
            else:
                [b.add_host(self.j.stream.me, h[0].replace("192", "129"),
                            h[1]) for h in self.j.s5bserver.hosts]
        if pref('jabber.use_proxy_ft'):
            b.hosts.extend(set(h for hosts in self.j.known_s5b_proxies.values() for h in hosts))
            if pref('jabber.use_jabber_org_proxy', True):
                b.add_host("proxy.jabber.org", "208.245.212.98", 7777)
        b.as_xml(i.get_node())


        self.j.send_cb(i, success=self.handle_ready, error=self.handle_error, timeout=self.timed_out)

    def kill_socket_hash(self):
        c = self.j.s5bserver.retrieve_hash(self.hash)
        if c not in (False, None):
            try:
                c.close()
            except: pass

    def timed_out(self):
        #cleanup
        self.kill_socket_hash()
        self.event("stream_connect_failed")

    def handle_error(self, stanza):
        #cleanup
        import traceback;traceback.print_exc()
        self.kill_socket_hash()
        self.event("stream_connect_failed")
        log.info(stanza.serialize())

    def handle_ready(self, stanza):
        log.info(stanza.serialize())
        try:
            b = ByteStreams(stanza.get_query())
            used_jid = b.host_used
        except:
            #cleanup
            self.kill_socket_hash()
            self.event("stream_connect_failed")
            return
        #debug:
        if not pref('jabber.use_proxy_ft'):  assert used_jid == self.j.stream.me
        if not pref('jabber.use_direct_ft'): assert used_jid != self.j.stream.me
#        assert used_jid != self.j.stream.me
        if used_jid == self.j.stream.me:
            self.conn = self.j.s5bserver.retrieve_hash(self.hash)
            if self.conn not in (False, None):
                self.socket_connected()
                self.event("stream_connected")
            else:
                self.event("stream_connect_failed")
                #cleanup?
        else:
            #cleanup socket server
            self.kill_socket_hash()

            hosts = set(h for hosts in self.j.known_s5b_proxies.values() for h in hosts)

            if not (used_jid in [h.jid for h in hosts]):
                self.event("stream_connect_failed")
                return

            streamhost = [h for h in hosts if h.jid == used_jid]
            if len(streamhost) != 1:
                self.event("stream_connect_failed")
                return
            self.streamhost = streamhost = streamhost[0]

            #start proxy here:
            #same as s5bsocket
            self.conn = S5B_proxyConnect((streamhost.host, streamhost.port),
                                    self.hash, streamhost)
            self.conn.bind_event("connected", self.handle_proxy_connect)
            self.conn.bind_event("connection_failed", self.socket_failed)
            self.conn.get_connect()

        log.info('handle_ready done')

    def socket_failed(self):
        self.unbind_all()
        self.event("stream_connect_failed")

    def socket_connected(self):
        self.conn.unbind("connection_failed", self.socket_failed)
        self.conn.unbind("connected", self.handle_proxy_connect)

        self.conn.bind_event("socket_error", self.stream_error)
        self.conn.bind_event("socket_closed", self.stream_closed)

    def stream_closed(self):
        self.unbind_all()
        self.event("stream_closed")

    def stream_error(self):
        self.unbind_all()
        self.event("stream_error")

    def unbind_all(self):
        self.conn.unbind("connection_failed", self.socket_failed)
        self.conn.unbind("connected", self.handle_proxy_connect)
        self.conn.unbind("socket_error", self.stream_error)
        self.conn.unbind("socket_closed", self.stream_closed)

    def handle_proxy_failure(self):
        log.info('handle proxy failure')
        #no cleanup necessary, except unbind
        self.unbind_all()
        self.event("stream_connect_failed")

    def handle_proxy_failure2(self):
        log.info('handle proxy failure2')
        #kill socket, unbind
        try:
            self.conn.close()
        except:
            import traceback;traceback.print_exc()
        self.event("stream_connect_failed")

    def handle_proxy_connect(self):
        log.info('handle_proxy_connect called')
        self.conn.set_terminator(0)
        #activate
        streamhost = self.streamhost
        sh_jid = streamhost.jid
        targ_jid = self.jid
        b = ByteStreams(None, self.sid)
        b.activate = targ_jid
        i = Iq(to_jid=sh_jid, stanza_type='set')
        b.as_xml(i.get_node())
        self.j.send_cb(i, success=self.handle_proxy_activate,
                          error=self.handle_proxy_failure2,
                          timeout=self.proxy_activate_timeout)

    def proxy_activate_timeout(self):
        #kill socket, unbind
        self.unbind_all()
        try:
            self.conn.close()
        except:
            import traceback;traceback.print_exc()
        self.event("stream_connect_failed")

    def handle_proxy_activate(self, stanza):
        log.info('handle_proxy_activate called')
        self.socket_connected()
        self.event("stream_connected")

    def close(self):
        self.conn.close_when_done()
        #self.event("stream_closed") needs bind on socket
        #cleanup

    def cancel(self):
        try:
            self.conn.close()
        except:
            pass


def dumpfile(conn, filestor, progress_cb):
    #send
    log.info('dumpfile called')
    conn.push_with_producer()
    conn.close_when_done()

stream_connectors = {BYTESTREAMS_NS:SOCKS5OutBytestream}

#   return Storage(
#       size    = os.path.getsize(filepath),
#       obj     = open(filepath, 'rb'),
#       modtime = filestats[stat.ST_MTIME],
#       ctime   = filestats[stat.ST_CTIME],
#       name    = os.path.split(filepath)[1],
#       path    = filepath,
#   )
