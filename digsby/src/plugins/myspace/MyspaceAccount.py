import path
import logging
import os.path
import time
import random

import protocols
import gui.infobox.providers as gui_providers
import gui.infobox.interfaces as gui_interfaces

import hooks
import social
import netextensions
import common
import common.protocolmeta as protocolmeta
import common.oauth_util as oauth_util

import rpc.jsonrpc as jsonrpc

import oauth.oauth as oauth

import util
import util.net as net
import util.cacheable as cacheable
import util.callbacks as callbacks
import util.Events as events

MAX_MYSPACE_STORIES = 50

DIGSBY_UTM_ARGS = dict(utm_source   = "Digsby",
                       utm_medium   = "MID",
                       utm_campaign = "Digsby_v1")

DIGSBY_UTM = "utm_source=Digsby&utm_medium=MID&utm_campaign=Digsby_v1"
log = logging.getLogger('myspace.new.account')

def digsby_link_for_activity(proto = 'merge'):
    import branding
    campaign = branding.get('digsby.myspace.newsfeed.campaign', 'digsby_myspace', 'myspacenewsfeed')

    return str(net.UrlQuery("http://www.digsby.com/",
                            utm_campaign = campaign,
                            utm_medium = 'msp',
                            utm_source = proto))

class MyspaceAccount(social.network, oauth_util.OAuthAccountBase,
                     jsonrpc.RPCClient):

    url_base = 'http://www.myspace.com/index.cfm'

    AuthClass = oauth_util.InternalBrowserAuthenticator # UserBrowserAuthenticator
    #AuthClass = oauth_util.InternalBrowserAuthenticatorOpenID

    events = events.EventMixin.events | set((
        # stuff
    ))

    service = protocol = 'myspace'

    indicators_keys = ['blogcommenturl', 'blogsubscriptionposturl',
                       'picturecommenturl', 'eventinvitationurl',
                       'commenturl', 'phototagapprovalurl',
                       'friendsrequesturl', 'videocommenturl',
                       'groupnotificationurl', 'recentlyaddedfriendurl',
                       'birthdayurl',
                       #'countpendingim',
                       ]

    feed_keys = [
                 'statuses',
                 'friends',
                 'posts',
                 'groups',
                 'photos',
                 'music',
                 'videos',
                 'events',
                 'applications',
                 ]

    header_fuseactions = dict((
                ('Home',          'user'),
                #('Profile',       'user.viewprofile'), # supposed to take you to myspace.com/yourname but instead just goes to myspace.com (??)
                ('Inbox',         'mail.inboxV2'),
                ('Friends',       'user.viewfriends'),
                ('Blog',          'blog.ListAll'),
                ('Post Bulletin', 'bulletin'),
            ))

    def url_destination(name):
        def get_url(self):
            kwargs = DIGSBY_UTM_ARGS.copy()

            self_userid = getattr(self.connection, 'userid', None)
            if self_userid is not None:
                kwargs.update(friendId = self_userid)

            kwargs.update(fuseaction = self.header_fuseactions[name])

            return self.openurl(net.UrlQuery(self.url_base, **kwargs))
        return get_url

    openurl_Home = url_destination("Home")
    openurl_Profile = url_destination("Profile")
    openurl_Inbox = url_destination("Inbox")
    openurl_Friends = url_destination("Friends")
    openurl_Blog = url_destination("Blog")
    openurl_Post = url_destination("Post Bulletin")

    del url_destination

    def __init__(self, *a, **k):
        common.Protocol.StateMixin.__init__(self)
        oauth_util.OAuthAccountBase.__init__(self, **k)

        self.count = 0
        self.connection = None
        self._dirty = False

        filters = k.pop('filters', {})
        self.filters = dict(indicators=dict(zip(self.indicators_keys, filters.get('indicators', [True]*len(self.indicators_keys)))),
                            feed = dict(zip(self.feed_keys,   filters.get('feed',   [True]*len(self.feed_keys)))),
                            )

        self.header_funcs = (
            ('Home',            self.openurl_Home),
#            ('Profile',         self.openurl_Profile),
            ('Inbox',           self.openurl_Inbox),
            ('Friends',         self.openurl_Friends),
            ('Blog',            self.openurl_Blog),
            ('Post Bulletin',   self.openurl_Post),
        )

        if 'password' not in k:
            k['password'] = None

        social.network.__init__(self, *a, **k)
        self._remove_password = not self.protocol_info()['needs_password']
        if self._remove_password:
            self.password = None

        from social.network import SocialFeed
        self.social_feed = SocialFeed('myspace_' + self.username,
                                      'activities',
                                      lambda: iter(self.connection.combined_feed()),
                                      self.htmlize_activities,
                                      self._set_dirty)

    def htmlize_activities(self, activities, context):
        t = MyspaceIB(self)
        return t.get_html(None, set_dirty=False,
                          file='activities.tenjin',
                          dir=t.get_context()['app'].get_res_dir('base'),
                          context=dict(activities = activities))

    def Connect(self):
        log.info('Connect called for %r', self)
        self._update_now()

    def create_connection(self):
        if self.connection is not None:
            raise Exception('Already have a connection')

        import MyspaceProtocol as MSP
        self.connection = MSP.MyspaceProtocol(self.username, self.oauth_token, self._decryptedpw, self.api_data, self.filters)

        self.bind_events()

    @property
    def cache_path(self):
        return os.path.join('myspace-social3', self.username, 'api-results.dat')

    def _cache_data(self, api_data):
        self.api_data = api_data

    api_data = cacheable.cproperty({}, user = True)

    def on_feed_invalidated(self):
        ids = [p.id for p in self.connection.combined_feed()]
        self.social_feed.new_ids(ids)

    def observe_count(self,callback):
        self.add_gui_observer(callback, 'count')
    def unobserve_count(self,callback):
        self.remove_gui_observer(callback, 'count')

    def _got_indicators(self, inds):
        log.info('got indicators: %r', inds)
        indicators = {}
        for k in self.indicators_keys:
            if k in inds and self.filters['indicators'].get(k, False):
                indicators[k] = inds[k]

        num_inds = len(indicators)

        if inds.get('mailurl', None) is not None:
            num_inds += 1

        if getattr(self, '_num_inds', -1) != num_inds:
            self._num_inds = num_inds
            self.setnotify('count', num_inds)

    def get_authenticator(self, url_generator):
        AuthClass = self._get_auth_class(prefkey = 'myspace.authenticator')

        return AuthClass(self.username, url_generator,
                         '/myspace/{username}/oauth'.format(username = self.username),
                         'MySpace Login - %s' % self.username,
                         "http://www.digsby.com/myspace/",
                         'serviceicons.myspace')

    def bind_events(self):
        oauth_util.OAuthAccountBase.bind_events(self)
        self.connection.bind('on_indicators', self._got_indicators)

    def unbind_events(self):
        conn = oauth_util.OAuthAccountBase.unbind_events(self)
        if conn is None:
            return

        conn.unbind('on_indicators', self._got_indicators)

    def _on_protocol_connect(self):
        pass

    def _connect(self):
        #assert self.connection is not None
        self.connection.connect()
        log.info('Calling connect for connection')

    def _update_now(self):
        if self.enabled:
            self.update_now()
        else:
            self.set_offline(self.Reasons.NONE)

    @common.action(lambda self: common.pref('can_has_social_update', None) or None)
    def update_now(self):
        log.info('updating... %r', self)

        self.start_timer()
        if self.state == self.Statuses.OFFLINE:
            self.change_state(self.Statuses.CONNECTING)
            try:
                self.create_connection()
                self._connect()
            except Exception:
                import traceback; traceback.print_exc()
                self.Disconnect(self.Reasons.CONN_FAIL)
                return

        self._update()

    def _update_pre(self):
        if self._has_updated or self._forcing_login:
            st = self.Statuses.CHECKING
        else:
            st = self.Statuses.CONNECTING

        self.change_state(st)

    def _reset_connection(self):
        self._has_updated = False
        self._on_auth_done()
        #self.connection.disconnect()

    def Disconnect(self, reason = None):
        log.info('Disconnect called')
        self.pause_timer()
        self._reset_connection()
        self.unbind_events()
        self.connection = None
        reason = reason or self.Reasons.NONE

        if self.state != self.Statuses.OFFLINE:
            self.set_offline(reason)

        common.UpdateMixin.disconnect(self)

    disconnect = Disconnect

    def _update_error(self, e):
        log.debug("%r got update error: %r", self, e)
        if hasattr(e, 'read'):
            log.debug_s('\tbody: %r', e.read())

        if isinstance(e, oauth.OAuthError):
            return self._handle_oauth_error(getattr(e, 'oauth_data', None))

        if self.state == self.Statuses.OFFLINE:
            return

        if self._has_updated:
            rsn = self.Reasons.CONN_LOST
        else:
            rsn = self.Reasons.CONN_FAIL

        self.Disconnect(rsn)

    def _handle_oauth_error(self, details):
        log.error('oauth error occurred: %r', details)
        problem = details.get('oauth_problem', None)

        self.clear_oauth_token()

        if problem == 'timestamp_refused':
            self.error_txt = _("Please set your computer clock to the correct time / timezone.")
        self.Disconnect(self.Reasons.BAD_PASSWORD)

    def update_info(self, **info):

        filters = info.pop('filters', None)

        if filters is not None:
            self.filters.update(
                    dict(indicators=dict(zip(self.indicators_keys, filters.get('indicators', [True]*len(self.indicators_keys)))),
                         feed = dict(zip(self.feed_keys,   filters.get('feed',   [True]*len(self.feed_keys)))),
                    ))

            self._set_dirty()

        if info.get('password') is not None and self._remove_password:
            info['password'] = None

        return social.network.update_info(self, **info)

    def get_options(self):
        opts = super(MyspaceAccount, self).get_options()
        opts.update({'informed_ach': True, 'post_ach_all': False})
        opts.update(filters = dict(feed =   [bool(self.filters['feed'].get(x, True))   for x in self.feed_keys],
                                   indicators = [bool(self.filters['indicators'].get(x, True)) for x in self.indicators_keys]))

        if opts.get('password') is not None and self._remove_password:
            opts['password'] = None

        if 'oauth_token' not in opts:
            opts['oauth_token'] = self.oauth_token

        return opts

    @common.action()
    def edit_status(self):
        if common.pref('social.use_global_status', default = False, type = bool):
            import wx
            wx.GetApp().SetStatusPrompt([self])
        else:
            from myspacegui.editstatus import get_new_status
            get_new_status(success = self.set_web_status)

    DefaultAction = OpenHomeURL = edit_status

    @callbacks.callsback
    def SetStatusMessage(self, message, callback = None, **opts):
        if len(message) == 0:
            return callback.success()

        self.connection.set_status_message(message, callback = callback)

    def _dirty_get(self):
        return getattr(getattr(self, 'connection', None), '_dirty', True)

    def _dirty_set(self, val):
        if self.connection is not None:
            self.connection._dirty = val

    _dirty = property(_dirty_get, _dirty_set)

    @common.action(lambda self: common.pref('can_has_social_update', None) or None)
    def _set_dirty(self):
        self._dirty = True

    ## TODO: Move all this rpc nonsense to a superclass, with bind/unbind/callbacks and some sweet-ass decorator magic.
    _rpc_handlers = {
                     'near_bottom'   : 'more_content',
                     'post_comment'  : 'post_comment',
                     'hook'          : 'rpc_hook',
                     'load_comments' : 'load_comments',
                     'initialize_feed' : 'initialize_feed',
                     'next_item'     : 'next_item',
                     'do_permissions': 'initiate_login',
                     'do_like'       : 'newsfeed_do_like',
                     'do_dislike'    : 'newsfeed_do_dislike',
                     }

    def initiate_login(self, *a, **k):
        self.connection.userinfo = None
        oauth_util.OAuthAccountBase.initiate_login(self, *a, **k)

    def user_dislikes(self, userid, item):
        return item.user_dislikes(userid)

    def user_likes(self, userid, item):
        return item.user_likes(userid)

    def newsfeed_do_dislike(self, rpc, webview, id, post_id):
        item = self.connection.get_post_by_id(post_id)
        if item is None:
            log.error("%r: no post for post_id %r", self, post_id)
            return

        if self.user_dislikes(self.connection.userid, item):
            log.info("user already dislikes this post")
            return

        import myspace.objects as MSO
        self.post_comment(rpc, webview, id, MSO.MyspaceComment.DISLIKE, post_id, append = False, success = lambda *a, **k: self.dislike_added(webview, id, post_id))

    def newsfeed_do_like(self, rpc, webview, id, post_id):
        item = self.connection.get_post_by_id(post_id)
        if item is None:
            log.error("%r: no post for post_id %r", self, post_id)
            return

        if self.user_likes(self.connection.userid, item):
            log.info("user already likes this post")
            return

        import myspace.objects as MSO
        self.post_comment(rpc, webview, id, MSO.MyspaceComment.LIKE, post_id, append = False, success = lambda *a, **k: self.like_added(webview, id, post_id))

    def dislike_added(self, webview, id, post_id):
        self.refresh_likes(webview, id, post_id, True)
        hooks.notify('digsby.myspace.dislike_added', post_id)

    def like_added(self, webview, id, post_id):
        self.refresh_likes(webview, id, post_id, False)
        hooks.notify('digsby.myspace.like_added', post_id)

    def refresh_likes(self, webview, id, post_id, dis = False):\

        log.info("refreshing item: %r", post_id)
        #regen likes block, regen likes link block, send to callback
        #regen cached post html

        item = self.connection.get_post_by_id(post_id)
        item_html = self.generate_newsfeed_html([item])

        self.Dsuccess(webview, id, item_html = item_html)

    @callbacks.callsback
    def post_comment(self, rpc, webview, id, comment, post_id, append = True, callback = None):
        post = self.connection.get_post_by_id(post_id)
        if append:
            post._numComments += 1
            callback.success += lambda *a: self.append_comments(webview, id, post_id)
        else:
            import myspace.objects as MSO
            post.comments.append(MSO.MyspaceComment.from_json(
                dict(
                     userid = 'myspace.com.person.%s' % self.connection.userid,
                     text = comment,
                     commentId = str(random.randint(0, 0x7fffffff)),
                     postedDate_parsed = time.time(),
                     )))

        callback.error += lambda *a: self.Dexcept(webview, id, *a)

        self._post_comment(comment, post_id, callback = callback)

    @callbacks.callsback
    def _post_comment(self, comment, post_id, callback = None):
        self.connection.post_comment(post_id, comment,
                                     callback = callback)

    def generate_newsfeed_html(self, activities, _context_id = None, do_comments = True):
        t = MyspaceIB(self)
        activities_html = t.get_html(None, set_dirty=False,
                                     file='activities.tenjin',
                                     dir=t.get_context()['app'].get_res_dir('base'),
                                     context=dict(activities = activities))

        return activities_html

    def append_comments(self, webview, id, post_id):
        t = MyspaceIB(self)
        context = {}
        context['item'] = self.connection.get_post_by_id(post_id)
        comments_html = t.get_html(None, set_dirty=False,
                                  file='comment_section.tenjin',
                                  dir=t.get_context()['app'].get_res_dir('base'),
                                  context=context)
        bottom_row_html = t.get_html(None, set_dirty=False,
                                     file='bottom_row.tenjin',
                                     dir=t.get_context()['app'].get_res_dir('base'),
                                     context=context)

        self.Dsuccess(webview, id, comments_html = comments_html, bottom_row_html = bottom_row_html)

        self.api_data['friend_status'] = self.connection.friend_status
        self._cache_data(self.api_data)

    def more_content(self, rpc, webview, id, **params):
        current_posts, _last_post_id = params.get('current_posts', 0), params.get('last_post_id', None)
        if current_posts < len(self.connection.combined_feed()):
            activities = self.connection.combined_feed()[current_posts:current_posts+1]
            activities_html = self.generate_newsfeed_html(activities)
            self.Dsuccess(webview, id, contents = activities_html)
        else:
            self.Derror(webview, id)

    def initialize_feed(self, rpc, webview, id, *extra, **params):
        self.social_feed.jscall_initialize_feed(webview, id)

    def next_item(self, rpc, webview, id, *extra, **params):
        self.social_feed.jscall_next_item(webview, id)

    def load_comments(self, rpc, webview, id, post_id):
        self.connection.get_comments_for(post_id,
                                         #success = lambda: self.refresh_likes(webview, id, post_id),
                                         success = lambda: self.append_comments(webview, id, post_id),
                                         error   = lambda error_obj = None, **k:  self.Dexcept(webview, id, error_obj = error_obj, **k))

    #self.more_content(args['current_posts'], args.pop('last_post_id', None), rpc.pop('id'))

    def user_from_activity(self, act):
        return self.connection.user_from_activity(act)

    def get_imageurl_for_user(self, user):
        if user is None:
            return None
        else:
            return user.get('image', user.get('thumbnailUrl', None))

    def user_from_id(self, id):
        return self.connection.user_from_id(id)

    def _name_for_user(self, user):
        name = getattr(user, 'name', None)
        if name is None:
            return getattr(user, 'displayName', 'Private User')

        firstname, lastname = name.get('givenName', None), name.get('familyName', None)

        if (firstname, lastname) == (None, None):
            return name

        if firstname and lastname:
            return u"%s %s" % (firstname, lastname)

        return firstname or lastname

class MyspaceIB(gui_providers.InfoboxProviderBase):
    protocols.advise(asAdapterForTypes=[MyspaceAccount], instancesProvide=[gui_interfaces.ICacheableInfoboxHTMLProvider])
    def __init__(self, acct):
        gui_providers.InfoboxProviderBase.__init__(self)
        self.acct = acct

    def get_html(self, htmlfonts = None, **opts):
        if opts.pop('set_dirty', True):
            self.acct._dirty = False
        return gui_providers.InfoboxProviderBase.get_html(self, **opts)

    def get_app_context(self, ctxt_class):
        return ctxt_class(path.path(__file__).parent.parent, self.acct.protocol)

    def get_context(self):
        import wx, gui.skin as skin
        ctxt = gui_providers.InfoboxProviderBase.get_context(self)

        conn = self.acct.connection
        ctxt.update(
          wx = wx,
          acct = self.acct,
          conn = conn,
          users = conn.users,
          self_status = conn.status,
          indicators = conn.filtered_indicators(),
          activities = [],#conn.combined_feed()[:MAX_MYSPACE_STORIES],
          skin = skin,
        )

        return ctxt

    @property
    def _dirty(self):
        return self.acct._dirty

def explode_msParameters(d):
    return [dict(key = k, value = v) for k,v in d.items()]

def ms_analytics_url(source, term):
    return net.UrlQuery('http://www.digsby.com/', utm_campaign = 'msnewsfeed', utm_medium='msp', utm_source = source, utm_term = term)

def media_item_for_proto(proto):
    return {#'mimeType' : 'image',
            'msMediaItemUri' : myspace_icon_url(proto)}

_icon_owner_id = 90302818
_icon_album_id = 3107399
_icon_id_digsby = 53761354
_icon_id_by_name = {
                    'aim'      :  53761351,
                    'aolmail'  :  53761352,
                    'digsby'   :  _icon_id_digsby,
                    'email'    :  53761355,
                    'facebook' :  53761356,
                    'fbchat'   :  53761357,
                    'gmail'    :  53761359,
                    'gtalk'    :  53761360,
                    'hotmail'  :  53761361,
                    'icq'      :  53761362,
                    'jabber'   :  53761363,
                    'linkedin' :  53761364,
                    'merged'   :  53761365,
                    'msn'      :  53761366,
                    'myspace'  :  53761367,
                    'twitter'  :  53761369,
                    'yahoo'    :  53761370,
                    'ymail'    :  53761371,
                    }

def myspace_icon_url(proto):
    return ("http://api.myspace.com/v1/users/%s/albums/%s/photos/%s" %
            (_icon_owner_id, _icon_album_id,
             _icon_id_by_name.get(protocolmeta._icon_exceptions.get(proto, proto), _icon_id_digsby)))

