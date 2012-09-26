from __future__ import with_statement
import sys
import random
import logging
import socket
import collections
import time

from threading import RLock
from traceback import print_exc

import hub
import common
import oscar

from oscar.Snactivator import Snactivator
from util import Storage, try_this, callsback, isgeneratormethod
from util.primitives.structures import unpack_named

log = logging.getLogger('oscar.sock')
#log.setLevel(logging.WARNING)

from struct import pack
from common import netcall

def _generate_flap_sequence_start():
    n = random.randint(0, sys.maxint)
    s = 0

    i = n
    while i:
        i >>= 3
        s = (s + i) % 0xFFFFFFFF

    return ((((0 - s) ^ (n & 0xFF)) & 7 ^ n) + 2) & 0x7FFF

def flap_sequence_number(start = 0):
    i = start
    while 1:
        yield i
        i += 1
        if i >= 0x8000:
            i = 1

def default_cb(*a, **kw):
    log.debug_s('Socket ignoring (%s, %s)', a, kw)

class OscarSocket(common.socket):
    flap_hdr_size = 6
    snac_hdr_size = 10
    id = 0x2A

    func_templ = \
    '''
    def %(name)s (self):
        print "%(name)s is not implemented!"
        print self.hdr
        print self.data
    '''

    def _repr(self):
        try:
            return repr(self.__oserver)
        except Exception:
            return '??'

    def __init__(self):
        common.socket.__init__(self)

        self.on_connect = default_cb
        self.on_incoming = default_cb
        self.on_close = default_cb

        self.cookie = None
        self.bos = False

        self.callbacks = collections.defaultdict(list)
        self.error_callbacks = collections.defaultdict(list)

        self.rate_lock = RLock()

        self.hdr = None
        self.buf = ''
        self.data = ''
        self.seq = flap_sequence_number(_generate_flap_sequence_start())
        self.req = flap_sequence_number(_generate_flap_sequence_start())
        self.rate_classes = []
        self.rates = {}
        self.rate_lvl_incr = False

        # At first, don't use rate limiting.
        self.snactivate = self._send_snac
        self.snactivator = None


    @callsback
    def connect(self, server, cookie = None, incoming = None, close = None, callback = None, bos = False):
        self.on_connect = callback or default_cb
        self.on_incoming = incoming or default_cb
        self.on_close = close or default_cb

        self.cookie = cookie
        self.bos = bos # True if this is the main connection

        self.set_terminator(self.flap_hdr_size)
        log.info('oscar socket connecting to %s', server)
        self.__oserver = server

        common.socket.connect(self, server, error=callback.error)

    def handle_error(self, e = None):
        if isinstance(e, socket.error):
            if self.on_close is not None:
                log.error('Socket error for %r, calling on_close (= %r): %r', self, self.on_close, e)
                self.on_close(self)
            else:
                log.info('handle_error in %r but on_close is None' % self)

        common.socket.handle_error(self, e)

    def test_connection(self):
        # send a keep alive packet
        try:
            self.send_flap(5)
        except Exception, e:
            print_exc()

            # usually will not fail, but if it does, we need to close now
            (self.on_close or default_cb)(self)

    def apply_rates(self, rate_classes, rate_groups):
        '''The socket init process obtains rate info from the server, and calls
        this function.'''

        with self.rate_lock:
            if not self.rate_classes:
                self.rate_classes = rate_classes
            else:
                for rates in rate_classes:
                    rates.pop('last_time', 0) # The format of the time provided by oscar servers is not compatible with the format we use locally.
                    self.rate_classes[rates.id-1].update(rates)

            self.rates.update(rate_groups)

        with self._lock:
            # Now use rate limiting.
            if self.snactivator is None:
                self.snactivator = Snactivator(self)
                self.snactivator.start()

            self.snactivate = self.snactivator.send_snac

    def calc_rate_level(self, rate_class):
        '''
        If we send a packet with the specified family and subtype right now,
        we would have the returned rate level, which is a tuple of the rate
        level (a number), and the last time we sent a packet.
        '''
        old_level = rate_class.current_level
        window = rate_class.window

        now = int(time.time())
        time_diff = (now - rate_class.last_time) * 1000
        new_level = min(int(((window-1) * old_level + time_diff)/window),
                        rate_class.max_level)
        return (new_level, now)

    def snac_rate_class(self, fam, sub, *a):
        try:
            return self.rate_classes[self.rates[(fam, sub)]-1]
        except KeyError:
            return None

    #figure out lock here!
    def _get_rate_lvls(self, rclass):
        return rclass.max_level, rclass.current_level, rclass.alert_level, \
            rclass.clear_level, rclass.window

    def time_to_send(self, s):
        'Returns the number of milliseconds this snac should be sent in.'

        fam, sub = s[0], s[1]
        rclass = self.snac_rate_class(fam, sub)

        ml, curl, al, clrl, w = self._get_rate_lvls(rclass)

        assert clrl >= al

        # don't use a threshold higher than we can reach
        threshold = min(ml, (al + ((clrl - al)*2)))

        with self.rate_lock:
            if ((curl < al) or self.rate_lvl_incr) and curl < threshold:
                self.rate_lvl_incr = True
            else:
                # We've hit (or are above the threshold, send now.
                self.rate_lvl_incr = False
                return 0

        k = 500.0
        step = ml / k
        wait = w * step + curl
        delta = rclass.last_time - int(time.time())
        to_send = delta + wait/1000

#        log.info('k = %r, ml = %r, step = %r, w = %r, curl = %r, wait = %r, last_time = %r, delta = %r, to_send = %r',
#                 k, ml, step, w, curl, wait, rclass.last_time, delta, to_send)

        return max(0, to_send)

    #########################
    # Begin AsynSocket interface

    def handle_connect(self):
        log.debug('connected')

    def handle_close(self):
        log.info('closed. calling on_close=%r', self.on_close)
        (self.on_close or default_cb)(self)
        self.close()

    def handle_expt(self):
        log.warning('oob data')
        self.handle_close()

    def collect_incoming_data(self, data):
        if self.hdr is None:
            self.buf += data
        else:
            self.data += data

    def set_terminator(self, term):
        assert term != 0
        common.socket.set_terminator(self, term)

    def found_terminator(self):
        try:
            if self.hdr is None:
                with self._lock:
                    self.hdr = unpack_named('!BBHH', 'id', 'chan', 'seq', 'size', self.buf)
                    self.buf = ''
                    if self.hdr.size == 0:
                        # SNACs without any data will have no more data. Handle them immediately,
                        # and DONT set the terminator to 0.
                        self.found_terminator()
                    else:
                        self.set_terminator(self.hdr.size)
            else:
                try:
                    assert len(self.data) == self.hdr.size
                    getattr(self, 'channel_%d' % self.hdr.chan, self.unknown_channel)()
                except oscar.errors, e:
                    # pass oscar errors up to the user
                    hub.get_instance().on_error(e)
                except Exception:
                    log.critical("Error handling FLAP 0x%x (DATA: %s) " %
                                 (self.hdr.seq, repr(self.data)))
                    raise
                finally:
                    with self._lock:
                        self.hdr, self.data = None, ''
                        self.set_terminator(self.flap_hdr_size)
        except socket.error:
            # reraise socket errors, assuming we are disconnected
            raise
        except Exception, e:
            # all other exceptions may not be fatal to the connection
            log.critical('%r had a non-socket error', self)

            print_exc()
        finally:
            if self.terminator == 0:
                log.critical('terminator was 0, closing socket!')
                self.handle_close()

    def close(self):
        self._cleanup()
        common.socket.close(self)

    def _cleanup(self):
        self.on_incoming = None
        self.on_close = None

        if self.snactivator:
            self.snactivator.stop()
            del self.snactivator
            self.snactivator = None

    def close_when_done(self):
        self._cleanup()
        try:
            self.send_flap(0x04)
        except socket.error, (errno, desc):
            if errno not in [9, 10054, 10057]:
                # 9 is bad file descriptor, means socket is closed
                # and cannot be written to, something quite likely
                # when closing.

                # 10057 is "socket is already closed"

                # 10054 is connection reset by peer, something
                # to be expected if both ends are closing
                raise
        finally:
            common.socket.close_when_done(self)

    def send_flap(self, chan, data=''):
        log.debug_s('Sending FLAP on channel %d, data is < %r >', chan, data)
        netcall(lambda: common.socket.push(self, pack('!BBHH', self.id, chan, self.seq.next(), len(data)) + data))

    # end AsyncSocket interface
    #########################

    def send_snac(self, fam, sub, data='', priority=5, req=False, cb=None, *args, **kwargs):
        '''
        Sends a snac.

        If req is True, cb must be a callable which will be invoked later with the
        specifed *args and **kwargs--this function will be called when a SNAC with
        the correct request ID comes back from the network.
        '''
        req_id = self.req.next()
        if req:
            # don't leak memory by accumulating lists in the defaultdict
            remove_empty_lists(self.callbacks)
            remove_empty_lists(self.error_callbacks)

            if cb:
                self.callbacks[req_id].append((cb, args, kwargs))

            err_cb = kwargs.pop('err_cb', None)
            if err_cb is not None:
                self.error_callbacks[req_id].append((err_cb, args, kwargs))

        # Fire the Snactivator! (maybe)

        snac = (fam, sub, req_id, data)
        if self.snactivator is None:
            self._send_snac(snac, priority)
        else:
            self.snactivator.send_snac(snac, priority)

    send_snac_first = send_snac

    def _send_snac(self, (fam, sub, req_id, data), priority=None):

        server_version = getattr(self, 'server_snac_versions', {}).get(fam, None)
        if server_version is None:
            version = None
        else:
            my_version = getattr(getattr(oscar.snac, 'family_x%02x' % fam, None), 'version', None)
            if (my_version == server_version) or my_version is None:
                version = None
            else:
                version = my_version

        flags = 0 if version is None else 0x8000

        if version:
            ver_tlv = oscar.util.tlv(1,2,version)
            ver_tlv = pack('!H', len(ver_tlv))  + ver_tlv
        else:
            ver_tlv = ''

        log.debug('sending snac: fam=0x%02x, sub=0x%02x, req=0x%04x', fam, sub, req_id)
        log.debug_s('\t\tdata=%r', data)
        to_send = pack('!HHHI', fam, sub, flags, req_id) + ver_tlv + data
        self.send_flap(0x02, to_send)

        # Set rate class's last time
        if (fam, sub) in self.rates:
            rclass = self.snac_rate_class(fam,sub)
            rclass.current_level, rclass.last_time = self.calc_rate_level(rclass)
            clevel = rclass.current_level
            i = sorted(list(self._get_rate_lvls(rclass)) + [clevel]).index(clevel)

            try:
                names = ('disconnect','limit','alert','clear', 'max')[i:i+2]
                hi, lo = names[0], names[-1]
                if not (hi == 'clear' and lo == 'max'):
                    log.debug('current rate level is: %s < %d < %s', hi, clevel, lo)
            except Exception:
                import traceback
                traceback.print_exc()

    def channel_1 (self):
        log.info('got channel 1 (new connection) flap')
        to_send = pack('!I', 1)
        if self.cookie is not None:
            to_send += oscar.util.tlv(0x06, self.cookie)
            with self._lock: self.cookie = None

#        else:
#            to_send += oscar.util.tlv(0x8003, 4, 0x100000)

        self.send_flap(0x01, to_send)
        try:
            (self.on_connect or default_cb)(self)
        except StopIteration:
            pass

        del self.on_connect
        self.on_connect = None

    def channel_2(self):
        hdr, data = unpack_named('!HHHI',
                                 'fam', 'sub', 'flags', 'req',
                                 self.data[:self.snac_hdr_size]), self.data[self.snac_hdr_size:]
        log.debug('got channel 2 (snac data) flap. fam=0x%02x, sub=0x%02x, req=0x%04x', hdr.fam, hdr.sub, hdr.req)
        log.debug_s('\t\tdata=%r', data)

        snac = Storage(hdr=hdr, data=data)

        if snac.hdr.flags & 0x8000:
            log.debug('got version data for snac, trimming')
            snac_ver_fmt = (('tlvs_len', 'H'),
                            ('tlvs', 'tlv_list_len', 'tlvs_len')
                            )
            tlvs_len, ver, snac.data = oscar.util.apply_format(snac_ver_fmt, snac.data)

        if self.is_ignored(snac):
            log.debug('Ignored snac: %r', snac)
            return

        cbs  = self.callbacks
        req_id = snac.hdr.req

        try:
            if req_id in cbs:
                call_later = []
                try:
                    for func, args, kwargs in cbs[req_id]:
                        if snac.hdr.flags & 0x0001:
                            call_later.append((func, args, kwargs))
                        if isgeneratormethod(func):
                            assert not kwargs
                            try: func((self, snac)+args)
                            except StopIteration: pass
                        else:
                            func(self, snac, *args, **kwargs)
                finally:
                    with self._lock:
                        if not call_later:
                            cbs.pop(req_id)
                        else:
                            cbs[req_id] = call_later

            else:
                if self.on_incoming is None:
                    default_cb(self, snac)
                elif isgeneratormethod(self.on_incoming):
                    try: self.on_incoming((self, snac))
                    except StopIteration: pass
                    except Exception:
                        print repr(snac)
                        raise
                else:
                    self.on_incoming(self, snac)
        except oscar.snac.SnacError, e:
            if self.handle_error_callbacks(snac, e):
                log.info('ignoring SnacError because it was handled by a callback')
                return

            (fam, _), (sub, _) = e.args[:2]
            if (fam, sub) in self.ignored_errors:
                log.error('SNAC error occured and was ignored: %r', snac)
            else:
                # tell user
                hub.get_instance().on_error(e)

    def handle_error_callbacks(self, snac, exc):
        handled = False
        if snac.hdr.req in self.error_callbacks:
            for func, args, kwargs in self.error_callbacks[snac.hdr.req]:
                handled = handled or func(snac, exc, *args, **kwargs)

        return handled

    def is_ignored(self, snac):
        if (snac.hdr.fam, snac.hdr.sub) in self.ignored_snacs:
            return True

    ignored_snacs= [(0x01, 0x13),        # MOTD
                     ]

    ignored_errors = [(0x01, 0x0d), # Request denied- usually for requesting buddy icon service
                      (0x15, 0x02), # ICQ family rate limit
                      (0x13, 0x01), # SSI invalid snac header error, seems to happen on 'edit start' packets (0x13, 0x11)
                      (0x15, 0x05), # ICQ service requested unavailable
                      (0x13, 0x05), # SSI service requested unavailable
                      (0x07, 0x15), # Admin service error, "invalid account".
                      ]

    def channel_4 (self):
        log.info('got channel 4 (close connection) flap')
        fmt = (('tlvs', 'tlv_dict'),)
        tlvs, data = oscar.unpack(fmt, self.data)
        if try_this(lambda:ord(tlvs[0x09][-1]), False):
            (self.on_close or default_cb)(self, oscar.protocol.Reasons.OTHER_USER)
        else:
            (self.on_close or default_cb)(self)

        del self.on_close
        self.on_close = None

        self.close_when_done()

    def unknown_channel(self):
        log.warning('Unknown channel for data: %r', self.data)

def remove_empty_lists(mapping):
    for k, v in list(mapping.iteritems()):
        if not v:
            mapping.pop(k)

