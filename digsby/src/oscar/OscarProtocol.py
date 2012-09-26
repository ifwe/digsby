'''

OSCAR protocol

'''
from __future__ import with_statement

import logging
import traceback

from hashlib import md5
import hub, util.observe as observe, common, util
import random, sys
from common import profile, netcall
from common.actions import ActionMeta, action

import oscar
from oscar import OscarException
import oscar.snac as snac
import oscar.ssi as ssi

from util import callsback, Timer
from util.primitives.error_handling import traceguard
from util.primitives.funcs import do
from util.rtf import rtf_to_plain

import oscar.rendezvous.filetransfer as filetransfer

from traceback import print_exc
from datetime import datetime
import time
import struct
from oscar.api import ICQ_API, AIM_API, get_login_cookie
from util.threads.threadpool2 import threaded

log = logging.getLogger('oscar'); info = log.info

hub = hub.get_instance()

aim_only = lambda self, *a: None if self.icq else True
icq_only = lambda self, *a: True if self.icq else None

AVAIL_MAX_LEN = 250
SERVICE_REQUEST_TIME_SECS = 30 * 60

class OscarProtocol(common.protocol):
    __metaclass__ = ActionMeta

    USE_NEW_MD5   = True

    name          = 'oscar'
    client_string = 'ICQ Client' #"Digsby v0.99 alpha"

    def _get_locale_info(self, key, default):
        try:
            return getattr(hub, 'get_%s' % key)().encode('utf-8')
        except Exception, e:
            log.error('There was an error getting the %r for oscar: %r', key, e)
            print_exc()
            return default

    def get_lang(self):
        return self._get_locale_info('language', 'en')

    def get_country(self):
        return self._get_locale_info('country', 'us')

    def get_encoding(self):
        return 'utf-8'

    lang          = property(get_lang)
    country       = property(get_country)
    encoding      = property(get_encoding)

    is_ordered    = True

    max_icon_bytes = 7168
    max_icon_size  = (48, 48)
    icon_formats = ['JPEG', 'BMP', 'GIF'] # server rejects PNG

    bots = common.protocol.bots | set(['aolsystemmsg', 'twitterim'])

    supports_group_chat = True

    def email_hint(self, contact):
        if self.icq: return ''
        else:        return contact.name + '@aol.com'

    contact_order = True

    def __init__(self, username, password, user, server, login_as = 'online', protocol = None, **extra_args):
        common.protocol.__init__(self, username, password, user)

        #before init_buddy_vars, so that we're not still "oscar" when the self buddy is created.

        if protocol == 'icq':
            self.icq = True
            self.name = 'icq'
        elif protocol == 'aim':
            self.icq = False
            self.name = 'aim'
        else:
            assert protocol is None
            try:
                int(self.username)
            except Exception:
                self.icq = False
                self.name = 'aim'
            else:
                self.icq = True
                self.name = 'icq'
        if self.icq:
            self.icq_number = extra_args.pop('icq_number', None)
            if self.icq_number is not None:
                self.username = self.icq_number

        self.log = log

        self.init_buddy_vars()
        self.disconnected = False

        self.init_server = server
        self.status = login_as
        self.user = user

        self._search_disclosure = sentinel

        self.icq_req_cbs = {}

        self.block_unknowns = extra_args.get('block_unknowns', False)

        self.webaware      = extra_args.get('webaware', False)
        self.auth_required = extra_args.get('auth_required', False)

        self._keepalive_timer = Timer(common.pref('oscar.keepalive', type = int, default = 30),
                                      self.on_keepalive)

        self.endpoints = None

        self.block_url_requests = extra_args.get('block_url_requests', True)

    def has_buddy_on_list(self, buddy):
        bname = oscar._lowerstrip(buddy.name)
        if bname in self.buddies:
            for group in self.root_group:
                for listbuddy in group:
                    if oscar._lowerstrip(listbuddy.name) == bname and buddy.service == listbuddy.service:
                        return True

    def init_buddy_vars(self):
        self.buddies = oscar.buddies(self)
        self.self_buddy = self.buddies[self.username]

        self.sockets = {}
        self.conversations = observe.observable_dict()
        self.ssimanager = ssi.manager(self)
        self.root_group = self.ssimanager.ssis.root_group

    def get_login_info(self, pass_hash):
        info = self.client_info()

        data = ((1, oscar._lowerstrip(self.username)),
                (0x3, self.client_string),
                (0x25, pass_hash),
                (0x16, 2, info[0]),        # client id
                (0x17, 2, info[1]),        # client major version
                (0x18, 2, info[2]),        # client minor version
                (0x19, 2, info[3]),        # client lesser version
                (0x1a, 2, info[4]),        # client build number
                (0x14, 4, info[5]),        # distribution number
                (0x0f, self.lang),         # client language
                (0x0e, self.country),      # client country
                )

        if self.USE_NEW_MD5:
            data += ((0x4c, ''), # new authentication method?!
                     )

        if self.icq:
            pass
        else:
            data += ((0x4a, 1, True),
                     )

        return data
    def client_info(self):
        if self.icq:
            info = (0x010a, 0x06, 0x05, 0, 0x03ed, 0x7537)  # ICQ6.5
            #info = (0x010a, 0x14, 0x34, 0, 0x0c18, 0x043d)  # ICQBasic
            #info = (0x010a, 0x06, 0x00, 0x00, 0x1bb7, 0x7535) # ICQ6.0
            #info = (0x010a, 0x07, 0x00, 0, 0x0410, 0x7538)
            #info = (0x010a, 0x14, 0x34, 0, 0x0bb8, 0x043d)
        else:
            info = (0x0109, 0x05, 0x09, 0, 0x0f15, 0x0000)

        return info

    def on_keepalive(self):
        def do_keepalive(socket): #this is here to pull the closure away from the for loop below
            log.info('sending keepalive on %r', socket)
            # Channel 5 flap is keep alive
            netcall(lambda: socket.send_flap(0x5, ''))

        for socket in set(filter(lambda x: isinstance(x, oscar.socket), self.sockets.values())):
            do_keepalive(socket)

        for k in self.sockets:
            if isinstance(self.sockets[k], SnacQueue):
                if k in (1, 'bos',):
                    continue
                log.info('requesting service %r', k)
                self.service_request(k)

        self._keepalive_timer.start()

    @property
    def caps(self):
        from common import caps

        return [caps.INFO,
                caps.IM,
                caps.FILES,
                caps.EMAIL,
                caps.SMS,
                caps.BLOCKABLE,
                caps.VIDEO]

    def __repr__(self):
        return '<OscarProtocol %s (%s)>' % (self.username, self.state)

    @action(lambda self, *a, **k: True if self.state == self.Statuses.OFFLINE else None)
    def Connect(self, invisible = False):
        log.info('connecting %s (as %s)...', self, 'invisible' if invisible else 'available')

        # set the invisible flag in the self buddy if necessary.
        self.self_buddy.invisible = invisible

        self.change_state(self.Statuses.CONNECTING)
        self._icq_check()

    def _icq_number(self):
        try:
            int(self.username)
        except Exception:
            pass
        else:
            return self.username
        return self.icq_number

    def _icq_check(self):
        if self.icq:
            icq_number = self._icq_number()
            if not icq_number:
                from .api import get_login_data, ICQ_API
                from util import callbacks
                callbacks.callsback(get_login_data)(self.username, self.password, ICQ_API,
                                                    success = self._icq_check_success,
                                                    error = self._icq_check_fail)
            else:
                self._set_icq_username(icq_number)
                self._icq_check_done()
        else:
            self._icq_check_bypass()

    def _icq_check_success(self, req, ret=None):
        if ret is None:
            ret = req
        try:
            data = ret.read()
            import simplejson
            data = simplejson.loads(data)
            if self.icq:
                username = data['response']['data']['loginId']
                acct = self.account
                self.icq_number = acct.icq_number = username
                acct.update()
                self._set_icq_username(username)
        except Exception:
            print_exc()
        self._icq_check_done()

    def _set_icq_username(self, username):
        if username == self.username:
            return
        self_buddy_name = self.self_buddy.name
        self.buddies[username] = self.self_buddy
        self.self_buddy.name = username
        self.username = username
        del self.buddies[self_buddy_name]

    def _icq_check_fail(self, *a, **k):
        self._icq_check_done()

    def _icq_check_done(self):
        if getattr(self, 'endpoints', None) is None:
            self.endpoints = self.endpoint_generator()
        threaded(self.get_cookie)(success = lambda resp: netcall(lambda: self._reconnect_icq(resp)),
                                  error = lambda *_a: netcall(self._icq_check_bypass))

    def _icq_check_bypass(self):
        if getattr(self, 'endpoints', None) is None:
            self.endpoints = self.endpoint_generator()
        self.server = self.endpoints.next()
        self._reconnect()

    def get_cookie(self):
        if self.icq:
            api = ICQ_API
        else:
            api = AIM_API
        #async goes here!!!!~!
        return get_login_cookie(self.username, self.password, api)

    def _reconnect_icq(self, resp):
        try:
            data = resp['response']['data']
            host = data['host']
            port = data['port']
            cookie = data['cookie'].decode('b64')
        except Exception:
            traceback.print_exc()
            return self._icq_check_bypass()
        else:
            #this is used as a flag for "don't connect anywhere else",
            # sometimes interpreted as "we've already connected" or vice versa
            self.endpoints = None
        if hasattr(self,'cancel'):
            log.critical('cancelled connect')
            self.set_offline(None)
            return
        if self._keepalive_timer is None:
            self._keepalive_timer = Timer(45, self.on_keepalive)
        self._keepalive_timer.start()
        sck = oscar.socket()
        self.sockets['bos'] = sck
        self.server = (host, port)
        sck.connect((host, port),
            cookie,
            success = self.init_session,
            close = self.close_socket,
            bos = True)

    def _reconnect(self):
        #HAX: mcd
        if hasattr(self,'cancel'):
            log.critical('cancelled connect')
            self.set_offline(None)
            return
        if self._keepalive_timer is None:
            self._keepalive_timer = Timer(45, self.on_keepalive)
        self._keepalive_timer.start()
        sck = oscar.socket()
        self.sockets['bos'] = sck
        sck.connect(self.server,
                    success = self.auth_process,
                    error = lambda *a: self.logon_err(sck, *a),
                    close = self.close_socket,
                    bos   = False)

    def endpoint_generator(self):
        yield self.init_server
        default_host = 'login.icq.com' if self.icq else 'login.oscar.aol.com'
        hosts = (self.init_server[0],)
        if default_host not in hosts:
            hosts = hosts + (default_host,)

        for host in hosts:
            if self.init_server[1] != 443:
                yield (host,443)
            yield (host, 5190)
            yield (host, 80)
            yield (host, 25)
            yield (host, 21)

    def _close_sockets(self):
        info('closing sockets')
        do(sock.close() for sock in set(self.sockets.values()))
        self.sockets.clear()

    def Disconnect(self, reason=None):
        return netcall(lambda: self._Disconnect(reason))

    #@action(lambda self, *a, **k: (self.state != self.Statuses.OFFLINE) or None)
    def _Disconnect(self, reason=None):

        if self.disconnected:
            log.info('Already disconnected %r.', self)
            return

        # mcd: HAX!
        log.info('reason was: %s, state was: %s', reason, self.state)
        if reason is None or self.state != self.Statuses.CONNECTING:
            self.cancel = object()
        if self._keepalive_timer is not None:
            self._keepalive_timer.stop()
            self._keepalive_timer = None

        log.info('disconnecting...')
        if self.state == self.Statuses.OFFLINE:
            self._close_sockets()
            return

        if getattr(self, 'endpoints', None) is None:
            log.warning('offline reason: %r', self.offline_reason)
            self.set_offline(reason)
            do_reconnect = False
        else:
            try:
                self.server = self.endpoints.next()
            except StopIteration:
                self.endpoints = None
                log.warning('offline reason: %r', reason)
                self.set_offline(reason)
                do_reconnect = False
            else:
                do_reconnect = True

        cs = self.conversations

        info('exiting conversations')
        do(c.exit() for c in set(cs.values()))
        cs.clear()

        self._close_sockets()

        info('signing off buddies')
        for buddy in self.buddies.values():
            buddy.protocol = None
            buddy.observers.clear()
            buddy.status = 'offline'

        self.buddies.observers.clear()
        self.buddies.clear()
        self.buddies.kill()

        if self.root_group is not None:
            for group in self.root_group:
                group.protocol = None
                group.observers.clear()

            self.root_group.protocol = None
            self.root_group.observers.clear()
            self.root_group = None

        common.protocol.Disconnect(self)

        if do_reconnect:
            self.init_buddy_vars()
            if self.icq:
                self._icq_check()
            else:
                self._reconnect()
        else:
            log.info('disconnected')
            self.disconnected = True

            if False:
                # disabled for now, since some GUI elements hold onto
                # buddy objects temporarily.
                self._cleanup_references()

    def _cleanup_references(self):
        '''
        this shouldn't technically be necessary, but OscarProtocol leaks without it.
        TODO: more investigating as to why this is the case.
        '''

        with traceguard:
            self.ssimanager.o = None
            self.ssimanager = None
            self.self_buddy.protocol = None
            del self.self_buddy
            self.buddies.protocol = None

    def close_socket(self, sock, reason=None):
        log.info('close_socket for %r with reason %r', sock, reason)
        sockets = self.sockets

        if reason is None:
            reason = self.Reasons.CONN_LOST

        isbos = sock.bos
        log.info('  is bos? %r', isbos)

        dead_fams = []
        for key, sck in sockets.items():
            if sck is sock:
                sockets.pop(key)
                dead_fams.append(key)
        log.info('  it was for these services:  %r', dead_fams)

        if ((isbos or not sockets or 'bos' not in sockets)
            and (self.state != self.Statuses.OFFLINE or reason == self.Reasons.OTHER_USER)):
            log.info('  no bos socket, disconnecting')
            self.Disconnect(reason)
        else:
            log.info('  not calling disconnect, but sending a keep alive')

            if 'bos' in self.sockets:
                # send a keep alive to make sure BOS is still alive
                try:
                    self.sockets['bos'].send_flap(5)
                except Exception, e:
                    # the keep alive won't be sent immediately, but catch errors here anyways
                    log.critical('could not send keep alive')
                    print_exc()
                    self.Disconnect(reason)

        sock.close_when_done()

    def logon_err(self, sock=None, *a):
        if sock is not None:
            sock.close()

        log.critical('Could not connect to authentication server: %r', sock)

        rsn = self.Reasons.CONN_FAIL
        self.Disconnect(rsn)
        raise LoginError

    @property
    def block_list(self):
        return self.ssimanager.blocklist()

    @property
    def ignore_list(self):
        return self.ssimanager.ignorelist()

    @callsback
    def send_sms(self, sms_number, message, callback = None):
        'Send an SMS message to sms_number.'

        from common.sms import normalize_sms
        sms_number = normalize_sms(sms_number)

        message = message.encode('utf-8')
        snd = snac.snd_channel1_message

        # send the message
        auto = False
        fam, sub, data = snd(self, '+' + sms_number, message, save=(not auto), auto=auto, req_ack = True)
        self.send_snac(fam, sub, data, priority=4)
        callback.success()

    def send_file(self, buddy, filestorage):
        '''
        Sends a file to a buddy.

        fileobj must be a file like object.
        '''
        if hasattr(buddy, 'name'):
            buddy = buddy.name

        if self.buddies[buddy] == self.self_buddy:
            raise OscarException("You can't send files to yourself.")

        return filetransfer.send(self, buddy, filestorage)

    def send_folder(self, buddy, filestorage):
        'Sends a folder to a buddy.'

        self.send_file(buddy, filestorage)

    def direct_connect(self, buddy):
        if hasattr(buddy, 'name'):
            buddy = buddy.name

        import oscar.rendezvous
        return oscar.rendezvous.directconnect(self, buddy)

    def auth_requested(self, bname, msg=''):

        b = self.buddies[bname]

        if self.auth_required:
            if self.block_url_requests and util.linkify(msg) != msg:
                log.info("Auth request from %r was blocked because it has a URL in it. Message: %r", bname, msg)
                self.authorize_buddy(b, False)
                return
            self.hub.authorize_buddy(self, b, msg)
        else:
            self.authorize_buddy(b, True)

    def authorize_buddy(self, buddy, authorize, _username_added=None):
        auth_snac = snac.x13_x1a(buddy,
#                                 'I like friends. p.s. get digsby'
#                                 if authorize else
#                                 "I'll be your friend when you get digsby",
                                 '',
                                 authorize)
        self.send_snac('bos', *auth_snac)

    @util.gen_sequence
    def auth_process(self, sock):
        try:
            self.endpoints.close()
            self.endpoints = None
        except AttributeError:
            assert False, "Why wasn't there an 'endpoints' attribute?!"
        me = (yield None); assert me

        old_incoming, sock.on_incoming = sock.on_incoming, me.send

        self.change_state(self.Statuses.AUTHENTICATING)

        try:
            sock.send_snac(*snac.x17_x06(self.username))
            key = self.gen_incoming((yield None))

            if self.USE_NEW_MD5:
                pw_to_hash = md5(self.password).digest()
            else:
                pw_to_hash = self.password

            pass_hash = md5(key + pw_to_hash +
                            "AOL Instant Messenger (SM)").digest()
            sock.send_snac(*snac.x17_x02(self, pass_hash))
            server_str, cookie = self.gen_incoming((yield None))
        except OscarException, e:
            try:
                if e.code in (0x1, 0x4, 0x5):
                    r = self.Reasons.BAD_PASSWORD
                elif e.code in (0x18, 0x1D):
                    r = self.Reasons.RATE_LIMIT
                else:
                    r = self.Reasons.CONN_FAIL
                log.critical('doing disconnect with reason %r', r)
                self.Disconnect(r)
            except common.ActionError:
                log.critical("couldn't call disconnect because of an action error. should really fix that...")
            return

        host, port = server_str.split(":")
        port = int(port)

        sock.on_incoming = old_incoming
        sock.close_when_done()
        sck = oscar.socket()
        self.sockets['bos'] = sck
        sck.connect((host, port),
                    cookie,
                    success = self.init_session,
                    close = self.close_socket,
                    bos = True)


    @util.gen_sequence
    def init_session(self, sock):
        '''
        This is just a wrapper around init_socket that sets flags
        appropriately
        '''
        me = (yield None); assert me
        sock.on_incoming = me.send
        _sock, snac = (yield None)

        while (snac.hdr.fam, snac.hdr.sub) != (0x01, 0x03):
            log.info('Got unexpected snac for socket initialization, ignoring it: %r', snac)
            _sock, snac = (yield None)

        self.init_socket((_sock,snac))

    @util.gen_sequence
    def init_socket(self, (sock, first_snac)):
        me = (yield None); assert me
        log.info('first snac = %r', first_snac)
        serv_families = self.incoming(sock, first_snac)

        sock.on_incoming = me.send
        sock.send_snac(*snac.x01_x17(self, serv_families, sock), req=True, cb=me.send)

        while True:
            sck, snc = (yield None)
            val = self.gen_incoming((sck, snc))
            if (snc.hdr.fam, snc.hdr.sub) == (0x01, 0x18):
                break

        continue_ = val

        if not continue_:
            raise LoginError(['\xff'], 'Error when initializing socket.')

        def when_done():
            sock.send_snac_first(*snac.x01_x02(serv_families))

            # connect any pending chat sockets
            serv_families.extend(k for k in self.sockets.iterkeys()
                    if oscar.util.is_chat_cookie(k))

            for fam in serv_families:
                if isinstance(self.sockets[fam], SnacQueue):
                    q = self.sockets.get(fam, None)
                    if q is None:
                        continue

                    assert hasattr(q, 'sock') and q.sock is sock
                    q.flush()
                    self.sockets[fam] = q.sock

            if self.state != self.Statuses.ONLINE:
                self.get_search_response()
                #self.send_snac(*snac.x01_x1e(self))
                self.change_state(self.Statuses.ONLINE)
                self.request_offline_messages()

            log.info('%r done logging in. online and all SNAC families set up.', self)

            for buddy in self.buddies.values():
                if buddy._status == 'unknown':
                    buddy._status = 'offline'

        ready_counter = util.CallCounter(len(serv_families), when_done)

        for family in serv_families[:]:
            if not self.icq and family == 0x15:
                ready_counter._trigger -= 1
                continue

            fam_init = getattr(snac, 'x%02x_init' % family, None)
            if fam_init is None:
                log.error('Don\'t know about oscar family %r, counting it as ready.', family)
                ready_counter._trigger -= 1
                try:
                    serv_families.remove(family)
                except ValueError:
                    pass
            else:
                old_counter = ready_counter._trigger
                try:
                    fam_init(self, sock, ready_counter)
                except Exception:
                    traceback.print_exc()
                    log.error('Error initializing oscar family %r, counting it as ready.', family)
                    if ready_counter._trigger == old_counter:
                        ready_counter -= 1

        # send client ready
        sock.on_incoming = self.incoming

    @util.gen_sequence
    def service_request(self, service_id, parent=None):
        me = (yield None); assert me

        if service_id in self.sockets:
            assert isinstance(self.sockets[service_id], SnacQueue)

        sock_id = service_id

        if isinstance(service_id, tuple):
            raise ValueError('I think you forgot to splat a snac...')

        if isinstance(service_id, basestring):
            assert service_id != 'bos'
            service_id = 0x0e # chat

        assert isinstance(service_id, int)

        self.send_snac('bos', *snac.x01_x04(sock_id), req=True, cb=me.send)

        log.info('Requesting service with id: %r', service_id)
        try:
            s_id, address, cookie = self.gen_incoming((yield None))
        except (TypeError, ValueError):
            log.error('Error getting service %r', service_id)
            self.sockets[sock_id] = DisabledSocket(sock_id, time.time())
            return

        assert s_id == service_id

        server = util.srv_str_to_tuple(address, self.server[-1])
        self.connect_socket(server, cookie, [sock_id], parent)

    @util.gen_sequence
    def connect_socket(self, server, cookie, sock_ids, parent=None, bos = False):
        me = (yield None); assert me
        sock = oscar.socket()
        sock.connect(server,
                     cookie,
                     success=me.send,
                     incoming=me.send,
                     error=RedirectError,
                     close = self.close_socket,
                     bos = bos)
        yield None # pause for socket to connect

        #give first packet to init socket
        _sock, snac = (yield None)
        while (snac.hdr.fam, snac.hdr.sub) != (0x01, 0x03):
            log.info('Got unexpected snac for socket initialization, ignoring it: %r', snac)
            _sock, snac = (yield None)

        self.init_socket((_sock,snac))

        #sock.on_incoming = self.incoming
        for sock_id in sock_ids:
            if sock_id in self.sockets:
                if isinstance(self.sockets[sock_id], SnacQueue):
                    self.sockets[sock_id].sock = sock
                else:
                    self.sockets[sock_id] = sock
            else:
                self.sockets[sock_id] = SnacQueue(sock)
        #sock.on_close = self.close_socket
        if parent is not None:
            parent.send(sock)

    def send_snac_cb(self, snac, cb):
        self.send_snac(*snac)

    def send_snac(self, sock_id, *args, **kwargs):
        if isinstance(sock_id, int):
            args = (sock_id,) + args

        def request(sock_id):
            self.sockets[sock_id] = SnacQueue()
            self.service_request(sock_id)

        if sock_id not in self.sockets:
            if sock_id == 'bos':
                log.info('  no bos socket for send_snac, disconnecting')
                self.Disconnect(self.Reasons.CONN_LOST)
            else:
                log.debug('requesting service %r', sock_id)
                request(sock_id)

        # if we've got a DisabledSocket for this service, and enough time
        # has passed, try re-requesting.
        if getattr(self.sockets[sock_id], 'should_rerequest', False):
            request(sock_id)

        log.debug_s('sending snac to %r, snac args = %r, %r', self.sockets[sock_id], args, kwargs)
        self.sockets[sock_id].send_snac(*args, **kwargs)

    def gen_incoming(self, (s, snac)):
        return self.incoming(s, snac)

    def incoming(self, sock, snac):
        log.debug('incoming: calling snac.x%02x_x%02x', snac.hdr.fam, snac.hdr.sub)
        f = getattr(oscar.snac, 'x%02x_x%02x' % (snac.hdr.fam, snac.hdr.sub), None)
        if f is None:
            return log.warning('%r got an unknown snac: %r', self, snac)
        else:
            return f(self, sock, snac.data)

    def pause_service(self, sock, fam_list):
        if not fam_list:
            families = [s_id for (s_id, s) in self.sockets.items()
                        if s is sock]

        sock.send_snac(*snac.x01_x0c(fam_list))

        q = SnacQueue(sock)

        for id, s in self.sockets.items():
            if s is sock: self.sockets[id] = q

    def group_for(self, contact):
        'Returns the group name the specified contact is in.'

        return self.ssimanager.ssis[contact.id[0]].name.decode('utf-8', 'replace')

    def unpause_service(self, sock, fam_list):
        if not fam_list:
            families = [s_id for (s_id, s) in self.sockets.items()
                        if s.sock is sock]

        sock.send_snac(*snac.x01_x0c(fam_list))

        q = self.sockets[families[0]]
        for fam in families:
            assert q is self.sockets[fam] and q.sock is sock
            self.sockets[fam] = sock

        q.flush()

    def incoming_message(self, userinfo, message, is_auto_response=False, offline=False, timestamp=None, html=True):
        log.info_s('Got a message: %r', (userinfo, message, is_auto_response, offline, timestamp, html))
        screenname = userinfo.name.lower().replace(' ','')

        if isinstance(userinfo, type(self.self_buddy)):
            b = userinfo
        else:
            b = self.buddies[screenname]
            b.update(userinfo)

        try:
            c = self.conversations[screenname]
        except KeyError:
            c = self.conversations.setdefault(screenname, oscar.conversation(self))

        if screenname not in c:
            c.buddy_join(screenname)
        if self.self_buddy.name not in c:
            c.buddy_join(self.self_buddy.name)

        self._forward_message_to_convo(c, b, message,
            is_auto_response=is_auto_response,
            offline=offline,
            timestamp=timestamp,
            html=html,
            screenname=screenname)

    def _forward_message_to_convo(self, convo, buddy, message, is_auto_response=False, offline=False, timestamp=None, html=True, screenname=None):
        b = buddy
        c = convo

        if screenname is None:
            screenname = b.name

        client = b.guess_client()
        _test_message = message.strip().upper()
        has_html_tags = lambda: _test_message.startswith('<HTML') and _test_message.endswith('</HTML>')

        if not (client == 'mobile' and is_auto_response): # AIM servers send an HTML message auto-response when you send a message to a phone.
            if b.capabilities and not b.get_sends_html_messages(convo.ischat):
                if not (client == 'mobile' and has_html_tags()):
                    log.info('Overriding "html" for this message because the buddy doesn\'t send html messages. (b.guess_client() == %r)', client)
                    html = False
        if any(_x in client for _x in ('miranda', 'ebuddy', 'digsby')) and b.sends_html_messages:
            # miranda doesn't know how to use html capabilities for messages.
            html = True

        # offline messages may come in from buddies we don't yet have capabilities for. cheat and look for <HTML>
        # Also, some TERRIBLE AWFUL clients like lotus sametime don't send any capabilities.
        if client == 'unknown' and has_html_tags():
            log.info('overriding HTML to be True for this message, because client is unknown and it starts and ends with <html> tags')
            html = True

        if not html:
            log.info('xml encoding message')
            message = message.encode('xml')
            log.info_s('encoded message: %r', message)

        if timestamp is not None:
            if isinstance(timestamp, str):
                with traceguard:
                    posixtime = struct.unpack('!I', timestamp)[0]
                    timestamp = datetime.utcfromtimestamp(posixtime)
            else:
                assert isinstance(timestamp, datetime)

        message = message.replace('\x00', '')

        c.incoming_message(screenname, message,
                           auto      = is_auto_response,
                           offline   = offline,
                           timestamp = timestamp,
                           content_type = 'text/html',
                           )

    def incoming_rtf_message(self, userinfo, message, is_auto_response=False):
        log.info('received RTF message')
        try:
            plain_message = rtf_to_plain(message)
        except Exception, e:
            # Error parsing RTF, assume plaintext
            plain_message = message
        self.incoming_message(userinfo, plain_message, is_auto_response = is_auto_response, html=False)

    def convo_for(self, buddyname):
        if hasattr(buddyname, 'name'): buddyname = buddyname.name
        if not isinstance(buddyname, basestring):
            raise TypeError(str(type(buddyname)))

        bname = str(buddyname).lower().replace(' ','')

        try:
            return self.conversations[bname]
        except KeyError:
            c = self.conversations.setdefault(bname, oscar.conversation(self))
            c.buddy_join(self.self_buddy.name)
            c.buddy_join(bname)
            return c

    def chat_with(self, bname):
        info('chat_with %r', bname)
        bname = common.get_bname(bname).lower().replace(' ','')

        try:
            c = self.conversations[bname]
        except KeyError:
            c = self.conversations.setdefault(bname, oscar.conversation(self))

        if bname not in c:
            c.buddy_join(bname)
        if self.self_buddy not in c:
            c.buddy_join(self.self_buddy.name)
        return c

    get_buddy_icon = snac.get_buddy_icon
    set_buddy_icon = snac.set_buddy_icon

    def get_self_bart_data(self):
        ssim = self.ssimanager
        ssis = ssim.find(type = 0x14)
        res = []
        for ssi in ssis:
            try:
                type = int(ssi.name)
            except ValueError:
                continue

            if type & 1:
                res.append((type, ssi.tlvs.get(0xD5, '')))

        return ''.join([(struct.pack('!H', t) + val) for t,val in sorted(res)])

    def get_buddy(self, name):
        if not isinstance(name, basestring): raise AssertionError()
        name = name.encode('utf-8')

        return self.buddies[name]

    def get_buddy_info(self, b, profile = True, away = True, caps = True, cert = False):
        bname = common.get_bname(b)
        if isinstance(bname, unicode):
            bname = bname.encode('utf8')
        b = self.buddies[bname]

        getting = ','.join(filter(None, ['profile' if profile else None,
                                         'away' if away else None]))
        log.info('retreiving [%s] for %r', getting, bname)

        self.send_snac(*snac.x02_x15(bname,
                                     profile = profile, away = away,
                                     caps = caps, cert = cert))

        if b.service == 'icq':
            log.info('requesting additional icq info')
            from common import pref
            if pref('icq.profile_unicode', True):
                req = snac.icq_request_profile_unicode(self, b.name)
            else:
                req = snac.request_more_icq_info(self, b.name)

            if req:
                self.send_snac(*req)

    def exit_conversation(self, c):
        if c.type == 'chat':
            self.close_socket(c.sock)

        cs = self.conversations
        [cs.pop(k) for k in cs.keys() if c is cs[k]]

    @callsback
    def _do_rejoin_chat(self, old_conversation, callback=None):
        self.join_chat(cookie=old_conversation.cookie, notify_profile=False, callback=callback)

    @callsback
    def join_chat(self, convo = None, room_name = None, cookie=None, server=None, notify_profile=True, callback = None):
        if cookie is None:
            cookie, room_name = generate_chatroom_cookie(room_name)

        if cookie and not cookie.startswith('!'):
            cookie = '!' + cookie

        try:
            c = self.conversations[cookie]
        except KeyError:
            c = self.conversations.setdefault(cookie, oscar.conversation(self, 'chat', cookie=cookie, roomname=room_name))
            c.connect_chat_socket(callback = callback)
        else:
            callback.success(c)

        if notify_profile:
            profile.on_entered_chat(c)

    def set_message(self, message='', status='away', format = None):
        self.status = status.lower()
        self.self_buddy.setnotify('status', self.status)

        self.status_message = message

        if self.status in ('online', 'available', 'free for chat'):
            # do not apply formatting to available messages--they have a maximum
            # length of 255 and clients seemingly do not expect formatting anyways
            self.set_invisible(False)
            self.set_away()
            message = message.encode('utf-8')
            self.set_avail(message)

        elif self.status in ('offline', 'invisible'):
            log.debug('setting invisible on %r', self)
            self.set_invisible(True)
            self.set_away()
            if self.icq: self.update_extended_info()

        else:
            # only apply formatting to away messages
            if message == '':
                message = _("Away")

            if message[:5].lower() != '<html' or self.icq:

                message = message.encode('xml')

                if format is not None and not self.icq:
                    from oscar.oscarformat import to_aimhtml
                    message = to_aimhtml(message, format, body_bgcolor = True, replace_newlines=True).encode('utf-8')

            if isinstance(message, unicode):
                message = message.encode('utf8')
            self.status_message = message
            if self.icq:
                self.set_avail(message)
            self.set_away(message)
            if self.icq:
                self.update_extended_info()

    @callsback
    def set_icq_psm(self, msg, callback = None):
        self.send_snac(req = True, cb = callback, *snac.set_icq_psm(self, msg))

    def set_avail(self, message):
        if len(message) > AVAIL_MAX_LEN:
            message = message[:AVAIL_MAX_LEN]
            log.warning('avail message is too long, chopping to %s chars', AVAIL_MAX_LEN)
        self.self_buddy._avail_msg = message

        def update_infos(*a):
            self.update_location_info()
            self.update_extended_info()

        if self.icq:
            self.set_icq_psm(message, success = update_infos)
        else:
            update_infos()


    def update_extended_info(self, *args):
        self.send_snac('bos', *snac.x01_x1e(self))

    def update_location_info(self):
        self.send_snac('bos', *snac.x02_x04(self))

    def set_away(self, message=''):
        self.self_buddy.away_msg = self.status_message = message
        if not self.self_buddy.idle:
            self.set_idle()

        def update_infos(*a):
            self.update_location_info()
            self.update_extended_info()

        if self.icq:
            self.set_icq_psm(message, success = update_infos)
        else:
            update_infos()

    def set_profile(self, value = '', format = None):
        from common import pref
        if self.icq and pref('oscar.icq.set_about', False):
            if not isinstance(value, basestring): value = value.format_as('html')
            self.send_snac(*snac.send_icq_profile(self, value))
            self.self_buddy.profile = value

        elif not self.icq:

            if isinstance(value, basestring):
                if format is not None:
                    # Add AIM formatting.
                    from oscar.oscarformat import to_aimhtml
                    value = to_aimhtml(value, format, body_bgcolor = True)
            else:
                value = value.format_as('html')

            self.self_buddy.profile = value.replace('\n', '<br>')[:self.MAX_PROF_HTML]

        self.update_location_info()

    def set_idle(self, how_long = 0):

        self._enable_idle_privacy()

        how_long = int(how_long )
        self.self_buddy.setnotifyif('idle', time.time() - how_long)
        self.send_snac('bos', *snac.x01_x11(int(how_long)))

    def _enable_idle_privacy(self):
        # TODO: see ticket #2668
        pass

    def set_invisible(self, invis = True):
        self.self_buddy.invisible = invis

#        if self.icq:
#            self.set_privacy(not invis, 'all')
        if self.icq and not invis:
            self.set_privacy(True, 'all')
        elif self.icq:
            self.set_privacy(True, 'list')

        self.update_extended_info()

    def request_offline_messages(self):
        if self.icq:
            self.send_snac(*snac.request_offline_messages_icq(self))
        else:
            self.send_snac(*snac.x04_x10())

    def is_mobile_buddy(self, bname):
        bname = getattr(bname, 'name', bname)
        buddy = self.get_buddy(bname)
        return buddy.sms or buddy.mobile

    @callsback
    def remove_buddy(self, ssi_ids, gpo=None, callback = None):
        self.ssimanager.remove_buddy_ssi(ssi_ids, callback = callback)

    @callsback
    def move_buddy(self, contact, to_group, from_group=None, pos=0, callback = None):
        ssi = contact.id
        to_group_orig = to_group

        if isinstance(to_group, basestring):
            to_group = self.get_group(to_group)

        # Change the Contact's id
        old = callback.success

        def on_move(ssi_tuple, old=old):
            assert isinstance(ssi_tuple, tuple)
            contact.id = ssi_tuple
            old(ssi_tuple)

        callback.success = on_move

        if to_group is not None:
            if to_group != from_group:
                for c in to_group:
                    if c.name == contact.name:
                        return self.remove_buddy(contact.id, success = lambda *a: callback.success(c.id))

            self.ssimanager.move_ssi_to_position(ssi, pos, to_group.my_ssi, callback = callback)
        else:
            callback.error()

    def set_remote_alias(self, *args):
        self.ssimanager.alias_ssi(*args)

    def rename_group(self, protocol_object, name):
        self.ssimanager.rename_ssi(protocol_object, name)



    @callsback
    def add_buddy(self, buddy_name, groupid, service = None, callback = None):
        buddy_name = str(buddy_name)

#        # This function assumes the group is already there.
#        def doadd(buddy_name, group):
#            #group = self.ssimanager.find(name=group, type=1)[0]
        self.ssimanager.add_new_ssi(buddy_name, groupid, error=lambda *a:
                                    self.add_buddy_try_auth(buddy_name, groupid, service=service, callback=callback))

#        if isinstance(group, basestring):
#            groupobj = self.get_group(group)
#
#            # if the group isn't there, add it first, then callback and add the buddy.
#            if groupobj is None:
#                self.add_group(group, success = lambda *a: doadd(buddy_name, group))
#            else:
#                doadd(buddy_name, group)


    add_contact = add_buddy

    def request_auth_for(self, ):
        pass

    @callsback
    def add_buddy_try_auth(self, buddy_name, group, service=None, callback = None):


        print "add_buddy_try_auth"
        self.ssimanager.add_new_ssi(buddy_name, group, authorization=True,
                                    callback = callback)
        self.request_authorization(buddy_name, 'Digsby rulz')

    def request_authorization(self, buddy_name, reason=''):
        self.send_snac(req=True, cb=lambda *a,**k: None, *snac.x13_x18(buddy_name, reason))

    @callsback
    def add_group(self, group_name, callback = None):
        self.ssimanager.add_new_ssi(group_name, callback = callback)

    def get_group(self, groupname):
        '''
        Returns a Group object for a given groupname. Case does not matter,
        as per Oscar protocol.

        If the group doesn't exist this function will return None.
        '''
        groupname = groupname.encode('utf-8')
        group = self.ssimanager.find(name=groupname, type=1)
        if group:
            return self.ssimanager.ssis.get_group(group[0])

    def remove_group(self, gpo):
        self.ssimanager.remove_group(gpo)

    @action(aim_only)
    def format_screenname(self, new_name):
        '''
        Change the formatting of your screenname.

        You can add or remove spaces or change capitalization.
        '''
        new_name = str(new_name)

        if new_name.replace(' ','').lower() != \
            self.username.replace(' ','').lower():
            raise ScreennameError('Formatted name is not equal to account name')

        if new_name != self.self_buddy.nice_name:
            self.send_snac(*snac.x07_x04(screenname=new_name))

    @callsback
    def get_account_email(self, callback = None):
        if self.icq:
            return

        def success(sock, snc):
            if (0x07, 0x03) == (snc.hdr.fam, snc.hdr.sub):
                result = snac.x07_x03(self, sock, snc.data)
                if 17 in result:
                    return callback.success(result[17].decode('utf-8'))

            return callback.error()

        cb_args = dict(req=True, cb=success)
        self.send_snac(*snac.x07_x02('email'), **cb_args)

    #@action(aim_only, needs = lambda self: ((str, _('AIM Account Email'), ''),))
    @action(aim_only)
    def set_account_email(self, new_email):
        if isinstance(new_email, unicode):
            new_email = new_email.encode('utf-8')

        #TODO: validate email?
        self.send_snac(*snac.x07_x04(email=new_email))

    @action(aim_only)
    def request_account_confirm(self):
        self.send_snac(*snac.x07_x06())

    @action()
    def change_password(self):
        self.hub.launchurl('http://aim.aol.com/redirects/password/change_password.adp')

    @action(aim_only)
    def im_forwarding(self):
        self.hub.launchurl('http://www.aim.com/redirects/inclient/imforwarding.adp')

    @action(aim_only)
    def aol_alerts(self):
        self.hub.launchurl('http://alerts.aol.com/ar/directory/noauth.ev')

    @action(icq_only)
    def my_icq_page(self):
        self.hub.launchurl('http://www.icq.com/people/about_me.php?uin=%s' % self.self_buddy.name)


    def move_group(self, gpo, pos=0):
        # gpo should be an ssi tuple...
        self.ssimanager.move_ssi_to_position(gpo, pos)

    @callsback
    def block(self, buddy, set_block = True, callback = None):
        if set_block:
            # block them
            if self.icq:
                f = self.ssimanager.ignore_buddy
            else:
                f = self.ssimanager.block_buddy

            f(buddy, callback = callback)
            self.set_privacy(False, 'list')
        else:
            # unblock them
            if self.icq:
                f = self.ssimanager.unignore_buddy
            else:
                f = self.ssimanager.unblock_buddy

            f(buddy, callback = callback)

    @callsback
    def ignore(self, buddy, set_ignore=True, callback=None):
        if set_ignore:
            if self.icq:
                f = self.ssimanager.block_buddy
            else:
                f = self.ssimanager.ignore_buddy

            f(buddy, callback=callback)
        else:
            if self.icq:
                f = self.ssimanager.unblock_buddy
            else:
                f = self.ssimanager.unignore_buddy

            f(buddy, callback=callback)

    @callsback
    def unignore(self, buddy, callback=None):
        self.ignore(buddy, False, callback=callback)

    def permit(self, buddy, set_allow):
        if set_allow:
            self.ssimanager.allow_buddy(buddy)
        else:
            self.ssimanager.unallow_buddy(buddy)

    def warn(self, buddy, anon=True):
        if hasattr(buddy, 'name'): buddy = buddy.name
        self.send_snac(*snac.x04_x08(buddy, anon))

    def _get_chat(self, cookie):
        '''Returns the OscarConversation chat for the given cookie.'''

        return self.conversations.get(cookie, None)

    def buddy_list_from_file(self, open_fh):
        import re
        result = []
        last_opened = []
        depth = 0
        depth_to_tag = [
                        ('rah','blah'),
                        ('<%s>','</%s>'),
                        ('<%s>','</%s>'),
                        ('<buddy name=%s>','</buddy>'),
                        ('<buddyinfo type=%s>','</buddyinfo>'),
                        ('%s','%s'),
                        ]
        for line in open_fh:
            line = line.strip()
            if line.endswith('{'):
                depth += 1
                line = line.strip('{').strip()
                if line.strip('"') == line:
                    line = '"%s"' % line
                #last_opened.append(line)
                try: line = depth_to_tag[depth][0] % line
                except TypeError: pass
                except Exception: print depth;raise
            elif line.endswith('}'):
                depth -= 1
                try: line = depth_to_tag[depth][1] % line
                except TypeError: pass
            else:
                if line.strip('"') == line:
                    line = '"%s"' % line
            result.append(line)

        return result

    def buddy_list_to_file(self, open_fh):
        open_fh.write('Buddy {\nlist {\n')
        for group in self.ssimanager.ssis.groups[0,0]:
            open_fh.write('"%s" {\n' % group.name)
            for contact in group:
                open_fh.write('%s\n' % contact.buddy.name.lower().replace(' ',''))
            open_fh.write('}\n')


    def set_privacy(self, allow, who, _ignore = True):
        '''
        allow is a boolean. True for allow, false for block
        who is a string from the following list: ['all','contacts','list']

        (True, 'contacts') and (False, 'contacts') are semantically the same.

        (True, 'all') means everyone can message you and (False, 'all') means no one.
        '''


        '''
        [TLV(0x00CA), itype 0x04, size 01] - This is the byte that tells the AIM servers your
        privacy setting. If 1, then allow all users to see you. If 2, then block all users from
        seeing you. If 3, then allow only the users in the permit list. If 4, then block only the
        users in the deny list. If 5, then allow only users on your buddy list.
        '''
        allow = bool(allow)
        assert who in ['all','contacts','list']

        ps = self.ssimanager.get_privacy_ssi()

        userclass = 0xFFFFFFFF
        see = 1
        if who == 'all':
            val = 1 if allow else 2
        if who == 'list':
            val = 3 if allow else 4
        if who == 'contacts':
            val = 5

        if (allow, who) == (False, 'all'):
            userclass = 4

        ps.tlvs[0xca] = util.Storage(type=0xca, length=1, value=val)
        ps.tlvs[0xcb] = util.Storage(type=0xcb, length=4, value=userclass)
        ps.tlvs[0xcc] = util.Storage(type=0xcc, length=4, value=see)

        self.ssimanager.add_modify(ps)

    def get_privacy(self):
        ps = self.ssimanager.get_privacy_ssi()
        return ps.tlvs
#
#        from util import Storage as S
#
#        privacy = {1: 'allowall',
#                   2: 'blockall',
#                   3: 'permitlist',
#                   4: 'denylist',
#                   5: 'buddylist'}
#
#        return S(privacy = privacy[struct.unpack('B', tlvs[0xca])[0]])
#        #ps.tlvs

    def set_webaware(self, webaware):
        self.webaware = webaware
        self.send_snac(*snac.set_icq_privacy(self))

        self.update_extended_info()

    def set_auth_required(self, auth_required):
        self.auth_required = auth_required
        self.send_snac(*snac.set_icq_privacy(self))

        self.update_extended_info()

    @callsback
    def get_icq_privacy(self, callback=None):
        pass
        #self.send_snac(*snac.get_icq_privacy(callback=callback))


    def save_icq_privacy(self):
        self.send_snac(*snac.save_icq_privacy(self))

    def set_search_response(self, disclosure):
        '''
        What happens when a user searches for your email in AIM directory search.
        full means they can see whatever they want,
        limited means just your screenname
        none means no info at all.

        disclosure: True = full
                    False= limited
                    None = none
        '''
        self._search_disclosure = disclosure
        disclosure = {True: 3, False: 2, None: 1}[disclosure]
        self.send_snac(*snac.x07_x04(reg_status=disclosure))

    @callsback
    def get_search_response(self, callback=None):
        if self.icq: return

        def success(sock, snc):
            if (0x07, 0x03) != (snc.hdr.fam, snc.hdr.sub):
                return callback.error()
            else:
                value, = struct.unpack('!H', snac.x07_x03(self, sock, snc.data)[0x13])
                disclosure = {3:True, 2:False, 1:None}[value]
                log.info('Got disclosure response: %r ( => %r)', value, disclosure)

                self._search_disclosure = disclosure
                callback.success(disclosure)

        cb_args = dict(req=True, cb=success)
        self.send_snac(*snac.x07_x02('registration'), **cb_args)

    def set_require_auth(self, auth=True):
        self.send_snac(*snac.set_require_auth(self, auth))

    def set_allow_list(self, L):
        for bname in L:
            b = self.buddies[bname]
            if b.blocked:
                b.block(False)

    def set_block_list(self, L):
        for bname in L:
            b = self.buddies[bname]
            if not b.blocked:
                b.block(True)

    def add_to_visible_list(self, bname):
        b = self.buddies[bname]
        if b.blocked:
            b.block(False)

        PERMIT = 0x02
        if not self.ssimanager.find(name=bname,type=PERMIT):
            new_id = self.ssimanager.new_ssi_item_id(0)
            self.ssimanager.add_modify(oscar.ssi.item(bname, 0, new_id, type_=PERMIT))

    def allow_message(self, buddy, mobj):
        '''
        Blocking is handled by the server, except for icq's "block_unknowns"
        '''
        super = common.protocol.allow_message(self, buddy, mobj)
        if super in (True, False):
            return super

        search = lambda **k: self.ssimanager.find(name=oscar.util.lowerstrip(buddy.name), **k)

        if self.icq and self.block_unknowns and not (search(type=0) or search(type=2)):
            return False

        # AOLSystemMsg can go on your blocklist, but the server ignores it and
        # gives you its messages anyways.
        #
        # TODO: implement get_privacy_tlv so we can know the current privacy settings.
        # this may not always be accurate!
        if buddy.name == 'aolsystemmsg' and buddy.blocked:
            return False

        return True

    def should_log(self, messageobj):
        return messageobj.buddy.name not in self.bots

class SnacQueue(list):
    def __init__(self, sock=None):
        list.__init__(self)
        self.sock = sock

    def send_snac_first(self, *args, **kwargs):
        self.insert(0, ('snac', args, kwargs))

    def send_snac(self, *args, **kwargs):
        self.append(('snac', args, kwargs))

    def send_flap(self, *args, **kwargs):
        self.append(('flap', args, kwargs))

    def flush(self, out=None):
        if not self: return

        if out is None:
            assert self.sock
            out = self.sock
        log.debug('flushing SnacQueue to %r', out)
        while self:
            what, args, kwargs = self.pop(0)
            if what == 'flap':
                out.send_flap(*args, **kwargs)
            elif what == 'snac':
                out.send_snac(*args, **kwargs)
            else:
                raise ValueError("%r is not a valid thing to send. Was expecting 'flap' or 'snac'. Args/kwargs were: %r", what, (args, kwargs))
        log.debug('done flushing')

    def close_when_done(self):
        del self[:]

    close = close_when_done

    def __hash__(self):
        return hash((self.sock, id(self)))

    def __repr__(self):
        return '<SnacQueue %r>' % list.__repr__(self)

class DisabledSocket(object):
    '''
    a mock OscarSocket that dumps calls into the void. used if a service is down.
    '''
    def __init__(self, sock_id, time):
        self.sock_id = sock_id
        self.time = time
        self.ignored_calls = 0

    @property
    def should_rerequest(self):
        '''
        returns True if enough time has elapsed since the creation of this
        DisabledSocket
        '''
        return time.time() - self.time > SERVICE_REQUEST_TIME_SECS

    def _do_nothing(self, *a, **k):
        self.ignored_calls += 1

    send_snac = \
    send_flap = \
    flush = \
    close_when_done = \
    close = \
    _do_nothing

    def __hash__(self):
        return hash((self.sock_id, self.time))

    def __repr__(self):
        return '<DisabledSocket(sock_id=%r, time=%r, ignored_calls=%r)' % (self.sock_id, self.time, self.ignored_calls)


class RedirectError(OscarException): pass
class ScreennameError(OscarException): pass
class LoginError(OscarException):
    def __init__(self, code=None, url=None):
        self.code = code
        self.url = url
        if code:
            num = ord(code[-1])
            reason = oscar.auth_errcode.get(num, 'unknown')
            Exception.__init__(self, reason, url)
            self.code = num
        else:
            Exception.__init__(self)

def generate_chatroom_cookie(room_name=None):
    if room_name is None:
        room_name = 'DigsbyChat%s' % random.randint(0, sys.maxint)

    return oscar.util.chat_cookie(room_name), room_name

