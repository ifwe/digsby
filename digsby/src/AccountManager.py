from __future__ import with_statement
from contextlib import contextmanager, nested
from threading import RLock
from util.primitives import with_traceback
from common.hashacct import HashedAccounts
from util import threaded
from util.primitives.funcs import Delegate
from util.threads.timeout_thread import Timer, wakeup as wakeup_timeout_thread
import traceback
import util
import sys
import cPickle
import itertools
import hooks
import functools

from util.observe import ObservableList, Observable
from common import pref, StateMixin, UpdateMixin, fire
from util import Storage, traceguard, call_later, nicetimecount
from util.primitives.funcs import get
from util.primitives.structures import oset
from util.threads.bgthread import on_thread

from common.protocolmeta import protocols
from common.emailaccount import EmailAccount
from common.buddy_watcher import BuddyWatcher
from digsbyprofile import is_im_account, email_accounts, social_accounts
import social

nice_proto_names = dict((key, protocols[key]['name']) for key in protocols)

import logging
import digsby.digsbylocal

import services.service_provider as SP

log = logging.getLogger('accountmanager')

NETWORK_FLAG = "NETWORK_FLAG"
DELETING = "DELETING"

SECONDS_FOR_IDLE     = 60 * 5

IDLE_RECONNECT_MIN   = 60 * 10
IDLE_RECONNECT_MAX   = 60 * 30
ACTIVE_RECONNECT_MIN = 1
ACTIVE_RECONNECT_MAX = IDLE_RECONNECT_MIN

LOCAL_MODE_URL = 'http://wiki.digsby.com/doku.php?id=faq#q30'

DEBUG_ACCOUNTS = False # more logs
SAVE_ACCOUNTS  = True  # send to disk + server (or not - for debugging or experimental code)

import sys

def accounts_debug(*a, **k):
    return log.debug_s(*a, **k)

def _all_account_call(f):
    @functools.wraps(f)
    def wrapper(self, *a, **k):

        accts = k.pop('accts', self)
        for account in accts:
            with traceguard:
                f(account, *a, **k)

    return wrapper

class AccountManager(Observable, HashedAccounts):

    def __init__(self, profile):
        Observable.__init__(self)

        self.accounts_loaded = False

        self.profile = profile
        self.connected_accounts = ObservableList()
        self.reconnect_timers   = {}

        # holds "cancel" objects from Popups
        self.cancellers = {}

        self.profile.add_observer(self.on_state_change,   'state')
        self.profile.add_observer(self.on_offline_change, 'offline_reason')
        self.profile.add_observer(self.profile_state_changed, 'state')

        import wx
        wx.GetApp().OnBuddyListShown.append(lambda *a, **k: Timer(.25,
            threaded(self.release_accounts), *a, **k).start())

        self._hash = sentinel

        self.got_accounts = False

        self.acct_calls = Delegate()
        self.delay_accounts = True
        self.acct_delay_lock = RLock()

        self._all_acct_hash = {}
        self.last_server_order = None

        self._all_accounts = Storage()
        for type_ in ('im', 'em', 'so'):

            s = Storage(accounts = ObservableList(),
                        old = [])

            setattr(self._all_accounts, type_, s)

            # when the order of accounts changes, or accounts are added or deleted,
            # calls profile.accounts_changed('im', list)
            s.accounts.add_observer(getattr(self, type_ + '_accounts_changed'))

        self.accounts = self._all_accounts.im.accounts
        self.emailaccounts = self._all_accounts.em.accounts
        self.socialaccounts = self._all_accounts.so.accounts

        self.buddywatcher = BuddyWatcher()

        import services.service_provider as sp
        container = sp.ServiceProviderContainer(self.profile)
        container.on_order_changed += self._set_order

    def get_account_for_protocol(self, proto):
        for account in self.connected_im_accounts:
            if getattr(account, 'connection', None) is proto:
                return account

        return None

    def find_account(self, username, protocol):
        for acct in self.all_accounts:
            if acct.username == username and acct.protocol == protocol:
                return acct

        return None

    @property
    def connected_im_accounts(self):
        'A list of all connected IM accounts.'

        accts = list(self.connected_accounts)
        if self.profile in accts:
            accts.remove(self.profile)

        return accts

    def get_im_account(self, username, service):
        for acct in self.connected_accounts:
            conn = acct.connection
            if conn is not None:
                if conn.name == service and conn.username == username:
                    return acct

    @property
    def all_accounts(self):
        'Returns all IM, social, and email accounts in one list.'

        return self.accounts + self.emailaccounts + self.socialaccounts

    def profile_state_changed(self, src, attr, old, new):
        '''
        notify target.
        used to initiate retrieval of accounts from the server
        when the profile goes online
        '''
        assert src == self.profile
        assert attr == 'state'
        from digsby import protocol as digsby_protocol
        if old == new: return


        if new == digsby_protocol.Statuses.SYNC_PREFS:
            with traceguard:
                self.profile.connection.get_accounts(success=lambda stanza:
                                                     self.finished_get(
                                    digsby.accounts.Accounts(stanza.get_query())))

    def _xfrm_sort(self, src, cls, pred):
        '''
        Filters sequence src by predicate pred, and sorts src by its 'order' attribute. Transforms elements
        by calling cls.from_net on each.
        '''
        from common.protocolmeta import protocols, proto_init
        accounts = []
        for x in src:
            if pred(x):
                with traceguard:
                    if x.protocol not in protocols:
                        log.info('don\'t know what kind of account %r is: %r', x.protocol, x)
                        continue

                    if protocols.get(x.protocol, {}).get('smtp_pw_type', False):
                        cls2 = proto_init(x.protocol)
                        acct = cls2.from_net(x)
                    else:
                        acct = cls.from_net(x)

                    accounts.append(acct)

        return sorted(accounts, key=lambda x: src.order.index(x.id) if x.id in src.order else len(src))

    def maybe_delay_accounts(self, cb):
        '''
        if self.delay_accounts is True, calls cb later and returns True.
        '''
        with self.acct_delay_lock:
            if self.delay_accounts:
                self.acct_calls.append(cb)
                return True

    def load_from_identity(self, identity = None):
        '''
        isolating the behavior required to support identities without
        completely trashing the rest of the existing code.
        '''
        self.setnotify('got_accounts', True)
        accounts = identity.load_data('accounts')
        self.replace_local(accounts, do_save=False)
        self.setnotify('accounts_loaded', True)

    def finished_get(self, accounts):
        '''
        this is the response to a get request to the server.
        since we currently only request the entire list,
        the value we get here should be a complete
        representation of what the server has at this moment
        '''
        self.setnotify('got_accounts', True)

        if self.maybe_delay_accounts(lambda: self.finished_get(accounts)):
            return

        if self._all_acct_hash != accounts.calc_hash():
            accounts_debug("!!!!! last known server list is not the same as the server")
            accounts_debug('all_acct_hash: %r', self._all_acct_hash)
            accounts_debug('calc_hash(): %r', accounts.calc_hash())
            self.replace_local(accounts)
        #or if the last recorded server order is not the same as the server now.
        elif self.last_server_order != accounts.order:
            accounts_debug("!!!!! the last recorded server order is not the same as the server now.")
            accounts_debug('last_server_order: %r', self.last_server_order)
            accounts_debug('accounts.order(): %r', accounts.order)
            self.replace_local(accounts)
        #if we made it this far, the server hasn't changed since we last heard
        #from it, therefore, push changes (if any) to the server.
        else:
            accounts_debug('!!!!! update_server')
            self.update_server(accounts)

        self.setnotify('accounts_loaded', True)

    def load_from_local(self, accounts, last_known_server_hash, last_server_order):
        self.setnotify('got_accounts', True)

        if self.maybe_delay_accounts(lambda: self.load_from_local(accounts, last_known_server_hash, last_server_order)):
            return

        self.replace_local(accounts, do_save=False)
        accounts_debug('_all_acct_hash: %r,\nlast_known_server_hash:%r', self._all_acct_hash, last_known_server_hash)
        self._all_acct_hash = last_known_server_hash
        accounts_debug('last_server_order: %r,\nlast_server_order:%r', self.last_server_order, last_server_order)
        self.last_server_order = last_server_order
        self.setnotify('accounts_loaded', True)

    def do_load_local_notification(self):
        if sys.opts.start_offline:
            return # if --online was passed on the command line, don't show a popup

        if self.maybe_delay_accounts(self.do_load_local_notification):
            return

        log.debug('local mode popup')
        fire('error',
             title = _('Digsby is running in "Local Mode"'),
             major =  '',
             minor = _('Changes to Digsby preferences may not synchronize to your other PCs right away'),
             onclick = LOCAL_MODE_URL)

    def replace_local(self, accounts, do_save=True):
        '''
        This function should replace the local list with the server list
        '''
        accounts_debug('replace local')
        # find common simple hashes
        server_list = dict((a.min_hash(), a) for a in accounts)
        accounts_debug('server_list: %r, %r', server_list, accounts)
        local_list = dict((a.min_hash(), a) for a in self)
        accounts_debug('local_list: %r, %r', local_list, list(self))
        common = set(server_list.keys()).intersection(set(local_list.keys()))
        accounts_debug('common: %r', common)

        # update
        update = [server_list[k] for k in common]
        accounts_debug('update: %r', update)

        # delete remainder of local list
        local_del = set(local_list.keys()) - common
        accounts_debug('local_del: %r', local_del)
        delete = [local_list[k] for k in local_del]
        accounts_debug('delete: %r', delete)

        # add remainder of new list
        remote_add = set(server_list.keys()) - common
        accounts_debug('remote_add: %r', remote_add)
        add = [server_list[k] for k in remote_add]
        accounts_debug('add: %r', add)

        # get rid of hashes for things that don't exist anymore.
        # can happen between logins when the server has changed,
        # though it should also require something to have happened locally.
        disappeared = (set(self._all_acct_hash.keys()) - set(a.id for a in accounts)) - set(a.id for a in self)
        for k in disappeared:
            self._all_acct_hash.pop(k, None)

        from digsby.accounts.accounts import Accounts
        add = Accounts(add, order = accounts.order)
        import services.service_provider as sp
        with sp.ServiceProviderContainer(self.profile).rebuilding() as container:
            self.acct_del(delete)
            self.acct_add(add)
            self.acct_update(update)
            container.rebuild(self)
        self.order_set(accounts.order)
        if do_save: self.save_all_info()

    def update_server(self, accounts):
        '''
        This function should do the minmal amount of work required to
        synchronize our local list to the server and other remote clients.
        '''
        accounts_debug('!!!!! update server list')
        server_list = dict((a.id, a) for a in accounts)
        accounts_debug('server_list: %r', server_list)
        local_list = dict((a.id, a) for a in self)
        accounts_debug('local_list: %r', local_list)
        common = set(server_list.keys()).intersection(set(local_list.keys()))
        accounts_debug('common: %r', common)

        #update
        update = []
        for k in common:
            if local_list[k].total_hash() != server_list[k].total_hash():
                accounts_debug("update append: %r != %r", local_list[k].total_hash(), server_list[k].total_hash())
                update.append(local_list[k])
        accounts_debug("update: %r", update)
        #delete remainder of local list
        remote_del = set(server_list.keys()) - common
        delete = []
        for k in remote_del:
            delete.append(server_list[k])
        accounts_debug("delete: %r", delete)
        #add remainder of new list
        remote_add = set(local_list.keys()) - common
        add = []
        for k in remote_add:
            add.append(local_list[k])
        accounts_debug("add: %r", add)

        conn = self.profile.connection
        from digsby.accounts import ADD, DELETE, UPDATE
        order = self.order[:]
        def set_order(*args, **kwargs):
            self.last_server_order = order
        def new_done(func=None):
            done = Delegate()
            if func is not None:
                done += func
            done += set_order
            done += self.save_server_info
            return done

        for a in delete:
            accounts_debug('deleting: %r, a.id: %r', a, a.id)
            def del_id(_, a=a):
                self._all_acct_hash.pop(a.id, None)
            done = new_done(del_id)
            if SAVE_ACCOUNTS:
                conn.set_account(a, action=DELETE, order=order, success=done)

        for _accounts, action in ((update, UPDATE), (add, ADD)):
            for a in _accounts:
                accounts_debug('%s: %r, a.id: %r, a.total_hash(): %r', action, a, a.id, a.total_hash())
                h = a.total_hash()
                def on_update(_, a=a, h=h):
                    a.store_hash(h)
                    self._all_acct_hash[a.id] = h
                done = new_done(on_update)
                if SAVE_ACCOUNTS:
                    conn.set_account(a, action=action, order=order, success=done)

        if self.profile.order != accounts.order:
            done = new_done()
            if SAVE_ACCOUNTS:
                conn.set_accounts(order=order, success=done)

    def update_account(self, account, force=False):
        '''
        Called when an account changes.
        If the account is flagged that we are on the network thread (or at least
        as a result of network changes), then this does nothing.
        Otherwise, the account + new account order are pushed to the server
        in an update.
        '''
        self.save_local_info()
        return
        if not SAVE_ACCOUNTS:
            return
        if account.isflagged(DELETING):
            return
        if force or not account.isflagged(NETWORK_FLAG):
            h = account.total_hash()
            order = self.order[:]
            try:
                def done(*a, **k):
                    import services.service_provider as sp
                    opts = account.get_options()
                    sp.get_provider_for_account(account).update_info(opts)
                    self.last_server_order = order
                    account.store_hash(h)
                    self._all_acct_hash[account.id] = account._total_hash
                    self.save_server_info()
                if not force and h == account._total_hash and order == self.last_server_order \
                    and self._all_acct_hash[account.id] == account._total_hash:
                    return
                self.profile.connection.set_account(account, action = 'update',
                                                    order=order, success=done)
            except Exception:
                traceback.print_exc()

    def acct_del(self, accts):
        '''
        Network account delete.
        '''
        for acct in accts:
            for account in self:
                if acct.id == account.id:
                    acct2 = account
                    break
            else:
                acct2 = None
            if acct2 is not None:
                with self.accounts_flagged(NETWORK_FLAG):
                    if get(acct2, 'enabled', False):
                        acct2.enabled = False

                    self.remove(acct2)
                    self._all_acct_hash.pop(acct2.id, None)

                    from gui import toast
                    for id in getattr(acct2, 'popupids',()):
                        toast.cancel_id(id)

    def _get_order(self):
        self_order = oset([a.id for a in self])
        import services.service_provider as sp
        container = sp.ServiceProviderContainer(self.profile)
        sp_order = oset(container.get_order())
        return list(sp_order | self_order)

    def _set_order(self, new):
        import services.service_provider as sp
        lookup = dict((v,k) for (k,v) in enumerate(new))
        newlen = len(new)
        for k in ('im','em','so'):
            self._all_accounts[k].accounts.sort(key=lambda a: lookup.get(a.id, newlen))
        container = sp.ServiceProviderContainer(self.profile)
        container.set_order(new)

    order = property(_get_order, _set_order)

    def order_set(self, order):
        '''
        An order update, coming from the network.
        '''
        with self.accounts_flagged(NETWORK_FLAG):
            self.order = order[:]
            self.last_server_order = order[:]

    def accounts_set(self, stanza=None, accounts=None):
        '''
        Handle incoming network changes to the accounts list.
        '''
        if stanza is None:
            assert accounts
        else:
            accounts = digsby.accounts.Accounts(stanza.get_query())

        if self.maybe_delay_accounts(lambda: self.accounts_set(accounts=accounts)):
            return

        from digsby.accounts import ADD, UPDATE, DELETE, Accounts

        del_accts = [acct for acct in accounts if acct.action == DELETE]
        add_accts = [acct for acct in accounts if acct.action == ADD or acct.action == None]
        mod_accts = [acct for acct in accounts if acct.action == UPDATE]
        del_accts = Accounts(del_accts, accounts.order)
        add_accts = Accounts(add_accts, accounts.order)
        mod_accts = Accounts(mod_accts, accounts.order)

        import services.service_provider as sp
        with sp.ServiceProviderContainer(self.profile).rebuilding() as container:
            self.acct_del(del_accts)
            self.acct_add(add_accts)
            self.acct_update(mod_accts)
            self.save_all_info()
            container.rebuild(self)
        self.order_set(accounts.order)

    def acct_add(self, accts):
        '''
        Network account add.
        '''
        with self.accounts_flagged(NETWORK_FLAG):
            self.add_all(accts)

    def acct_update(self, accts):
        '''
        Network account update.
        '''
        for acct in accts:
            real_acct = [a for a in self if a.id == acct.id][0]
            info = dict(name = acct.username,
                   password = acct.password,
                   protocol = acct.protocol,
                   id=acct.id,
                   **cPickle.loads(acct.data))
            with real_acct.flagged(NETWORK_FLAG):
                real_acct.update_info(**info)
                real_acct.store_hash()
                self._all_acct_hash[real_acct.id] = real_acct._total_hash

    @contextmanager
    def accounts_flagged(self, flags):
        '''
        convenience function, nests the context managers of all
        account types and flags each with these flags.
        '''
        with nested(*[accts.accounts.flagged(flags)
                  for accts in self._all_accounts.values()]):
            yield

    def release_accounts(self, autologin=False):
        '''
        function to be called to apply all network account changes received from
        the network.
        '''
        with self.acct_delay_lock:
            self.delay_accounts = False
            self.acct_calls.call_and_clear()

        import plugin_manager.plugin_hub as plugin_hub
        plugin_hub.act('digsby.accounts.released.async')
        if autologin and sys.opts.autologin_accounts:
            log.debug('doing autologin')
            self.autologin()

    def autologin(self):
        'Auto login all accounts with autologin enabled.'
        for account in self:
            if is_im_account(account) and getattr(account, 'autologin', False):
                with_traceback(account.connect)

    def __iter__(self):
        #needs update to interleave based on overall order
        return itertools.chain(self.accounts, self.emailaccounts, self.socialaccounts)

    @property
    def reconnect(self):
        return pref('login.reconnect.attempt', False)

    @property
    def reconnect_times(self):
        return pref('login.reconnect.attempt_times', 5)

    def watch_account(self, acct):
        acct.add_observer(self.on_enabled_change, 'enabled')
        acct.add_observer(self.on_state_change, 'state')
        acct.add_observer(self.on_offline_change, 'offline_reason')

    def unwatch_account(self, acct):
        acct.remove_observer(self.on_enabled_change, 'enabled')
        acct.remove_observer(self.on_state_change, 'state')
        acct.remove_observer(self.on_offline_change, 'offline_reason')

    @util.callsback
    def disconnect_all(self, callback = None):
        '''
        Call (D|d)isconnect on all accounts and set_enabled(False) if appropriate.
        After they all go to OFFLINE state, call callback.success.
        '''
        self.disconnect_cb = callback

        for a in self.connected_accounts[:]:
            if a is not self.profile:
                log.debug('      im: Calling "disconnect" on %r', a)
                with traceguard:
                    a.disconnect()

        for a in self.emailaccounts:
            with traceguard:
                if a.state != a.Statuses.OFFLINE:
                    log.debug('   email: Calling "disconnect", "set_enabled(False)" on %r', a)
                    a.set_enabled(False)
                    a.disconnect()

        for a in self.socialaccounts:
            with traceguard:
                if a.state != a.Statuses.OFFLINE:
                    log.debug('  social: Calling "Disconnect", "set_enabled(False)" on %r', a)
                    a.set_enabled(False)
                    a.Disconnect()

        self._check_all_offline()

    def all_active_accounts(self):
        '''
        Like self.connected_accounts but also for email and social accounts
        '''
        accts = self.connected_accounts[:]
        try:
            accts.remove(self.profile)
        except ValueError:
            pass
        return accts

    def _check_all_offline(self):
        if getattr(self, 'disconnect_cb', None) is not None:
            active = self.all_active_accounts()
            if not active:
                # This attribute is ONLY set when disconnect_all is called.
                dccb, self.disconnect_cb = self.disconnect_cb, None
                log.debug('All accounts disconnected, calling disconnect callback: %r', dccb.success)
                import wx
                wx.CallAfter(dccb.success)
            else:
                log.debug('All accounts not disconnected yet, remaining = %r', active)


    def on_state_change(self, src, attr, old, new):
        assert attr in ('state', None)

        hooks.notify('account.state', src, new)

        # Update "connected_accounts" list
        conn = [a for a in self.accounts + [self.profile] if a.connected]
        if self.connected_accounts != conn:
            self.connected_accounts[:] = conn

        if new != StateMixin.Statuses.OFFLINE:
            if src in self.cancellers:
                self.cancellers.pop(src).cancel()
            x = self.reconnect_timers.pop(src,None)

            if x is not None:
                x.stop()

        if new == StateMixin.Statuses.OFFLINE:
            self._on_account_offline(src)
            self._check_all_offline()

        if new == StateMixin.Statuses.ONLINE:
            src.error_count = 0

            # for IM accounts signing on, set their profile.
            if src in self.accounts:
                self.profile.set_formatted_profile(src.connection)

    def _on_account_offline(self, src):
        '''
        Notifies the buddylist sorter than an account is now offline.
        '''
        sorter = getattr(self.profile.blist, 'new_sorter', None)
        if sorter is None:
            return

        if is_im_account(src) or src is self.profile:
            log.info('informing the sorter that (%r, %r) went offline', src.username, src.protocol)
            on_thread('sorter').call(sorter.removeAccount, src.username, src.protocol)

    def on_offline_change(self, src, attr, old, new):
        accounts_debug('%s\'s %s changed from %s to %s', src, attr, old, new)
        assert attr in ('offline_reason', None)
        attr = 'offline_reason'
        if new is None:
            new = getattr(src, attr)
        Reasons = StateMixin.Reasons

        conditions = (old       == new,                          # no change...this function shouldn't have been called in the first place
                      new       == StateMixin.Reasons.NONE,      # normal offline state, doesn't matter
                      )

        if any(conditions):
            return

        log.debug('%s offline reason: %r->%r', src, old, new)


        if getattr(Reasons, 'WILL_RECONNECT', None) in (new, old):
            # something we set - ignore for now
            # new means we set it lower down in this function, old means we're moving out of this state, which should
            # not be an error.
            log.debug('Skipping the rest because reason is WILL_RECONNECT')
            return

        if new == getattr(Reasons, 'BAD_PASSWORD', None) and src is self.profile:
            if not self.profile.has_authorized:
                log.debug('Wrong password for digsbyprofile - not going to reconnect')
                return
            else:
                new = None

        if src is self.profile and not self.profile.loaded:
            log.debug('DigsbyProfile has never connected, not reconnecting after %s state.', new)
            return


        if (is_im_account(src) or src is self.profile) and new not in (Reasons.BAD_PASSWORD, Reasons.NO_MAILBOX,
                       Reasons.OTHER_USER, Reasons.RATE_LIMIT, Reasons.SERVER_ERROR):

            maxerror = (pref('%s.max_error_tolerance' % src.protocol, False) or
                        getattr(src, 'max_error_tolerance', False) or
                        pref('login.max_error_tolerance', False) or

                        4

                        )

            count = src.error_count
            src.error_count += 1
            log.info('%s\'s error_count is now %d.', src, src.error_count,)


            if (self.reconnect or src is self.profile): #and count < maxerror:
                if src in self.reconnect_timers:
                    src.error_count -= 1
                    # account is already scheduled for a reconnect
                    return

                src.setnotifyif('offline_reason', Reasons.WILL_RECONNECT)
                # schedule/attempt reconnect
                reconnect_time = get((1,10,30,300), count, 300)

                if src in self.accounts or src is self.profile:
                    profile_on_return = False
                    if src is self.profile:
                        log.critical('Going to try to reconnect the digsbyprofile. This could get interesting...')
                        reconnect_time, profile_on_return = self.get_profile_reconnect_time()

                    def rct():
                        log.info('Reconnecting %s...', src)
                        try:
                            log.warning('src=%r...setting on_connect to change_state', src)
                            if src is self.profile:
                                def set_online(*a, **k):
                                    src.connection.setnotify('state', StateMixin.Statuses.ONLINE)
                                src.on_connect = set_online
                            if getattr(src, 'connection', None) is None:
                                src._reconnect()
                            else:
                                log.error('There was already a connection for this account that was supposed to reconnect: %r', src)
                        except Exception, e:
                            log.critical('Error while trying to reconnect %s (error was: %r)', src, e)
                            traceback.print_exc()
                        x = self.reconnect_timers.pop(src,None)
                        if x is not None:
                            x.stop()

                    log.info('Starting reconnect timer for %s. Will reconnect in %d seconds %r', src, reconnect_time, self.state_desc(src))
                    self.reconnect_timers[src] = rct_timer = call_later(reconnect_time, threaded(rct))

                    if profile_on_return:
                        def reconnect_profile_now(*a, **k):
                            rct_timer.done_at = 0
                            wakeup_timeout_thread()
                        self.profile.OnReturnFromIdle += reconnect_profile_now

                    return
                else:
                    assert isinstance(src, UpdateMixin)
                    # this is a social or email account -- it has its own timers and things
                    # and will attempt the next update when appropriate
                    return

            log.info('Error count too high, or reconnect disabled.')
        elif not is_im_account(src):
            log.info('%r is not an IM account. skipped a bunch of error_count/reconnect stuff.', src)

        if not src.offline_reason or old is None:
            return

        if (not getattr(src,'_dirty_error', True)) and (getattr(src, '__last_reason', '') == src.offline_reason):
            log.info('%r has already acknowledged offline reason %r, not firing popups.', src, src.offline_reason)
            return

        # if we made it to here, notifications need to be fired
        clear_error = lambda: (setattr(src, '_dirty_error', False), setattr(src, '__last_reason', src.offline_reason))

        connect   = lambda: (getattr(src, 'enable', src.Connect)() , clear_error())
        retry     = (_('Retry'), connect)
        reconnect = (_('Reconnect'), connect)
        close     = (_('Close'), clear_error)
        edit_acct = (_('Edit Account'), lambda: self.edit(src, connect = True))
        _moreoptions = {'onuserclose':clear_error, 'onclose':clear_error}

        if src.protocol_info().get('needs_password', True):
            bad_pw_opts = (edit_acct, close)
        else:
            bad_pw_opts = (retry, close)

        popupinfo = {
         Reasons.BAD_PASSWORD:
                    (_('Authentication Error'), True,
                     bad_pw_opts, _moreoptions),
         Reasons.NO_MAILBOX:
                    (_('Mailbox does not exist'), True,
                    (close,), _moreoptions),
         Reasons.OTHER_USER:
                    (_('This account has been signed on from another location'), True,
                     (reconnect, close), _moreoptions),
         Reasons.CONN_LOST:
                    (_('Connection to server lost'), False,
                     (reconnect, close), _moreoptions),
         Reasons.CONN_FAIL:
                    (_('Failed to connect to server'), False,
                     (retry, close), _moreoptions),
         Reasons.RATE_LIMIT  :
                    (_('Could not connect because you are signing on too often. Please wait 20 minutes before trying to log in again.'), True,
                     (retry, close), dict(onclick=lambda d:self.edit(src), onclose = clear_error, onuserclose=clear_error)),
        }

        msg, sticky, buttons, moreoptions = popupinfo[src.offline_reason]

        if src.offline_reason == Reasons.BAD_PASSWORD:
            rsn = getattr(getattr(src, 'connection', None), '_auth_error_msg', None)
            if rsn:
                msg = msg + ' - ' + rsn

        addtl_txt = getattr(src, 'error_txt', False)
        if addtl_txt:
            msg = msg + ': ' + addtl_txt
            sticky = True
            del src.error_txt

        log.debug('Firing popup for %r', src)
        canceller = fire('error',
                         title   = _('{protocol_name} Error').format(protocol_name = nice_proto_names[src.protocol]),
                         msg     = src.display_name,
                         details = msg,
                         sticky  = sticky,
                         buttons = buttons,
                         popupid = src,
                         **moreoptions)

        if src in self.cancellers:
            old = self.cancellers.pop(src)
            if old is not canceller:
                from weakref import ref
                with traceguard:
                    for item in old.get():
                        canceller.put(ref(item))

        self.cancellers[src] = canceller

    def get_profile_reconnect_time(self):
        '''
        Returns the number of seconds to reconnect the main digsby connection in,
        and whether to reconnect on idle.

        The seconds value is chosen randomly, and is higher if you're idle.
        '''
        from gui.native.helpers import GetUserIdleTime
        from random import randint
        idle = GetUserIdleTime() > (1000 * SECONDS_FOR_IDLE)
        info = getattr(self.profile, 'balance_info', False)
        default = True
        reconnect_strategy = getattr(info, 'reconnect_strategy', None)
        if reconnect_strategy is not None:
            if reconnect_strategy.get('strategy', False) == 'min_max':
                try:
                    rc_min, rc_max = int(reconnect_strategy['min_seconds']),  int(reconnect_strategy['max_seconds'])
                except Exception:
                    traceback.print_exc()
                else:
                    default = False

        if default and not idle:
            rc_min, rc_max = pref('debug.profile_connect_time_min', ACTIVE_RECONNECT_MIN, type=int), \
                                       pref('debug.profile_connect_time', ACTIVE_RECONNECT_MAX, type=int)
        elif default:
            rc_min, rc_max = IDLE_RECONNECT_MIN, IDLE_RECONNECT_MAX
        if idle:
            # returning from idle instantly reconnects the profile
            profile_on_return = True
        else:
            profile_on_return = False

        reconnect_time = randint(rc_min, rc_max)

        return reconnect_time, profile_on_return

    def state_desc(self, acct):
        if acct.state == StateMixin.Statuses.ONLINE:
            return ''

        if acct.state == StateMixin.Statuses.OFFLINE:
            return _(self.offline_message_for_account(acct))
        else:
            return _(acct.state)

    def cancel_reconnect(self, acct):
        acct.disconnect()
        acct.setnotify('offline_reason',StateMixin.Reasons.NONE)
        timer = self.reconnect_timers.pop(acct, None)
        if timer:
            timer.cancel()

    def offline_message_for_account(self, acct):
        reconnect = StateMixin.Reasons.WILL_RECONNECT

        if acct in self.reconnect_timers:

            if acct.offline_reason != reconnect:
                acct.offline_reason = reconnect

            rem_time = self.reconnect_timers[acct].remaining
            return reconnect % nicetimecount(rem_time)

        elif acct.offline_reason == reconnect:
            if isinstance(acct, UpdateMixin):
                return reconnect % nicetimecount(acct.timer.remaining)
            else:
                return StateMixin.Reasons.CONN_FAIL
        elif acct.offline_reason == StateMixin.Reasons.NONE:
            return ''

        return acct.offline_reason

    def on_enabled_change(self, acct, _enabled, old, new):
        if is_im_account(acct) and (old != new) and (new is not None):

            if acct.enabled and not acct.connection:
                self.cancel_reconnect(acct)
                acct.connect()
            elif not acct.enabled:
                self.cancel_reconnect(acct)
                if acct.connection:
                    acct.disconnect()

    def enable(self, acct):
        acct.enabled = True

    def disable(self, acct):
        acct.enabled = False

    def add(self, acct, type, ignore_on_rebuild=False):
        import services.service_provider as sp
        if ignore_on_rebuild:
            new = (acct,)
        else:
            new = ()
        with sp.ServiceProviderContainer(self.profile).rebuilding(new=new) as container:
            accts = getattr(self._all_accounts, type).accounts

            if acct not in accts:
                accts.append(acct)
                self.watch_account(acct)
                #self.profile.add_account(acct)
            container.rebuild(self)

    def add_multi(self, seq):
        import services.service_provider as sp
        with sp.ServiceProviderContainer(self.profile).rebuilding() as container:
            for acct, type in seq:
                self.add(acct, type)
            container.rebuild(self)

    def add_all(self, allnewaccts):
        import services.service_provider as sp
        with sp.ServiceProviderContainer(self.profile).rebuilding() as container:
            from imaccount import Account
            setup = [
                     ('im', is_im_account, Account),
                     ('em', email_accounts, EmailAccount),
                     ('so', social_accounts, social.network),
                    ]
            for type, pred, cls in setup:
                newaccts = self._xfrm_sort(allnewaccts, cls, pred)
                self._add_all(newaccts, type)
            container.rebuild(self)

    def _add_all(self, newaccts, type):
        accts = getattr(self._all_accounts, type).accounts
        newaccts = list(newaccts)
        for acct in newaccts:
            if accts.isflagged(NETWORK_FLAG):
                acct.store_hash()
                self._all_acct_hash[acct.id] = acct._total_hash
            self.watch_account(acct)
        accts.extend(newaccts)

    def remove(self, acct):
        import services.service_provider as sp
        with sp.ServiceProviderContainer(self.profile).rebuilding() as container:
            log.info('removing account %r', acct)

            with acct.flagged(DELETING):
                if acct.connected and hasattr(acct, 'disable'):
                    with traceguard:
                        acct.disable()
                elif get(acct, 'enabled', False):
                    acct.enabled = False

            removed = False

            for x in self._all_accounts.values():
                try:
                    x.accounts.remove(acct)
                except ValueError:
                    continue
                else:
                    break

            try:
                self.connected_accounts.remove(acct)
            except ValueError: #ok, so it wasn't in the list
                pass

            self.unwatch_account(acct)

            from gui import toast
            for id in getattr(acct, 'popupids',()):
                toast.cancel_id(id)

            container.rebuild(self)

    def edit(self, acct, connect=False, parent = None):

        # used to take linkparent

        import hooks, services.service_provider as SP
        sp = SP.get_provider_for_account(acct)
        diag = hooks.first('digsby.services.edit', parent = parent, sp = sp, impl="digsby_service_editor")
        old_offline = acct.offline_reason
        acct.offline_reason = StateMixin.Reasons.NONE

        info = None
        try:
            res = diag.ShowModal()
            from wx import ID_SAVE
            if diag.ReturnCode == ID_SAVE:
                info = diag.RetrieveData()
        finally:
            diag.Destroy()

        if info is None:
            return

        sp.update_info(info)
        sp.update_components(info)

        if not connect:
            return

        for ctype in sp.get_component_types():
            comp = sp.get_component(ctype, create = False)
            if comp is None:
                continue

            if comp is acct:
                #enable it.
                if hasattr(comp, 'enable'):
                    if old_offline == StateMixin.Reasons.BAD_PASSWORD:
                        log.info('comp.Connect() %r', comp)
                        comp.Connect()
                    elif not comp.enabled:
                        log.info('comp.enable() %r', comp)
                        comp.enable()
                else:
                    #UpdateMixin
                    if not comp.enabled:
                        log.info('comp.enabled = True %r', comp)
                        comp.enabled = True
                    else:
                        log.info('comp.Connect() %r', comp)
                        comp.Connect()
            else:
                if comp.enabled and hasattr(comp, 'enable'):
                    log.info('comp.enable() %r', comp)
                    comp.enable()
                else:
                    #UpdateMixin
                    if comp.enabled:
                        log.info('comp.Connect() %r', comp)
                        comp.Connect()

    def save_all_info(self):
        self.save_local_info()
#        self.save_server_info()

    def save_local_info(self):
        'Writes our local account data to disk.'
        hooks.notify('digsby.identity.save_data', 'accounts', self.all_accounts)
        return
        if not SAVE_ACCOUNTS:
            return
        try:
            digsby.digsbylocal.save_local_info(
                self.profile.username, self.profile.password,
                self.all_accounts, self.order)
            log.info('serialized local accounts')
        except Exception:
            log.error('failed to serialize local accounts')
            traceback.print_exc()

    def save_server_info(self, _possible_stanza=None):
        '''Writes server side account data to disk:

        self._all_acct_hash
        self.last_server_order'''
        if not SAVE_ACCOUNTS:
            return
        try:
            digsby.digsbylocal.save_server_info(
                self.profile.username, self.profile.password,
                self._all_acct_hash, self.last_server_order)
            log.info('serialized server hash and order')
        except Exception:
            log.error('failed to serialize server hash and order')
            traceback.print_exc()

    def im_accounts_changed(self, src, attr, old, new):
        return self.accounts_changed('im', src, attr, old, new)

    def em_accounts_changed(self, src, attr, old, new):
        return self.accounts_changed('em', src, attr, old, new)

    def so_accounts_changed(self, src, attr, old, new):
        return self.accounts_changed('so', src, attr, old, new)

    def accounts_changed(self, t, src, attr, old, new):
        '''
        Invoked when the order of accounts changes or an account is added or
        deleted. "t" is 'im', 'em', or 'so'
        Will not push incoming network changes when properly flagged.
        '''
        accts = self._all_accounts[t]
        assert src is accts.accounts

        if src.isflagged(NETWORK_FLAG):
            log.info('%s received', t)
            accts.old = src[:]
            return
        else:
            self.save_local_info()
            log.warning('%s has already been received', t)
        if not SAVE_ACCOUNTS:
            return
        if accts.old != src:
            old_list = dict((a.id, a) for a in accts.old)
            new_list = dict((a.id, a) for a in src)

            local_add = set(new_list.keys()) - set(old_list.keys())
            added = [new_list[k] for k in local_add]

            local_del = set(old_list.keys()) - set(new_list.keys())
            deleted = [old_list[k] for k in local_del]

            accts.old = src[:]
            order = self.order[:]
            done = Delegate()
            def set_order(*args, **kwargs):
                self.last_server_order = order
            done += set_order

            try:
                conn = self.profile.connection
                conn.set_account
                conn.stream
                conn.stream.send
            except AttributeError:
                log.critical('profile not connected, skipping network push')
                return

            try:
                if deleted:
                    assert not added, (added, deleted, cmp(added, deleted))
                    assert len(deleted) == 1
                    def del_id(*args, **kwargs):
                        conn = self._all_acct_hash.pop(deleted[0].id, None)
                    done += del_id
                    done += self.save_server_info
                    conn.set_account(deleted[0], action='delete', order=order, success=done)
                if added:
                    assert not deleted, (added, deleted,cmp(added, deleted))
                    assert len(added) == 1
                    a = added[0]
                    h = a.total_hash()
                    done += (lambda *args, **kwargs: a.store_hash(h))
                    def update_server_hash(*args, **kwargs):
                        self._all_acct_hash[a.id] = h
                    done += update_server_hash
                    done += self.save_server_info
                    conn.set_account(a, action='add', order=order, success=done)
                if not (added or deleted):
                    done += self.save_server_info
                    conn.set_accounts(order=order, success=done)
            except Exception:
                traceback.print_exc()

    disconnect = _all_account_call(lambda a: a.disconnect())
    connect = _all_account_call(lambda a: a.connect())
