'''
Support for LinkedIn as a digsby social network component.
'''
import os
import traceback
import logging

import path
from social.network import SocialFeed, SocialNetwork
import util
import util.net as net
import util.callbacks as callbacks
import util.cacheable as cacheable

import hooks

import common
import common.oauth_util as oauth_util

import protocols

import common.protocolmeta as protocolmeta

import gui.skin as skin
import gui.infobox.interfaces as gui_interfaces
import gui.infobox.providers as gui_providers
import gui.infobox.infoboxapp as infoboxapp

import rpc.jsonrpc as jsonrpc

import LinkedInObjects as LIO
import branding

log = logging.getLogger("linkedin.account")


UPGRADE_QUESTION = '''
Would you like to post your achievements within Digsby to your Network Activity Stream?
(eg: Posted 100 LinkedIn Status updates)
'''.strip()

class input_callback(object):
    close_button = True
    spellcheck = True

    def __init__(self, cb):
        self.input_cb = cb

    def __eq__(self, other):
        return getattr(other, 'input_cb', object()) == self.input_cb

class LinkedInAccount(SocialNetwork, oauth_util.OAuthAccountBase, jsonrpc.RPCClient):

    _rpc_handlers = {
                     'post_comment' : 'newsfeed_post_comment',
                     'next_item'    : 'newsfeed_next_item',
                     'initialize_feed' : 'newsfeed_initialize_feed',
                     'near_bottom'   : 'newsfeed_more_content',
                     #'load_comments' : 'newsfeed_load_comments',

                     'do_like'       : 'newsfeed_do_like',
                     'do_dislike'    : 'newsfeed_do_dislike',

                     }

    updatefreq = 10 * 60 # ten minutes
    class Statuses(SocialNetwork.Statuses):
        CHECKING = _('Checking now...')

    BORDER = '0'
    service = protocol = 'linkedin'

    AuthClass = oauth_util.InternalBrowserAuthenticator
    #AuthClass = oauth_util.UserBrowserAuthenticator

    webroot = 'https://www.linkedin.com'

    def weblink(self, resource = ''):
        return net.httpjoin(self.webroot, resource)

    @property
    def header_funcs(self):
        return (
                (_('Home'), self.weblink()),
                (_('Inbox'), self.weblink('inBox')),
                (_('Contacts'), self.weblink('connections')),
                (_('Profile'), self.weblink('myprofile')),
                )

    def _get_inbox_count_str(self):
        if self.count:
            return ' (%d)' % self.count
        else:
            return ''

    def __init__(self, **options):
        self.time_offset = None
        options['password'] = None
        oauth_util.OAuthAccountBase.__init__(self, **options)

        self.connection = None
        self._dirty = False

        SocialNetwork.__init__(self, **options)
        self.social_feed = SocialFeed('linkedin_' + self.username,
                                             'linkedin_' + self.username,
                                             self.get_newsfeed_iter,
                                             self.generate_newsfeed_html,
                                             lambda: self.set_infobox_dirty)


    def set_dirty(self):
        log.info("set dirty")
        self._dirty = True

    def _cache_data(self, api_data):
        self.api_data = api_data

    api_data = cacheable.cproperty({}, user = True)

    def get_newsfeed_iter(self):
        return iter(getattr(getattr(self, 'connection', None), 'updates', []))

    def set_infobox_dirty(self):
        self._dirty = True
        self.notify('dirty')

    @property
    def cache_path(self):
        return os.path.join(self.protocol, self.name, 'api-results.dat')

    def get_options(self):
        opts = {'informed_ach': True, 'post_ach_all': False}
        opts.update(SocialNetwork.get_options(self))
        opts.update(oauth_util.OAuthAccountBase.get_options(self))
        return opts

    def Connect(self):
        self.error_txt = None
        log.info('Connect called for %r', self)
        self._update_now()

    def _update_now(self):
        if self.enabled:
            self.update_now()
        else:
            self.set_offline(self.Reasons.NONE)

    def _connect(self):
        self.connection.connect()

    def create_connection(self):
        if self.connection is not None:
            raise Exception('Already have a connection')

        import LinkedInProtocol as LIP
        self.connection = LIP.LinkedInProtocol(self.username, self.oauth_token, self.api_data, self.filters,
                                               time_offset = self.time_offset)

        self.bind_events()

    def connect_failed(self, e):
        self._dirty_error = True
        self.Disconnect(reason = self.Reasons.CONN_FAIL)

    def Disconnect(self, reason = None):
        if reason is None:
            reason = self.Reasons.NONE
        self.unbind_events()
        self.connection = None
        self.set_offline(reason)
        common.UpdateMixin.disconnect(self)

    def handle_rate_limited(self):
        log.info("rate limited!")
        self.error_txt = _("API request limit has been reached.")
        self.handle_update_failed('RATE_LIMIT')

    def handle_update_failed(self, _reason):
        reason = getattr(self.Reasons, _reason, self.Reasons.CONN_FAIL)
        self.Disconnect(reason = reason)

    def update_item_to_notification(self, item):
        import weakref
        import gui.browser.webkit.imageloader as imageloader

        default_icon = skin.get('BuddiesPanel.BuddyIcons.NoIcon', None)

        if hasattr(item, 'content_body'):
            body = item.content_body()
        else:
            html = self.generate_item_html(item)
            body = util.strip_html(html).strip()

        n = util.Storage(acct = weakref.ref(self),
                         icon = imageloader.LazyWebKitImage(item.person.picture_url, default_icon),
                         body = body,
                         title = item.person.name,
                         url = getattr(item, 'url', item.person.profile_url),
                         post_id = item.id)

        return n

    def do_notifications(self, updates):
        if not updates:
            return

        items = []
        for item in updates:
            try:
                items.append(self.update_item_to_notification(item))
            except Exception:
                traceback.print_exc()

        common.fire('linkedin.newsfeed',
                 items=items,
                 popupid='%d.linkedin' % id(self),
                 update='paged',
                 badge=skin.get('serviceicons.linkedin', None),
                 buttons = self.get_popup_buttons,
                 onclick = self.on_popup_click)

    def get_popup_buttons(self, item):
        self._last_popup_item = item
        buttons = []

        my_item = self.connection.get_post_by_id(item.item.post_id)
        if my_item is None:
            return buttons

        def count_str(count):
            return (' (%s)' % count) if count and count != 0 else ''

        if my_item.supports_comments:
            buttons.append((_("Comment") + count_str(len(my_item.get_comments())), input_callback(self.on_popup_comment)))

        return buttons

    def on_popup_comment(self, item, control, text, options):
        post_id = options['item'].post_id
        self._post_comment(post_id, text,
                           success=(lambda *a, **k: (self.set_dirty(), control.update_buttons())))

    on_popup_comment.takes_popup_control = True

    def on_popup_click(self, item):
        import wx
        url = getattr(item, 'url', None)
        if url:
            import wx
            wx.LaunchDefaultBrowser(url)

    def bind_events(self):
        conn = oauth_util.OAuthAccountBase.bind_events(self)
        bind = conn.bind

        bind('on_rate_limit', self.handle_rate_limited)
        bind('update_error', self.handle_update_failed)

        bind('newsfeed_updates', self.do_notifications)

    def unbind_events(self):
        conn = oauth_util.OAuthAccountBase.unbind_events(self)
        if conn is None:
            return

        unbind = conn.unbind

        unbind('on_rate_limit', self.handle_rate_limited)
        unbind('update_error', self.handle_update_failed)

        unbind('newsfeed_updates', self.do_notifications)

    @common.action()
    def SetStatus(self):
        if common.pref('social.use_global_status', default = False, type = bool):
            import wx
            wx.GetApp().SetStatusPrompt([self])
        else:
            log.error("No alternative to global status dialog for new linked in account!")

    DefaultAction = OpenHomeURL = SetStatus

    @callbacks.callsback
    def _set_status(self, new_message, callback = None, **k):
#        callback.success += lambda * a: self.update_now()
        if new_message:
            callback.success += lambda * a: setattr(self.connection.users[self.connection.userid], 'status', new_message)
            callback.success += lambda * a: self.set_dirty()
            callback.success += lambda * a: hooks.notify('digsby.linkedin.status_updated', self, new_message, *a)

        self.connection.set_status(new_message, callback = callback)

    SetStatusMessage = _set_status

    def disconnect(self, *a, **k):
        pass

    def observe_count(self, callback):
        return NotImplemented

    def observe_state(self, callback):
        return NotImplemented

    def unobserve_count(self, callback):
        return NotImplemented

    def unobserve_state(self, callback):
        return NotImplemented

    def OnClickHomeURL(self):
        return self.weblink()

    def launchbrowser(self, what):
        import wx
        wx.LaunchDefaultBrowser(self.weblink(what))

    @common.action()
    def openurl_Home(self):
        self.launchbrowser('')

    @common.action()
    def openurl_Inbox(self):
        self.launchbrowser('inBox')

    @common.action()
    def openurl_Friends(self):
        self.launchbrowser('connections')

    @common.action()
    def openurl_Profile(self):
        self.launchbrowser('myprofile')

    @common.action(lambda self: ((self.state == self.Statuses.ONLINE) and common.pref('can_has_social_update', False)) or None)
    def update_now(self):
        log.info('updating... %r', self)

        self.start_timer()
        log.info("current state: %r", self.state)
        if self.state == self.Statuses.OFFLINE or self.connection is None:
            self.change_state(self.Statuses.CONNECTING)
            try:
                self.create_connection()
                self._connect()
            except Exception:
                traceback.print_exc()
                self.Disconnect(self.Reasons.CONN_FAIL)
                return

        self._update()

    def request_status(self):
        self.set_waiting('status')
        self.connection.request_status()

    def _on_protocol_connect(self):
        log.info("connection ready")

    def handle_connect(self):
        self.change_state(self.Statuses.AUTHENTICATING)

    def handle_status(self, status_info = None):
        log.info('Got status info: %r', status_info)

#    def update_info(self, **info):
#        return SocialNetwork.update_info(self, **info)

    def on_feed_invalidated(self):
        self.social_feed.new_ids([p.id for p in self.connection.updates])

    def _handle_oauth_error(self, details):
        log.error('oauth error occurred: %r', details)
        problem = net.WebFormData.parse(details.get('oauth_problem', ''))

        self.clear_oauth_token()

        if 'timestamp_refused' in problem:
            self.error_txt = _("Please set your computer clock to the correct time / timezone.")
        self.Disconnect(self.Reasons.BAD_PASSWORD)

    def get_authenticator(self, url_generator):
        AuthClass = self._get_auth_class(prefkey = 'linkedin.authenticator')

        return AuthClass(self.username, url_generator,
                         '/linkedin/{username}/oauth'.format(username = self.username),
                         'LinkedIn Login - %s' % self.username,
                         'http://www.digsby.com/myspace',
                         'serviceicons.linkedin')

    def _authenticate_post(self):
        log.info("authenticated successfully!")
        oauth_util.OAuthAccountBase._authenticate_post(self)
        self.update_now()

    @callbacks.callsback
    def newsfeed_post_comment(self, rpc, webview, id, comment, post_id, append = True, callback = None):
        if append:
            callback.success += lambda *a: self.append_comments(webview, id, post_id)
        callback.error += lambda error_obj = None: self.Dexcept(webview, id, error_obj = error_obj)

        self._post_comment(post_id, comment, callback = callback)

    @callbacks.callsback
    def _post_comment(self, post_id, comment, callback = None):
        self.connection.get_post_by_id(post_id).comments.append(LIO.LinkedInComment(sequence_number = -1,
                                                                                    text = comment,
                                                                                    person = self.connection.users[self.connection.userid]))

        self.connection.post_comment(post_id, comment, callback = callback)

    def append_comments(self, webview, id, post_id):
        hooks.notify('digsby.linkedin.comment_added', {})
        t = LinkedInIB(self)
        context = {}
        context['item'] = self.connection.get_post_by_id(post_id)
        comments_html = t.get_html(None, set_dirty = False,
                                  file = 'comments_list.tenjin',
                                  dir = t.get_context()['app'].get_res_dir('base'),
                                  context = context)
        comment_link_html = t.get_html(None, set_dirty = False,
                                       file = 'comment_link.tenjin',
                                       dir = t.get_context()['app'].get_res_dir('base'),
                                       context = context)

        log.debug("comments_html = %r; comment_link_html = %r", comments_html, comment_link_html)

        self.Dsuccess(webview, id, comments_html = comments_html, comment_link_html = comment_link_html)

    def generate_newsfeed_html(self, items, _context_id = None, do_comments = True):
        t = LinkedInIB(self)
        context = {}
        context['items'] = items
        context['conn'] = self.connection
        context['do_comments'] = do_comments

        html = t.get_html(None, set_dirty = False,
                          file = 'items.tenjin',
                          dir = t.get_context()['app'].get_res_dir('base'),
                          context = context)

        return html

    def generate_item_html(self, item):
        t = LinkedInIB(self)
        context = {}
        context['item'] = item
        context['conn'] = self.connection
        context['friend'] = item.person

        html = t.get_html(None, set_dirty = False,
                          file = '%s.tenjin' % item.type,
                          dir = t.get_context()['app'].get_res_dir('base'),
                          context = context)
        return html

    def _update_post(self):
        super(LinkedInAccount, self)._update_post()

    def newsfeed_next_item(self, rpc, webview, id, *extra, **params):
        return self.social_feed.jscall_next_item(webview, id)

    def more_content(self, rpc, webview, id, **params):
        current_posts, _last_post_id = params.get('current_posts', 0), params.get('last_post_id', None)
        t = LinkedInIB(self)
        if current_posts < len(self.connection.updates):

            items = self.connection.updates[current_posts:current_posts + 1]
            items_html = self.generate_newsfeed_html(items)

            self.Dsuccess(webview, id, contents = items_html)
        else:
            self.Derror(webview, id)

    def newsfeed_initialize_feed(self, rpc, webview, id, *extra, **params):
        return self.social_feed.jscall_initialize_feed(webview, id)

    def newsfeed_do_dislike(self, rpc, webview, id, post_id, **kwds):
        log.info("do dislike: kwds = %r", kwds)

        item = self.connection.get_post_by_id(post_id)
        if item is None:
            log.error("%r: no post for post_id %r", self, post_id)
            return

        if item.user_dislikes(self.connection.userid):
            log.info("user already dislikes this post")
            return

        self.newsfeed_post_comment(rpc, webview, id, LIO.LinkedInComment.DISLIKE, post_id, append = False, success = lambda *a, **k: self.dislike_added(webview, id, post_id))

    def dislike_added(self, webview, id, post_id):
        self.refresh_likes(webview, id, post_id, True)
        hooks.notify('digsby.linkedin.dislike_added', post_id)

    def newsfeed_do_like(self, rpc, webview, id, post_id, **kwds):
        log.info("do like: kwds = %r", kwds)

        item = self.connection.get_post_by_id(post_id)
        if item is None:
            log.error("%r: no post for post_id %r", self, post_id)
            return
        if item.user_likes(self.connection.userid):
            log.info("user already likes this post")
            return

        self.newsfeed_post_comment(rpc, webview, id, LIO.LinkedInComment.LIKE, post_id, append = False, success = lambda *a, **k: self.like_added(webview, id, post_id))

    def like_added(self, webview, id, post_id):
        self.refresh_likes(webview, id, post_id, True)
        hooks.notify('digsby.linkedin.like_added', post_id)

    def refresh_likes(self, webview, id, post_id, dis = False):\

        log.info("refreshing item: %r", post_id)
        #regen likes block, regen likes link block, send to callback
        #regen cached post html

        item_html = self.generate_newsfeed_html([self.connection.get_post_by_id(post_id)], None)

        self.Dsuccess(webview, id, item_html = item_html)

    def _create_activity(self, body):
        self.connection.create_activity(body = body)

class LinkedInIB(gui_providers.InfoboxProviderBase):
    protocols.advise(asAdapterForTypes = [LinkedInAccount], instancesProvide = [gui_interfaces.ICacheableInfoboxHTMLProvider])
    def __init__(self, acct):
        gui_providers.InfoboxProviderBase.__init__(self)
        self.acct = acct

    def get_html(self, htmlfonts = None, **opts):
        self.acct._dirty = False
        return gui_providers.InfoboxProviderBase.get_html(self, **opts)

    def get_app_context(self, ctxt_class):
        return ctxt_class(path.path(__file__).parent.parent, self.acct.protocol)

    def get_context(self):
        ctxt = gui_providers.InfoboxProviderBase.get_context(self)

        conn = self.acct.connection
        ctxt.update(
          conn = conn,
          items = [],
          alerts = [],
          skin = skin
        )

        return ctxt

    @property
    def _dirty(self):
        return self.acct._dirty

