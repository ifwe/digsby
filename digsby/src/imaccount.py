'''
base classes for all IM accounts
'''
# XXX: shouldn't this be in common?
from __future__ import with_statement
from prefs.prefsdata import localprefs
import wx, cPickle
import util
from util.observe import ObservableProperty
from common import AccountBase, StateMixin
from util import try_this
from util.primitives.funcs import Delegate
from common.actions import action
from util.callbacks import callsback
from common import profile

DEFAULT_JABBER_PRIORITY = 5
DEFAULT_JABBER_RESOURCE = 'Digsby'

from logging import getLogger; log = getLogger('imaccount')
info = log.info; warning = log.warning

from common.protocolmeta import proto_init

import protocols
class IConnectCallable(protocols.Interface):
    protocols.advise(equivalentProtocols =
                     [protocols.protocolForURI("http://www.dotsyntax.com/protocols/connectcallable")])
    def __call__(callable):
        pass

def get_netcall(*a, **k):
    from common import netcall
    return netcall

protocols.declareAdapterForType(IConnectCallable, get_netcall, object)

class ChatProtocol(object):
    def __init__(self):
        self.reconnected_callbacks = Delegate()

    def when_reconnect(self, callback):
        '''
        Register a callback to be called when this account reconnects.

        It will only be called once--call this method again if you need to be registered
        for future reconnects.
        '''
        self.reconnected_callbacks += callback


class Account(AccountBase, ChatProtocol):
    'Local account object.'

    required = 'name password protocol'.split()

    def __init__(self, name, password=None, **options):
        AccountBase.__init__(self, name, password, **options)
        ChatProtocol.__init__(self)

        # Make options local to the account
        self.update_with_defaults(options)

        # Connection attribute: the Protocol subclass which is this account's active connection
        # to the server.
        self.connection = None

        self.offline_reason = StateMixin.Reasons.NONE
        self.error_acked = True

        self.add_observer(self.offline_changed, 'offline_reason')

    @property
    def display_name(self):
        return try_this(lambda: getattr(self, self.prefs['account.display_attr']), self.username)

    def offline_changed(self, src, attr, old, new):

        if old == new:
            return

        if self.offline_reason != StateMixin.Reasons.NONE:
            self.setnotifyif('error_acked', False)
        else:
            self.setnotifyif('error_acked', True)

    @property
    def service(self):
        return self.protocol

    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.protocol)

    @property
    def statusicon(self):
        from gui import skin
        from common.Protocol import ProtocolStatus
        return skin.get('statusicons.%s'% ('available' if self.state==ProtocolStatus.ONLINE else 'offline'))

    def toggle_connect(self):
        self.connect() if not self.connection else self.disconnect()

    def _get_state(self):
        return try_this(lambda: self.connection.state, StateMixin.Statuses.OFFLINE)

    def _set_state(self, val):
        if self.connection is not None:
            self.connection.change_state(val)

    state = property(_get_state, _set_state)

    def connect(self, **connect_args):
        # Find the protocol's __init__ method from the import path in ProtocolMeta.py
        log.info('Loading protocol for account %r...', self)
        connection_class = proto_init(self.protocol)

        # were_connected is a list of Accounts that were connected before the
        # status was set to "Offline"
        profile_obj = profile()
        profile_obj.maybe_return_from_offline()

        self.disconnect() # This will close an old connection and remove it from the reconnect_timers map

        import hub
        self.connection = connection_class(self.name, profile_obj.plain_pw(self.password),
                                           hub.get_instance(),
                                           **self.get_options(True))
        self.connection.account = self

        self.connection.add_observer(self.connection_state_changed, 'state', 'offline_reason')

        self.setnotifyif('offline_reason', self.connection.offline_reason)

        # if invisible was not specified, get from the profile's current status
        if 'invisible' not in connect_args:
            connect_args['invisible'] = profile_obj.status.for_account(self).invisible

        self._connect_args = connect_args
        self._reconnect(also_disconnect=False)

    Connect = connect

    def _reconnect(self, also_disconnect=True):
        cargs = getattr(self, '_connect_args', {})

        conn = self.connection
        if conn is not None \
            and conn.state == conn.Statuses.ONLINE \
            and conn.offline_reason == conn.Reasons.NONE:
            log.info('%r was told to reconnect but is already connected. bailing out.', self)
            return

        if also_disconnect and self.connection is not None:
            self.disconnect()

        if self.connection is None:
            return self.connect(**cargs)

        def go():
            if self.connection is not None:
                self.connection.Connect(**cargs)

        self.setnotifyif('state', self.connection.Statuses.CONNECTING)
        IConnectCallable(self.connection)(go)

    def connection_state_changed(self, src, attr, old, new):
        "Makes a protocol's state trigger a notify in the account."

        log.warning('*'*80)
        log.warning('connection_state_changed: %r', src)

        if attr == 'offline_reason':
            self._auth_error_msg = getattr(src, '_auth_error_msg', None)
            self.setnotifyif(attr, new)
            return

        conn = self.connection
        new = conn.state if conn is not None else None

        if new == StateMixin.Statuses.ONLINE:
            if hasattr(self, '_connect_args'):
                del self._connect_args
            else:
                log.warning('%s had no _connect_args', self)

            status = profile.status
            if not status.for_account(conn).invisible or conn.name in ('digsby','gtalk','jabber','fbchat'): #HAX ticket #3880
                # invisible status is handled by Protocol.Connect(invisible = True)
                conn._set_status_object(profile.status)

            if profile.icon:
                wx.CallAfter(lambda : conn.set_and_size_icon(profile.icon))

            self.reconnected_callbacks.call_and_clear(conn)

        elif new == StateMixin.Statuses.OFFLINE:
            rsn = self.connection.offline_reason
            self.connection = None
            self.setnotifyif('offline_reason', rsn)

        self.notify(attr, old, new)

    def disconnect(self):
        conn = self.connection
        if conn is None:
            return

        rct_timers = profile.account_manager.reconnect_timers
        if self in rct_timers:
            timer = rct_timers.pop(self)
            log.info('Removed %r from reconnect_timer map', self)
            timer.stop()
            del timer

        conn.Disconnect()

    def get_is_connected(self):
        conn = self.connection
        return bool(conn and (conn.state == conn.Statuses.ONLINE or conn.is_connected))

    is_connected = ObservableProperty(get_is_connected, observe='connection')
    connected = property(lambda self: self.is_connected)

    def update_info(self, **options):
        "Update this account's information. The server will be notified."

        self.update_with_defaults(options)

        # Tell the server.
        from common import profile
        profile.update_account(self)

        if self.offline_reason in (StateMixin.Reasons.BAD_PASSWORD,
                                   StateMixin.Reasons.NO_MAILBOX):
            self.connect(**getattr(self, '_connect_args', {}))

    def update_with_defaults(self, newoptions):
        try:
            # this is a new account
            protocol = newoptions['protocol']
        except KeyError:
            # this is an old account
            protocol = self.protocol

        options = self.protocol_info(protocol).defaults.copy()

        for key, value in newoptions.iteritems():
            if key == 'server':
                # This tuple is a source of endless pointless trouble
                port = value[1] if value[1] != '' else options[key][1]
                port = min(65535, port)

                options[key] = (value[0] if value[0] != '' else options[key][0], port)
            elif key == 'resource' or key == 'priority' and protocol == 'jabber':
                options[key] = value
            elif value != '' and value != ('',''):
                options[key] = value

        res = options.pop('resource', sentinel)
        priority = options.pop('priority', sentinel)

        for k, v in options.iteritems():
            try:
                setattr(self, k, v)
            except Exception, e:
                log.error('Error setting %r.%r to %r: %r', self, k, v, e)

        #storage is dependant on username + protocol, so do this last
        if res is not sentinel:
            self.resource = res
        if priority is not sentinel:
            self.priority = priority

        self.notify()

    def _localpref_key(self, key):
        return '/'.join([self.protocol, self.username, key]).lower()

    def set_enabled(self, enabled, notify = True):
        old = getattr(self, 'autologin', False)
        self.autologin = enabled
        if notify:
            self.notify('enabled', old, enabled)
        profile.update_account(self)
        return

    def get_enabled(self):
        return getattr(self, 'autologin', False)

    enabled = property(get_enabled, set_enabled)

    def enable(self):
        log.info("enable: %r", self)
        if not self.enabled:
            self.enabled = True
        elif self.connection is None:
            self.connect()

    def disable(self):
        log.info("disable: %r", self)
        if self.enabled:
            self.enabled = False
        elif self.connection is not None:
            self.disconnect()

    def set_resource(self, res):
        if self.protocol == 'jabber':
            key = self._localpref_key('resource')
            if res and res != DEFAULT_JABBER_RESOURCE:
                localprefs()[key] = res
            elif key in localprefs():
                del localprefs()[key]
        else:
            self._resource = res

    def get_resource(self):
        if self.protocol == 'jabber':
            key = self._localpref_key('resource')
            if key in localprefs():
                return localprefs()[key]
            else:
                return DEFAULT_JABBER_RESOURCE
        else:
            return self._resource

    resource = property(get_resource, set_resource)

    def set_priority(self, priority):
        try:
            priority = int(priority)
        except ValueError:
            priority = DEFAULT_JABBER_PRIORITY
        if self.protocol == 'jabber':
            key = self._localpref_key('priority')
            if priority != DEFAULT_JABBER_PRIORITY:
                localprefs()[key] = priority
            elif key in localprefs():
                del localprefs()[key]
        else:
            self._priority = priority

    def get_priority(self):
        if self.protocol == 'jabber':
            key = self._localpref_key('priority')
            if key in localprefs():
                return int(localprefs()[key])
            else:
                return 5
        else:
            return self._priority

    priority = property(get_priority, set_priority)

    def get_options(self, include_defaults = False):
        '''
        Returns options which are unique to this account. (Defaults removed.)
        '''

        # Copy the dictionary
        options = self.__dict__.copy()
        pop = options.pop


        defaults = self.protocol_info().defaults

        #if it's not in defaults, it'll get cleared out below anyway.
        try:
            options['priority'] = self.priority
        except AttributeError:
            pass

        #if it's not in defaults, it'll get cleared out below anyway.
        try:
            options['resource'] = self.resource
        except AttributeError:
            pass

        # Remove unecessary attributes
        for attr in (set(options.keys()) - set(defaults.keys())):
            pop(attr, None)

        if include_defaults and self.protocol == 'jabber':
            if self.priority != DEFAULT_JABBER_PRIORITY:
                options['priority'] = self.priority
        if include_defaults and self.protocol == 'jabber':
            if self.resource != DEFAULT_JABBER_RESOURCE:
                options['resource'] = self.resource

        # If options are default, don't send to the server.
        if not include_defaults:
            for k, v in list(options.iteritems()):
                if k in defaults and defaults[k] == v:
                    pop(k)

        if include_defaults:
            getattr(self, 'add_options_%s' % self.protocol, lambda *a: None)(options)

        util.dictrecurse(dict)(options)

        return options

    def add_options_jabber(self, options):

        # Common options
        options.update(dict(sasl_md5 = True, use_md5 = True))

        # The encryption radio
        jabber_encryption_options = {
            0: dict(do_tls=True ),     # Use TLS if Possible
            1: dict(do_tls=True, require_tls = True), #Require TLS
            2: dict(do_ssl=True), #Force SSL
            3: dict(do_tls=False), #No Encrpytion
        }
        options.update(jabber_encryption_options[options.pop('encryption')])

        # Authentication
        if options.pop('allow_plaintext'):
            options.update(dict(sasl_plain = True,
                                plain = True))

        ignore = options.pop('ignore_ssl_warnings')
        options['verify_tls_peer'] = not ignore

    def delete_from_server(self, password, on_success, on_fail):
        import jabber
        if not issubclass(self.protocol_class(), jabber.protocol):
            return log.warning('cannot delete from server: %r is not a jabber subclass', self.protocol_class())

        if password != profile.plain_pw(self.password):
            log.error("password didn't match: %r %r", password, profile.plain_pw(self.password))
            return on_fail()
        if self.connection is None:
            log.error('connection was None')
            return on_fail()

        self.connection.delete_account(on_success=on_success, on_fail=on_fail)

    @action(lambda self: True if hasattr(self.connection, 'change_password') else None,
            needs = '@gui.protocols.jabbergui.PasswordChangeDialog')
    @callsback
    def change_password(self, password, callback=None):
        self.connection.change_password(password, success= lambda s:
                                            self.change_acct_password(password,
                                                                      callback=callback),
                                            error=lambda s:
                                            wx.MessageBox("Failed to change password",
                                            "Failed to change password"))

    @callsback
    def change_acct_password(self, password, callback=None):
        self.password = profile.crypt_pw(str(password))
        profile.update_account(self)
        callback.success()

    def __call__(self): return self.toggle_connect()

    @classmethod
    def from_net(cls, acct):
        if acct.id not in cls._ids:
            cls._ids.insert(acct.id, acct.id)
        try:
            opts = cPickle.loads(acct.data)
        except:
            opts = {}
        return cls(name = acct.username,
                   password = acct.password,
                   protocol = acct.protocol,
                   id=acct.id,
                   **opts)

    def update(self):
        profile.update_account(self)

    def setup_linkrefs(self):
        reason = StateMixin.Reasons
        state  = StateMixin.Statuses
        connect, disconnect = lambda *a: self.Connect(), lambda *a: self.disconnect()

        self.linkrefs = {
            (state.OFFLINE, reason.SERVER_ERROR)        : (_('Connect'),       connect),
            (state.OFFLINE, reason.BAD_PASSWORD)        : (_('Edit Account'),  lambda *a: profile.account_manager.edit(self,True)),
            (state.OFFLINE, reason.CONN_FAIL)           : (_('Retry'),         connect),
            (state.OFFLINE, reason.OTHER_USER)          : (_('Reconnect'),     connect),
            (state.OFFLINE, reason.CONN_LOST)           : (_('Reconnect'),     connect),
            (state.OFFLINE, reason.RATE_LIMIT)          : (_('Reconnect'),     connect),
            (state.OFFLINE, reason.WILL_RECONNECT)      : (_('Cancel'),        lambda *a: profile.account_manager.cancel_reconnect(self)),
            (state.OFFLINE, reason.NONE)                : (_('Connect'),       connect),
            (state.ONLINE, reason.NONE)                 : (_('Disconnect'),    disconnect),
            (state.CONNECTING, reason.NONE)             : (_('Cancel'),        disconnect),
            (state.AUTHENTICATING, reason.NONE)         : (_('Cancel'),        disconnect),
            (state.LOADING_CONTACT_LIST, reason.NONE)   : (_('Cancel'),        disconnect),
        }

        return self.linkrefs

    def get_link(self):
        reason = StateMixin.Reasons
        state  = StateMixin.Statuses

        try:
            linkrefs = self.linkrefs
        except AttributeError:
            linkrefs = self.setup_linkrefs()

        try:
            return linkrefs[(self.state, self.offline_reason)]
        except KeyError:
            log.critical('(%r,%r) not in linkref dictionary', self.state, self.offline_reason)
            if self.state == state.ONLINE:
                return linkrefs[(state.ONLINE, reason.NONE)]
            else:
                return '',''

    def get_error_txt(self):
        return getattr(self, '_error_txt', False) or getattr(getattr(self, 'connection', None),
                                                             'error_txt', False)

    def set_error_txt(self, value):
        self._error_txt = value

    def del_error_txt(self):
        self._error_txt = False
        try:
            del self.connection.error_txt
        except Exception:
            pass

    error_txt = property(get_error_txt, set_error_txt, del_error_txt)

    @property
    def allow_contact_add(self):
        if self.protocol_info().get('allow_contact_add', True):
            return True
        else:
            if profile.prefs.get('%s.allow_add' % self.protocol, False):
                return True
            else:
                return False
