from .stanzas.action import Action, SYNC_PROTOS
from .stanzas.counter import CounterQuery
import stanzas.action
from peak.util.addons import AddOn
from threading import RLock
from util.threads.timeout_thread import ResetTimer
from collections import defaultdict
import warnings
import traceback

COUNT_TIMEOUT = 5 * 60 #seconds

simple_incrementers = [
    # twitter
    ('digsby.twitter.status_updated', 'twit_post'),
    ('digsby.twitter.direct_sent', 'twit_post'),
    ('digsby.statistics.twitter.feed_window.shown', 'twit_feed_window_shown'),
    ('digsby.statistics.twitter.feed_window.activated', 'twit_feed_window_activated'),
    ('digsby.statistics.twitter.new_search', 'twit_new_search'),
    ('digsby.statistics.twitter.viewed_search', 'twit_viewed_search'),
    ('digsby.statistics.twitter.infobox.shown', 'twit_infobox_shown'),

    ('digsby.statistics.twitter.invite.shown', 'twitter.invite.shown'),
    ('digsby.statistics.twitter.invite.yes', 'twitter.invite.yes'),
    ('digsby.statistics.twitter.invite.no', 'twitter.invite.no'),

    # email
    ('digsby.statistics.email.inbox_opened', 'email.inbox_opened'),
    ('digsby.statistics.email.delete', 'email.delete'),
    ('digsby.statistics.email.archive', 'email.archive'),
    ('digsby.statistics.email.mark_as_read', 'email.mark_as_read'),
    ('digsby.statistics.email.spam', 'email.spam'),
    ('digsby.statistics.email.email_opened', 'email.email_opened'),
    ('digsby.statistics.email.compose', 'email.compose'),
    ('digsby.statistics.email.sent_from_imwindow', 'email.imwin_sent'),

    ('digsby.statistics.email.invite.shown', 'email.invite.shown'),
    ('digsby.statistics.email.invite.yes', 'email.invite.yes'),
    ('digsby.statistics.email.invite.no', 'email.invite.no'),

    # myspace
    ('digsby.myspace.status_updated', 'mysp_post'),
    ('digsby.myspace.photo_seen',     'mysp_photo'),
    ('digsby.myspace.comment_added',  'mysp_comment'),
    ('digsby.myspace.dislike_added',  'mysp_dislike'),
    ('digsby.myspace.like_added',     'mysp_like'),

    # facebook
    ('digsby.facebook.status_updated', 'face_post'),
    ('digsby.facebook.like_added', 'face_like'),
    ('digsby.facebook.dislike_added', 'face_dislike'),
    ('digsby.facebook.comment_added', 'face_comment'),
    ('digsby.facebook.photo_seen', 'face_photo'),

    # linkedin
    ('digsby.linkedin.status_updated', 'link_post'),
    ('digsby.linkedin.comment_added',  'link_comment'),
    ('digsby.linkedin.dislike_added',  'link_dislike'),
    ('digsby.linkedin.like_added',     'link_like'),

    # buddylist
    ('digsby.statistics.buddylist.search', 'buddylist.search'),

    # Feed Ads
    ('digsby.statistics.feed_ads.impression', 'feed_ad.impression'),
    ('digsby.statistics.feed_ads.click', 'feed_ad.click'),
    ('digsby.statistics.feed_ads.share', 'feed_ad.share'),

    ('digsby.statistics.feed_ads.citygrid.click',       'feed_ad.citygrid.click'),
    ('digsby.statistics.feed_ads.citygrid.impression',  'feed_ad.citygrid.impression'),
    ('digsby.statistics.feed_ads.citygrid.share',       'feed_ad.citygrid.share'),
]

# add simple_incrementers
stanzas.action.WHITELISTED_TYPES.update(name for hook, name in simple_incrementers)

def incrementer(what):
    def incr(self, *a, **k):
        self.increment(what)

    return incr

class CountTracker(AddOn):
    def __init__(self, subject):
        self.profile = subject
        self.values  = defaultdict(int)
        self.cached  = {}
        self.thresholds  = {}
        self.lock = RLock()
        self.did_setup = False
        super(CountTracker, self).__init__(subject)

    def self_incrementer(self, what):
        def incr(*a, **k):
            self.increment(what)

        return incr

    def im(self, _conv, _msg, type):
        if type == 'outgoing':
            self.increment('im_sent')
        if type == 'incoming':
            self.increment('im_received')

    emoticon_box_viewed = incrementer('emoticon_box_viewed')
    emoticon_chosen = incrementer('emoticon_chosen')
    video_chat_requested = incrementer('video_chat_requested')
    sms_sent = incrementer('sms_sent')

    log_viewed = incrementer('log_viewed')

    prefs_opened = incrementer('prefs.prefs_opened')

    def increment_account(self, prefix, account):
        protocol = getattr(account, 'protocol', None)
        if isinstance(protocol, basestring) and protocol in SYNC_PROTOS:
            self.increment(prefix + '.' + protocol)

    infobox_shown = incrementer('infobox.shown')

    imwin_created = incrementer('imwin.imwin_created')

    def imwin_engage(self, seconds):
        self.increment('imwin.imwin_engage', seconds)

    contact_added = incrementer('contact_added')
    ##
    contact_add_dialog = incrementer('ui.dialogs.add_contact.created')
    ui_select_status = incrementer('ui.select_status')

    def citygrid_click(self, cents):
        self.increment('feed_ad.citygrid.click_cents', cents)

    def setup(self):
        if self.did_setup:
            warnings.warn('reinitialized AddOn CountTracker')
            return
        self.did_setup = True
        from peak.util.plugins import Hook
        Hook('digsby.im.msg.async',            'stats_counter').register(self.im)

        Hook('digsby.statistics.emoticons.box_viewed', 'stats_counter').register(self.emoticon_box_viewed)
        Hook('digsby.statistics.emoticons.chosen',     'stats_counter').register(self.emoticon_chosen)
        Hook('digsby.video_chat.requested',            'stats_counter').register(self.video_chat_requested)
        Hook('digsby.statistics.sms.sent',  'stats_counter').register(self.sms_sent)

        Hook('digsby.statistics.logviewer.log_viewed', 'stats_counter').register(self.log_viewed)
        Hook('digsby.statistics.prefs.prefs_opened', 'stats_counter').register(self.prefs_opened)
        Hook('digsby.statistics.imwin.imwin_created', 'stats_counter').register(self.imwin_created)
        Hook('digsby.statistics.imwin.imwin_engage', 'stats_counter').register(self.imwin_engage)

        Hook('digsby.statistics.infobox.shown', 'stats_counter').register(self.infobox_shown)

        Hook('digsby.statistics.contact_added', 'stats_counter').register(self.contact_added)
        Hook('digsby.statistics.ui.select_status', 'stats_counter').register(self.ui_select_status)
        Hook('digsby.statistics.ui.dialogs.add_contact.created', 'stats_counter').register(self.contact_add_dialog)


        Hook('digsby.app.exit',                'stats_counter').register(self.flush)

        Hook('digsby.stats_counter.important_threshold', 'stats_counter').register(self.important)

        for hook_name, server_side_name in simple_incrementers:
            Hook(hook_name, 'stats_counter').register(self.self_incrementer(server_side_name))

        Hook('digsby.statistics.feed_ads.citygrid.click_cents', 'stats_counter').register(self.citygrid_click)

        Hook('digsby.research.run_time', 'stats_counter').register(self.research_run_time)

    def important(self, type, value):
        self.thresholds[type] = value

    def research_run_time(self, seconds):
        self.increment('research.run_time', int(seconds))

    #the fact that something is updating should be exposed through hooks, and then a hook to request a sync
    def increment(self, type, value=None):
        with self.lock:
            self.update_val(type=type, value=value)
            #threshold tracking needs some re-thinking for combined count tracking.
            if type in self.thresholds and type in self.cached:
                if self.values[type] + self.cached[type] >= self.thresholds[type]:
                    self.flush_key(type)
            elif type not in self.cached:
                self.flush_key(type) #get a value the first time something happens

    def update_val(self, type, value=None):
        if value is None:
            value = 1
        with self.lock:
            self.values[type] += value
            if hasattr(self, 'timer'):
                if self.timer.isAlive():
                    self.timer.reset()
            else:
                self.timer = ResetTimer(COUNT_TIMEOUT, self.flush)
                self.timer.start()

    def flush(self):
        with self.lock:
            values, self.values = self.values, defaultdict(int)
            self.thresholds.clear()

        self.send_updates_batched(values)

    def flush_key(self, key): #replace uses with flush when server is updated, no reason not to send everything together.
        with self.lock:
            assert key in self.values
            val = self.values.pop(key)
            self.thresholds.pop(key, None)
        self.send_update(key, val)

    def send_update(self, type, value=None):
        pass
    def send_updates_batched(self, updates):
        pass
    def handle_response(self, result):
        pass

class DigsbyProtocolCountTracker(CountTracker):
    def send_update(self, type, value=None):
        connection = None
        try:
            connection = getattr(self.profile, 'connection', None)
        except AttributeError:
            pass

        if connection is None:
            self.update_val(type, value) #try again later
            return

        iq = CounterQuery([Action(type, value=(value if value and value > 1 else None))]).make_push(connection)
        try:
            connection.send_cb(iq, success=self.handle_response)
        except Exception:
            traceback.print_exc()
        return #delete above when server is updated, in fact, this whole method can go.
        return self.send_updates_batched(dict(type=value))

    def send_updates_batched(self, updates):
        for update in updates.items():
            self.send_update(*update)
        return #delete above when server is updated

        connection = None
        try:
            connection = getattr(self.profile, 'connection', None)
        except AttributeError:
            pass

        #needs a batched version to avoid race conditions
        #(extremely unlikely, but might as well protect against)
        #code should be clearer as a result.
        if connection is None:
            for update in updates.items():
                self.update_val(*update) #try again later
            return

        iq = CounterQuery([Action(type, value=(value if value and value > 1 else None))
                           for type, value in updates.items()]).make_push(connection)
        try:
            connection.send_cb(iq, success=self.handle_response)
        except Exception:
            traceback.print_exc()

    def handle_response(self, stanza):
        try:
            c = CounterQuery(stanza.get_query())
        except ValueError:
            return
        with self.lock:
            for action in c: #usually one element, but whatever.
                if action.type is None:
                    continue
                self.cached[action.type] = action.result
        import hooks #has protected notify

        actions = []
        for action in c: #usually one element, but whatever.
            if action.type is None:
                continue
            actions.append(dict(
                                                 type    = action.type,
                                                 initial = action.initial,
                                                 value   = action.value,
                                                 result  = action.result,
                                                 )
            )
        for action in actions:
            hooks.notify('digsby.stats_counter', **action)
        hooks.notify('digsby.stats_counter.batch', actions)
