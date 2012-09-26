'''
Used to convert actions to API requests and emits events based on the results of those requests.
'''
import operator
import logging
import traceback

import lxml.etree as etree
import lxml.objectify as objectify
import lxml.builder as builder

import common.oauth_util as oauth_util

import util.net as net
import util.Events as Events
import util.callbacks as callbacks

import LinkedInApi
import LinkedInObjects as LIO

log = logging.getLogger("linkedin.protocol")

PROFILE_FIELDS = ('id',
                  'first-name',
                  'last-name',
                  'headline',
                  'current-status',
                  'picture-url',
                  'site-standard-profile-request',
                  )

class LinkedInProtocol(oauth_util.OAuthProtocolBase):
    events = oauth_util.OAuthProtocolBase.events | set((
        'on_rate_limit',
        'update_error',

        'newsfeed_updates',
    ))

    def __init__(self, username, token, cache_data = None, filters = None, time_offset = None):
        oauth_util.OAuthProtocolBase.__init__(self, username, token)
        self.userid = None
        self.pending = {}

        self.time_offset = time_offset

        self.users = {}
        self.updates = []
        self.last_update_time = None
        self._api_data = cache_data or {}

        self._load_cache()

    def _cache(self, datatype, data):
        self._api_data[datatype] = data
        self.event("need_cache", self._api_data)

    def _load_cache(self):
        for k in self._api_data:
            try:
                self._got_data(k, self._api_data.get(k, None), from_cache = True)
            except Exception:
                import traceback; traceback.print_exc()

    def _got_data(self, datatype, val, from_cache = False):
        if datatype == 'last_update_time':
            self.last_update_time = val

    def _create_api(self):
        self.api = LinkedInApi.LinkedInOAuthClient(self.username, self.token, time_offset = self.time_offset)

    @callbacks.callsback
    def set_status_message(self, message, callback = None):
        return NotImplemented

    def update(self):
        self.event('update_pre')

        if self.userid is None:
            self.api.call('people/~', fields = PROFILE_FIELDS).GET(quiet = True, success = self._got_profile, error = self._profile_error)

        else:
            self._get_network_updates()

    def get_time_offset(self):
        return self.api.get_time_offset()

    def _got_profile(self, resp):
        users = self.pending.setdefault('users', {})

        try:
            f = LIO.LinkedInFriend.from_etree(resp)
            users[f.id] = f
            self.userid = f.id
        except Exception, e:
            traceback.print_exc()

        self._get_network_updates()

    def _profile_error(self, e):
        if hasattr(e, 'read'):
            data = e.read()
            log.error("error retrieving self profile: %r", data)

            self.check_error(data, getattr(e, 'headers', {}).get('Content-Type'), status = e.code)
        elif isinstance(e, oauth_util.UserCancelled):
            self.update_error("BAD_PASSWORD")

    def check_error(self, data, content_type, status = 0):
        log.info("checking error in %r", data)

        if 'xml' in content_type or 'html' in content_type:
            if data:
                o = objectify.fromstring(data)
                status = o.status.text
                message = o.message.text

                log.info("status= %r", status)
                log.info("o.message.text= %r", message)
            else:
                message = ''
                status = str(status)

            if status == "403" and "Throttle" in message:
                self.on_rate_limit()
            elif status != "404":
                self.update_error(o)

        else:
            log.error("Unknown error occurred: %r", data)

    def _get_network_updates(self):
        params = {'count' : '250'}

        if self.last_update_time is not None:
            params['after'] = self.last_update_time

        self._failed_network_updates = 0

        self.api.call('people/~/network').GET(parameters = params,
                                              success = self._check_network_updates,
                                              error = self._network_updates_error)

    def _check_network_updates(self, resp):
        resp = resp.updates # the other element is "network-stats" which says how many first- and second-degree contacts there are
        expected_items_s = resp.attrib.get("total", None)
        count = int(resp.attrib.get('count', 0))
        start = int(resp.attrib.get('start', 0))

        try:
            expected_items = int(expected_items_s)
        except (ValueError, TypeError):
            expected_items = 0

        updates = self.pending.setdefault('updates', [])

        for update_data in getattr(resp, 'update', []):
            try:
                u = LIO.LinkedInNetworkUpdate.from_etree(update_data)
                if u is None:
                    self._failed_network_updates += 1
                else:
                    updates.append(u)
            except Exception, e:
                self._failed_network_updates += 1
                traceback.print_exc()

        if (len(updates) + self._failed_network_updates) >= expected_items:
            self._got_network_updates()
        else:
            params = dict(start = start + count, count = count)
            if self.last_update_time is not None:
                params['after'] = self.last_update_time

            log.info("need to request more updates! (%d/%d)", len(updates), expected_items)
            self.api.clear_waiting(net.httpjoin(self.api.API_BASE, 'people/~/network'))
            self.api.call('people/~/network').GET(parameters = params,
                                                  success = self._check_network_updates,
                                                  error = self._network_updates_error)

    def _got_network_updates(self):
        log.info('got all network updates')
        updates = filter(None, self.pending.get('updates', []))

        if updates:
            to_notify = [x for x in updates if x.timestamp > self.last_update_time]
            self.last_update_time = max(int(x.timestamp) for x in updates)
            self.newsfeed_updates(to_notify)
            self._cache('last_update_time', self.last_update_time)

        self.update_post()

    def _network_updates_error(self, e):
        data = e.read()
        log.error("error getting network updates: %r", data)

        self.check_error(data, getattr(e, 'headers', {}).get('Content-Type'))

    def apply_pending(self):
        users = self.pending.pop('users', None)
        if users is not None:
            self._got_all_users(users)

        updates = self.pending.pop('updates', None)
        if updates is not None:
            self._got_all_updates(updates)

    def set_dirty(self):
        self._dirty = True

    def should_show_entry(self, entry):
        # check filters

        return True

    def check_update_complete(self):
        return bool(self.users and self.updates)

    def _got_all_users(self, users):
        self.users.update(users)

    def _got_all_updates(self, updates):
        self.updates[:] = updates
        self.updates.sort(key=operator.attrgetter('timestamp'), reverse = True)

    @callbacks.callsback
    def post_comment(self, post_id, comment, callback = None):
        post = self.get_post_by_id(post_id)

        if post is None:
            return callback.error({'error_msg' : "Network update not found"})

        update_key = post.update_key

        post_data = etree.tostring(builder.E("update-comment", builder.E("comment", comment)), standalone = True, encoding = 'UTF-8')

        self.api.call('people/~/network/updates/key=%s/update-comments'
                      % update_key.encode('url')).POST(post_data,
                                                       success = callback.success,
                                                       error = lambda err: self._post_comment_error(err, callback = callback))

    @callbacks.callsback
    def _post_comment_error(self, err, callback = None):
        data = err.read()
        log.info("Error posting comment: %r", data)

        o = objectify.fromstring(data)
        error_msg = o.message.text

        callback.error(dict(error_msg = error_msg))

    @callbacks.callsback
    def refresh_comments(self, post_id, callback = None):
        uri = 'people/~/network/updates/key=%s/update-comments' % post_id.encode('url')
        self.api.clear_waiting(net.httpjoin(self.api.API_BASE, uri))
        self.api.call(uri).GET(success = lambda resp: self.process_comments(post_id, resp, callback = callback),
                               error = lambda err: self._post_comment_error(err, callback = callback))

    @callbacks.callsback
    def process_comments(self, post_id, resp, callback = None):
        log.debug_s("loading comments from %r", resp)
        post = self.get_post_by_id(post_id)
        post.load_comments(resp)

        callback.success()

    def get_post_by_id(self, post_id):
        for update in self.updates:
            if update.id == post_id:
                return update

        return None

    @callbacks.callsback
    def set_status(self, msg, callback = None):
        self.api.call("people/~/current-status").PUT(data = etree.tostring(builder.E("current-status", msg), standalone = True, encoding = 'UTF-8'),
                                                     callback = callback)

    def create_activity(self, body = '', locale = 'en_US', content_type = 'linkedin-html'):
        log.info("creating activity: %r", body)
        tree = builder.E("activity",
                         builder.E("content-type", content_type),
                         builder.E("body", body),

                         locale=locale,
                         )
        doc = etree.tostring(tree, standalone = True, encoding = 'UTF-8')

        def success(resp):
            log.info("create_activity success.")

        self.api.call("people/~/person-activities").POST(data = doc, success = success)
