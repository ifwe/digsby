import os
import path
import traceback
import logging

import social
import protocols

import common
import common.actions as actions
import common.protocolmeta as protocolmeta
from common.notifications import fire

import util
import util.callbacks as callbacks
import util.Events as Events
import util.cacheable as cacheable
import util.net as net
import util.primitives.strings as string_helpers

import gui.infobox.interfaces as gui_interfaces
import gui.infobox.providers as gui_providers
import common.AchievementMixin as AM

from . import fberrors
from . import action_links
from . import objects
from . import fbconnectlogin

import provider_facebook.facebook_service_provider as fb_sp
from facebook import oauth2login

log = logging.getLogger('facebook.acct')

DESKTOP_APP_POPUP = 'http://www.facebook.com/desktopapp.php?popup'
DISLIKE = u"Dislike! (via http://digsby.com/fb)"

class input_callback(object):
    close_button = True
    spellcheck = True

    def __init__(self, cb):
        self.input_cb = cb

    def __eq__(self, other):
        return getattr(other, 'input_cb', object()) == self.input_cb

class FacebookAccount(AM.AchievementMixin, social.network, Events.EventMixin):

    @property
    def updatefreq(self):
        return common.pref('facebook.updatefreq', 5 * 60) # in seconds

    events = Events.EventMixin.events | set([
                                      'connect_requested',
                                      'connect',
                                      'update_requested',
                                      'update',
                                      ])
    _dirty = True
    facebook_url      = 'http://www.facebook.com/'

    alerts_keys = 'num_msgs num_pokes num_shares num_friend_requests num_group_invites num_event_invites num_notifications'.split()
    header_funcs= [(k,lambda v=v: FacebookAccount.launchfacebook(v)) for k,v in
                   (('Home',''),
                    ('Profile','profile.php'),
                    ('Friends','friends.php'),
                    ('Photos','photos.php'),
                    ('Inbox','inbox/')
                    )]

    extra_header_func = ("Invite Friends", lambda: launchbrowser('http://apps.facebook.com/digsbyim/invite.php'))

    def __init__(self, **options):
        self.connection = False
        options.setdefault('password', None)
        self.secrets = options.setdefault('secrets', '')
        self.uid     = options.setdefault('uid', None)
        self.show_hidden_posts = options.setdefault('show_hidden_posts', False)
        self.preferred_filter_key = options.setdefault('preferred_filter_key', 1) #1 = live feed, the second key known to work.

        AM.AchievementMixin.__init__(self, **options)

        self.have_logged_in = False

        Events.EventMixin.__init__(self)
        self.bind_events()
        if not getattr(FBIB, '_tmpl', None):
            try:
                import time
                a = time.clock()
                t = FBIB(self)
                context = gui_providers.InfoboxProviderBase.get_context(t)
                t.load_files(context)
                t.get_template()
                FacebookAccount.preload_time = time.clock() - a
            except Exception:
                traceback.print_exc()

        filters = options.pop('filters', {})
        self._update_filters(filters)

        social.network.__init__(self, **options)

    @property
    def access_token(self):
        return self.secrets

    @access_token.setter
    def access_token(self, val):
        self.secrets = val

    def _update_filters(self, filters):
        found_filters = filters.get('alerts', [True]*len(self.alerts_keys))
        alert_filters = [True]*len(self.alerts_keys)
        alert_filters[:len(found_filters)] = found_filters
        self.filters = dict(alerts=dict(zip(self.alerts_keys, alert_filters)))
        return len(found_filters) != len(self.alerts_keys)

    def update_info(self, **info):
        filters = info.pop('filters', None)
        if filters is not None:
            self._update_filters(filters)
        self._dirty = True
        social.network.update_info(self, **info)

    def bind_events(self):
        self.bind('connect', self.call_on_connect)
        self.bind('connect_requested', self.do_login)
        self.bind('update_requested', self._update)
        self.bind('update', self.update_complete)

    def call_on_connect(self):
        self.on_connect()

    def should_update(self):
        return self.state is not self.Statuses.AUTHENTICATING

    def _update(self):
        if not self.should_update():
            return
        elif self.state is self.Statuses.OFFLINE:
            self.change_state(self.Statuses.CONNECTING)
        elif self.state not in (self.Statuses.CONNECTING, self.Statuses.CHECKING):
            self.change_state(self.Statuses.CHECKING)
        if self.connection:
            self.connection.clear()
        else:
            self.new_connection()
        self.connection.bind('not_logged_in', self.do_login)
        self.connection.bind('got_stream', self.update_complete)
        self.connection.bind('status_updated', self.set_dirty)
        self.connection.bind('conn_error', self.conn_error)
        self.connection.bind('infobox_dirty', self.set_dirty)
        self.connection.get_stream()

    def conn_error(self, *a, **k):
        self.set_offline(self.Reasons.CONN_LOST)

    def new_connection(self):
        import facebookprotocol
        self.connection = facebookprotocol.FacebookProtocol(self)

    def update_complete(self):
        self._dirty = True
        if self.OFFLINE:
            return
        self.change_state(self.Statuses.ONLINE)
        if self.achievements_paused: #don't need the lock to check here.
            self.unpause_achievements()
        self.fire_notifications(self.alerts if hasattr(self, 'alerts') else objects.Alerts(), self.connection.last_alerts)
        self.alerts = self.connection.last_alerts
        self.notification_popups()
        self.newsfeed_popups()

    @property
    def cache_dir(self):
        'directory for cache of this facebook account'
        assert self.uid
        return os.path.join('facebook', str(self.uid))

    @property
    def cache_path(self):
        return os.path.join(self.cache_dir, 'facebook.dat')

    old_stream_ids = cacheable.cproperty(set, user=True)

    def newsfeed_popups(self, filter_old=True):
        log.info('doing newsfeed popups')
        s = self.connection.last_stream
        old_ids = self.old_stream_ids if filter_old else ()
        feed = s['posts']
        new_posts = []
        for post in feed:
            if post['post_id'] in old_ids:
                log.info('post %r is old', post['post_id'])
                break
            source = post.get('source_id')
            actor  = post.get('actor_id')
            viewer = post.get('viewer_id')
            try:
                do_add = source and viewer and int(source) != int(viewer) and int(actor) != int(viewer)
            except ValueError:
                do_add = True
            if do_add:
                new_posts.append(post)
            else:
                log.info('filtered message %s because it came from this account', post['post_id'])

        options = dict(buttons=self.get_popup_buttons)

        if new_posts:
            from gui import skin
            if common.pref('facebook.popups.user_icons', default=True):
                from gui.browser.webkit.imageloader import LazyWebKitImage
                default_icon = skin.get('serviceicons.facebook', None)
                for post in new_posts:
                    try:
                        url = s.profiles[int(post['actor_id'])].pic_square
                    except Exception:
                        traceback.print_exc()
                    else:
                        post.icon = LazyWebKitImage(url, default_icon)

            fire(
                'facebook.newsfeed',
                profiles = s['profiles'],
                posts=new_posts,
                popupid='%d.facebook' % id(self),
                update='paged',
                badge=skin.get('serviceicons.facebook', None),
                scrape_clean=string_helpers.scrape_clean,
                onclick = self.on_popup_click_post, **options
            )
        self.old_stream_ids = set(self.connection.last_stream['post_ids'])

    old_notification_ids = cacheable.cproperty(set, user=True)

    def notification_popups(self, filter_old=True, filter_read=True):
        log.info('doing notification popups')
        s = self.connection.last_stream
        old_ids = self.old_notification_ids if filter_old else ()
        new_notifications = []
        notifications = s['notifications']
        for notification in notifications:
            if filter_read and int(notification['is_unread']) != 1:
                continue
            if notification['notification_id'] in old_ids:
                log.info('notification %r is old', notification['notification_id'])
                break
            if not notification['title_text']:
                continue
            new_notifications.append(notification)

        if new_notifications:
            from gui import skin
            options = {}
            if common.pref('facebook.popups.user_icons', default=True):
                from gui.browser.webkit.imageloader import LazyWebKitImage
                default_icon = skin.get('serviceicons.facebook', None)
                for notification in new_notifications:
                    try:
                        url = s.profiles[int(notification['sender_id'])].pic_square
                    except Exception:
                        traceback.print_exc()
                    else:
                        notification.icon = LazyWebKitImage(url, default_icon)
            fire(
                'facebook.notifications',
                profiles = s['profiles'],
                notifications=new_notifications,
                popupid='%d.facebook' % id(self),
                update='paged',
                sticky = common.pref('facebook.notifications.sticky_popup', type = bool, default = False),
                badge=skin.get('serviceicons.facebook', None),
                onclick = self.on_popup_click_notification, **options
            )

        self.old_notification_ids = set(n['notification_id'] for n in notifications)

    def get_popup_buttons(self, item):
        popup_buttons = []

        post = item.post
        post_id = post['post_id']
        post = self.connection.last_stream['post_ids'][post_id]
        enabled = not post.get('pending', False)

        def count_str(count):
            return (' (%s)' % count) if count and count != '0' else ''

        # comment button
        comments = post.get('comments', {})
        can_post = comments.get('can_post')
        if can_post:
            num_comments = int(comments.get('count', 0))
            popup_buttons.append((_('Comment') + count_str(num_comments), input_callback(self.on_popup_comment)))

        # like button
        likes = post.get('likes', {})
        can_like = likes.get('can_like', True)
        if can_like:
            liked = likes.get('user_likes', False)
            num_likes = int(likes.get('count', 0))
            like_caption = _('Like') if not liked else _('Unlike')
            popup_buttons.append((like_caption + count_str(num_likes), self.on_popup_like, enabled))

#        print popup_buttons

        return popup_buttons

    def on_popup_comment(self, text, options):
        post_id = options['post']['post_id']
        self.connection.addComment(post_id, text.encode('utf-8'),
                                   success=(lambda *a, **k: self.set_dirty()),
                                   error=self.on_popup_error(_('comment')))

    def on_popup_like(self, item, control):
        post = item.post
        post_id = post['post_id']

        if post['likes']['user_likes']:
            func = self.connection.removeLike
        else:
            func = self.connection.addLike

        def set_pending(pending):
            post['pending'] = pending
            control.update_buttons()

        def on_success(*a, **k):
            self.set_dirty()
            set_pending(False)

        def on_error(*a, **k):
            self.on_popup_error(_('like'))(*a, **k)
            set_pending(False)

        func(post_id, success=on_success,
                      error=self.on_popup_error(_('like')))

        set_pending(True)


    on_popup_like.takes_popup_item = True
    on_popup_like.takes_popup_control = True

    def on_popup_error(self, thing):
        def on_error(response, *a, **k):
            # if we don't have stream publish permissions, show a popup allowing
            # the user to grant it.
            if isinstance(response, fberrors.FacebookError) and int(response.tag.error_code) == 200:
                fire(
                    'error', title=_('Facebook Error'),
                    major = _('Error posting {thing}').format(thing=thing),
                    minor = _('Digsby does not have permission to publish to your stream.'),
                    buttons = [(_('Grant Permissions'), self.do_grant),
                               (_('Close'), lambda: None)]
                )
        return on_error

    @actions.action(lambda self, *a, **k: ((self.state == self.Statuses.ONLINE) and common.pref('can_has_social_update',False)) or None)
    def tell_me_again(self):
        self.fire_notifications(objects.Alerts(), self.connection.last_alerts)
        self.notification_popups(filter_old=False)
        return self.newsfeed_popups(filter_old=False)

    def fire_notifications(self, old_alerts, new_alerts):
        '''
        fires notifications for new information from facebook.
        '''
        log.debug('doing alert notifications')

        alerts = new_alerts - old_alerts
        if alerts and self.enabled:

            # newer, and still exists
            TITLE     = _("Facebook Alerts")

            fire_alerts = list()
            def firealert(msg, onclick):
                fire_alerts.append((msg, onclick))

            if alerts.msgs_time > 0 and new_alerts['num_msgs']:
                firealert(_('You have new messages.'), 'msgs')

            if alerts.pokes_time > 0 and new_alerts['num_pokes']:
                firealert(_('You have new pokes.'),    'pokes')

            if alerts.shares_time > 0 and new_alerts['num_shares']:
                firealert(_('You have new shares.'), 'shares')

            if alerts['num_friend_requests']:
                firealert(_('You have new friend requests.'), 'friend_requests')

            if alerts['num_group_invites']:
                firealert(_('You have new group invites.'), 'group_invites')

            if alerts['num_event_invites']:
                firealert(_('You have new event invites.'), 'event_invites')

            #this one isn't really useful by itself
            #we should check if the popups for notifications are on
            if alerts['num_notifications'] and fire_alerts:
                firealert(_('You have new notifications.'), 'notifications')

            if fire_alerts:
                if len(fire_alerts) > 1:
                    # With more than one type of new alert, just go to the main facebook page.
                    onclick = self.facebook_url
                else:
                    # Otherwise, get a more specific URL from Alerts.urls
                    msg, url_type = fire_alerts[0]
                    onclick = alerts.urls[url_type]

                message = u'\n'.join(k for k,_v in fire_alerts)

                fire(
                    'facebook.alert',
                    title   = TITLE,
                    msg     = message,
                    buttons = lambda item: [], # this is necessary until popups recognize "None" as clearing buttons.
                    update='paged',
                    popupid = '%d.facebook' % id(self),
                    onclick = onclick
                )

        if self.enabled:
            self.notify('count')

    @classmethod
    def launchfacebook(cls, strng):
        launchbrowser(cls.facebook_url + strng)

    def get_options(self):
        opts = super(FacebookAccount, self).get_options()
        secrets = self.secrets
        if secrets:
            opts['secrets'] = secrets
        uid = self.uid
        if uid:
            opts['uid'] = uid
        alrts = [bool(self.filters['alerts'][x]) for x in self.alerts_keys]
        opts['filters'] = dict(alerts=alrts)

        #CAS: needs to be abstracted
        for attr in ('show_hidden_posts', 'preferred_filter_key'):
            if getattr(self, attr, None) != self.default(attr):
                opts[attr] = getattr(self, attr, None)

        return opts

#========================================================================================================================
# begin socialnetwork/account interface
#========================================================================================================================
    # account boilerplate
    service = protocol = 'facebook'
    def Connect(self):
        self.change_state(self.Statuses.CONNECTING)

        def _ready_to_connect():
            if self.enabled:
                self.event('connect_requested')
            else:
                self.set_offline(self.Reasons.NONE)

        AM.AchievementMixin.try_connect(self, _ready_to_connect)

    def show_ach_dialog(self, success):
        from .fbgui import FacebookAchievementsDialog
        FacebookAchievementsDialog.show_dialog(None,
                                 u'New Facebook Integration (%s)' % self.name,
                                 message=UPGRADE_QUESTION,
                                 success=success,
                                 )


    def Disconnect(self, *a, **k):
        self.set_offline(self.Reasons.NONE)
    disconnect = Disconnect

    def DefaultAction(self):
        self.edit_status()

    @actions.action(lambda self, *a, **k: ((self.state == self.Statuses.ONLINE) and common.pref('can_has_social_update',False)) or None)
    def update_now(self, *a, **k):
        if not self.have_logged_in:
            self.have_logged_in = True
            self.unbind('connect_requested', self.do_login)
            self.bind('connect_requested', self.update_now)
        self.event('update_requested')

    def observe_count(self,callback):
        self.add_gui_observer(callback, 'count')

    def unobserve_count(self, callback):
        self.remove_gui_observer(callback, 'count')

    def observe_state(self, callback):
        self.add_gui_observer(callback, 'enabled')
        self.add_gui_observer(callback, 'state')

    def unobserve_state(self, callback):
        self.remove_gui_observer(callback, 'enabled')
        self.remove_gui_observer(callback, 'state')

    @property
    def count(self):
        return getattr(getattr(getattr(self, 'connection', None), 'last_alerts', None), 'count', 0)

    def login_success(self, check_instance, did_login=False, *a, **k):
        with fb_sp.FacebookLogin(self) as foo:
            self.connection.digsby = foo.loginmanager.digsby
            self.uid = foo.loginmanager.digsby.uid
        if did_login:
            self.loginproto = oauth2login.LoginCheck(api=self.connection.digsby,
                              login_success=self.real_login_success,
                              login_error=self.fail,
                              username=self.username,
                              acct=self)
            self.loginproto.initiatiate_check(False)
        else:
            self.change_state(self.Statuses.CONNECTING)
            return self.update_now(*a, **k)

    def real_login_success(self, *a, **k):
        try:
            self.access_token = self.connection.digsby.access_token
            self.password = None
            self.uid = self.connection.digsby.uid
            self.update_info()
        except Exception:
            traceback.print_exc()
        self.change_state(self.Statuses.CONNECTING)
        return self.update_now(*a, **k)

    def do_login(self):
        if not self.connection:
            self.new_connection()
        if self.OFFLINE or self.AUTHENTICATING:
            return
        self.change_state(self.Statuses.AUTHENTICATING)

        #ask the service provider to do this, somewhere we need a delay.

        with fb_sp.FacebookLogin(self) as foo:
            foo.do_check(
                         login_success=self.login_success,
                         login_error=self.fail,
                         )
        return

    def fail(self, check, answer=None, *a, **k):
        if isinstance(answer, dict) and answer.get('read_stream', None) == 0:
            try:
                fire(
                    'error',
                    title="Facebook Error",
                    major="Permission Missing - News Feed",
                    minor=('Digsby requires permission to access your News Feed to function properly.'
                           '  This permission was not allowed.')
                )
            except Exception:
                traceback.print_exc()
        self.set_offline(self.Reasons.BAD_PASSWORD)

    def json(self, rpc, webview):
        self.webview = webview
        method = rpc.pop('method')
        args = rpc.pop('params')[0]
        if method == 'do_like':
            self.do_like(args['post_id'], rpc.pop('id'))
        elif method == 'do_unlike':
            self.do_unlike(args['post_id'], rpc.pop('id'))
        elif method == 'do_dislike':
            self.do_dislike(args['post_id'], rpc.pop('id'))
        elif method == 'do_undislike':
            self.do_undislike(args['post_id'], rpc.pop('id'))
        elif method == 'post_comment':
            self.post_comment(args['post_id'], args['comment'], rpc.pop('id'))
        elif method == 'get_comments':
            self.get_comments(args['post_id'], rpc.pop('id'))
        elif method == 'remove_comment':
            self.remove_comment(args['comment_id'], rpc.pop('id'))
        elif method == 'do_grant':
            self.do_grant()
        elif method == 'initialize_feed':
            return self.connection.social_feed.jscall_initialize_feed(webview, rpc.pop('id'))
        elif method == 'next_item':
            return self.connection.social_feed.jscall_next_item(webview, rpc.pop('id'))
        elif method == 'edit_status':
            self.edit_status()
        elif method == 'hook':
            import hooks
            hooks.notify(args)
        elif method == 'link':
            link = args.pop('href')
            launchbrowser(link)
        elif method == 'get_album':
            self.get_album(args['aid'].encode('utf-8'), rpc.pop('id'))
        elif method == 'foo':
            print 'bar:', len(args['bar'])
        elif method == 'notifications_markRead':
            self.notifications_markRead(args['notification_ids'])
#        elif method == 'stop':
#            foo = 'wtf'
#            print foo #put breakpoint here; put "D.notify('stop');" in JavaScript.
    def get_album(self, aid, id):
        self.connection.digsby.query('select pid, src_big, link, caption from photo where aid="%s"' % aid,
                                     success=(lambda *a, **k:self.got_album(id=id, *a, **k)),)

    def notifications_markRead(self, notification_ids):
        self.connection.digsby.notifications.markRead(notification_ids=notification_ids)
        try:
            self.connection.last_alerts.update_notifications()
        except AttributeError:
            traceback.print_exc()
        else:
            self.notify('count')

    def got_album(self, album, id):
        if isinstance(album, list):
            self.Dsuccess(id, album=album)

    def post_comment(self, post_id, comment, id):
        comment = comment.encode('utf-8')
        post_id = post_id.encode('utf-8')
        self.connection.addComment(post_id, comment,
                                   success=(lambda *a, **k:self.append_comment(id=id, *a, **k)),
                                   error=(lambda *a, **k: self.Dexcept(id, *a, **k))
                                   )

    def get_comments(self, post_id, id):
        post_id = post_id.encode('utf-8')
        self.connection.getComments(post_id,
                                    success=(lambda *a, **k:self.render_comments(id=id, *a, **k)),
                                    error=(lambda *a, **k: self.Dexcept(id, *a, **k)))

    def render_comments(self, post_id, count, id):
        t = FBIB(self)
        context = {}
        context['post'] = self.connection.last_stream['post_ids'][post_id]
        context['feed'] = self.connection.last_stream
        context['comment_count'] = count
        comments_html = t.get_html(None, set_dirty=False,
                         dir=t.get_context()['app'].get_res_dir('base'),
                         file='comments.py.xml',
                         context=context)
        comment_link_html = t.get_html(None, set_dirty=False,
                         file='comment_link.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
#        print comments_html
#        print comment_link_html
#        print count
        self.Dsuccess(id, comments_html=comments_html, comment_link_html=comment_link_html, count=count)

    def append_comment(self, post_id, comment_dict, id):
        t = FBIB(self)
        context = {}
        context['post'] = self.connection.last_stream['post_ids'][post_id]
        context['comment'] = comment_dict
        comment_html = t.get_html(None, set_dirty=False,
                         file='comment.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
        comment_link_html = t.get_html(None, set_dirty=False,
                         file='comment_link.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
        comment_post_link = t.get_html(None, set_dirty=False,
                         file='comment_post_link.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
#        print comment_html
#        print comment_link_html
#        print comment_post_link
        self.Dsuccess(id, comment_html=comment_html, comment_link_html=comment_link_html,
                          comment_post_link=comment_post_link)

    def do_like(self, post_id, id):
        #regen likes block, regen likes link block, send to callback
        #regen cached post html
        post_id = post_id.encode('utf-8')
        self.connection.addLike(post_id,
                                success=(lambda *a, **k: self.refresh_likes(post_id, id)),
                                error=(lambda *a, **k: self.Dexcept(id, *a, **k))
                                )

    def do_unlike(self, post_id, id):
        post_id = post_id.encode('utf-8')
        self.connection.removeLike(post_id,
                                   success=(lambda *a, **k: self.refresh_likes(post_id, id)),
                                   error=(lambda *a, **k: self.Dexcept(id, *a, **k))
                                   )

    def do_dislike(self, post_id, id):
        comment = DISLIKE.encode('utf-8')
        post_id = post_id.encode('utf-8')
        self.connection.addComment(post_id, comment,
                                   success=(lambda *a, **k:self.dislike_added(post_id, id)),
                                   error=(lambda *a, **k: self.Dexcept(id, *a, **k))
                                   )


    def do_undislike(self, post_id, id):
        try:
            comments = self.connection.last_stream.comments[post_id]
            comments = [c for c in comments if int(c.fromid) == int(self.uid) and c.text == DISLIKE]
            comment_id = comments[0].id
        except Exception:
            return self.Dexcept(id)
        comment_id = comment_id.encode('utf-8')
        self.connection.removeComment(comment_id,
                                      success=(lambda *a, **k: self.dislike_removed(post_id, id)),
                                      error=(lambda *a, **k: self.Dexcept(id, *a, **k))
                                      )

    def dislike_added(self, post_id, id):
        self.refresh_likes(post_id, id, True)
        import hooks
        hooks.notify('digsby.facebook.dislike_added', post_id)

    def dislike_removed(self, post_id, id):
        self.refresh_likes(post_id, id, True)
        import hooks
        hooks.notify('digsby.facebook.dislike_removed', post_id)

    def refresh_likes(self, post_id, id, dis=False):
        #regen likes block, regen likes link block, send to callback
        #regen cached post html
        dis = (dis and 'dis') or ''
        t = FBIB(self)
        context = {}
        context['post'] = self.connection.last_stream['post_ids'][post_id]
        link_html = t.get_html(None, set_dirty=False,
                         file=dis + 'like_link.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
#        print repr(link_html)
        likes_html = t.get_html(None, set_dirty=False,
                         file=dis + 'likes.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
#        print repr(likes_html)
        self.Dsuccess(id, link_html=link_html, likes_html=likes_html)

    def Dsuccess(self, id, **k):
        import wx
        if not wx.IsMainThread(): raise AssertionError('Dsuccess called from a subthread')

        import simplejson
        script = '''Digsby.resultIn(%s);''' % simplejson.dumps({'result':[k], 'error':None, 'id':id})
        self.webview.RunScript(script)

    def Dexcept(self, id, response=None, *a, **k):
        if isinstance(response, fberrors.FacebookError):
            from .facebookprotocol import not_logged_in
            assert not k.pop('msg', False)
            if int(response.tag.error_code) == 200:
                k['grant'] = 'yes'
            elif not_logged_in(response):
                self.do_login() #TODO: short circuit the checks here.
            self.Derror(id, dict(error_code=response.tag.error_code, error_msg=response.tag.error_msg, **k))
        else:
            self.Derror(id, *a, **k)

    def Derror(self, id, error_obj=None, *a, **k):
        import wx
        if not wx.IsMainThread(): raise AssertionError('Derror called from a subthread')

        import simplejson
        if error_obj is None:
            error_obj = "error" #need something, and None/null isn't something.
        script = '''Digsby.resultIn(%s);''' % simplejson.dumps({'result':None, 'error':error_obj, 'id':id})
        self.webview.RunScript(script)

    def remove_comment(self, comment_id, id):
        comment_id = comment_id.encode('utf-8')
        self.connection.removeComment(comment_id,
                                      success=(lambda post_id: self.del_comment(comment_id, id, post_id)),
                                      error=(lambda *a, **k: self.Dexcept(id, *a, **k))
                                      )

    def del_comment(self, comment_id, id, post_id):
        t = FBIB(self)
        context = util.Storage()
        context['post'] = self.connection.last_stream['post_ids'][post_id]
        comment_link_html = t.get_html(None, set_dirty=False,
                         file='comment_link.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
        comment_post_link = t.get_html(None, set_dirty=False,
                         file='comment_post_link.py.xml',
                         dir=t.get_context()['app'].get_res_dir('base'),
                         context=context)
        self.Dsuccess(id, comment_id=comment_id, comment_link_html=comment_link_html,
                      comment_post_link=comment_post_link)

    def grant_url(self, permission):
        url = net.UrlQuery('http://www.facebook.com/connect/prompt_permissions.php',
                           api_key=self.connection.digsby.api_key,
                           skipcookie='',
                           fbconnect='true',
                           v='1.0',
                           display='popup',
                           extern='1',
                           next=DESKTOP_APP_POPUP,
                           ext_perm=permission)

        url = net.UrlQuery('http://www.facebook.com/login.php',
                           next=url,
                           display='popup',
                           skipcookie='')

        return url

    def do_grant(self):
        from .fbconnectlogin import FBLoginWindow
        url = self.grant_url('publish_stream')

        window = FBLoginWindow(self.name, self)
        window.LoadURL(url)

    @actions.action()
    def OpenHome(self):
        self.launchfacebook('')

    @actions.action()
    def OpenProfile(self):
        self.launchfacebook('profile.php')

    @actions.action()
    def OpenFriends(self):
        self.launchfacebook('friends.php')

    @actions.action()
    def OpenPhotos(self):
        self.launchfacebook('photos.php')

    @actions.action()
    def OpenMessages(self):
        self.launchfacebook('inbox/')

    @actions.action(lambda self: (self.state in (self.Statuses.ONLINE, self.Statuses.CHECKING)))
    def edit_status(self):
        if common.pref('social.use_global_status', default = False, type = bool):
            import wx
            wx.GetApp().SetStatusPrompt([self])

    def on_popup_click_post(self, post):
        link = post.get('permalink')

        # posts may not have a permalink. try the first media link
        if not link:
            attachment = post.get('attachment')
            if attachment:
                media = attachment.get('media')
                if media:
                    href = media[0].get('href')
                    if href:
                        link = href

        # as a last try, just link to the person
        if not link:
            actor_id = post.get('actor_id')
            if actor_id:
                profile = self.connection.last_stream['profiles'][int(actor_id)]
                link = profile.url

        launchbrowser(link)

    def on_popup_click_notification(self, notification):
        link = notification.get('href')
        launchbrowser(link)
        self.notifications_markRead([notification['notification_id']])

    @callbacks.callsback
    def SetStatusMessage(self, message, callback = None, **k):
        message = message.encode('utf-8')
        def phase2(permission):
            if permission:
                do_set()
            else:
                import wx
                wx.CallAfter(get_permission)

        def get_permission():
            from .fbconnectlogin import FBLoginWindow
            url = self.grant_url('publish_stream')
            window = FBLoginWindow(self.name, self)
            def on_close(*a, **k):
                do_set()
            window.set_callbacks(close=on_close)
            window.LoadURL(url)

        def do_set():
            def update(_set_response):
                if not message:
                    if _set_response is True:
                        self.connection.last_status = None
                        self.set_dirty()
                        callback.success()
                    else:
                        callback.error()
                else:
                    self.connection.update_status()
                    callback.success()
            self.do_set_status(message, success=update, error=callback.error)

        self.connection.digsby.users.hasAppPermission(ext_perm='publish_stream', success = phase2, error = callback.error)

    @callbacks.callsback
    def do_set_status(self, message, callback=None):
        if message:
            import hooks
            callback.success += lambda *a: hooks.notify('digsby.facebook.status_updated', self, message, *a)
            self.connection.digsby.users.setStatus(status=message, callback=callback,
                                                   status_includes_verb='true')
        else:
            self.connection.digsby.users.setStatus(clear='1', callback=callback)

    def set_dirty(self):
        self._dirty = True
        self.notify('dirty')

    def account_post_triggered(self, protocol=None, name=None):
        self.get_user_info(success=lambda info: self.do_post_account_trigged(info, protocol, name))

    def do_post_account_trigged(self, info, protocol=None, name=None):
        if protocol is None:
            message= (("is using Digsby to manage all %(his)s instant messaging, email, "
                       "and social network accounts from one application!") %
                      {'his':action_links.his_her_their(info['gender'])})
            URL = action_links.MERGED_URL()
            media=[
                   dict(type="image",
                        src=protocolmeta.web_icon_url("merged_%d" % i),
                        href=action_links.clicksrc(URL, 'image%d' % i))
                   for i in range(5)]
        else:
            message = "added %(his)s %(acct_type)s account into Digsby!" % {'his':action_links.his_her_their(info['gender']),
                                                                            'acct_type':action_links.get_acct_name(protocol)}
            URL = action_links.ACCT_BASE(protocol)
            media=[dict(type="image",
                        src=protocolmeta.web_icon_url(protocol),
                        href=action_links.clicksrc(URL, 'image'))]
        self.do_publish_newsfeed(info, message, URL, media)

    def count_triggered(self, type_, number):
        self.get_user_info(success=lambda info: self.do_post_count_triggered(info, type_, number))

    def do_post_count_triggered(self, info, type_, number):
        if type_ not in self.MILESTONE_MESSAGES:
            return

        message  = self.MILESTONE_MESSAGES[type_][0] % {'his':action_links.his_her_their(info['gender']),
                                                        'number':number}
        img_type = self.MILESTONE_MESSAGES[type_][1]

        URL = action_links.COUNT_BASE(type_)
        media=[dict(type="image",
                    src=protocolmeta.web_icon_url(img_type),
                    href=action_links.clicksrc(URL, 'image'))]

        self.do_publish_newsfeed(info, message, URL, media)

    def do_publish_newsfeed(self, info, message, link_base, media):
        if info['num_accts'] < 1:
            return

        post_title = "%(name_str)s using Digsby to stay connected on %(acct_str)s:" % info

        URL = link_base
        self.connection.digsby_ach.stream.publish(
                message=message,
                action_links=[{'text':"Download Digsby", 'href':action_links.clicksrc(URL, 'DL')}],
                attachment=dict(
                                name=post_title,
                                href=action_links.clicksrc(URL, 'HREF'),
                                properties=action_links.get_acct_properties(URL),
                                media=media
                                )
                )

    @callbacks.callsback
    def get_user_info(self, callback=None):
        self.connection.get_user_name_gender(success = lambda *a: self.handle_user_info(*a, callback=callback),
                                             error = callback.error)

    @callbacks.callsback
    def handle_user_info(self, info, callback=None):
        name_ = info.get('first_name')
        if name_:
            name_str = name_ + " is "
        else:
            name_str = "I'm "
        info['name_str'] = name_str
        info['gender'] = info.get('sex')
        from common import profile
        info['num_accts'] = num_accts = len(profile.all_accounts)
        info['acct_str'] = ('%d account' if num_accts == 1 else '%d accounts') % num_accts
        callback.success(info)

    def AchieveAccountAdded(self, protocol=None, name=None, *a, **k):
        super(FacebookAccount, self).AchieveAccountAdded(protocol, name, *a, **k)
        self.doAchieve(lambda: self.account_post_triggered(protocol=protocol, name=name))

    def AchieveAccounts(self, *a, **k):
        super(FacebookAccount, self).AchieveAccounts(*a, **k)
        self.doAchieve(lambda: self.account_post_triggered())

    def AchieveThreshold(self, type=None, threshold_passed=None, current_value=None, *a, **k):
        super(FacebookAccount, self).AchieveThreshold(type, threshold_passed, current_value, *a, **k)
        self.doAchieve(lambda: self.count_triggered(type, threshold_passed))

    @property
    def console(self):
        return self.connection.digsby.console()

    @property
    def stream(self):
        return self.connection.last_stream

class FBIB(gui_providers.InfoboxProviderBase):
    _tmpl = {}
    loaders = {}
    protocols.advise(asAdapterForTypes=[FacebookAccount], instancesProvide=[gui_interfaces.ICacheableInfoboxHTMLProvider])
    def __init__(self, acct, cache=True):
        gui_providers.InfoboxProviderBase.__init__(self)
        self.cache = cache
        self.acct = acct

    def get_html(self, *a, **k):
        if k.pop('set_dirty', True):
            self.acct._dirty = False
        return gui_providers.InfoboxProviderBase.get_html(self, *a, **k)

    @property
    def _dirty(self):
        if self.cache and common.pref('facebook.infobox.cache', True):
            return self.acct._dirty
        else:
            return True

    def get_app_context(self, ctxt_class):
        return ctxt_class(path.path(__file__).parent.parent, self.acct.protocol)

    def get_context(self):
        ctxt = gui_providers.InfoboxProviderBase.get_context(self)
        import wx
        from .content_translation import get_birthdays
        from util.primitives import preserve_newlines
        from gui import skin
        ctxt.update(feed=self.acct.connection.last_stream,
                    posts=[],
                    alerts=self.acct.connection.last_alerts,
                    status=self.acct.connection.last_status,
                    get_birthdays=get_birthdays,
                    skin=skin,
                    linkify=net.linkify,
                    wx=wx,
                    preserve_newlines=preserve_newlines,
                    strip_whitespace=getattr(self.acct, 'strip_whitespace', False))
        return ctxt

    def get_loader(self, dir=None):
        try:
            if self.cache and common.pref('facebook.infobox.cache', True):
                return FBIB.loaders[dir]
        except KeyError:
            pass
        FBIB.loaders[dir] = gui_providers.InfoboxProviderBase.get_loader(self, dir)
        return FBIB.loaders[dir]

def pstr_to_list(s):
    ret = []
    while s:
        try:
            next, s = upstring(s)
        except Exception:
            break
        else:
            ret.append(next)
    return ret

def pstring(s):
#    assert type(s) is bytes
    assert 0 <= len(s) < 1<<8
    return chr(len(s)) + s

def upstring(s):
    l = ord(s[0])
    return s[1:1+l], s[1+l:]

def launchbrowser(url):
    if url:
        import wx
        wx.LaunchDefaultBrowser(url)


UPGRADE_QUESTION = '''
Digsby's Facebook integration just got better.  It now has the complete
newsfeed including the ability to comment/like and publish back to
Facebook.

Would you like to post your achievements within Digsby to your Wall?
(eg: Commented on 100 Facebook Posts)
'''.strip()
