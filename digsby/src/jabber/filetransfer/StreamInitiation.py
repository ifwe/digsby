from __future__ import with_statement
from jabber.objects.si_filetransfer import File
from common.filetransfer import IncomingFileTransfer
from jabber.objects.si_filetransfer import Feature
from jabber.objects.si_filetransfer import SI_FileTransfer
from jabber.objects.si import SI_NS
from pyxmpp.error import STANZA_ERROR_NS
from pyxmpp.all import Iq
from util.primitives import lock
from jabber.filetransfer.initiateStream import if_not_done, done_states
from path import path
import threading

from logging import getLogger
log = getLogger('jabber.ft.si')

class StreamInitiationHandler(object):
    def __init__(self, jabber_object):
        self.j = jabber_object
        self.handlers = {}
        self.supported_streams = {}

    def set_stream_handler(self, namespace, handler):
        self.supported_streams[namespace] = handler

    def set_profile_handler(self, namespace, handler):
        self.handlers[namespace] = handler

    def register_handlers(self):
        self.j.stream.set_iq_set_handler('si', SI_NS, self.incoming)

    def incoming(self, stanza):
        """dispatch"""
        #CAS: error cases
        prof = stanza.xpath_eval('si:si/@profile',
                                 {'si':SI_NS})[0].content
        if prof not in self.handlers:
            self.respond_not_understood(stanza)
        else:
            self.handlers[prof](self, Iq(stanza.get_node()))

    def respond_no_valid(self, stanza):
        """we don't support any suggested stream type"""
        e = stanza.make_error_response('bad-request')
        n = e.xpath_eval('si:si', {'si':SI_NS})[0]
        n.unlinkNode()
        n.freeNode()
        e.set_from(None)
        er = e.xpath_eval('ns:error')[0]
        er.newProp('code', '400')
        c=er.newChild(None,'no-valid-streams',None)
        ns = c.newNs(SI_NS, None)
        c.setNs(ns)
        t = e.xpath_eval('ns:error/@type')[0]
        t.setContent('cancel')
        self.j.send(e)

    def respond_not_understood(self, stanza):
        """we don't support that Stream Initiation profile; i.e. it wasn't
        file transfer"""
        e = stanza.make_error_response('bad-request')
        n = e.xpath_eval('si:si', {'si':SI_NS})[0]
        n.unlinkNode()
        n.freeNode()
        e.set_from(None)
        er = e.xpath_eval('ns:error')[0]
        er.newProp('code', '400')
        c=er.newChild(None,'bad-profile',None)
        ns = c.newNs(SI_NS, None)
        c.setNs(ns)
        self.j.send(e)

    def reject(self, stanza, reason = None):
        """Say 'No, thanks'"""
        e = stanza.make_error_response('forbidden')
        n = e.xpath_eval('si:si', {'si':SI_NS})[0]
        n.unlinkNode()
        n.freeNode()
        e.set_from(None)
        er = e.xpath_eval('ns:error')[0]
        er.newProp('code', '403')
        c=er.newChild(None, 'text', reason or 'Offer Declined')
        ns = c.newNs(STANZA_ERROR_NS, None)
        c.setNs(ns)
        self.j.send(e)

    def send_accept(self, stanza, payload):
        """Say 'Yes, please'"""
        i = stanza.make_result_response()
        payload.as_xml(i.get_node())
        self.j.send(i)

    def result_accept(self):
        #accept
        pass

    def result_error(self):
        #400 no valid streams
        #400 profile not understood
        #403 forbidden: Offer Declined
        pass

class FileTransferSIHandler(IncomingFileTransfer):

    def __init__(self, si_handler, iq):
        self.si_handler = si_handler
        self.stanza = iq
        self.si_ft = SI_FileTransfer.from_iq(iq)
        self.bytestream = None
        self._lock = threading.RLock()

        if self.check_streams():
            #CAS: fix this with fail cases, i.e. check to see if this is a valid offer

            ft = self.si_ft
            self.numfiles = 1
            self.name     = ft.file.name
            self.size     = ft.file.size
            self.buddy    = self.si_handler.j.buddies[iq.get_from()]
            file_desc = unicode(ft.file.desc)
            IncomingFileTransfer.__init__(self)
            si_handler.j.hub.on_file_request(si_handler.j, self)

            self.on_get_buddy(self.buddy)

    @property
    def protocol(self):
        return self.si_handler.j

    def file_desc(self):
        return unicode(self.si_ft.file.desc)

    def decline(self, reason = None):
        self.si_handler.reject(self.stanza, reason)
        self.state = self.states.CANCELLED_BY_YOU
        IncomingFileTransfer.decline(self)

    @lock
    @if_not_done
    def cancel(self, state=None):
        #check if stream exists, and if our state is stransferring
        #find out other states and implement them.
        if state is None:
            state = self.states.CANCELLED_BY_YOU
        self.state = state

        if self.bytestream is not None:
            self.bytestream.close()

    def accept(self, _openfileobj):

        self.state = self.states.CONNECTING

        for stream_type in self.si_handler.supported_streams:
            if stream_type in self.si_ft.feature.possible_streams:
                selected = stream_type
                break
        else:
            assert False

        self._fileobj = _openfileobj
        self.filepath = path(_openfileobj.name)

        si_ft = SI_FileTransfer(self.si_ft.sid)
        si_ft.feature = Feature(selected_stream = selected)
        si_ft.file = File()

        self.bytestream = b = self.si_handler.supported_streams[selected](self.stanza)
        #bind events here
        b.bind("stream_connected", self.transferring)
        b.bind("stream_closed", self.stream_closed)
        b.bind("stream_connect_failed", self.stream_connect_failed)
        b.bind("stream_data_recieved", self.incoming_data)
        b.bind("stream_error", self.stream_error)

        #wrap result in feature ns elem
        self.si_handler.send_accept(self.stanza, si_ft)

    @lock
    @if_not_done
    def transferring(self):
        self.state = self.states.TRANSFERRING

    @lock
    @if_not_done
    def stream_connect_failed(self):
        self.state = self.states.CONN_FAIL
        self.cleanup()

    @lock
    @if_not_done
    def stream_error(self):
        self.state = self.states.CONN_FAIL_XFER
        self.cleanup()

    def cleanup(self):
        try: self._fileobj.close()
        except: pass
        self.unbind_all()

        if self.state != self.states.CANCELLED_BY_YOU:
            self.on_error()

    @lock
    @if_not_done
    def stream_closed(self):
        if self.completed == self.si_ft.file.size:
            try: self._fileobj.close()
            except: pass
            self.unbind_all()
            self._ondone()
        else:
            log.info('%r: Stream closed. Setting state to CANCELLED_BY_BUDDY and cleaning up.')
            self.state = self.states.CANCELLED_BY_BUDDY
            self.cleanup()

    def unbind_all(self):
        b = self.bytestream
        b.unbind("stream_connected", self.transferring)
        b.unbind("stream_closed", self.stream_closed)
        b.unbind("stream_connect_failed", self.stream_connect_failed)
        b.unbind("stream_data_recieved", self.incoming_data)

    def check_streams(self):
        """See if we can handle the request, if not, say so"""
        if set(self.si_ft.feature.possible_streams) \
            & set(self.si_handler.supported_streams):
            return True
        else:
            self.si_handler.respond_no_valid(self.stanza)
            return False

    def incoming_data(self, data):
        try:
            self._fileobj.write(data)
            self._setcompleted(len(data) + self.completed)
        except ValueError:
            with self._lock:
                assert self.state in done_states
            #file is dead, using an exception because try is free.
            # a lock is not needed because it's a file object

