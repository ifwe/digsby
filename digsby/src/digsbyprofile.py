'''
digsbyprofile.py

Global account information and preferences.
'''

from __future__ import with_statement
import wx
import sys
import logging
import traceback
from digsby.DigsbyProtocol import DigsbyProtocol
from util.threads.timeout_thread import ResetTimer
from common import netcall
from common.Buddy import LogSizeDict
from util.primitives.funcs import Delegate, PausableDelegate, CallCounter
from common.statusmessage import StatusMessage
from prefs.prefsdata import localprefs
from digsby.loginutil import DigsbyLoginError
from hashlib import sha1
from functools import partial
from util.observe import ObservableDict, ObservableList, Observable, ObservableProperty
from collections import defaultdict
from common import AccountBase, StateMixin
from util import dictadd, Storage, traceguard, try_this, dictdiff, threaded
from util.primitives.funcs import get
from util.callbacks import callsback, do_cb, wxcall
from cStringIO import StringIO
from path import path
from PIL import Image
from util.cacheable import save_cache_object, load_cache_object
from traceback import print_exc, print_stack
from config import platformName
from peak.util.plugins import Hook
from imaccount import Account, ChatProtocol
from digsby import digsbylocal
import util.cryptography
import hooks
import prefs

STATUS_UPDATE_FREQ_SECS = 60
PREF_UPDATE_FREQ_SECS   = 60
IDLE_UNIT               = 60  # also in seconds

HIBERNATE = "HIBERNATE"
UNHIBERNATE = "UNHIBERNATE"

DISCONNECT_TIMEOUT      = 6
NOWPLAYING_STATUS_PREF = 'plugins.nowplaying.initial_status'

from logging import getLogger
log = getLogger('digsbyprofile')
info = log.info
warning = log.warning

import logextensions
console_handler_class = logextensions.ColorStreamHandler

from common.protocolmeta import proto_init, protocols

DIGSBY_SERVER = ("digsby.org", 5555)
PROMOTE_STRING_HTML = '<br><br>I use <a href="http://www.digsby.com/?utm_source=aim&utm_medium=aim&utm_campaign=aimprofilelink">digsby</a>!'
PROMOTE_STRING_RTF = '\\par\\par I use {\\hl {\\hlloc  http://www.digsby.com/?utm_source=aim&utm_medium=aim&utm_campaign=aimprofilelink } {\\hlfr digsby} }'

profile = None
login_tries = 0


def get_login_tries():
    global login_tries
    return login_tries

initialized = Delegate()

def signin(identity):
    global profile

    if profile is not None:
        try_this(lambda: profile.connection.observers.clear(), None)
        profile = None

    if profile is None:
        profile = DigsbyProfile(identity)

def is_im_account(x):
    'Returns True if x is an IM account.'
    meta = protocols.get(x.protocol, {})
    type = meta.get('type', None)
    return type == 'im' or (type == 'service_component' and meta.get('component_type', None) == 'im')

regular_accounts = is_im_account  # compatibility alias


def email_accounts(x):
    meta = protocols.get(x.protocol, {})
    type = meta.get('type', None)
    return type == 'email' or (type == 'service_component' and meta.get('component_type', None) == 'email')


def social_accounts(x):
    meta = protocols.get(x.protocol, {})
    type = meta.get('type', None)
    return type == 'social' or (type == 'service_component' and meta.get('component_type', None) == 'social')


class DigsbyProfile(Observable, ChatProtocol):
    'A collection of accounts and preferences.'

    MAX_ICON_SIZE  = 96
    MAX_ICON_BYTES = 64 * 1024

    protocol = 'digsby'

    @property
    def display_name(self):
        from common import pref
        return try_this(lambda: getattr(self, pref('profile.display_attr')), self.username)

    def __init__(self, identity):
        Observable.__init__(self)
        ChatProtocol.__init__(self)

        self.identity = identity

        from AccountManager import AccountManager

        self.PreDisconnectHooks  = Delegate()
        self.PostDisconnectHooks = Delegate()

        if not getattr(getattr(sys, 'opts', None), 'limit_log', True):
            DelayedStreamLimiter = lambda s: s
        else:
            from fileutil import DelayedStreamLimiter

        self.consolehandlers = defaultdict(lambda: console_handler_class(DelayedStreamLimiter(sys.stdout)))

        self._status = None

        self.error_count = 0
        self.offline_reason = StateMixin.Reasons.NONE
        self.account_manager = AccountManager(profile = self)
        self.last_hiber_req = None
        self.hibernated = False
        self.linked_observers = False
        self.xfers = ObservableList()
        self.prefs = ObservableDict()
        self.defaultprefs = ObservableDict(prefs.defaultprefs())
        self.quiet = False
        self.prefs_loaded = False

        # set the common.pref lookup to point to our prefs
        import common
        common.set_active_prefs(self.prefs, self.defaultprefs)

        self.prefs.add_observer(self._prefs_changed)

        self.has_authorized = False

        self.statuses = ObservableList()
        self.statuses.add_observer(self._statuses_changed)

        self._xfercount = 0
        self.xfers.add_observer(self._on_file_transfer)

        self.widgets = ObservableList()

        self._encrypter, self._decrypter = util.cryptography.cipher_functions(sha1(self.password.encode('utf8')).digest()[:16])

        self.log_sizes = LogSizeDict()

        global profile
        if profile not in (self, None):
            warnmsg = 'Another DigsbyProfile has been created but the old one is still around!'
            if __debug__:
                raise ValueError(warnmsg)
            else:
                log.critical(warnmsg)

        profile = self  # hack! BuddyListStore needs profile.username

        from contacts.buddyliststore import BuddyListStore
        self.blist = BuddyListStore(self.account_manager.connected_accounts)

        self.set_contact_info = self.blist.set_contact_info
        self.get_contact_info = self.blist.get_contact_info

        from BlobManager import BlobManager
        self.blob_manager = BlobManager(self)

        self.account_manager.add_observer(self.check_loading, 'got_accounts')
        self.account_manager.add_observer(self.on_accounts_loaded, 'accounts_loaded')

        self.blob_manager.add_observer(self.check_loading, 'loading')
        self.loaded = False

        self.OnReturnFromIdle = Delegate()
        self.on_message = PausableDelegate()

        self.OnStatusChange = Delegate()

        self.setup_hub()

        self.idle_timer = None
        self.idle = False

        self.plugins_setup = False
        self.connection = None
        self.setup_plugins()

        self.do_local_load()

    @property
    def password(self):
        return self.identity.password
    @property
    def username(self):
        return self.identity.name

    def setup_plugins(self, *a, **k):
        assert not self.plugins_setup
        if not self.plugins_setup:

            self.plugins_setup = True
            wx.CallAfter(self._setup_plugins)

    def _setup_plugins(self):
        for hook in Hook('digsby.profile.addons'):
            try:
                getattr(hook(self), 'setup', lambda *a, **k: None)()
            except Exception:
                traceback.print_exc()

        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.plugin.load.async')

    def stop_timers(self):
        if self.idle_timer:
            self.idle_timer.stop()

    def _get_status(self):
        if self._status is None:
            self._status = self.load_saved_status()

        return self._status

    def _set_status(self, val):

        # digsby go_idle

        self._status = val
        if val is not None:
            if val.status != 'Idle':
                self.save_status()

    status = property(_get_status, _set_status)

    def setup_hub(self):
        import hub
        h = hub.get_instance()
        if h.filter_message not in self.on_message:
            self.on_message += h.filter_message

        # register IM windows for incoming messages
        from gui.imwin import on_message
        self.on_message += lambda *a, **k: wx.CallAfter(on_message, *a, **k)

        self.on_message.pause()

    def set_profile_blob(self, new_profile):
        self.profile = new_profile

        fstr = self.profile

        for acct in profile.account_manager.connected_accounts:
            self.set_formatted_profile(acct.connection, fstr)

        self.save()

    def on_chat_invite(self, protocol, buddy, message, room_name, on_yes=None, on_no=None):
        @wx.CallAfter
        def after():
            import hub
            hub.get_instance().on_invite(protocol=protocol,
                buddy=buddy,
                message=message,
                room_name=room_name,
                on_yes=on_yes,
                on_no=on_no)

    def on_entered_chat(self, convo):
        return self.on_message(convo=convo, raisenow=True)

    def set_formatted_profile(self, protocol, fstr=None):
        if fstr is None:
            fstr = self.profile

        # $$plugin setprofile
        import plugin_manager.plugin_hub as plugin_hub
        if not plugin_hub.act('digsby.im.setprofile.pre', protocol, fstr):
            return

        plugin_hub.act('digsby.im.setprofile.async', protocol, fstr)

        add_promo_string = self.prefs.get('profile.promote', True)
        if fstr.bestFormat == "rtf":
            if add_promo_string:
                fstr = fstr + PROMOTE_STRING_RTF
            format = None
        else:
            #legacy profile support
            if add_promo_string:
                fstr = fstr.format_as("plaintext").encode('xml') + PROMOTE_STRING_HTML
            from gui.uberwidgets.formattedinput import get_default_format
            format = get_default_format('profile.formatting')

        netcall(lambda: protocol.set_profile(fstr, format))

    def set_profile(self, *a, **k):
        pass

    def _on_file_transfer(self, src, attr, old, new):
        if all((not getattr(x, 'autoshow', True)) for x in new if x not in (old or []) and
               (x.state not in (x.states.CompleteStates | x.states.FailStates))):
            self._xfercount = len(new)
            return
        new, old = len(self.xfers), self._xfercount

        if self.prefs.get('filetransfer.window.show_on_starting', True) and new > old:
            from gui.filetransfer import FileTransferDialog
            wx.CallAfter(FileTransferDialog.Display)

        self._xfercount = new

    def __repr__(self):
        return AccountBase._repr(self)

    def _reconnect(self, initial=False):
        if getattr(self, 'connection', None) is not None:
            self.connection.observers.clear()
            self.connection.Disconnect()
            del self.connection

        self.disconnecting = False

        extra = {}
        resource = getattr(getattr(sys, 'opts', None), 'resource', None)
        if resource is not None:
            extra['resource'] = resource
        elif getattr(sys, 'DEV', False):
            extra['resource'] = 'dev'
        import hub
        conn = self.connection = DigsbyProtocol(self.username, self.password,
                                                self, hub.get_instance(),
                                                DIGSBY_SERVER,  # srvs,
                                                do_tls = False,
                                                sasl_md5 = False,
                                                digsby_login=True,
                                                initial=initial,
                                                **extra
                                                )
        conn.account = self

        conn.add_observer(self.connection_state_changed, 'state')
        conn.add_observer(self.offline_changed, 'offline_reason')

        conn.Connect(on_success = getattr(getattr(self, 'callback', None), 'success', None),
                     on_fail = self.connect_error)

    def do_local_load(self):
        self.local_load_exc = None
        self.blob_manager.load_from_identity(identity = self.identity)
        self.account_manager.load_from_identity(identity = self.identity)

    def connect_error(self):
        if self.has_authorized:
            return self.callback.error()
        else:
            return self.local_login()

    def local_login(self):
        '''
        After a failed network login, attempt to "log in" with self.username and
        self.password to the local accounts store.
        '''
        try:
            exc, self.local_load_exc = self.local_load_exc, None
            if exc is not None:
                raise exc
        except digsbylocal.InvalidPassword:
            self.callback.error(DigsbyLoginError('auth'))
        except Exception:
            self.callback.error()
        else:
            self.blob_manager.local_load()

            # Setup connection and call load_cb
            self.connection_state_changed(None, 'state', None, DigsbyProtocol.Statuses.AUTHORIZED)

            self.connection_state_changed(None, 'state', None, DigsbyProtocol.Statuses.ONLINE)
            self.offline_reason = DigsbyProtocol.Reasons.CONN_LOST
            self.offline_changed(None, 'offline_reason', None,
                                 DigsbyProtocol.Reasons.CONN_LOST)
            self.connection_state_changed(None, 'state', None, DigsbyProtocol.Statuses.OFFLINE)
            self.account_manager.do_load_local_notification()

    def offline_changed(self, src, attr, old, new):
        self.notify(attr, old, new)

    def connection_state_changed(self, src, attr, old, new):
        assert False
        log.info('connection_state_changed %r -> %r', old, new)

        assert type(src) in (DigsbyProtocol, type(None))

        if attr == 'state' and new == getattr(DigsbyProtocol.Statuses, 'AUTHORIZED', Sentinel()):
            self.error_count = 0
            self.watch_account(self)
            self.has_authorized = True
            log.info('Calling load with cb of %r', self.callback)

            self.load(self.callback)
            conn = self.connection
            if conn is not None:
                conn._set_status_object(profile.status)

        elif attr == 'state' and new == DigsbyProtocol.Statuses.OFFLINE:
            self.setnotifyif('offline_reason', getattr(src, 'offline_reason', None))
            if not self.has_authorized and getattr(src, 'offline_reason', None) == DigsbyProtocol.Reasons.BAD_PASSWORD:
                self.unwatch_account(self)
            if self in self.account_manager.connected_accounts:
                self.account_manager.connected_accounts.remove(self)
                self.account_manager.unwatch_account(self)
            self.connection = None

            dccb = getattr(self, '_disconnect_cb', None)
            if dccb is not None:
                self._disconnect_cb = None
                dccb.success()

        elif attr == 'state' and new == DigsbyProtocol.Statuses.ONLINE:
            self.reconnected_callbacks(self.connection)

        self.notify('state', old, new)

    @property
    def state(self):
        return try_this(lambda: self.connection.state, StateMixin.Statuses.OFFLINE)

    def when_active(self, callback):
        if not hasattr(callback, '__call__'):
            raise TypeError('argument "callback" must be callable')

        if self.idle:
            if callback not in self.OnReturnFromIdle:
                self.OnReturnFromIdle += callback
                log.info('added a callback to the idle queue: %r', callback)
            else:
                log.info('callback already in idle queue')
        else:
            log.info('not idle, calling now')
            return callback()

    @wxcall
    def signoff(self, kicked=False):
        'Return to the splash screen.'

        # $$plugin unload
        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.plugin.unload.async')

        if platformName == 'win':
            return wx.GetApp().Restart()

        # todo: confirm if there are (active) file transfers

        # hide all top level windows
        top = wx.GetTopLevelWindows
        for win in top():
            win.Hide()

        del self.on_message[:]
        del self.OnReturnFromIdle[:]
        self.stop_timers()

        def dodisconnect(success = True):

            if not success:
                log.info('there was an error saving all blobs.')

            # disconnect all accounts
            with traceguard:
                self.disconnect()

            # destroy all top level windows
            f = getattr(wx.GetApp(), 'buddy_frame', None)
            if f:
                f.on_destroy()

            for win in top():
                with traceguard:
                    if not win.IsDestroyed():
                        win.Destroy()

            # clear input shortcuts
            from gui.input.inputmanager import input_manager
            input_manager.reset()

            import gc
            import observe
            gc.collect()

            numCleared = observe.clear_all()
            log.info('cleared %d observers dicts', numCleared)

            # show the splash, preventing autologin
            wx.GetApp().ShowSplash(autologin_override = False, kicked=kicked)

        log.info('saving all blobs before signoff...')
        self.save(success = dodisconnect,
                  error   = lambda: dodisconnect(False))

        from gui import toast
        toast.cancel_all()

    def _statuses_changed(self, src, attr, old, new):
        if not hasattr(self, 'status_timer'):
            self.status_timer = t = ResetTimer(STATUS_UPDATE_FREQ_SECS, self._on_status_timer)
            t.start()
        else:
            self.status_timer.reset()

    def _on_status_timer(self):
        self.status_timer.stop()
        netcall(lambda: self.save('statuses'))

    def _prefs_changed(self, src, attr, old, new):
        if not hasattr(self, 'pref_timer'):
            self.pref_timer = t = ResetTimer(PREF_UPDATE_FREQ_SECS, self._on_pref_timer)
            t.start()
        else:
            self.pref_timer.reset()

    def _on_pref_timer(self):
        self.pref_timer.stop()
        netcall(lambda: self.save('prefs'))

    def SetStatusMessage(self, message, editable = True, edit_toggle = True, **k):
        new_status = StatusMessage(title = None,
                                   status = self.status.status,
                                   message = message,
                                   editable = editable,
                                   edit_toggle = edit_toggle)

        import hooks
        hooks.notify('digsby.statistics.ui.select_status')
        self.set_status(new_status)

    def maybe_return_from_offline(self):
        '''Called by IM accounts when they are connecting to clear an "Offline" status.'''

        if hasattr(self, 'were_connected'):
            log.info("protocol has 'were_connected', deleting and setting Available")
            del self.were_connected

            status = getattr(self, 'were_connected_status', StatusMessage.Available)
            self.set_status(status)

    def set_status(self, status):
        '''
        Takes a StatusMessage object and sets the status in all connected (and
        which will connect in the future) accounts.
        '''
        if status == self.status:
            return log.warning('set_status got an identical status.')

        # $$plugin status change
        from plugin_manager import plugin_hub
        plugin_hub.act('digsby.im.mystatuschange.pre', status)

        if status == '':
            return

        plugin_hub.act('digsby.im.mystatuschange.async', status)

        for hook in Hook('digsby.im.statusmessages.set.pre'):  # can't use query or notify (want the chained effect)
            status = hook(status)

        log.warning('set_status got %r', status)

        accts = [a for a in self.account_manager.connected_accounts if a is not self]

        def allaccts(func):
            for a in accts:
                with traceguard:
                    func(a)

        Offline   = StatusMessage.Offline

        # disconnecting
        if status == Offline:
            log.info('disconnecting all connected accounts')

            # store a list of the accounts which were connected prior
            # to disconnecting.
            self.were_connected = accts[:]
            self.were_connected_status = self.status
            allaccts(lambda a: a.disconnect())
        #reconnecting
        elif self.status == Offline and hasattr(self, 'were_connected'):
            accts = self.were_connected
            del self.were_connected
            for acct in accts:
                with traceguard:
                    if acct in self.account_manager.accounts:
                        acct.connect(invisible=(status.for_account(acct).invisible))
                    else:
                        log.warning('not reconnecting %s', acct)
        else:
            for acct in self.account_manager.connected_accounts[:]:
                with traceguard:
                    prev_invis = self.status.for_account(acct).invisible
                    this_invis = status.for_account(acct).invisible
                    #going to/returning from invisible
                    if (prev_invis or this_invis) and this_invis != prev_invis:
                        acct.connection.set_invisible(this_invis)
                    #just setting a status
                    if not this_invis:
                        acct.connection._set_status_object(status)

        self.setnotifyif('status', status.copy(editable=None, edit_toggle=None))
        self.save_status()

        hooks.notify('digsby.im.statusmessages.set.post', self.status)

    def add_account(self, **attrdict):
        # $$plugin
        self.account_manager.add(Account(**attrdict), 'im')
        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.im.addaccount.async', attrdict['protocol'], attrdict['name'])

    def add_email_account(self, **info):
        protocol = info.get('protocol')
        name = info.get('name')

        self.account_manager.add(proto_init(protocol)(**info), 'em')

        # $$plugin
        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.email.addaccount.async', protocol, name)

    def add_social_account(self, **info):
        protocol = info.pop('protocol')
        name = info.get('name')

        acct = proto_init(protocol)(**info)
        self.account_manager.add(acct, 'so')

        # $$plugin
        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.social.addaccount.async', protocol, name)
        return acct

    def register_account(self, on_success, on_fail, **attrdict):
        newacct = Account(**attrdict)
        newacct.connect(register = True, on_success=on_success, on_fail=on_fail)

    def update_account(self, account, force=False):

        self.account_manager.update_account(account, force=force)

        # $$plugin
        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.updateaccount.async', account)

    def add_status_message(self, status_obj = None, **info):
        if status_obj is None:
            assert info
            self.statuses.append(StatusMessage(**info))
        else:
            assert info == {}
            self.statuses.append(status_obj)

    def remove_account(self, account):
        self.account_manager.remove(account)

        # $$plugin
        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.removeaccount.async', account)

    remove_email_account = \
    remove_social_account = \
    remove_account

    def remove_status_message(self, status_message):
        self.statuses.remove(status_message)

    def get_widgets(self):
        self.connection.get_widgets()

    def incoming_widgets(self, widgets):
        self.widgets[:] = widgets
        hooks.notify('digsby.widgets.result', widgets)

    def blob_failed(self, name):
        try:
            self.connection.Disconnect()
            self.offline_changed(None, 'offline_reason', None,
                                 DigsbyProtocol.Reasons.CONN_FAIL)
        except Exception:
            pass

    def update_blob(self, name, useful_data):
        if name == 'prefs':

            log.critical('prefs updated from the network')

            with self.prefs.flagged('network'):
                if 'defaultprefs' not in self.blob_manager.waiting_blobs:
                    new_prefs = dictadd(self.defaultprefs, useful_data)
                    self.prefs.update(new_prefs)
                else:
                    self.prefs.update(useful_data)
                    new_prefs = useful_data
                if hasattr(self, 'defaultprefs'):
                    for key in set(self.prefs.keys()) - (set(new_prefs.keys()) | set(self.defaultprefs.keys())):
                        self.prefs.pop(key, None)

            self.prefs_loaded = True
            hooks.notify('blobs.update.prefs', self.prefs)

        elif name == 'defaultprefs':
            if 'prefs' not in self.blob_manager.waiting_blobs:
                new_prefs = dictadd(useful_data, self.prefs)
                self.prefs.update(new_prefs)
                if hasattr(self, 'defaultprefs'):
                    for key in set(self.defaultprefs.keys()) - set(useful_data.keys()):
                        self.prefs.pop(key, None)
            self.defaultprefs.update(useful_data)

        elif name == 'buddylist':
            self.blist.update_data(useful_data)

        elif callable(getattr(self, '_incoming_blob_' + name, None)):
            getattr(self, '_incoming_blob_' + name)(useful_data)

        else:
            log.critical('replacing profile attribute %s', name)
            if name == 'statuses':
                assert False
            setattr(self, name, observable_type(useful_data))

    def _incoming_blob_profile(self, profile_str_or_fmtstr):
        from util.primitives.fmtstr import fmtstr

        # self.profile used to be a string, but now it is a fmtstr, and goes out
        # over the wire as a JSON dict.
        #
        # assume that if we cannot parse the incoming profile blob as JSON, then
        # it must be an old-style string profile.
        if isinstance(profile_str_or_fmtstr, dict):
            fstr = fmtstr.fromDict(profile_str_or_fmtstr)
        else:
            from gui.uberwidgets.formattedinput import get_default_format
            fstr = fmtstr.singleformat(profile_str_or_fmtstr, format=get_default_format('profile.formatting'))

        self.profile = fstr

    def _incoming_blob_statuses(self, newdata):
        data = [(StatusMessage(**d) if isinstance(d, dict)
                             else d) for d in newdata]
        self.statuses[:] = data

    def _incoming_blob_notifications(self, newdata):
        def fix_underscore(d):
            for key in d.keys()[:]:
                if key and '_' in key:
                    d[key.replace('_', '.')] = d.pop(key)

        if not hasattr(self, 'notifications'):
            self.notifications = ObservableDict()
        else:
            fix_underscore(self.notifications)

        fix_underscore(newdata)

        self.notifications.update(newdata)
        import common.notifications

        # for any notification keys that exist in YAML, but not in the users
        # blob, add them with the values in the YAML 'default' key
        ni = common.notifications.get_notification_info()
        base = self.notifications[None]
        for k in ni:
            if k in base:
                continue

            try:
                defaults = ni[k].get('default', {})
                base[k] = [dict(reaction=v) for v in defaults.get('reaction', ())]
            except Exception:
                traceback.print_exc()
                continue

        import hooks
        hooks.notify('digsby.notifications.changed')

    def load(self, cb):
        'Loads network data from the server.'
        self.loaded = False

        def callback(_cb=cb):
            self.loaded = True

            log.info('Calling callback that was given to load: %r', _cb)
            _cb(lambda *a, **k: None)

            self.link_observers()

        with traceguard:
            conn = self.connection
            if conn is not None:
                conn.change_state(self.connection.Statuses.SYNC_PREFS)

                def on_accounts_loaded():
                    # show the myspace account wizard if all you have are the automagic accounts
                    def after():
                        if len(self.accounts) == 0 and \
                           len(self.socialaccounts) == 0 and \
                           len(self.emailaccounts) == 0 and \
                           len(self.widgets) == 0:
                            import gui.accountwizard
                            gui.accountwizard.show()
                    wx.CallLater(1000, after)

                on_accounts_loaded_cc = CallCounter(2, on_accounts_loaded)

                def call_cc(*a, **k):
                    on_accounts_loaded_cc()
                import util.hook_util
                if not util.hook_util.OneShotHook(self, 'digsby.accounts.released.async')(call_cc, if_not_fired=True):
                    call_cc()
                if not util.hook_util.OneShotHook(self, 'digsby.widgets.result')(call_cc, if_not_fired=True):
                    call_cc()

                self.get_widgets()

        self.load_cb = callback

        log.info('Forcing check_loading call')
        self.check_loading()

    def link_observers(self):
        if self.linked_observers:
            return

        link = self.prefs.link
        for pref in ('become_idle', 'idle_after',):
            link('messaging.%s' % pref, getattr(self, '%s_changed' % pref))

        self.setup_logger()
        self.prefs.add_observer(self.link_logging)

        for key in self.prefs:
            self.link_logging(self.prefs, key)

        self.linked_observers = True

    def check_loading(self, src=None, attr=None, old=None, new=None):
        if self.account_manager.got_accounts and not self.blob_manager.loading:
#            if self.connection is not None:
#                log.warning('connection is not None')
#                self.connection.change_state(self.connection.Statuses.ONLINE)
            initialized()
            if not self.loaded:
                self._have_connected = True
#                cb, self.load_cb = self.load_cb, (lambda *a, **k: None)
                self.loaded = True
                self.link_observers()
#                log.info('Calling load_cb: %r', cb)
#                cb()

    def on_accounts_loaded(self, src, attr, old, new):
        if new:
            log.info('unpausing the message queue')
            wx.CallAfter(self.on_message.unpause)

    def link_logging(self, src, key, *a, **k):
        n = 'logging'
        if not isinstance(key, basestring) or not key.startswith(n):
            return
        logname = key[len(n):] or None
        if logname is not None:
            logname = logname.strip('.')
        newlevel = try_this(lambda: int(get(src, key)), 0)
        logging.log(100, 'Setting %s to level %d', logname or 'root', newlevel)

        import main
        if not hasattr(main, 'full_loggers'):
            return  # logging system not setup

        # don't bother modifying console handlers if we never setup any
        if not getattr(main, 'logging_to_stdout', False):
            return

        if not logname:
            logger = logging.getLogger('')
            s_handlers = [h for  h in logger.handlers if (h.__class__ is console_handler_class) and h not in main.full_loggers]
            s_handlers[0].setLevel(newlevel)
        else:
            rootlogger = logging.getLogger('')
            root_handlers = [h for  h in rootlogger.handlers if (h.__class__ is not console_handler_class) or h in main.full_loggers]
            handler = self.consolehandlers[newlevel]
            handler.setLevel(newlevel)

            from main import ConsoleFormatter
            formatter = ConsoleFormatter()

            handler.setFormatter(formatter)
            root_handlers.append(handler)
            new_logger = logging.getLogger(logname)
            new_logger.propagate = False
            new_logger.handlers[:] = root_handlers

    def setup_logger(self):
        'Sets up an IM and event logging object.'
        from common.logger import Logger
        logger = self.logger = Logger()

        # logger receives all messages, incoming and outgoing.
        def later(*a, **k):
            wx.CallLater(1000, threaded(self.logger.on_message), *a, **k)
        self.on_message += lambda *a, **k: wx.CallAfter(later, *a, **k)

        set = lambda attr: lambda val: setattr(self.logger, attr, val)
        link = lambda attr, cb: self.prefs.link(attr, cb, obj = logger)
        link('log.ims',       set('LogIMs'))
        link('log.ims',       set('LogChats'))

    @callsback
    def save(self, saveblobs = None, force = False, callback = None):
        '''
        Save one, or more, or all, data blobs.

        if saveblobs is:
            None: saves all of them
            a string: it must be one of the blob names
            a sequence: all blobs in the sequence will be saved
        '''

        if saveblobs is None:                    # None means all blobs
            saveblobs = self.blob_manager.blob_names
        elif isinstance(saveblobs, basestring):  # put a string into a list
            saveblobs = [saveblobs]

        # check for correct blobnames
        diff = set(saveblobs) - set(self.blob_manager.blob_names)
        if len(diff) > 0:
            raise ValueError('illegal blob names: %s' % ', '.join(diff))

        saveblobs = set(saveblobs)
        waiting = set(self.blob_manager.waiting_blobs)
        output = saveblobs - waiting

        if len(output) < len(saveblobs):
            log.info("blobs failed to save, not yet loaded: %r",
                     waiting & saveblobs)

        if self.blob_manager.loading:
            info('blobs still loading, disallowing save')
            callback.success()
            return
        else:
            saveblobs = list(output)

        info('saving blobs %s', ', '.join(saveblobs))

        cbs = []
        for name in saveblobs:
            if name == 'buddylist':
                cbs.append(partial(self.blob_manager.set_blob, name,
                                   data = self.blist.save_data(), force = force))
            elif name == 'prefs':
                cbs.append(partial(self.save_out_prefs, force = force))
            elif name == 'defaultprefs':
                pass
            elif name == 'statuses':
                data = [s.__getstate__(network=True) for s in self.statuses]
                for s in data:
                    s['format'] = dict(s['format']) if s['format'] is not None else None
                cbs.append(partial(self.blob_manager.set_blob, name,
                                   data = data,
                                   force = force))
            elif name == 'profile':
                data = self.profile.asDict()
                cbs.append(partial(self.blob_manager.set_blob, name, data=data, force=force))
            else:
                cbs.append(partial(self.blob_manager.set_blob, name,
                                   data = to_primitive(getattr(self, name)),
                                   force = force))

        do_cb(cbs, callback = callback)

    def backup_blobs(self, dir):
        pth = path(dir)
        from util.json import pydumps
        from time import time
        for name in ['profile', 'buddylist', 'notifications', 'prefs', 'statuses', 'icon']:
            if name == 'buddylist':
                data = self.blist.save_data()
            elif name == 'prefs':
                data = to_primitive(dictdiff(profile.defaultprefs, self.prefs))
            elif name == 'defaultprefs':
                pass
            elif name == 'statuses':
                data = [s.__getstate__() for s in self.statuses]
                for s in data:
                    s['format'] = dict(s['format'])
            else:
                data = to_primitive(getattr(self, name))
            f = pth / name + '_' + str(int(time())) + '.blob'
            with f.open('wb') as out:
                if name == 'icon':
                    out.write(data)
                else:
                    out.write(pydumps(data).encode('z'))

    @property
    def localprefs(self):
        return localprefs()

    @callsback
    def save_blob(self, name, data, callback = None):
        assert name not in ('buddylist', 'prefs', 'defaultprefs', 'statuses')

        log.critical('replacing attribute %s in profile', name)
        setattr(self, name, data)
        self.blob_manager.set_blob(name, data = to_primitive(getattr(self, name)),
                                 callback = callback)

    @callsback
    def save_out_prefs(self, force = False, callback = None):
        'Pack the data and send it to the server.'
        data = dictdiff(profile.defaultprefs, self.prefs)
        self.blob_manager.set_blob('prefs', data = to_primitive(data), force = force,
                                 callback = callback)

    @callsback
    def disconnect(self, callback = None):
        if getattr(self, 'disconnecting', False):
            return

        self.disconnecting = True
        self.PreDisconnectHooks()

        complete_disconnect = lambda: self._finish_disconnect(callback=callback)
        self.account_manager.disconnect_all(
            success = lambda :
                self.disconnect_profile(success = complete_disconnect,
                                        error = complete_disconnect))

        self._force_dc_timer = util.Timer(DISCONNECT_TIMEOUT, complete_disconnect)
        self._force_dc_timer.start()

        self.stop_timers()

    @callsback
    def disconnect_profile(self, callback = None):
        log.info('Disconnect digsbyprofile')
        self._disconnect_cb = callback
        if getattr(self, 'connection', None) is not None:
            self.connection.Disconnect()

    def _finish_disconnect(self, callback):
        try:
            log.info('finishing profile disconnect')
            if getattr(self, '_force_dc_timer', None) is not None:
                self._force_dc_timer.stop()
                self._force_dc_timer = None

            self.PostDisconnectHooks()

        finally:
            callback.success()

    def hibernate(self):
        #called from windows (should be on wx thread)
        self.last_hiber_req = HIBERNATE
        self.check_hibernate_state()

    def unhibernate(self, delay = 15):
        #called from windows (should be on wx thread)
        self.last_hiber_req = UNHIBERNATE
        delay = max(int(delay), 0)
        if delay:
            wx.CallLater(delay * 1000, self.check_hibernate_state)
        else:
            self.check_hibernate_state()

    def check_hibernate_state(self):
        if self.last_hiber_req == HIBERNATE:
            if self.hibernated:
                return
            else:
                self.hibernated = True
                self._do_hibernate()
                return
        elif self.last_hiber_req == UNHIBERNATE:
            if not self.hibernated:
                return
            else:
                self.hibernated = False
                self._do_unhibernate()
                return

    def _do_hibernate(self):
        log.warning("HIBERNATING")
        self.hibernated_im     = hibernated_im     = []
        self.hibernated_email  = hibernated_email  = []
        self.hibernated_social = hibernated_social = []
        for a in self.account_manager.connected_accounts[:]:
            if a is not self:
                with traceguard:
                    a.disconnect()
                    hibernated_im.append(a)

        for a in self.account_manager.emailaccounts:
            with traceguard:
                if a.enabled:
                    a.set_enabled(False)
                    a.disconnect()
                    hibernated_email.append(a)

        for a in self.account_manager.socialaccounts:
            with traceguard:
                if a.enabled:
                    a.set_enabled(False)
                    a.Disconnect()
                    hibernated_social.append(a)

        if getattr(self, 'connection', None) is not None:
            self.connection.Disconnect()
        log.warning("HIBERNATED")

    def _do_unhibernate(self):
        log.warning("UN-HIBERNATING")
        hibernated_im     = self.hibernated_im
        hibernated_email  = self.hibernated_email
        hibernated_social = self.hibernated_social
        for a in hibernated_im:
            with traceguard:
                a._reconnect()

        for a in hibernated_email:
            with traceguard:
                a.set_enabled(True)

        for a in hibernated_social:
            with traceguard:
                a.set_enabled(True)

        self._reconnect()
        log.warning("UN-HIBERNATED")

    @property
    def allow_status_changes(self):
        'Used by the main status combo do decide whether or not to show itself.'

        if hasattr(self, 'were_connected'):
            # This means that "Disconnected" was selected in the Status dialog
            # were_connected is a list of account objects to reconnect if the
            # status is changed again.
            return True

        connecting = [a for a in self.account_manager.accounts if getattr(a, 'connection', None) is not None and
                      a.connection.state != a.connection.Statuses.OFFLINE]

        if connecting:
            return True

        return False

    def plain_pw(self, password):
        "Returns pw decrypted with the profile's password as the key."

        return self._decrypter(password if password is not None else '').decode('utf-8')

    def crypt_pw(self, password):
        "Returns pw encrypted with the profile's password as the key."
        if password and not isinstance(password, unicode):
            print_stack()
        return self._encrypter((password if password is not None else '').encode('utf-8'))

    @property
    def is_connected(self):
        return bool(getattr(self, 'connection', None) and (self.connection.state == self.connection.states['Connected'] or
                                                           self.connection.is_connected))

    #
    # buddy icon
    #

    def get_icon_bitmap(self):
        'Returns the current buddy icon.'

        if self.icon is None:
            log.info('get_icon_bitmap: self.icon is None, returning None')
            return None
        elif self.icon == '\x01':
            # a single 1 byte in the database means "use the default"
            # and is set in newly created accounts.
            img = wx.Image(path('res') / 'digsbybig.png')
            if not img.Ok():
                log.warning('get_icon_bitmap: could not load digsbybig.png, returning None')
                return None
            return wx.BitmapFromImage(img).Resized(self.MAX_ICON_SIZE)
        else:
            try:
                return Image.open(StringIO(self.icon)).WXB
            except Exception:
                log.warning('could not create wxImageFromStream with profile.icon data')
                return None

    def get_icon_bytes(self):
        if self.icon is None:
            return None
        elif self.icon == '\x01':
            return (path('res') / 'digsbybig.png').bytes()
        else:
            return self.icon

    @property
    def name(self):
        return self.username

    def protocol_info(self):
        return protocols['digsby']

    @property
    def metacontacts(self):
        return self.blist.metacontacts

    @property
    def buddylist(self):
        'Returns the buddylist GUI window.'

        return wx.FindWindowByName('Buddy List').Children[0].blist

    def __getattr__(self, attr):
        try:
            return Observable.__getattribute__(self, attr)

        except AttributeError, e:
            try:
                return getattr(self.account_manager, attr)
            except AttributeError:
                raise e

    def get_is_connected(self):
        conn = getattr(self, 'connection', None)
        return bool(conn and (conn.state in (conn.Statuses.ONLINE, conn.Statuses.AUTHORIZED)
                              or conn.is_connected))

    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.protocol)

    is_connected = ObservableProperty(get_is_connected, observe='connection')
    connected = property(lambda self: self.is_connected)

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

    def load_saved_status(self):
        try:
            saved_status = load_cache_object('laststatus', user=True)
        except Exception:
            saved_status = None
            print_exc()

        return saved_status if saved_status is not None else StatusMessage.Available

    def save_status(self):
        status = self._status
        if not any((status.offline, status.idle)):
            with traceguard:
                save_cache_object('laststatus', status, user=True)

    def become_idle_changed(self, new):
        from common import pref
        minutes = pref('messaging.idle_after', default=10, type=float)
        if self.idle_timer is None:
            self.idle_timer = util.RepeatTimer(minutes * IDLE_UNIT, self.set_idle)
            if new:
                self.idle_timer.start()
            else:
                self.idle_timer.stop()  # so that reset can work below.
        else:
            if new:
                self.idle_timer.reset()
            else:
                self.idle_timer.stop()

    def idle_after_changed(self, minutes):
        from common import pref
        minutes = try_this(lambda: float(minutes),
                  try_this(lambda: float(pref('messaging.idle_after', 10)), 10))
        if pref('messaging.become_idle', True):
            self.idle_timer.reset(minutes * IDLE_UNIT)

    def reset_timers(self):
        if self.idle_timer:
            self.idle_timer.reset()

    def set_idle(self, *a, **k):
        self.idle_timer.stop()
        # $$plugin load
        import plugin_manager.plugin_hub as plugin_hub
        if not plugin_hub.act('digsby.goidle.pre'):
            return
        plugin_hub.act('digsby.goidle.async')

        from common import pref
        if not pref('messaging.become_idle'):
            log.debug('idle is not enabled')
            return

        if self.status.invisible or self.status.offline:
            log.debug('currently invisible, not setting idle')
            return

        idle_msg = self.status.copy(status=StatusMessage.Idle.status)
        self.last_status = self.status

        self.setnotify('status', idle_msg)

        for acct in self.account_manager.connected_accounts:
            log.info('Setting idle on %r to %r', acct, self.idle_timer._interval)
            try:
                acct.connection.set_idle(self.idle_timer._interval)
            except Exception:
                log.error('Failed to set idle on this account: %r', acct)
                print_exc()

        log.info('setting idle = True')
        self.idle = True

    def return_from_idle(self):
        if self.idle:

            # $$plugin load
            import plugin_manager.plugin_hub as plugin_hub
            if not plugin_hub.act('digsby.unidle.pre'):
                return

            plugin_hub.act('digsby.unidle.async')

            self.idle = False
            for acct in profile.account_manager.connected_accounts:
                try:
                    acct.connection.set_idle(0)
                except Exception:
                    log.error('Failed to return from idle on this account: %r', acct)
                    print_exc()

            log.info('return from idle')

            from common import pref
            util.call_later(pref('profile.idle_return_delay', default=0, type=int), self.OnReturnFromIdle.call_and_clear)

            if self.last_status is not None:
                self.set_status(self.last_status)
                self.last_status = None

    @property
    def allow_contact_add(self):
        return self.prefs.get('digsby.allow_add', False)

    def get_account_for_protocol(self, proto):
        return self.account_manager.get_account_for_protocol(proto)

    def find_account(self, username = None, protocol = None):
        return self.account_manager.find_account(username, protocol)


def observable_type(thing):
    if type(thing) is list:
        return ObservableList(thing)
    elif type(thing) in (dict, Storage):
        return ObservableDict(thing)
    return thing


def to_primitive(thing):
    if isinstance(thing, ObservableDict):
        return dict(thing)
    elif isinstance(thing, ObservableList):
        return list(thing)
    return thing

import digsby.videochat
digsby.videochat.register_message_hook()


def on_prefs_loaded(prefs):
    '''
    for upgrading prefs
    '''

    old_focus_pref = 'conversation_window.steal_focus'
    new_focus_pref = 'conversation_window.new_action'

    steal_focus = prefs.pop(old_focus_pref, None)
    if steal_focus is not None:
        log.info('upgraded conversation_window.steal_focus pref')
        prefs[new_focus_pref] = 'stealfocus' if steal_focus else 'minimize'

hooks.register('blobs.update.prefs', on_prefs_loaded)


def load_local_accounts(username, password):
    '''
    Loads local accounts for a username and password.

    Returns tuple of (digsby.accounts.Accounts,
                      server_hash,
                      server_order)
    '''
    local_info = digsbylocal.load_local(username, password)
    server_info = digsbylocal.load_server(username, password)

    from digsby.accounts import Accounts
    return Accounts.from_local_store(local_info), server_info['accounts_hash'], server_info['server_order']


def set_simple_status(status):
    profile.set_status(profile.status.copy(status=status.title()))

from digsby_chatlogs.interfaces import IAliasProvider
from digsby_chatlogs.profilealiases import ProfileAliasProvider
import protocols as ptcls
ptcls.declareAdapterForType(IAliasProvider, ProfileAliasProvider, DigsbyProfile)
