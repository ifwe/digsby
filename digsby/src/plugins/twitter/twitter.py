from __future__ import print_function
import os
from time import time
import sys
import branding
import common
import hooks
import fileutil
import metrics
import protocols
import social
import string
import threading
import traceback
import simplejson
from rpc.jsonrpc import Dsuccess

from social.network import SocialFeed

from util import callbacks
from util.net import UrlQuery
from util.primitives.error_handling import traceguard
from util.primitives.funcs import Delegate
from util.primitives.mapping import Storage, to_storage
from path import path
from copy import deepcopy

import gui.infobox.providers as gui_providers
import gui.infobox.interfaces as gui_interfaces
import wx.webview

from oauth.oauth import OAuthToken

from logging import getLogger; log = getLogger('twitter')

import twitter_auth
#import twitter_xauth as twitter_auth

USE_REALTIME_STREAM = False or '--realtime' in sys.argv
SHOW_INVITE_DM_DIALOG_ON_CREATE = False

RES_PATH = (path(__file__).parent.abspath() / 'res').normpath()
APP_PATH = (RES_PATH / 'app.html').normpath()

#from twitter_tweets import DIGSBY_TWEET_MESSAGE

def LINK():
    return branding.get('digsby.twitter.achievements.link', 'digsby_twitter', 'http://bit.ly/r2d24u')

def DEMO_VIDEO_LINK():
    return branding.get('digsby.twitter.demovideo.link', 'digsby_twitter', 'http://bit.ly/clMDW5')

def new_reply_text(screen_name, text):
    import twitter_util as tutil
    s = '@' + screen_name + ' '
    cursor_position = len(s)

    hashtags = ' '.join(set(tutil.hashtag.findall(text)))
    if hashtags: s += ' ' + hashtags

    return s, cursor_position

def prefill_reply(options):
    '''Returns the text the popup reply button input field is prefilled with.'''

    tweet = options['tweet']
    return new_reply_text(tweet.user.screen_name, tweet.text.decode('xml'))

def prefill_retweet(options):
    '''Returns the text the popup retweet button input field is prefilled with.'''
    tweet = options['tweet']
    return 'RT @' + tweet.user.screen_name + ' ' + tweet.text.decode('xml')

def prefill_direct(options):
    '''Returns the text the popup retweet button input field is prefilled with.'''
    tweet = options['tweet']
    return 'd ' + tweet.user.screen_name + ' '


class TwitterAccount(social.network):
    service = protocol = 'twitter'
    _dirty = True
    update_mixin_timer = False

    @callbacks.callsback
    def SetStatusMessage(self, message, reply_to=None, callback=None, **k):
        @wx.CallAfter
        def after():
            def error(err):
                callback.error(Exception('Error sending tweet'))

            self.twitter_protocol.on_status(message,
                    reply_id=reply_to,
                    success=callback.success,
                    error=error)

    # console shortcuts

    @property
    def j(self):
        return self.connection.webkitcontroller.evaljs

    @property
    def w(self):
        return self.connection.webkitcontroller.webview

    def update_now(self):
        # if we're in "failed to connect" then just try reconnecting.
        if self.state == self.Statuses.OFFLINE and \
            self.offline_reason == self.Reasons.CONN_FAIL:
                self.Connect()
        else:
            self.twitter_protocol.update()

    @classmethod
    def tray_icon_class(cls):
        from .twitter_gui import TwitterTrayIcon
        return TwitterTrayIcon

    def menu_actions(self, menu):
        from .twitter_gui import menu_actions
        menu_actions(self, menu)

    @property
    def connection(self):
        return self.twitter_protocol

    def update_info(self, **info):
        '''new account info arrives from network/account dialog'''
        for item in ['do_follow_digsby', 'do_tweet_about_digsby']:
            info.pop(item, None)

        # if the user changes the password at runtime, then clear the oauth token
        if info.get('password', None) and self.password and info['password'] != self.password:
            log.critical('clearing oauth token')
            info['oauth_token'] = None

        super(TwitterAccount, self).update_info(**info)
        self.set_account_opts()

    def get_options(self):
        '''return the set of values to be serialized to the server'''

        opts = super(TwitterAccount, self).get_options()
        opts.update({'informed_ach': True, 'post_ach_all': False})
        for k in self.protocol_info()['defaults'].iterkeys():
            v = getattr(self, k)
            if v != self.default(k):
                opts[k] = v

        if self.oauth_token is not None:
            opts['oauth_token'] = self.oauth_token

        api_server = getattr(self, 'api_server', None)
        if api_server is not None:
            opts['api_server'] = api_server

        return opts

    def account_prefs(self):
        return [('autoscroll_when_at_bottom', 'twitter.autoscroll.when_at_bottom', True), ]

    def set_account_opts(self):
        if self.twitter_protocol is not None:
            opts = self.get_account_opts()
            self.twitter_protocol.set_options(opts)

    def on_pref_change(self, *a, **k):
        @wx.CallAfter
        def after():
            try:
                timer = self._preftimer
            except AttributeError:
                timer = self._preftimer = wx.PyTimer(self.set_account_opts)

            timer.StartOneShot(500)

    @property
    def update_frequencies(self):
        return dict((a, getattr(self, a)) for a in
                    ('friends_timeline',
                     'direct_messages',
                     'replies',
                     'search_updatefreq'))

    def __init__(self, **options):
        for key in self.protocol_info()['defaults'].iterkeys():
            try: val = options[key]
            except KeyError: val = self.default(key)
            setattr(self, key, val)

        self.oauth_token = options.pop('oauth_token', None)

        self._on_online = Delegate()

        self.count = None
        self.twitter_protocol = None

        if False:
            # TODO: this will take an hour to come back from idle
            @guithread
            def later():
                self.idle_timer = wx.PyTimer(self.on_idle_timer)
                MINUTE_MS = 60 * 1000 * 60
                self.idle_timer.StartRepeating(30 * MINUTE_MS)

        social.network.__init__(self, **options)

        self.header_funcs = [
            (_('Home'), 'http://twitter.com'),
            (_('Profile'), lambda: wx.LaunchDefaultBrowser('http://twitter.com/' + self.twitter_username)),
            (_('Followers'), 'http://twitter.com/followers'),
            (_('Following'), 'http://twitter.com/following'),
        ]

        import twitter_notifications as twitter_notifications
        twitter_notifications._register_hooks()

        # options that affect first creation of the account.
        # account dialog will call onCreate
        self.do_follow_digsby = options.pop('do_follow_digsby', False)
#        self.do_tweet_about_digsby = options.pop('do_tweet_about_digsby', False)

        for twitter_pref, digsby_pref, default in self.account_prefs():
            common.profile.prefs.link(digsby_pref, self.on_pref_change)

        #self.extra_header_func = (_('Invite Friends'), self.on_invite_friends)

        self.api_server = options.get('api_server', None)

    @property
    def twitter_username(self):
        assert wx.IsMainThread()
        return self.j('account.selfScreenNameLower')

    def on_invite_friends(self):
        '''show a dialog asking ot direct message followers, inviting them to digsby'''

        from .twitter_gui import show_acheivements_dialog
        show_acheivements_dialog(lambda: self.j('inviteFollowers();'))

    def on_idle_timer(self):
        if self.twitter_protocol is not None:
            import gui.native.helpers
            from common import pref
            idle = gui.native.helpers.GetUserIdleTime() > pref('twitter.idle_time', type=int, default=(10 * 60 * 1000))
            val = 'true' if idle else 'false'
            self.j('window.userIdle = %s;' % val)

    def onCreate(self):
        '''called just after this account type is created by the user'''

        if self.do_follow_digsby:
            self._on_online += lambda: self.twitter_protocol.webkitcontroller.JSCall('follow', screen_name='digsby')
#        if self.do_tweet_about_digsby:
#            self._on_online += lambda: self.twitter_protocol.on_status(DIGSBY_TWEET_MESSAGE())
        if SHOW_INVITE_DM_DIALOG_ON_CREATE:
            wx.CallAfter(self.on_invite_friends)

    def get_account_opts(self):
        opts = dict((a, getattr(self, a))
                for a in self.protocol_info()['defaults'])

        for twitter_pref, digsby_pref, default in self.account_prefs():
            opts[twitter_pref] = common.pref(digsby_pref, default)

        opts['demovideo_link'] = DEMO_VIDEO_LINK()

        api_server = getattr(self, 'api_server', None)
        log.warning('api_server: %r', api_server)
        if api_server is not None:
            opts['apiRoot'] = api_server

        return opts

    def on_state_change(self, state):
        log.info('on_state_change: %r', state)

        if state == 'online':
            self.change_state(self.Statuses.ONLINE)
            self._on_online.call_and_clear()

        elif state == 'autherror':
            self.set_offline(self.Reasons.BAD_PASSWORD)

        elif state == 'oautherror':
            if self._should_retry_oauth():
                log.warning('negotiating new OAuth token')
                metrics.event('Twitter OAuth Refresh Token')
                self.Disconnect(set_state=False)
                self.oauth_token = None
                self.Connect()
            else:
                self.set_offline(self.Reasons.BAD_PASSWORD)

        elif state == 'connfail':
            self.set_offline(self.Reasons.CONN_FAIL)
            self.Disconnect(set_state=False)

    _last_oauth_retry_time = 0

    def _should_retry_oauth(self):
        now = time()
        if now - self._last_oauth_retry_time > 60*2:
            self._last_oauth_retry_time = now
            return True

    def Connect(self):
        @guithread
        def _connect():
            log.warning('twitter Connect')
            self.change_state(self.Statuses.CONNECTING)

            if self.twitter_protocol is not None:
                self.twitter_protocol.disconnect()

            self.twitter_protocol = TwitterProtocol(self.username, self._decryptedpw())
            self.json = self.twitter_protocol.json
            self.twitter_protocol.account = self
            self.twitter_protocol.connect(self.get_account_opts())
            e = self.twitter_protocol.events
            e.state_changed += self.on_state_change
            e.on_unread_counts += self.on_unread_counts
            e.on_feeds += self.on_feeds
            e.recent_timeline += self.invalidate_infobox
            e.self_tweet += self.invalidate_infobox
            e.status_update_clicked += self.update_status_window_needed
            e.on_corrupted_database += self.on_corrupted_database
            e.update_social_ids += self.on_update_social_ids
            e.received_whole_update += self.on_received_whole_update

    def _get_database_path(self):
        return self.connection._get_database_path()

    def on_corrupted_database(self):
        '''
        The webkit control window signals this method via "D.rpc('on_corrupted_database');"
        when sqlite indicates that the database is corrupted, or if the openDatabase call
        returns undefined.

        We try to remove the database file entirely, and then reconnect.
        '''

        if getattr(self, 'did_attempt_recovery', False):
            log.info('skipping on_corrupted_database, already done once')
            return

        log.info('corrupted_database detected')
        log.info('free disk space: %r', fileutil.free_disk_space())

        if self.connection:
            dbpath = self._get_database_path()
            log.info('  path to database: %r', dbpath)
            if dbpath:
                result = try_opening_tempfile(os.path.dirname(dbpath))
                log.info('opening tempfile: %r', result)

                self.Disconnect()

                def disconnected():
                    try:
                        log.info('  attempting delete')
                        os.remove(dbpath)
                    except Exception:
                        traceback.print_exc()
                    else:
                        log.info('success! reconnecting')
                        self.Connect()

                    self.did_attempt_recovery = True

                wx.CallLater(1000, disconnected)


    def on_feeds(self, feeds):
        self.invalidate_infobox()

    def observe_count(self, callback):
        self.add_gui_observer(callback, 'count')

    def unobserve_count(self, callback):
        self.remove_gui_observer(callback, 'count')

    def on_unread_counts(self, opts):
        self.setnotify('count', opts.get('total'))
        self.invalidate_infobox()

    def invalidate_infobox(self, *a, **k):
        self.on_update_social_ids()
        self.set_infobox_dirty()

    def on_received_whole_update(self):
        self.did_receive_whole_update = True

    def on_update_social_ids(self):
        if self.state == self.Statuses.ONLINE and getattr(self, 'did_receive_whole_update', False):
            self.twitter_protocol.update_social_ids()

    def set_infobox_dirty(self):
        self._dirty = True
        self.notify('dirty')

    def disconnect(self):
        self.Disconnect()

    def Disconnect(self, *a, **k):
        log.warning('twitter Disconnect')
        if self.twitter_protocol is not None:
            @guithread
            def after():
                p, self.twitter_protocol = self.twitter_protocol, None
                e = p.events
                e.state_changed -= self.on_state_change
                e.on_unread_counts -= self.on_unread_counts
                e.recent_timeline -= self.invalidate_infobox
                e.self_tweet -= self.invalidate_infobox
                e.on_feeds -= self.on_feeds
                e.status_update_clicked -= self.update_status_window_needed
                e.on_corrupted_database -= self.on_corrupted_database
                e.update_social_ids -= self.on_update_social_ids
                e.received_whole_update -= self.on_received_whole_update
                p.disconnect()

        @guithread
        def after2():
            set_state = k.pop('set_state', True)
            if set_state:
                self.set_offline(self.Reasons.NONE)

            self.did_receive_whole_update = False

            success = k.pop('success', None)
            if success is not None:
                success()

    def DefaultAction(self):
        if self.twitter_protocol is not None and self.state == self.Statuses.ONLINE:
            self.twitter_protocol.open_timeline_window()

    def update_status_window_needed(self):
        if common.pref('social.use_global_status', default=False, type=bool):
            wx.GetApp().SetStatusPrompt([self])
        else:
            self.twitter_protocol.open_timeline_window()

    def _enable_unread_counts(self):
        self.connection.set_account_pref('show_unread_count', True)
        self.on_unread_counts({'total':self.count})

    def _disable_unread_counts(self):
        self.connection.set_account_pref('show_unread_count', False)
        self.on_unread_counts({'total':self.count})

    def should_show_unread_counts(self):
        return _get_account_pref(self.username, 'show_unread_count', True)

    def count_text_callback(self, txt):
        if self.should_show_unread_counts() and self.count is not None:
            return txt + (' (%s)' % self.count)
        else:
            return txt

    def mark_all_as_read(self):
        self.connection.mark_all_as_read()

class TwitterProtocol(object):
    event_names = '''
        state_changed
        following
        reply
        trends
        on_unread_counts
        on_feeds
        on_edit_feed
        on_view
        on_change_view
        status_update_clicked
        recent_timeline
        self_tweet
        on_corrupted_database
        update_social_ids
        received_whole_update
'''.split()

    def __init__(self, username, password):
        self.username = username
        self.password = password

        self.recent_timeline = []
        self.self_tweet = None
        self.trends = {}

        self.feeds = []
        self.feeds_by_name = {}
        self.unread_counts = []

        e = self.events = Storage((name, Delegate()) for name in self.event_names)

        e.following += self.on_following
        e.trends += self.on_trends
        e.on_unread_counts += self.on_unread_counts
        e.recent_timeline += self.on_recent_timeline
        e.self_tweet += self.on_self_tweet
        e.on_feeds += self.on_feeds
        e.on_change_view += self.on_change_view
        e.on_view += self.on_view_changed

        def render_tweets(tweets, render_context):
            return htmlize_tweets(self, tweets)

        self.social_feed = SocialFeed('twitter_' + self.username,
                                      'twitter_' + self.username,
                                      self.get_tweet_feed,
                                      render_tweets,
                                      lambda: self.account.set_infobox_dirty)

    def _get_database_path(self):
        webview = self.webkitcontroller.webview
        return webview.GetDatabasePath('digsbysocial_' + self.username)

    def set_options(self, options):
        guithread(lambda: self.webkitcontroller.JSCall('setAccountOptions', **options))

    def on_change_view(self, feed_name):
        log.info('on_change_view %r', feed_name)
        window = self.webkitcontroller.FeedWindow
        if window is not None:
            log.info('  found a window, calling switch_to_view')
            window.switch_to_view(feed_name)
            tlw = window.Top
            if tlw.IsIconized(): tlw.Iconize(False)
            window.Top.Raise()
        else:
            log.info('  no window found, calling open_timeline_window')
            self.webkitcontroller.open_timeline_window(feed_name)

    def on_view_changed(self, feed_name):
        feed = self.feeds_by_name.get(feed_name, None)
        if feed is not None and feed.get('query', None) is not None and feed.get('save', False):
            hooks.notify('digsby.statistics.twitter.viewed_search')

    def on_feeds(self, feeds):
        self.feeds = feeds
        self.feeds_by_name = dict((f['name'], f) for f in feeds)
        self.feeds_by_name.update(favorites=dict(name='favorites', label=_('Favorites')),
                                  history=dict(name='history', label=_('History')))

        import twitter_notifications as tnots
        tnots._update_notifications(self, feeds)

        self._save_feeds(feeds)

    def _save_feeds(self, feeds):
        # don't include non-saved searches
        def should_save(f):
            return f['type'] not in ('search', 'user') or f.get('save', False)

        feeds_pref = filter(should_save, deepcopy(feeds))

        # don't serialize certain attributes out to prefs
        for feed in feeds_pref:
            for attr in ('count', 'label'):
                feed.pop(attr)

        self.set_account_pref('feeds', feeds_pref)

    @property
    def account_prefix(self):
        return 'twitter.' + self.username

    def account_pref_key(self, name):
        return _account_pref_key(self.username, name)

    def set_account_pref(self, name, value):
        from common import setpref
        value = simplejson.dumps(value)
        setpref(self.account_pref_key(name), value)

    def get_account_pref(self, name, default):
        return _get_account_pref(self.username, name, default)

    def on_unread_counts(self, opts):
        self.unread_counts = opts.get('feeds')
        self.unread_total = opts.get('total')

    def on_recent_timeline(self, tweets):
        self.recent_timeline = [to_storage(t) for t in tweets]
        self.recent_timeline.reverse()
        self.events.update_social_ids()

    def update_social_ids(self):
        try:
            t = self._socialtimer
        except AttributeError:
            def later():
                ids = [p['id'] for p in self.recent_timeline]
                self.social_feed.new_ids(ids)

            t = self._socialtimer = wx.PyTimer(later)

        if not t.IsRunning():
            t.StartOneShot(1000)

    def on_self_tweet(self, tweet):
        self.self_tweet = to_storage(tweet)

    def on_following(self, ids):
        # TODO: stop should actually do something
        if hasattr(self, 'stream'):
            self.stream.stop()

        if common.pref('twitter.streaming', default=False):
            from twitterstream import TwitterStream
            self.stream = TwitterStream(self.username, self.password, ids)
            self.stream.on_tweet += self.on_stream_tweet
            self.stream.start()

    def on_trends(self, trends):
        # TODO: store trends over time?
        #self.trends.update(trends['trends'])

        trends = trends['trends']
        self.trends = trends[trends.keys()[0]]

    def on_stream_tweet(self, tweet):
        if self.webkitcontroller is not None:
            wx.CallAfter(self.webkitcontroller.realtime_tweet, tweet)

    def connect(self, accountopts):
        @guithread
        def later():
            self.webkitcontroller = TwitterWebKitController(self)
            self.webkitcontroller.initialize(self.username,
                    self.password,
                    self.get_user_feeds(),
                    accountopts)
            self.init_webkit_methods()

    def _verify_databases(self):
        # webkit doesn't release file object locks for corrupted databases,
        # so check the integrity of the databases we care about here first.
        # upon any errors, they are deleted.

        import sqlite3

        def try_query_remove_on_error(dbpath, query):
            '''try a query on database dbpath. dbpath is deleted on any
            exception.'''

            dbpath = path(dbpath)
            log.info('verifying db %r', dbpath)
            if not dbpath.isfile():
                log.info('not a file')
                return

            try:
                conn = sqlite3.connect(dbpath)
                with conn:
                    conn.execute(query)
                conn.close()
            except Exception:
                traceback.print_exc()
                with traceguard:
                    log.warning('exception encountered, removing %r', dbpath)
                    dbpath.remove()
                    log.warning('remove completed')

        # check the integrity of the "index" database that webkit uses to track
        # each site's database
        try_query_remove_on_error(
                path(self.webkitcontroller.webview.GetDatabaseDirectory()) / 'Databases.db',
                'select * from Databases limit 1')

        # calling window.openDatabase is necessary once for the below
        # _get_database_path() call to work.
        self.webkitcontroller.webview.RunScript(
            '''var test_db = window.openDatabase('_test_db_', "1.0", "test db", 1024);''')

        # ensure the twitter database is okay.
        try_query_remove_on_error(
                self._get_database_path(),
                'create table if not exists _test (foo int)')

    def get_user_feeds(self):
        def deffeed(n):
            return dict(name=n, type=n)

        default_feeds = [deffeed(n) for n in
                        ('timeline', 'mentions', 'directs')]

        userfeeds = self.get_account_pref('feeds', default_feeds)

        def revert():
            log.warning('REVERTING user feeds, was %r:', userfeeds)
            self.set_account_pref('feeds', default_feeds)
            return default_feeds

        from pprint import pprint; pprint(userfeeds)

        if not isinstance(userfeeds, list):
            return revert()

        try:
            if userfeeds is not default_feeds:
                for feed in default_feeds:
                    for ufeed in userfeeds:
                        if feed['type'] == ufeed['type']:
                            break
                    else:
                        return revert()
        except Exception:
            traceback.print_exc()
            return revert()

        return userfeeds

    def init_webkit_methods(self):
        # forward some methods to webkitcontroller
        for method_name in '''
            open_timeline_window
            clear_cache
            update
            on_status
            on_status_with_error_popup
            add_feed
            edit_feed
            delete_feed
            set_feeds
            add_group
            get_users
            get_prefs'''.split():

            setattr(self, method_name, getattr(self.webkitcontroller, method_name))

    def json(self, *a, **k):
        self.webkitcontroller.json(*a, **k)

    def disconnect(self):
        self.webkitcontroller.disconnect()

    def mark_all_as_read(self):
        self.webkitcontroller.evaljs('markAllAsRead();')

    def on_reply(self, id, screen_name, text):
        from .twitter_gui import TwitterFrame
        TwitterFrame.Reply(id, screen_name, text)

    def on_retweet(self, id, screen_name, text):
        from .twitter_gui import TwitterFrame
        TwitterFrame.Retweet(id, screen_name, text)

    def on_direct(self, screen_name):
        from .twitter_gui import TwitterFrame
        TwitterFrame.Direct(screen_name)

    def mark_feed_as_read(self, feed_name):
        self.webkitcontroller.JSCall('markFeedAsRead', feedName=feed_name)

    def toggle_addstocount(self, feed_name):
        self.webkitcontroller.JSCall('toggleAddsToCount', feedName=feed_name)

    def get_ids_and_context(self, _feed_context):
        #_feed_context ?= tab
        return list(t['id'] for t in self.get_tweet_feed()), self.recent_timeline

    def get_tweet_feed(self):
        self_id = self.self_tweet['id'] if self.self_tweet is not None else None
        for tweet in self.recent_timeline:
            if self_id is None or self_id != tweet['id']:
                yield tweet

class TwitterWebKitController(object):
    def __init__(self, protocol):
        from .twitter_gui import TwitterWebView

        self.hidden_frame = wx.Frame(None)

        self.protocol = protocol
        w = self.webview = TwitterWebView(self.hidden_frame, protocol)
        w._setup_logging(log)

        from rpc.jsonrpc import JSPythonBridge
        self.bridge = JSPythonBridge(w)
        self.bridge.on_call += self.on_call

        w.Bind(wx.webview.EVT_WEBVIEW_LOAD, self.on_load)
        self.when_load = None

        # button callbacks for popups
        self.tweet_buttons = [(_('Reply'), input_callback(self.on_popup_reply, prefill_reply)),
                              (_('Retweet'), input_callback(self.on_popup_retweet, prefill_retweet))]
        self.direct_buttons = [(_('Direct'), input_callback(self.on_popup_direct, prefill_direct))]

    @property
    def FeedWindow(self):
        from .twitter_gui import TwitterFrame
        for win in wx.GetTopLevelWindows():
            if isinstance(win, TwitterFrame):
                if win.Parent.Top is self.hidden_frame:
                    return win.panel.webview

    def JSCall(self, method, **opts):
        if not wx.IsMainThread():
            raise AssertionError('JSCall called from thread ' + threading.current_thread().name)

        return self.bridge.Call(method, **opts)

    def on_popup_click(self, tweet):
        from common import pref
        from util import net

        url = None
        if pref('twitter.scan_urls', type=bool, default=True):
            links = net.find_links(tweet.text)
            if links and len(links) == 1:
                url = links[0]

        if url is None:
            if tweet.tweet_type == 'direct':
                url = 'http://twitter.com/#inbox'
            else:
                url = 'http://twitter.com/%s/statuses/%s' % (tweet.user.screen_name, tweet.id)

        wx.LaunchDefaultBrowser(url)

    def on_popup_reply(self, text, options):
        self.protocol.on_status_with_error_popup(text, options['tweet'].id)

    def on_popup_retweet(self, text, options):
        self.protocol.on_status_with_error_popup(text)

    def on_popup_direct(self, text, options):
        tweet = options['tweet']
        prefix = 'd ' + tweet.user.screen_name + ' '

        if not text.startswith(prefix):
            text = prefix + text

        self.protocol.on_status_with_error_popup(text)

    def on_call_corrupted_database(self, params):
        log.info('on_call_corrupted_database %r', params)
        self.protocol.events.on_corrupted_database()

    def on_call_edit_feed(self, feed):
        self.protocol.events.on_edit_feed(feed)

    def on_call_feeds(self, feeds):
        self.protocol.events.on_feeds(feeds)

    def on_call_unread(self, feeds):
        self.protocol.events.on_unread_counts(feeds)

    def on_call_change_view(self, feed_name):
        self.protocol.events.on_change_view(feed_name)

    def on_call_send_tweet(self, param, id_):
        param = dict((str(k), v) for k, v in param.items())
        self.on_status_with_error_popup(**param)

    def on_call_favorite_tweet(self, param, id_, webview):
        param = dict((str(k), v) for k, v in param.items())
        dumps = simplejson.dumps
        def run_success(result, **k):
            webview.RunScript('''Digsby.successIn(%s, %s);''' % (dumps(result), dumps(id_)))
        def run_error(error, **k):
            webview.RunScript('''Digsby.errorIn(%s, %s);''' % (dumps(error), dumps(id_)))
        self.JSCall('favorite', success=run_success, error=run_error, **param)

    def on_call_delete_tweet(self, param, id_, webview):
        param = dict((str(k), v) for k, v in param.items())
        dumps = simplejson.dumps
        def run_success(result, **k):
            webview.RunScript('''Digsby.successIn(%s, %s);''' % (dumps(result), dumps(id_)))
        def run_error(error, **k):
            webview.RunScript('''Digsby.errorIn(%s, %s);''' % (dumps(error), dumps(id_)))
        self.JSCall('deleteTweet', success=run_success, error=run_error, **param)

    def on_call_get_idle_time(self, params, id_, webview):
        from gui.native.helpers import GetUserIdleTime
        t = GetUserIdleTime()
        wx.CallAfter(Dsuccess, id_, self.webview, idleTime=t)

    def json(self, rpc, webview):
        # Javascript calls to D from the infobox get sent here
        self.on_call(rpc, webview)

    def on_call(self, json_obj, webview=None):
        params = json_obj.get('params')
        method = json_obj.get('method')
        id_ = json_obj.get('id')
        events = self.protocol.events

        try:
            call = getattr(self, 'on_call_' + method)
            call.__call__
        except AttributeError:
            pass
        else:
            if call.func_code.co_argcount < 3:
                return call(params[0])
            elif call.func_code.co_argcount < 4:
                return call(params[0], id_)
            else:
                return call(params[0], id_, webview)

        if method == 'viewChanged':
            feedName = params[0].get('feedName')
            events.on_view(feedName)
        elif method == 'following':
            following = params[0].get('following')
            events.following(following)
        elif method == 'state':
            state = params[0].get('state')
            if state is not None:
                events.state_changed(state)
        elif method == 'received_whole_update':
            events.received_whole_update()
        elif method == 'trends':
            trends = params[0].get('trends', None)
            if trends is not None:
                events.trends(trends)
        elif method == 'recentTimeline':
            tweets = params[0].get('tweets')
            events.recent_timeline(tweets)
        elif method == 'selfTweet':
            tweet = params[0].get('tweet')
            events.self_tweet(tweet)
        elif params:
            param = params[0]
            if param is not None and isinstance(param, dict):
                url = param.get('url')
                if url and url.startswith('digsby:'):
                    url = UrlQuery.parse('http' + url[6:], utf8=True) # UrlQuery doesn't like digsby://
                    q = url['query'].get

                    netloc = url['netloc']
                    if netloc == 'reply':
                        id, screen_name, text = q('id'), q('screen_name'), q('text')
                        if id and screen_name:
                            self.protocol.on_reply(id, screen_name, text)
                    elif netloc == 'retweet':
                        id, screen_name, text = q('id'), q('screen_name'), q('text')
                        if id and screen_name:
                            self.protocol.on_retweet(id, screen_name, text)
                    elif netloc == 'direct':
                        screen_name = q('screen_name')
                        if screen_name:
                            self.protocol.on_direct(screen_name)

    def on_call_next_item(self, params, id_, webview):
        return self.protocol.social_feed.jscall_next_item(webview, id_)

    def on_call_initialize_feed(self, params, id_, webview):
        return self.protocol.social_feed.jscall_initialize_feed(webview, id_)

    def on_call_status_update_clicked(self, *a, **k):
        self.protocol.events.status_update_clicked()

    def on_call_hook(self, hook_name):
        '''Allows Javascript to call Hooks.'''

        hooks.notify(hook_name)

    def on_call_fire(self, opts, id=None, buttons=None, onclick=None):
        from common import fire, pref
        from gui import skin

        # stringify keys, so that they can be keywords.
        # also turn dicts into storages
        opts = to_storage(dict((str(k), v)
                    for k, v in opts.iteritems()))

        if pref('twitter.popups.user_icons', default=True):
            from gui.browser.webkit.imageloader import LazyWebKitImage
            twitter_icon = skin.get('serviceicons.twitter', None)
            for tweet in opts.tweets:
                tweet.icon = LazyWebKitImage(tweet.user.profile_image_url, twitter_icon)

        def buttons_cb(item):
            if hasattr(item.tweet, 'sender_id'):
                return self.direct_buttons
            else:
                return self.tweet_buttons

        opts.update(onclick=onclick or self.on_popup_click,
                    popupid='twitter20_' + self.username + str(opts.get('popupid_postfix', '')),
                    buttons=buttons or buttons_cb,
                    max_lines=10)

        if pref('twitter.popups.mark_as_read', default=True):
            opts.update(mark_as_read=self.mark_as_read)

        opts.update(badge=skin.get('serviceicons.twitter', None))

        fire(**opts)

    def mark_as_read(self, item):
        self.JSCall('markAsRead', tweet_id=item.tweet['id'])

    def initialize(self, username, password, userfeeds=None, accountopts=None):
        self.username = username
        self.password = password
        userfeeds = [] if userfeeds is None else userfeeds


        def when_load():
            self.protocol._verify_databases()
            self.evaljs('window.resdir = %s' % simplejson.dumps((path(__file__).parent / 'res').url()))
            def success(token):
                opts = dict(username=self.username,
                            password=self.password,
                            feeds=userfeeds,
                            accountopts=accountopts or {})

                if token is not None:
                    assert hasattr(token, 'key'), repr(token)
                    opts.update(oauthTokenKey = token.key,
                                oauthTokenSecret = token.secret,

                                oauthConsumerKey = twitter_auth.CONSUMER_KEY,
                                oauthConsumerSecret = twitter_auth.CONSUMER_SECRET)

                    time_correction = twitter_auth.get_time_correction()
                    if time_correction is not None:
                        opts['accountopts'].update(timeCorrectionSecs=-time_correction)

                self.JSCall('initialize', **opts)

            api_server = getattr(self.protocol.account, 'api_server', None)
            if api_server is not None:
                return success(None)

            if self.oauth_token is not None:
                try:
                    token = OAuthToken.from_string(self.oauth_token)
                except Exception:
                    traceback.print_exc()
                else:
                    log.info('using token stored in account')
                    return success(token)

            def on_token(token):
                token_string = token.to_string()
                log.info('on_token received token from network: %r', token_string[:5])
                self.protocol.account.update_info(oauth_token=token_string)
                success(token)

            def on_token_error(e):
                errcode = getattr(e, 'code', None)

                # if obtaining an token fails, it may be because our time is set incorrectly.
                # we can use the Date: header returned by Twitter's servers to adjust for
                # this.
                if errcode == 401:
                    server_date = getattr(e, 'hdrs', {}).get('Date', None)
                    retries_after_401 = getattr(self.protocol, 'retries_after_401', 0)
                    if server_date and retries_after_401 < 1:
                        self.protocol.retries_after_401 = retries_after_401 + 1
                        log.warning('on_token_error: server date is %r', server_date)
                        server_date = parse_http_date(server_date)
                        log.warning('on_token_Error: RETRYING WITH NEW SERVER DATE %r', server_date)
                        twitter_auth.set_server_timestamp(server_date)
                        return twitter_auth.get_oauth_token(self.username, self.password, success=on_token, error=on_token_error)

                state = 'autherror' if errcode == 401 else 'connfail'
                log.error('on_token_error: e.code is %r', errcode)
                log.error('  changing state to %r', state)
                self.protocol.events.state_changed(state)

            log.info('getting new oauth token from network')
            twitter_auth.get_oauth_token(self.username, self.password, success=on_token, error=on_token_error)

        self.when_load = when_load

        url = APP_PATH.url()

        from gui.browser import webkit
        webkit.update_origin_whitelist(url, 'https', 'twitter.com', True)
        webkit.update_origin_whitelist(url, 'http', 'twitter.com', True)

        api_server = getattr(self.protocol.account, 'api_server', None)
        if api_server is not None:
            api = UrlQuery.parse(api_server)
            webkit.update_origin_whitelist(url, api['scheme'], api['netloc'], True)

        self.bridge.LoadURL(url)

    def set_oauth_token(self, token):
        self.protocol.account.oauth_token = token

    def get_oauth_token(self):
        return self.protocol.account.oauth_token

    oauth_token = property(get_oauth_token, set_oauth_token)

    def disconnect(self):
        @guithread
        def _disconnect():
            if not wx.IsDestroyed(self.hidden_frame):
                self.hidden_frame.Destroy()

    def open_timeline_window(self, feed_name=None):
        from .twitter_gui import TwitterFrame

        frame = TwitterFrame.ForProtocol(self.protocol)
        if frame is not None:
            frame.Iconize(False)
            frame.Raise()
        else:
            if feed_name is not None:
                js = 'openWindow(%s);' % simplejson.dumps(feed_name)
            else:
                js = 'openWindow();'

            self.evaljs(js)

    def update(self):
        self.evaljs('update();');

    def clear_cache(self):
        self.evaljs('dropAllTables();');

    def get_users(self, success=None, error=None):
        self.JSCall('getUsers', success=success, error=error)

    def get_prefs(self, success=None):
        self.JSCall('getPrefs', success=success)

    def on_status_with_error_popup(self, status, reply_id=None, success=None, error=None):
        '''sends a direct or tweet. on error, fire('error') is called (and
        optionally your own error callback.'''

        def _error(e):
            from common import fire
            import gui.clipboard

            if isinstance(e, basestring):
                error_message = u''.join([e, u'\n\n', u'"', status, u'"'])
            else:
                error_message = status


            fire('error',
                 title=_('Twitter Error'),
                 major=_('Send Tweet Failed'),
                 minor=error_message,
                 buttons=[(_('Retry'), lambda: self.on_status_with_error_popup(status)),
                          (_('Copy'),  lambda: gui.clipboard.copy(status)),
                          (_('Close'), lambda * a, **k: None)],
                 sticky=True)

            if error is not None:
                error(e)

        return self.on_status(status, reply_id, success, _error)

    def on_status(self, status, reply_id=None, success=None, error=None):
        return self.JSCall('tweet',
                         status=status,
                         replyTo=reply_id,
                         success=success,
                         error=error)

    def evaljs(self, js):
        if not wx.IsMainThread():
            raise AssertionError('evaljs called from thread ' + threading.current_thread().name)

        return self.webview.RunScript(js)

    def realtime_tweet(self, tweet_json):
        script = 'onTweet(' + tweet_json.strip() + ');'
        self.evaljs(script)

    def on_load(self, e):
        e.Skip()
        if e.GetState() == wx.webview.WEBVIEW_LOAD_ONLOAD_HANDLED:
            if self.when_load is not None:
                when_load, self.when_load = self.when_load, None
                when_load()

    def add_feed(self, feed_info):
        self.JSCall('addFeed', feed=feed_info)

    def edit_feed(self, feed_info):
        self.JSCall('editFeed', feed=feed_info)

    def delete_feed(self, feed_name):
        self.JSCall('deleteFeed', feedName=feed_name)

    def set_feeds(self, feeds):
        self.JSCall('setFeeds', feeds=feeds)

    def add_group(self, group_info):
        self.JSCall('addGroup', group=group_info)

class TwitterIB(gui_providers.InfoboxProviderBase):
    protocols.advise(asAdapterForTypes=[TwitterAccount], instancesProvide=[gui_interfaces.ICacheableInfoboxHTMLProvider])

    def __init__(self, acct):
        gui_providers.InfoboxProviderBase.__init__(self)
        self.acct = acct

    def get_html(self, *a, **k):
        if k.pop('set_dirty', True):
            self.acct._dirty = False
        return gui_providers.InfoboxProviderBase.get_html(self, *a, **k)

    def get_app_context(self, ctxt_class):
        return ctxt_class(path(__file__).parent.parent, self.acct.protocol)

    def get_context(self):
        ctxt = gui_providers.InfoboxProviderBase.get_context(self)
        conn = self.acct.twitter_protocol
        import twitter_util as tutil
        from path import path
        resdir = path(__file__).dirname() / 'res'
        ctxt.update(acct=self.acct,
                    conn=conn,
                    trends=conn.trends,
                    tweets=[],
                    counts=conn.unread_counts,
                    self_tweet=conn.self_tweet,
                    res=lambda p: (resdir / p).url(),
                    twitter_linkify=tutil.twitter_linkify,
                    format_tweet_date=tutil.format_tweet_date)
        return ctxt

    @property
    def _dirty(self):
        # TODO: no
        return True

def title_from_query(query):
    '''
    attempts to return a "title" for a search query

    >>> title_from_query('"Happy Labor Day" OR "Labour Day"')
    'Happy Labor Day'
    '''

    def dequote(s):
        if s.count('"') == 2 and s.startswith('"') and s.endswith('"'):
            return s[1:-1]

    title = dequote(query)
    if title is None:
        title = query.split(' OR ')[0].split(' AND ')[0]
        title = dequote(title) or title.split()[0].strip(string.punctuation)

    return title

def guithread(func):
    '''Calls func now if we're on the GUI thread; else calls it later on the
    GUI thread.'''

    if wx.IsMainThread():
        with traceguard:
            func()
    else:
        wx.CallAfter(func)

class input_callback(object):
    '''Passed to fire() as handlers for "buttons" callbacks. Causes popups to
    show input fields after pressing those buttons.'''

    # TODO: document this interface and place an abstract class in toast.py

    close_button = True
    spellcheck = True

    def spellcheck_regexes(self):
        import twitter_util
        return twitter_util.spellcheck_regex_ignores

    def __init__(self, cb, value_cb):
        self.input_cb = cb
        self.get_value = value_cb
        self.char_limit = 140

def _account_pref_key(username, name):
    return '.'.join(['twitter.prefs', username, name])

def _get_account_pref(username, name, default):
    from common import pref
    p = pref(_account_pref_key(username, name), default=default)
    if isinstance(p, basestring): p = simplejson.loads(p)
    return p

def get_users(callback, accts=None):
    if accts is None:
        from common import profile
        accts = [a for a in profile.socialaccounts
                 if a.connection is not None
                 and isinstance(a, TwitterAccount)]

    ctx = dict(count=0)
    all_users = {}

    for acct in accts:
        def cb(users):
            all_users.update(users)
            ctx['count'] += 1
            if ctx['count'] == len(accts):
                callback(all_users)

        acct.connection.get_users(cb)

def try_opening_tempfile(dirpath):
    '''
    some users see WebKit returning undefined from the openDatabase call. this
    function attempts to open a file in the database directory and write to it-
    to see if they don't have permission.
    '''

    try:
        tempfile = os.path.join(dirpath, 'test.tmp')
        with open(tempfile, 'w') as f:
            f.write('test')
        if not os.path.isfile(tempfile):
            raise Exception('file wasn\'t found after write: %r' % tempfile)

        try:
            os.remove(tempfile)
        except Exception:
            pass

    except Exception:
        traceback.print_exc()
        return False
    else:
        log.info('wrote to %r successfully', dirpath)
        return True

def htmlize_tweets(protocol, tweets, self_tweet=None):
    '''Given a protocol and a sequence of tweets, returns infobox HTML for them.'''

    t = TwitterIB(Storage(twitter_protocol=protocol, protocol='twitter'))
    return t.get_html(None,
                      set_dirty=False,
                      file='tweets.tenjin',
                      dir=t.get_context()['app'].get_res_dir('base'),
                      context=Storage(tweets=tweets, self_tweet=self_tweet))

def parse_http_date(s):
    import email.utils
    return email.utils.mktime_tz(email.utils.parsedate_tz(s))

