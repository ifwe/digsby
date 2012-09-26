'''
Jabber Protocol.
'''

from common import pref, netcall
from digsby.loadbalance import DigsbyLoadBalanceManager
from hashlib import sha256
from jabber.JabberProtocol import JabberProtocol
from jabber.threadstream import ThreadStream
from logging import getLogger
from peak.util.imports import lazyModule
from pyxmpp.all import Iq, Presence
from pyxmpp.jabber.client import JabberClient
from pyxmpp.jid import JID
from traceback import print_exc
from util.callbacks import callsback, CallLater
from util.introspect import callany, funcinfo
from util.primitives.funcs import Delegate, do
from util.primitives.mapping import odict
from util.primitives.structures import enum
from util.threads.threadpool2 import threaded
import blobs
import common
import digsby
import hooks
import jabber
import random
import string
import sys
from common.Protocol import StateMixin

callbacks      = lazyModule('util.callbacks')
mapping        = lazyModule('util.primitives.mapping')
funcs          = lazyModule('util.primitives.funcs')
error_handling = lazyModule('util.primitives.error_handling')
hook_util      = lazyModule('util.hook_util')
util_threads   = lazyModule('util.threads')

log = getLogger('jabber.protocol')
methods_dict = odict(dict(digsby_login="sasl:DIGSBY-SHA256-RSA-CERT-AES"))

log = getLogger('digsbyImportProtocol')

LOAD_BALANCE_ADDRS = [
                      ('login1.digsby.org', 80),
                      ('login2.digsby.org', 80)
                     ]

JABBER_SRVS_FALLBACK = [
                        'api1.digsby.org',
                        'api2.digsby.org',
                        ]

class DigsbyProtocol(JabberClient, StateMixin):

    states = enum('Disconnected',
                  'Authenticating',
                  'Connected')

    #layering violations from threadstream.py
    do_ssl = False
    connect_killed = False

    def __init__(self, username, password, server, resource="Digsby"):

        host, port = server

        alphanum = string.letters + string.digits
        resource = resource + "." + "".join(random.choice(alphanum) for _x in xrange(6))
        jid = JID(username, "digsby.org", resource)

        if isinstance(username, unicode):
            username = username.encode('utf8')
        if isinstance(password, unicode):
            password = sha256(password.encode('utf-8')).digest()

        jkwargs = dict(jid          = jid,
                       password     = password,
                       keepalive    = 45)

        if host:
            jkwargs.update(server = host)
        if port:
            jkwargs.update(port = port)

        jkwargs.update(auth_methods = ("sasl:DIGSBY-SHA256-RSA-CERT-AES",))
        JabberClient.__init__(self, **jkwargs)
        StateMixin.__init__(self)
        self.stream_class = ThreadStream

    @callsback
    def Connect(self, callback=None):

        self.change_state(self.Statuses.CONNECTING)

        self.connect_callback = callback

        def conn_attmpt_failed():
            log.debug('conn_attmpt_failed')
            #nowhere else to go, + report conn fail
            self.set_offline(self.Reasons.CONN_FAIL)
            callback.error()
        self.connect_attempt_failed = conn_attmpt_failed
        try:
            self.connect()
        except Exception as _e:
            print_exc()
            self.connect_attempt_failed()
        else:
            self.connect_attempt_succeeded()

        # Go find the load balancer; if you cannot, call on_fail
        #self.get_login_servers(l.username)

    def connect_attempt_succeeded(self):
        log.debug('connect_attempt_succeeded')
        with self.lock:
            self.idle_loop = Delegate()
            self.idle_loop += self.idle
            self.idle_looper = jabber.IdleLoopTimer(1, self.idle_loop)

    def connect_attempt_failed(self):
        raise AssertionError('connection attempt cannot fail before it is attempted')

    def connected(self):
        with self.lock:
            if self.state == self.Statuses.CONNECTING:
                self.change_state(self.Statuses.AUTHENTICATING)

    def disconnected(self, want_try_again = False):
        log.debug('disconnected 1')
        with self.lock:
            log.debug('disconnected 2')
            if not want_try_again and not self.want_try_again:
                log.debug('disconnected 3')
#                assert False
                self.change_state(self.Statuses.OFFLINE)
            JabberClient.disconnected(self)

    def _get_stream(self):
        return getattr(self, '_stream', None)

    def _set_stream(self, stream):
        new = stream
        if new is None:
            old = self.stream
            if old is not None:
                netcall(old.close)
                for attr in ('process_stream_error', 'state_change', 'owner'):
                    setattr(old, attr, Null)
        self._stream = new

    stream = property(_get_stream, _set_stream)

#    def auth_failed(self, reason=''):
#        if reason:
#            self._auth_error_msg = reason
#        self.setnotifyif('offline_reason', self.Reasons.BAD_PASSWORD)
#        self.Disconnect()

    def auth_failed(self, reason=''):
        if reason in ('bad-auth', 'not-authorized'):
            self._auth_error_msg = reason
            self.setnotifyif('offline_reason', self.Reasons.BAD_PASSWORD)
        elif reason:
            self.error_txt = reason
        self.fatal_error()


    @callsback
    def _reconnect(self, invisible = False,
                do_conn_fail = True, callback=None):
        log.info('jabber _reconnect!')
        getattr(getattr(self, 'idle_looper', None), 'stop', lambda: None)()

        #grab next set of connection opts
        opts = self._get_next_connection_options()
        if opts is None:
            return self.fatal_error()

        self.change_state(self.Statuses.CONNECTING)

        self.server, self.port = opts.pop('server')

        #collect $200
        threaded(lambda: JabberProtocol.Connect(self, invisible = invisible,
                                       do_conn_fail = do_conn_fail, callback=callback))()

    def fatal_error(self):
        if getattr(self.stream, '_had_host_mismatch', False) and not self.offline_reason:
            log.error('there was a host mismatch, interpreting it as auth error...')
            self.setnotifyif('offline_reason', self.Reasons.BAD_PASSWORD) # technically it's a bad username, but auth error regardless

        reason = self.offline_reason or self.Reasons.CONN_LOST
        log.info('Out of connection options. Changing to %r', reason)
        self.set_offline(reason)
        return False

    def connect(self):
        """Connect to the server and set up the stream.

        Set `self.stream` and notify `self.state_changed` when connection
        succeeds. Additionally, initialize Disco items and info of the client.
        """
        JabberClient.connect(self, register=False)

    def stop_idle_looper(self):
        idle_looper, self.idle_looper = getattr(self, 'idle_looper', None), None
        if idle_looper is not None:
            idle_looper.stop()

        del self.idle_looper

    def stop_timer_loops(self):
        self.stop_idle_looper()

    def Disconnect(self):
        netcall(self._Disconnect)

    def _Disconnect(self):
        log.debug('logging out %r', self.want_try_again)
        with self.lock:
            pres = Presence(stanza_type="unavailable",
                            status='Logged Out')
            try:
                self.stream.send(pres)
            except AttributeError:
                pass
            self.connect_killed = True
            self.disconnect()
            try:
                self.stop_timer_loops()
            except AttributeError:
                print_exc()

            if getattr(self, 'idle_loop', None) is not None:
                del self.idle_loop[:]

            if self.interface_providers is not None:
                del self.interface_providers[:]
                self.interface_providers = None

            if self.stream is not None:
                self.stream = None

            log.debug('1logged out %r', self.want_try_again)
            self.offline_reason = None
#            self.disconnected()
        log.debug('1logged out %r', self.want_try_again)

        common.protocol.Disconnect(self)

    def session_started(self):
        '''
        Called when the IM session is successfully started (after all the
        neccessery negotiations, authentication and authorizasion).
        '''
        with self.lock:
            self.idle_looper.start()
        log.info('session started')

        s = self.stream

        newstate = self.Statuses.AUTHORIZED
        #when this is true, don't try to start a new connection on conn_lost
        self.have_connected = True

        # set up handlers for supported <iq/> queries
        s.set_iq_get_handler("query", "jabber:iq:version", self.get_version)

        # set up handlers for <presence/> stanzas
#        do(s.set_presence_handler(name, func) for name, func in [
#            (None,           self.buddies.update_presence),
#            ('unavailable',  self.buddies.update_presence),
#            ('available',    self.buddies.update_presence),
#            ('subscribe',    self.subscription_requested),
#            ('subscribed',   self.presence_control),
#            ('unsubscribe',  self.presence_control),
#            ('unsubscribed', self.presence_control),
#        ])

        self.session_started_notify(s)

        self.connect_callback.success()
        self.change_state(newstate)
        log.info('session started done')

    def session_started_notify(self, s):
        '''
        whatever needs to be done after most setup and before the callback/state change happens.
        usually that will be plugins doing their own setup.
        allows notify to be overridden in subclass
        '''
        hooks.notify('digsby.jabber.session_started', self, s)

    def authorized(self):
        log.info('authorized1')
        JabberClient.authorized(self) # required!
        log.info('authorized2')

    def get_version(self,iq):
        """Handler for jabber:iq:version queries.

        jabber:iq:version queries are not supported directly by PyXMPP, so the
        XML node is accessed directly through the libxml2 API.  This should be
        used very carefully!"""
        iq = iq.make_result_response()
        q = iq.new_query("jabber:iq:version")
        q.newTextChild( q.ns(), "name", "Digsby Import Client" )
#        q.newTextChild( q.ns(), "version", ('%s %s' % (sys.REVISION, sys.TAG)).strip()) # strip because sometimes TAG is ''
        if not self.hide_os:
            import platform
            platform_string = platform.platform()
            # for some reason, on my XP box, platform.platform() contains both
            # the platform AND release in platform.platform(). On Ubuntu, OS X,
            # and I believe older versions of Windows, this does not happen,
            # so we need to add the release in all other cases.
            if platform_string.find("XP") == -1:
                platform_string += " " + platform.release()

            q.newTextChild( q.ns(), "os", platform_string )
        self.send(iq)
        return True

    # presense start

    def presence_push(self):
        pres = Presence()
        self.send_presence(pres)

    def presence_control(self,*_a, **_k):
        '''
        Handle subscription control <presence/> stanzas -- acknowledge
        them.
        '''
        return True

    # presense end

    @callsback
    def send_cb(self, query, timeout_duration=None, callback=None):
        '''
        Given a callback object with callable attributes success, error, and timeout,
        sends out a query with response handlers set.
        '''

        def free_stanza(st):
            stream = self.get_stream()
            with stream.lock:
                if stream.doc_out is not None:
                    st.free()
                else:
                    if st._error:
                        st._error.xmlnode = None
                    st.xmlnode = None

        def my_super_callback_success(stanza):
            stanza.handler_frees = True
            if not isinstance(callback.success, list):
                try:
                    log.info("what is this?, callback was %r", funcinfo(callback.success))
                except Exception:
                    log.error('bad callback.success %r', callback.success)
                    return free_stanza(stanza)
            if len(callback.success) == 0:
                return free_stanza(stanza)

            try:
                f = callback.success[0].cb
                _call_free = CallLater(lambda:free_stanza(stanza))
                def my_hyper_callback_success(st):
                    try: f(st)
                    except Exception:
                        log.error('error processing %r', f)
                        print_exc()
                    finally: _call_free()
                callback.success[0].cb = my_hyper_callback_success
                callany(callback.success, stanza)
            except Exception:
                print_exc()
                log.error('failed to set up success stanza.free for %r, %r', callback, stanza)

        def my_super_callback_error(stanza):
            stanza.handler_frees = True
            if not isinstance(callback.error, list):
                try:
                    log.info("what is this?, callback was %r", funcinfo(callback.error))
                except Exception:
                    log.error('bad callback.error %r', callback.error)
                    return free_stanza(stanza)
            if len(callback.error) == 0:
                return free_stanza(stanza)

            try:
                f = callback.error[0].cb
                _call_free = CallLater(lambda:free_stanza(stanza))
                def my_hyper_callback_error(st):
                    try: f(st)
                    except Exception:
                        log.error('error processing %r', f)
                        print_exc()
                    finally: _call_free()
                callback.error[0].cb = my_hyper_callback_error
                callany(callback.error, stanza)
            except Exception:
                print_exc()
                log.error('failed to set up error stanza.free for %r, %r', callback, stanza)

        def my_super_callback_timeout(*_a):
            '''
            consume the arguments, they are from ExpiringDictionary and cause problems
            with the number of arguments taken by timeout function,
            which in this case is expected to be 0, since we can store the context in it's closure
            and hardly anything even uses timeouts.
            '''
            return callback.timeout()

        s = self.get_stream()
        if s is not None:
            try:
                if timeout_duration is not None:
                    self.stream.set_response_handlers(query, my_super_callback_success,
                                                         my_super_callback_error,
                                                         my_super_callback_timeout,
                                                         timeout = timeout_duration)
                else:
                    self.stream.set_response_handlers(query, my_super_callback_success,
                                                         my_super_callback_error,
                                                         my_super_callback_timeout)
            except Exception as _e:
                print_exc()
                log.critical("couln't set stream handlers")
                return callany(callback.error)
            try:
                self.stream.send(query)
            except Exception as _e:
                print_exc()
                log.critical("couln't send query")
                try:
                    return callany(callback.error)
                except Exception:
                    log.critical("couln't call callany(callback.error) %r", callback)

    def send_presence(self, pres):
        assert isinstance(pres, Presence)
        self.send(pres)

    def send_iq(self, iq):
        assert isinstance(iq, Iq)
        self.send(iq)

    def send(self, stanza):
        s = self.get_stream()
        if s is not None:
            try:
                self.stream.send(stanza)
            except Exception as _e:
                print_exc()
                log.critical("couln't send stanza")

    def idle(self):
        try:
            JabberClient.idle(self)
            if not self.stream.socket or self.stream.eof:
                raise AssertionError, "if the stream is dead or gone, we can't really send a keep-alive"
        except Exception:
            self.stop_timer_loops()
        else:
            self.cache.tick()

    def stream_error(self, err):
        if err.get_condition().name == "pwchanged":
            self.change_reason(self.Reasons.BAD_PASSWORD)
            self.profile.signoff(kicked=True)
        elif err.get_condition().name == "conflict":
            self.change_reason(self.Reasons.OTHER_USER)
        else:
            self.change_reason(self.Reasons.CONN_LOST)
            JabberClient.stream_error(self, err)

    class Statuses(jabber.protocol.Statuses):
        SYNC_PREFS = _('Synchronizing Preferences...')
        #LOAD_SKIN  = _('Loading Skin...')
        AUTHORIZED = _('Synchronizing...')

    @callsback
    def get_blob_raw(self, elem_name, tstamp='0', callback=None):
        try:
            blob = blobs.name_to_obj[elem_name](tstamp)
            blob._data = None
            iq = blob.make_get(self)
        except Exception:
            blob = blobs.name_to_obj[elem_name]('0')
            blob._data = None
            iq = blob.make_get(self)
        self.send_cb(iq, callback = callback)

    @callsback
    def get_accounts(self, callback=None):
        iq = digsby.accounts.Accounts().make_get(self)
        self.send_cb(iq, callback = callback)


class DigsbyLoadbalanceStuff(object):

    def __init__(self):
        self.callback = None
        self.profile = None
        self.initial = None

    def finish_init(self, sock):
        self.hosts = sock
        _lh = len(self.hosts)
        self.alt_connect_opts = alt_ops = []
        self.on_alt_no = 0

        add   = lambda **k: alt_ops.append(k)
        if getattr(getattr(sys, 'opts', None), 'start_offline', False) \
          and not pref('debug.reenable_online', type=bool, default=False):
            self.offline_reason = self.Reasons.CONN_FAIL
            return self.connect_opts['on_fail']()

#         add lots of places to connect
        for host in self.hosts:
            add(server = (host, 443),
                do_tls = True,
                require_tls = False,
                verify_tls_peer = False,
                do_ssl = False)

        for host in self.hosts:
            add(server = (host, 5222),
                do_tls = True,
                require_tls = False,
                verify_tls_peer = False,
                do_ssl = False)

        for host in self.hosts:
            add(server = (host, 5223),
                do_tls = False,
                require_tls = False,
                verify_tls_peer = False,
                do_ssl = True)

        getLogger('digsbylogin').info('got potential servers: %r', self.hosts)
        self.success()

    def success(self):
        callback, self.callback = self.callback, None
        if callback is not None:
            callback.success(self.alt_connect_opts)

    @callsback
    def get_login_servers(self, username='', callback = None):
        if self.callback is not None:
            raise Exception

        self.callback = callback
        srvs = list(LOAD_BALANCE_ADDRS)
        load_server = getattr(getattr(sys, 'opts', None), 'loadbalancer', None)
        if load_server is not None:
            ls = load_server.split(':')
            if len(ls) != 2:
                ls = (load_server, 80)
            else:
                ls = (ls[0], int(ls[1]))
            srvs = [ls]
        random.shuffle(srvs)
        #idle
        DigsbyLoadBalanceManager(profile = self.profile, username=username, servers=srvs, success=self.lb_success, error=self.lb_error,
                                 load_server=load_server, initial=self.initial).process_one()

    def lb_success(self, lb_mgr, balance_info):
        loadbalanced_servers = balance_info.addresses
        strategy = balance_info.reconnect_strategy
        if strategy:
            self.offline_reason = self.Reasons.CONN_FAIL
            self.profile.balance_info = balance_info
            self.connect_opts['on_fail']()
        else:
            self.lb_finish(lb_mgr, loadbalanced_servers)

    def lb_error(self, lb_mgr):
        self.lb_finish(lb_mgr)

    def lb_finish(self, lb_mgr, loadbalanced_servers=None):
        #do fallback
        if not loadbalanced_servers:
            hosts = list(JABBER_SRVS_FALLBACK)
            random.shuffle(hosts)
            log.error("could not get server information from HTTP load interface. falling back to %r", hosts)
            ret = hosts
        else:
            ret = loadbalanced_servers
        #inject commandline
        opts_server = getattr(getattr(sys, 'opts', None), 'server', None)
        #commandline lb answer preempts commandline server
        opts_server = [opts_server] if (opts_server and not lb_mgr.load_server) else []
        self.finish_init(opts_server + ret)

if __name__ == '__main__':
    pass
