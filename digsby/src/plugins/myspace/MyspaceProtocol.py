import time, calendar, feedparser
import weakref
import operator
import logging
import MyspaceAPI
import objects
import common
import common.oauth_util as oauth_util
import hooks
import lxml.etree as etree
import lxml.html as html
import ClientForm
import simplejson as json
import util
import util.primitives.funcs as funcs
import util.httptools as httptools
import util.callbacks as callbacks
import util.net as net
import util.Events as Events

import gui
import gui.browser.webkit.imageloader as imageloader

COMMENTS_TTL = 300

log = logging.getLogger('myspace.new.protocol')

_alert_texts = {
    "birthdayurl" : _("Birthdays"),
    "blogcommenturl" : _("Blog Comments"),
    "blogsubscriptionposturl" : _("Blog Subscriptions"),
    "commenturl" : _("Comments"),
    "eventinvitationurl" : _("Event Invitations"),
    "friendsrequesturl" : _("Friend Requests"),
    "groupnotificationurl" : _("Group Notifications"),
    "phototagapprovalurl" : _("Photo Tag Approvals"),
    "picturecommenturl" : _("Picture Comments"),
    "recentlyaddedfriendurl" : _("Recently Added Friends"),
    "videocommenturl" : _("Video Comments"),
    "mailurl" : _("Mail"),
    }

_activity_types = ['PhotoTagged', 'PhotoAdd',
                   'SongUpload', 'ProfileSongAdd',
                   'BlogAdd', 'ForumPosted',
                   'ForumTopicReply', 'VideoAdd',
                   'ProfileVideoUpdate', 'FriendAdd',
                   'FavoriteVideoAdd','JoinedGroup',
                   'FriendCategoryAdd', 'BandShowAdded',
                   'EventPosting', 'EventAttending',
                   'ApplicationAdd', #'StatusMoodUpdate',
                   'ApplicationInnerActivity']


class input_callback(object):
    close_button = True
    spellcheck = True

    def __init__(self, cb):
        self.input_cb = cb

    def __eq__(self, other):
        return getattr(other, 'input_cb', object()) == self.input_cb

def text_for_alert(alert, alerts):
    text = _alert_texts.get(alert, None)
    if text is not None:
        return text

    else:
        if alert == 'mailurl':
            mailcount = alerts.get('countnewmail', None)
            if mailcount is not None:
                return _("Mail ({mailcount})").format(mailcount = mailcount)

    return None

class MyspaceWeb(httptools.WebScraper, Events.EventMixin):
    _bday_test = False

    domain = 'myspace.com'
    events = Events.EventMixin.events | set((
    ))

    def transform_json_varname(self, name):
        return dict(
                    moodPictureURL = 'moodurl',
                    moodName       = 'mood',
                    #timestamp      = 'time',
                    ).get(name, name)

    def __init__(self, username, pw_provider):
        httptools.WebScraper.__init__(self)
        Events.EventMixin.__init__(self)
        self.username = username
        self.pw_provider = pw_provider

        self._status_info = {}

        self.urls = {
                     'loginform' : 'http://m.myspace.com/login.wap?isredirected=true',
                     'statusform': 'http://m.myspace.com/mood.wap',
                     }

    def is_logged_in(self):
        return bool(self.get_cookie('uwtbr', domain='m.myspace.com', default = False))

    def login(self):
        if self.is_logged_in():
            return

        self.request('loginform', success = self._submit_login_form)

    def _submit_login_form(self, resp):
        resp.seek(0)
        self._login_resp = resp
        forms = ClientForm.ParseResponse(resp)
        form = None
        for form in forms:
            if form.name == 'aspnetForm':
                break

        if form is None:
            return

        form.set_value(self.username, 'emailTextBox')
        form.set_value(self.pw_provider(), 'passwordTextBox')

        self.request('login', request = form.click())

    def build_request_login(self, name, request = None):
        assert request is not None
        return request

    def done_waiting(self):
        pass

    def build_request_default(self, name):
        req = httptools.WebScraper.build_request_default(self, name)
        return req

    def handle_success_default(self, name, resp, **req_options):
        log.info('Got response for %r: %r / %r', name, resp, resp.read())
        httptools.WebScraper.handle_success_default(self, name, resp, **req_options)

    @callbacks.callsback
    def set_status(self, status, mood = '', callback = None):
        def _do_set(resp):
            if not self.is_logged_in():
                callback.error(Exception("not logged in"))

            resp.seek(0)
            form = ClientForm.ParseResponse(resp)[0]
            form.set_value(status, 'us')
            form.set_value(mood, 'mn')

            p = net.UrlQuery.parse(form.action)
            p['query'].pop('bfd', None)
            form.action = net.UrlQuery.unparse(**p)

            self.request('set_status', request = form.click(), callback = callback)

        self.request('statusform', success = _do_set, error = callback.error)

    def build_request_set_status(self, name, request):
        return request

class MyspaceProtocol(oauth_util.OAuthProtocolBase):
    events = oauth_util.OAuthProtocolBase.events | set((
        'on_indicators',
    ))

    def __init__(self, username, token, pw_provider, cache_data = None, filters = None):
        oauth_util.OAuthProtocolBase.__init__(self, username, token)
        self.userid = None
        self.userinfo = None
        self.pending = {}
        self.web = None
        self.status = {}
        self._recvd_userinfo = False
        self.pw_provider = pw_provider

        self.api_data = cache_data or {}

        self.activities = []
        self.users = {}
        self.friend_status = []
        self.indicators = {}
        self.filters = filters or dict(feed={}, alerts={})
        self._load_cache()

    def _cache(self, name, data):
        self.api_data[name] = data
        self.event("need_cache", self.api_data)

    def _load_cache(self):

        for name in ('userinfo', 'status', 'friend_info', 'friend_status', 'friend_activities'):
            try:
                getattr(self, '_got_%s' % name)(self.api_data.get(name, None), from_cache = True)
            except Exception:
                import traceback; traceback.print_exc()

    def user_from_id(self, id):
        if msid_eq(id, self.userid):
            return self.userinfo

        if not self.users:
            return None

        user = self.users.get(id, self.users.get('myspace.com.person.%s' % id, None))

        if user is not None:
            return user

        for friend in self.users.values():
            if msid_eq(getattr(friend, 'userId', getattr(friend, 'id', None)), id):
                return friend
            elif getattr(friend, 'webUri', getattr(friend, 'profileUrl', None)) == id:
                return friend

        return None

    def user_from_activity(self, act):
        user_id = act.author_id

        if msid_eq(user_id, self.userid):
            return self.userinfo

        user_url = getattr(act, 'author_url', None)

        user = self.users.get(user_id, None)
        if user is not None:
            return user

        for friend in self.users.values():
            if friend.profileUrl == user_url:
                return friend

        return None

    def _create_api(self):
        cls = MyspaceAPI.MyspaceOAuthClient
        #cls = MyspaceAPI.MyspaceOpenSocialClient
        self.api = cls(self.username, self.token, default_params = dict(dateFormat='utc'))

    @callbacks.callsback
    def set_status_message(self, message, callback = None):

        def on_error(e):
            e_msg = getattr(e, "headers", {}).get("x-opensocial-error", e)
            callback.error(e_msg)
            self.update()

        callback.success += lambda *a: util.Timer(2, self.update).start()
        import hooks
        callback.success += lambda *a: hooks.notify('digsby.myspace.status_updated', *a)
        self.api.call('statusmood/@me/@self',
                      OpenSocial = True).PUT(data = json.dumps(dict(status=message.encode('utf8'), moodName = None)),
                                             retries = 1,
                                             success = callback.success,
                                             error = on_error)

    def update(self):
        self.event('update_pre')

        if self.userinfo is None:
            self._recvd_userinfo = False
#            self.api.call('user').GET(success = self.process_userinfo_and_update,
#                                      error = self.update_error)
            self.api.call('people/@me/@self', OpenSocial = True).GET(success = self.process_userinfo_and_update,
                                                                     error = self.update_error)
        else:
            with self.api.batch() as api:
                base = 'users/{userid}/%s.json'
                for resource in ('indicators',):
                    api.call(base % resource,
                             userid = self.userid).GET(success = lambda val, res = resource: self.set_pending(res, val),
                                                       error = self.update_error)

                act_args = {'composite' : 'true',
                            'activityTypes' : '|'.join(_activity_types)}
#                if self.activities:
#                    act_args.update(datetime = time.strftime('%d/%m/%Y', time.gmtime(self.activities[0].updated_parsed)))

                api.call('users/{userid}/friends/activities.atom',
                         userid = self.userid).GET(parameters = act_args,
                                                   success = lambda val, res = 'friends/activities.atom': self.set_pending(res, val),
                                                   error = self.update_error)

                self._friend_requester = OpenSocialPageRequester(self, 'people/@me/@friends',
                                                                 success = lambda val, res = 'friends': (setattr(self, '_friend_requester', None), self.set_pending(res, val)),
                                                                 error = self.update_error)
                self._friend_requester.get_all()

                api.call('statusmood/@me/@self',
                         OpenSocial = True).GET(success = lambda val, res = 'status': self.set_pending(res, val),
                                                error = self.update_error)

                self._status_requester = OpenSocialPageRequester(self, 'statusmood/@me/@friends/history',
                                                                 parameters = {"includeself":"true"},
                                                                 max = 50,
                                                                 success = lambda val, res = 'friends/status': (setattr(self, '_status_requester', None), self.set_pending(res, val)),
                                                                 error = self.update_error)
                self._status_requester.get_all()

    def process_userinfo_and_update(self, userinfo):
        log.info("got userinfo: %r", userinfo)
        self.userinfo = userinfo.person
        self.userid = self.userinfo.id
        if self.userid.startswith('myspace.com.person.'):
            log.debug("removing specifier from userid: %r", self.userid)
            self.userid = self.userid.split('.')[-1]
        self._recvd_userinfo = True
        self.update()

    def set_pending(self, key, val):
        self.pending[key] = val

    def check_update_complete(self):
        # this event ("requests_complete") happens when the auth process is happening also,
        # so check if we're in the middle of authenticating before confirming update is complete.
        # we also need to have some pending data.
        update_complete = (not self._authenticating) and self._recvd_userinfo and ((self._friend_requester, self._status_requester) == (None, None))

        log.info('update complete? : %s', update_complete)
        if update_complete:
            return self.update_post()

    def check_os_update_complete(self):
        pass

    def apply_pending(self):
        status = self.pending.get('status', None)
        if self.activities:
            most_recent_activity_time = max(map(operator.attrgetter('updated_parsed'), self.activities))
        else:
            most_recent_activity_time = 0

        if self.friend_status:
            most_recent_status_time = max(map(operator.attrgetter('updated_parsed'), self.friend_status))
        else:
            most_recent_status_time = 0

        if self.status:
            my_status_time = self.status.updated_parsed
        else:
            my_status_time = 0

        most_recent_time = max(most_recent_status_time, most_recent_activity_time, my_status_time)

        if status is not None:
            with util.traceguard():
                self._got_status(status)

        friend_info = self.pending.get('friends', None)
        if friend_info is not None:
            self._got_friend_info(friend_info)

        friend_status = self.pending.get('friends/status', None)
        if friend_status is not None:
            self._got_friend_status(friend_status)

        indicators = self.pending.get('indicators', None)
        if indicators is not None:
            self._got_indicators(indicators)

        friend_activities = self.pending.get('friends/activities.atom', None)
        if friend_activities is not None:
            self._got_friend_activities(friend_activities)

        self._notify_since(most_recent_time)

    def _notify_since(self, when):
        to_notify = filter(lambda x: x.updated_parsed > when, reversed(self.combined_feed()))
        self_user = self.user_from_id(self.userid)
        to_notify = filter(lambda x: self.user_from_id(x.author_id) is not self_user, to_notify)

        default_icon = gui.skin.get('BuddiesPanel.BuddyIcons.NoIcon', None)


        for thing in to_notify:
            if getattr(thing, 'acct', None) is None:
                thing.acct = weakref.ref(self)
            if getattr(thing, 'icon', None) is not None:
                continue

            user = self.user_from_id(thing.author_id)
            url = getattr(user, 'thumbnailUrl', None)
            thing.icon = imageloader.LazyWebKitImage(url, default_icon)

        log.info_s("myspace notifying: %r", to_notify)
        if to_notify:
            common.fire('myspace.newsfeed',
                        title = _("MySpace Newsfeed"),
                        items = to_notify,
                        conn = self,
                        onclick = lambda item: getattr(item, 'url',
                                                       util.try_this(lambda:getattr(self.user_from_activity(item), 'webUri', None) or
                                                                            getattr(self.user_from_activity(item), 'profileUrl', None),
                                                                     None)),
                        popupid = '%r.myspace' % self,
                        update = 'paged',
                        util = util,
                        badge = gui.skin.get('serviceicons.myspace', None),
                        buttons = self.get_popup_buttons)

    def get_popup_buttons(self, item):
        self._last_popup_item = item
        buttons = []

        item = item.item
        def count_str(count):
            return (' (%s)' % count) if count and count != 0 else ''

        if item.supports_comments:
            buttons.append((_("Comment") + count_str(len(item.get_comments())), input_callback(self.on_popup_comment)))

        return buttons

    def on_popup_comment(self, item, control, text, options):
        post_id = options['item'].id
        self.post_comment(post_id, text.encode('utf8'),
                          success=(lambda *a: (self.set_dirty(), control.update_buttons())),
                          error=self.on_popup_error(_('comment')))

    on_popup_comment.takes_popup_control = True

    def on_popup_error(self, thing, repeat = None):
        def on_error(**k):
            if k.get('permissions'):
                common.fire('error', title=_('MySpace Error'),
                            major = _('Error posting {thing}').format(thing=thing),
                            minor = _('Digsby does not have permission to perform this action.'),
                            buttons = [(_('Grant Permissions'), self.need_permissions),
                                       (_('Close'), lambda: None)],
                            sticky = True,
                            )
        return on_error

    def _got_userinfo(self, userinfo, from_cache = False):
        if not from_cache:
            self._cache('userinfo', userinfo)

        if userinfo is None:
            return

        self.userid = userinfo.userId
        self.userinfo = userinfo

    def _got_status(self, status, from_cache = False):
        if not from_cache:
            self._cache('status', status)
        else:
            log.info("got cache data for status: %r", status)

        if status is None:
            return

        log.info('status: %r', status)

        status['moodlastupdated'] = status.get('moodLastUpdated', status.get('moodStatusLastUpdated', None))
        status['moodimageurl'] = status.get('moodImageUrl', status.get('moodPictureUrl',  None))
        status['moodid'] = status.get('moodId', None)
        new_status = objects.StatusUpdate(self)

        try:
            new_status.populate(status, objects.InputType.JSON)
            if getattr(new_status, 'comments', None) is None:
                new_status.comments = []
        except Exception, e:
            log.error('Error loading status from json. error = %r, data = %r', e, status)
            import traceback; traceback.print_exc()
        else:
            if new_status != self.status:
                log.info('Got new status')
                self.status = new_status
                self._feed_invalidated()

    def _got_friend_info(self, friend_info, from_cache = False):

        if not from_cache:
            friends = {}
            for entry in friend_info:
                friend = entry['person']
                friends[friend.id] = friend

            self._cache('friend_info', friends)
        else:
            friends = friend_info

        self._friend_requester = None

        if friends is None or 'Friends' in friends:
            return

        self.users.update(friends)

    def _got_friend_status(self, statuses, from_cache = False):
        if statuses is None:
            return

        self._status_requester = None

        def empty_status(x):
            return bool(x['status'])

        def status_from_json(x):
            try:
                o = objects.StatusUpdate(self)
                o.populate(x, objects.InputType.JSON)
                return o
            except Exception, e:
                log.error('Error loading status update. exception = %r, data = %r', e, x)
                return None

        if not from_cache:
            updated_status = filter(None, map(status_from_json, filter(empty_status, statuses)))
            _before = updated_status + self.friend_status
            merged_status = util.removedupes(self.friend_status + updated_status, key = lambda x: x.id)
#            for status in merged_status:
#                self.get_comments_for(status.id)
            self._cache('friend_status', merged_status)
        else:
            for status in statuses:
                status.comments = map(objects.MyspaceComment.from_json, getattr(status, 'comments', []))
            merged_status = statuses

        if self.friend_status != merged_status:
            self.friend_status = merged_status[:common.pref('myspace.max_friendstatus', type = int, default = 200)]
            self._feed_invalidated()
            log.info('Got new friend status')

    def _got_indicators(self, indicators):
        indicators.pop('user', None)

        indicators.pop('countnewmail', None) # we don't care about the number

        if indicators is None:
            return

        to_notify = util.dictdiff(self.indicators, indicators)
        dirty = self.indicators != indicators
        self.indicators = indicators

        self.event('on_indicators', indicators)

        self._notify_alerts(to_notify)

        if dirty:
            self._dirty = True
            log.info('Got new alerts')

    def _notify_alerts(self, alerts):
        log.info('MySpace got the following alerts: %r', alerts)
        for alert in alerts:
            if alert == 'countnewmail':
                continue

            if self.filters['indicators'].get(alert, False) or alert == 'mailurl':
                text = text_for_alert(alert, alerts)
                if text is None:
                    continue

                common.fire('myspace.alert',
                            title = _("MySpace Alerts"),
                            msg   = _("You have new %s") % (text),
                            onclick = lambda *a, **k: self.openurl(alerts[alert]),
                            popupid = '%r.myspace' % self)

    def filtered_indicators(self):
        inds = self.indicators.copy()
        for ind in inds.keys():
            if not (self.filters['indicators'].get(ind, False) or ind in ('mailurl', 'countnewmail')):
                inds.pop(ind, None)

        return inds

    def _got_friend_activities(self, f_acts, from_cache = False):
        if f_acts is None:
            return

        if not from_cache:
            activities = []

            entries = getattr(f_acts, 'entry', [])
            for entry in entries:
                activity = objects.Activity()
                try:
                    activity.populate(entry, objects.InputType.XML)
                except Exception:
                    log.error('Error processing this activity: %r', etree.tostring(entry))
                    raise

                if activity.title == (activity.author_name + ' '):
                    continue

                self.fix_title(activity)
                activities.append(activity)

            log.info("got %r activities", len(activities))
            activities = util.removedupes(activities + self.activities, key = lambda x: x.id)
            self._cache('friend_activities', activities[:common.pref('myspace.newsfeed.maxlength', type = int, default = 200)])
        else:
            activities = f_acts

        if self.activities != activities:
            log.info('Got new activities')
            self.activities = activities[:common.pref('myspace.max_activities', type = int, default = 200)]
            self._feed_invalidated()

    def fix_title(self, act):
        if act.title.endswith(':'):
            act.title = act.title[:-1] + '.'

        try:
            act.title = util.strip_html(act.title)
        except Exception, e:
            log.error("error stripping html: %r (data = %r)", e, act.title)

    def combined_feed(self):
        activities = self.activities[:]
        statuses = self.friend_status[:]

        entries = activities + statuses
        entries.sort(key = lambda x: funcs.get(x, 'updated_parsed', 0), reverse = True)

        return filter(self.should_show_entry, entries)

    def should_show_entry(self, entry):
        atype = entry.activity_type

        alert_name = activities_to_alert_type.get(atype)

        if atype == "StatusMoodUpdate":
            # Old style of status update that isn't used anymore.
            return False

        return self.filters.get('feed', {}).get(alert_name, False)

    def create_activity(self, activity_args):
        self.api.call('activities/@me/@self/@app', OpenSocial = True).POST(activity_args)

    def get_post_by_id(self, post_id):

        for status in self.friend_status + [self.status]:
            if post_id in (status.id, "%r//%r//%r" % ('status-update', status.author_id, status.published_parsed)):
                return status

        for activity in self.activities:
            if activity.id == post_id:
                return activity

        return None

    @util.callsback
    def post_comment(self, post_id, comment, callback = None):
        # TODO: post comment.
        post = self.get_post_by_id(post_id)

        comment_data = util.Storage({'author': util.Storage({'id' : self.userid }),
                                     'body' : comment})

        params = {'format':'json',
                  'fields':'author,displayName,profileUrl,thumbnailUrl'}

        statusId = getattr(post, 'statusId', None)
        if statusId is not None:
            params['statusId'] = statusId
        else:
            params['postedDate'] = post.published

        def error(e):
            if e.code == 401:
                opensocial_err = getattr(e, 'headers', {}).get('x-opensocial-error', None)
                log.info("got opensocial_err = %r", opensocial_err)
                if opensocial_err is None:
                    return callback.error(error_obj = e)
                elif opensocial_err == 'Application does not have permission to publish activities.':
                    return callback.error(error_msg = opensocial_err, permissions = True)
                else:
                    return callback.error(error_msg = opensocial_err)
            elif e.code == 404:
                return callback.error(error_msg = _("Activity stream item not found. It may have been removed by its creator."))
            else:
                return callback.error(error_obj = e)

        self.api.call('statusmoodcomments/%s/@self/%s' % (post.author_id, post.id),
                      OpenSocial = True).POST(data = json.dumps(dict(comment_data)),
                                              parameters = params,
                                              use_default_params = False,
                                              success = lambda *a:self._check_post_comment_success(post_id, comment_data, callback, *a),
                                              error = error)

    def _check_post_comment_success(self, post_id, comment_data, callback, result):
        log.info('Got post comment result: %r', result)
        post = self.get_post_by_id(post_id)
        comment_collection = post.comments

        now = int(time.time())

        comment = objects.MyspaceComment(util.Storage(commentId = "fake-comment-id-%r" % now,
                                                      postedDate_parsed = now,
                                                      body = comment_data.body,
                                                      author = comment_data.author,
                                         ))

        post.comments.append(comment)
        post.commentsRetrievedDate = 0
        hooks.notify('digsby.myspace.comment_added', comment_data)
        callback.success()

    @util.callsback
    def get_comments_for(self, post_id, callback = None):
        post = self.get_post_by_id(post_id)

        if post is None or (time.time() - getattr(post, 'commentsRetrievedDate', 0)) <= COMMENTS_TTL:
            return callback.error(error_msg = "no_change")

        self._request_comments_for_post(post_id, callback = callback)

    def _request_comments_for_post(self, post_id, callback):
        log.info('requesting comments for post_id: %r', post_id)
        post = self.get_post_by_id(post_id)

        statusId = getattr(post, 'statusId', None)
        if statusId is not None:
            params = dict(statusId = statusId)
        else:
            params = dict(postedDate = post.published)


        def error(e):
            if getattr(e, 'code', None) == 401:
                opensocial_err = getattr(e, 'headers', {}).get('x-opensocial-error', None)
                log.info("got opensocial_err = %r", opensocial_err)
                if opensocial_err is None:
                    return callback.error(error_obj = e)
                elif opensocial_err == 'Application does not have permission to publish activities.':
                    return callback.error(error_msg = opensocial_err, permissions = True)
                else:
                    return callback.error(error_msg = opensocial_err)
            else:
                return callback.error(error_obj = e)

        self.api.call('statusmoodcomments/%s/@self/%s' % (post.author_id, post.id),
                      OpenSocial = True,
                      vital = False).GET(success = lambda *a: self._handle_comment_response(post_id, callback, *a),
                                         error = error,
                                         use_default_params = False,
                                         parameters = params)

    def _handle_comment_response(self, post_id, callback, comments_data):
        log.info("Got comment response for %r: %r", post_id, comments_data)

        post = self.get_post_by_id(post_id)

        request_ids = []

        comments = []
        for comment_data in comments_data.entry:
            comment = objects.MyspaceComment(comment_data)
            comments.append(comment)

            userid = comment.userid
            if userid != '-1' and self.user_from_id(userid) is None:
                request_ids.append(userid)


        post.commentsRetrievedDate = time.time()
        post.comments = comments

        if len(request_ids):
            log.info("Requesting %d users for comment author info", len(request_ids))
            cc = util.CallCounter(len(request_ids), callback.success)
            for id in request_ids:
                self.api.call('people/%s/@self' % id,
                              OpenSocial = True,
                              vital = False).GET(success = lambda info: (self._on_userinfo(info), cc()),
                                                 error = lambda *a: cc())
        else:
            callback.success()

    def _on_userinfo(self, info):
        # TODO: don't put them in friends! need a 'users' attribute
        info = info['person']
        self.users[info.id] = info


class OpenSocialPageRequester(object):
    @callbacks.callsback
    def __init__(self, conn, uri, parameters = None, max = None, callback = None):
        self.conn = conn
        self.uri = uri
        self.parameters = parameters or {}
        self.callback = callback
        self.max = max
        self.startIndex = 0
        self.count = 2
        self.data = []

    def get_all(self, startIndex = 0, count = 100):
        self.count = count
        self.startIndex = startIndex
        self._next_page()

    def _next_page(self):
        log.info('requesting %r, startIndex = %r, count = %r', self.uri, self.startIndex, self.count)
        parameters = self.parameters.copy()
        if self.startIndex:
            parameters['startIndex'] = self.startIndex
        if self.count:
            parameters['count'] = self.count

        self.conn.api.call(self.uri,
                           OpenSocial = True).GET(parameters = parameters,
                                                  error = self.on_error,
                                                  success = self.on_page)

    def on_page(self, data = None):
        if data is None:
            callback, self.callback = self.callback, None
            if callback is not None:
                return callback.error(ValueError("no data was received"))
            else:
                log.info("no data was received and no callback present. (%r)", self)
                return

        if not self.collect_data(data):
            return False

        numOmittedEntries = int(data.get('numOmittedEntries', 0))
        self.count = int(data['itemsPerPage'])
        self.startIndex = int(data['startIndex'])
        totalResults = int(data['totalResults'])

        log.info("got a page of data: %r/%r/%r", self.startIndex, self.count, totalResults)
        log.info_s('\tdata=%r', data)

        if self.max is not None:
            _max = min(self.max, totalResults)
        else:
            _max = totalResults

        if (self.startIndex + self.count) < _max:
            self.startIndex += self.count
            self.conn.api.clear_waiting(net.httpjoin(getattr(self.conn.api, 'OS_API_BASE', self.conn.api.API_BASE), self.uri))
            self._next_page()
        else:
            callback, self.callback = self.callback, None
            if callback is not None:
                data, self.data = self.data, []
                callback.success(data)

    def collect_data(self, data):
        try:
            self.data.extend(data['entry'])
        except Exception as e:
            log.error("\tdata: %r", data)
            self.on_error(e)
            return False
        else:
            return True

    def on_error(self, e):
        callback, self.callback = self.callback, None
        if callback is not None:
            self.data = []
            callback.error(e)

activities_to_alert_type = dict(
                            ApplicationAdd         = 'applications',
                            BlogAdd                = 'posts',
                            ForumPosted            = 'posts',

                            DigsbyStatusUpdate     = 'statuses',
                            StatusMoodUpdate       = 'statuses',

                            FriendAdd              = 'friends',
                            FriendCategoryAdd      = 'friends',
                            JoinedGroup            = 'groups',

                            EventAttending         = 'events',
                            PersonalBandShowUpdate = 'events',

                            MobilePhotoUpload      = 'photos',
                            PhotoAdd               = 'photos',
                            PhotoTagged            = 'photos',

                            ProfileSongAdd         = 'music',
                            SongUpload             = 'music',

                            FavoriteVideoAdd       = 'videos',
                            ProfileVideoUpdate     = 'videos',
                            VideoAdd               = 'videos',
                        )


def _compress_activities(start_activities):
    final_activities = []

    start_activities.sort(key = lambda x: x.updated_parsed, reverse = True)
    seen_ids = set()
    current = None
    while start_activities:
        act = start_activities.pop()

        if current is None:
            current = act
            continue

        if len(current.objects) == 0:
            current.objects = [current.object]
            current.object = None

        if not (current.source        == act.source and
                current.activity_type == act.activity_type and
                current.author_id     == act.author_id):
            final_activities.insert(0, current)
            current = act
            continue

        if act.object is not None:
            current.objects.append(act.object)
        elif len(act.objects):
            current.objects.extend(act.objects)

    if len(current.objects) == 0:
        current.objects = [current.object]
    final_activities.insert(0, current)

    return final_activities


class MyspaceStatus(object):
    Spacer_URL = 'http://x.myspacecdn.com/modules/common/static/img/spacer.gif'
    Default_Post_Url = 'http://home.myspace.com/modules/homedisplay/services/home.asmx/SaveMoodStatus'
    def __init__(self, ms, userid, username, status, mood, when):
        if userid == 'self':
            userid = ms.userid
        self.myspace = ms
        self.userid = userid
        self.username = username
        self.status = status
        self.mood = mood
        self.when = when

    def __repr__(self):
        return '<%s: %s %s (%s)>' % (type(self).__name__, self.username, self.status, self.when)

class OldPersonalStatus(MyspaceStatus):
    @classmethod
    def fromDoc(cls, doc):
        status_span = doc.find('.//div[@class="StatusMood"]//span[@id="friendStatus"]')
        if status_span is None:
            return {}

        name_link = status_span.find('.//a')
        if name_link is not None:
            username = name_link.text
            status = name_link.getparent().tail
        else:
            username = None
            status = None

        mood_span = doc.find('.//div[@class="StatusMood"]//*[@id="currentMood"]')
        if mood_span is not None:
            mood = mood_span.text
        else:
            mood = None

        if None in (username, status):
            return None

        return dict(username = username,
                    mood = mood,
                    status = status,
                    time = None)

class NewPersonalStatus(MyspaceStatus):
    @classmethod
    def fromDoc(cls, doc):

        statusMoods = doc.xpath(".//div[@id='userstatus']//*[contains(@class, 'statusMood')]", smart_strings = False)
        if len(statusMoods):
            hsm = statusMoods[0]
        else:
            log.info_s('no headerStatusMood found in %r', html.tostring(doc))
            return None

        status_info = {}

        for key in ('status', 'username', 'hash', 'mood', 'time', 'webserviceurl', 'moodurl'):
            status_info[key] = hsm.get(key)

        status_info['timestamp'] = status_info.pop('time')

        return status_info

class AnotherPersonalStatus(MyspaceStatus):
    @classmethod
    def fromDoc(cls, doc):
        status_info = {}
        topstatus_div = doc.find('.//div[@id="userstatus"]')
        if topstatus_div is None:
            return status_info

        username_span = topstatus_div.find('.//span[@id="hsmUserName"]')
        if username_span is not None:
            status_info['username'] = username_span.text

        statustext_span = topstatus_div.find('.//span[@id="hsmStatus"]')
        if statustext_span is not None:
            status_info['status'] = statustext_span.text

        when_span = topstatus_div.find('.//span[@id="hsmTimestamp"]')
        if when_span is not None:
            status_info['time'] = when_span.text

        mood_span = topstatus_div.find('.//span[@id="hsmMoodName"]')
        if mood_span is not None:
            status_info['mood'] = mood_span.text

        return status_info


def msid_eq(id1, id2):
    id1_s, id2_s = ['myspace.com.person.%s' % x for x in (id1, id2)]

    if id1 in (id2, id2_s) or id1_s in (id2, id2_s):
        return True

    return False

