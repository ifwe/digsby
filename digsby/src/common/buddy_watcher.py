from common import pref
from common.notifications import fire
from util import Timer
from util.primitives.error_handling import try_this
from util.primitives.funcs import CallCounter, Delegate, readonly
from collections import defaultdict
from time import time
from plugin_manager.plugin_hub import act as plugin_act
from weakref import ref

import logging
log = logging.getLogger('buddywatcher')
info = log.info
debug = log.debug

class BuddyState(object):
    '''
    lightweight objects meant to capture a buddy's current status and status message
    important bits:
        status
        status message

        online time?
        idle time?
        online?        | properties?
        offline?    |

        mobile?
        idle?
    '''

    service = ''

    attrs = 'status message idle'.split()

    __slots__ = ['buddy',
                 '_status',
                 '_message',
                 '_idle_time',
                 '_timestamp']

    def __init__(self, buddy=None):

        self._timestamp = time()

        if buddy is None:
            self._status    = 'offline'
            self._message   = ''
            self._idle_time = 0
        else:
            self._status    = buddy.status
            self._message   = buddy.stripped_msg or ''
            self._idle_time = int(buddy.idle or 0)

        self.buddy = ref(buddy) if buddy is not None else None

    timestamp = readonly('_timestamp')
    status    = readonly('_status')
    idle_time = readonly('_idle_time')
    message   = status_message = readonly('_message')

    def __eq__(self, other):
        for attr in self.attrs:
            if getattr(self, attr, Sentinel()) != getattr(other, attr, Sentinel()):
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def known(self):
        return self.status != 'unknown'

    @property
    def online(self):
        return self.known and not self.offline

    @property
    def available(self):
        return self.online and not self.away

    @property
    def offline(self):
        return self.status == 'offline'

    @property
    def idle(self):
        #return self.status == 'idle'
        return bool(self.idle_time)

    @property
    def away(self):
        return self.status == 'away'

    def __repr__(self):
        return '<%s %s: status=%r, message=%r, idletime=%r>' % (type(self).__name__,
                                                                 try_this(lambda:key(safe_deref(self.buddy)), None),
                                                                 self.status,
                                                                 getattr(safe_deref(self.buddy), 'stripped_msg', ''),
                                                                 self.idle_time)

class BuddyStateUpdate(object):
    __slots__ = ['timestamp', 'old', 'new', 'transitions', 'buddy', 'changed']

    def __init__(self, old, new):
        self.timestamp = time()
        self.old = old
        self.new = new
        self.buddy = self.old.buddy

        self.transitions = [(key, getattr(old, key), getattr(new, key)) for key in new.attrs]
        self.changed     = [trans for trans in self.transitions if trans[1] != trans[2]]

    def __nonzero__(self): return bool(self.changed)

    def __repr__(self):
        return '<%s for %s: %s>' % (type(self).__name__, key(safe_deref(self.buddy)), self.changed)

class BuddyWatcher(object):

    watch_attrs = '''
        status
        status_message
        idle
        idle_time
    '''.split()

    ACTIVE_THRESHOLD = 4

    def __init__(self):
        self.known    = defaultdict(BuddyState)
        self.active   = {}
        self.watchers = {}

    def register(self, buddy):
        if not getattr(buddy, '_bw_register', True):
            return

        k = key(buddy)
        if k in self.known:
            log.warning('%s tried to register with buddy_watcher again, replacing old buddy', buddy)
            state = self.known[k]

            old_buddy = safe_deref(state.buddy)
            if old_buddy is not None:
                old_buddy.remove_observer(self.on_change, *self.watch_attrs)

        self.known[k] = BuddyState(buddy)

        buddy.add_observer(self.on_change, *self.watch_attrs)

    def on_change(self, buddy, *a):

        bkey = key(buddy)
        new = BuddyState(buddy)

        try:
            if bkey in self.active:
                if (new.timestamp - self.active[bkey].timestamp) > self.ACTIVE_THRESHOLD:
                    self.active.pop(bkey, None)

            if bkey in self.active:
                oldest = self.active[bkey].old
                last = self.active[bkey].new #self.known[bkey]

                if (oldest.status == new.status) and (oldest.message == new.message):
                    oldest = last
            else:
                oldest = last = self.known[bkey]
        except KeyError:
            info('Did not have previous record for buddy %r (bkey=%r). Creating blank BuddyState', buddy, key(buddy))
            oldest = last = BuddyState()
            oldest.buddy = last.buddy = ref(buddy)

        self.known[bkey] = new

        for x in (oldest, last, new):
            if safe_deref(x.buddy) is None:
                x.buddy = ref(buddy)

        update_notify = BuddyStateUpdate(oldest, new)
        update_store  = BuddyStateUpdate(last, new)

        if update_store and update_notify:
            self.active[bkey] = update_store
            self.notify(buddy, update_notify)
            self.known[bkey] = new

    def unregister(self, buddy):
        self.known.pop(key(buddy), None)
        self.active.pop(key(buddy), None)
        buddy.remove_observer(self.on_change, *self.watch_attrs)

    def notify(self, buddy, update):
        bkey = key(buddy)

        # stupid hack for common.buddy AND 'StatusMessage' as buddy objects
        try:
            # $$plugin status change
            if not plugin_act('digsby.im.status.change.pre', buddy):
                return
            plugin_act('digsby.im.status.change.async', buddy)
        except:
            info('invalid buddy')

        quiet  = getattr(buddy.protocol, '_notifyquiet', False)
        selfbuddy = buddy is buddy.protocol.self_buddy

        #self.active[bkey] = update
        nots = self.determine_notifies(buddy, update)

        debug('Got the following notifies for update %r: %r', update, nots)

        def pop():
            debug('Removing %r from active dictionary', bkey)
            self.active.pop(bkey, None)

        try:
            watcher = self.watchers[bkey]
        except KeyError:
            pass
        else:
            watcher(update)

        fired = set()

        pop = CallCounter(len(nots), pop) # Help! this isn't right. it should be the number of reactions that happened.

        for notify in nots:
            if notify['topic'] not in fired:
                fired.add(notify['topic'])
                notify['on_done'] = pop

                if not (quiet or selfbuddy):
                    fire(**notify)
                else:
                    if quiet:
                        reason = 'quiet'
                    elif selfbuddy:
                        reason = 'selfbuddy'
                    info('Not firing notifications for %r because of %r', buddy, reason)
                    pop()
            else:
                pop()

    def determine_notifies(self, buddy, update):
        nots = []
        for old, new, two, action in checks:

            old = old or (lambda x:   True)
            new = new or (lambda x:   True)
            two = two or (lambda x,y: True)

            assert action
            if old(update.old) and new(update.new) \
               and two(update.old, update.new):
                nots.append(action(buddy))
                continue

        return nots

    def watch_status(self, buddy, callback):
        assert callable(callback)
        bid = key(buddy)

        try:
            watchers = self.watchers[bid]
        except KeyError:
            watchers = self.watchers.setdefault(bid, Delegate())

        watchers += callback

    def unwatch_status(self, buddy, callback):
        self.watchers[key(buddy)] -= callback



def key(buddy):
    return getattr(buddy, 'popup_key', buddy.info_key)

#################################
# some primitives
#################################

def available(x):
    return x.available
def online(x):
    return x.online
def away(x):
    return x.away
def idle(x):
    return x.idle
def away_idle(x):
    return away(x) and idle(x)
def offline(x):
    return x.offline
def same_msg(x,y):
    return x.message == y.message
def not_available(x):
    return not available(x)
def not_online(x):
    return not online(x)
def not_away(x):
    return not away(x)
def not_idle(x):
    return not idle(x)
def not_offline(x):
    return not offline(x)
def diff_msg(x,y):
    return not same_msg(x,y)
def avail_not_idle(x):
    return available(x) and not_idle(x)
#################################
# responses
#################################

def tag_stripped_msg(contact):
    import hooks
    msg = hooks.reduce('digsby.status.tagging.strip_tag', contact.stripped_msg, contact.status, impl='text')
    return msg

def args_for_topic(topic, equivalence, chatclick=True):
    def args_for_buddy(b):
        update = getattr(b, '_popup_update', 'replace')

        d = dict(topic=topic, buddy=b,
                 stripped_msg = tag_stripped_msg(b),
                 onclick=lambda e: b.chat(),
                 popupid=key(b)+'_'+str(equivalence),
                 update=update,
                 )


        if not chatclick:
            d.pop('onclick')
        return d

    return args_for_buddy

contact_signon          = args_for_topic('contact.signon', 0)
contact_signoff         = args_for_topic('contact.signoff', 0, chatclick=False)
contact_away            = args_for_topic('contact.away', 0)
contact_available       = args_for_topic('contact.available', 0)
contact_statusmessage   = args_for_topic('contact.statusmessage', 0)
contact_idle            = args_for_topic('contact.idle', 1)
contact_returnsfromidle = args_for_topic('contact.returnsfromidle', 1)

#
#TODO: these are acting as predicate functions in the "logix" block below just
#       to get additional functionality in, but we should make the "checks" loop
#       above generic enough to do things other than common.notifications.fire
#
def go_online(old, new):
    # causes the buddylist to bold new oncoming buddies
    buddy = safe_deref(old.buddy)
    if buddy is None:
        return

    protocol = buddy.protocol

    # If protocol._notifyquiet is True, then we don't mark a buddy as "entering."
    # _notifyquiet is usually set on signon.
    #
    # Additionally, ignore the self buddy here because it may "come online" before
    # _notifyquiet is set.
    if not getattr(protocol, '_notifyquiet', False) and \
        buddy is not protocol.self_buddy: # self buddy is created before _notifyquiet in some protocols

        buddy.entering = True
        Timer(pref('buddylist.coming_going_time', 3),
              lambda: buddy.setnotifyif('entering', False)).start()

    return True

def go_offline(old, new):
    # causes the buddylist to grey out leaving buddies
    buddy = safe_deref(old.buddy)
    if buddy is None:
        return

    buddy.leaving = True
    Timer(pref('buddylist.coming_going_time', 3),
          lambda: buddy.setnotifyif('leaving', False)).start()

    # Clear out ome attributes that don't make sense for offline buddies.
    b = safe_deref(old.buddy)
    if b is None:
        return

    b.online_time = 0
    try:
        b.idle = 0
    except AttributeError:
        pass
    b.status_message = ''
    return True

#################################
# teh logix
#################################

checks = (
    (offline, online, go_online, contact_signon),
    (online, offline, go_offline, contact_signoff),

    (lambda x: online(x) and not_away(x), away, None, contact_away),
    (away, away, diff_msg, contact_statusmessage),

    (lambda x: online(x) and not_available(x), lambda x: available(x) and not_idle(x), None, contact_available),
    (avail_not_idle, avail_not_idle, diff_msg, contact_statusmessage),

    (lambda x: online(x) and not_idle(x), idle, None, contact_idle),
    (lambda x: idle(x) and not_away(x), lambda x: available(x) and not_idle(x), None, contact_returnsfromidle),
    (lambda x: idle(x) and away(x), lambda x: online(x) and not_idle(x), None, contact_returnsfromidle),

)

def safe_deref(r):
    if r is not None:
        return r()
