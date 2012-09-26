from util.callbacks import callsback
from util.threads.timeout_thread import Timer
from util.primitives import Storage as S
from traceback import print_exc
import util.primitives.structures as structures
from .fbutil import trim_profiles, extract_profile_ids
import traceback
import simplejson
import facebookapi
import hooks
from social.network import SocialFeed
from util.Events import EventMixin
import util.primitives.mapping as mapping

from logging import getLogger
from util.primitives.mapping import Ostorage
from gui import skin
import graphapi
log = getLogger("Facebook2.0")

POSTS_LIMIT = 100

FORCED_APPS = {'News Feed':      'nf',
               'Status Updates': 'app_2915120374',
               'Photos':         'app_2305272732',
               'Links':          'app_2309869772'}

FORCED_KEYS = {
               '__notification__':{'name':'Notifications',
                                   'icon_url':'facebookicons.notifications_icon'}
               }

KNOWN_APPS_LOOKUP = mapping.dictreverse(FORCED_APPS)

#COMMENTS_QUERY = "SELECT fromid, text, time, post_id, id FROM comment WHERE post_id IN (SELECT post_id FROM #posts)"
PROFILES_QUERY = """SELECT id, name, pic_square, url FROM profile WHERE id IN (SELECT viewer_id FROM #posts) OR id IN(SELECT actor_id FROM #posts) OR id in (SELECT target_id FROM #posts) OR id in (SELECT source_id FROM #posts) OR id IN (SELECT likes.sample FROM #posts) OR id IN (SELECT likes.friends FROM #posts) OR id IN (SELECT sender_id FROM #notifications)"""
#ALL_POSTS_QUERY = 'SELECT post_id, comments, permalink, created_time, updated_time, viewer_id, actor_id, target_id, source_id, message, attachment, action_links, likes FROM stream where filter_key="nf" and is_hidden=0 LIMIT 100'
BIRTHDAY_QUERY  = 'select name, birthday_date, profile_url, uid from user where uid IN (select uid2 from friend where uid1=%d)'
NOW_QUERY       = 'select now() from user where uid=%d'
EVENTS_QUERY    = 'select eid from event where eid in (select eid from event_member where uid=me() and rsvp_status="not_replied") and start_time > now()'
STATUS_QUERY    = 'select message, status_id, time, uid from status where uid=me() limit 1'

NOTIFICATIONS_QUERY = 'select notification_id,sender_id,created_time,updated_time,title_html,title_text,href,is_unread,app_id from notification where recipient_id=me()'
APP_QUERY = 'SELECT app_id,icon_url FROM application WHERE app_id IN (SELECT app_id from #notifications)'

POST_FILTER_KEY_QUERY = "select post_id, filter_key from stream where post_id in (select post_id from #latest_posts) and filter_key in (select filter_key from #filter_keys)"
FILTER_KEY_QUERY = "select filter_key, name, icon_url from stream_filter where uid=me() and ((is_visible=1 and type='application') or filter_key in ('" + "', '".join(FORCED_APPS.values()) + "')) ORDER BY rank ASC"
POST_QUERY = 'SELECT post_id, comments, permalink, created_time, updated_time, viewer_id, actor_id, target_id, source_id, message, attachment, action_links, likes FROM stream where post_id="%s"'

#UPDATED_POSTS_QUERY = 'SELECT post_id, comments, permalink, created_time, updated_time, viewer_id, actor_id, target_id, source_id, message, attachment, action_links, likes FROM stream where filter_key="nf" and is_hidden=0 and updated_time > %s LIMIT 100'
LATEST_POSTS_QUERY = ' '.join(x.strip() for x in '''
        SELECT post_id, updated_time
        FROM stream
        WHERE filter_key="%%s" %%s ORDER BY created_time DESC
        LIMIT %d
        '''.strip().splitlines()) % POSTS_LIMIT
UPDATED_POSTS_QUERY = ' '.join(x.strip() for x in '''SELECT post_id, comments, permalink, created_time, updated_time, viewer_id, actor_id, target_id, source_id, message, attachment, action_links, likes
        FROM stream
        WHERE post_id in
            (
                SELECT post_id
                FROM #latest_posts
                WHERE updated_time > %s
            ) ORDER BY created_time DESC'''.strip().splitlines())

UPDATE_STREAM_QUERY = {
                     #'comments':COMMENTS_QUERY,
                     'profiles':PROFILES_QUERY}

from facebook.fbacct import FBIB

class FacebookProtocol(EventMixin):
    events = EventMixin.events | set([
                                      'stream_requested',
                                      'not_logged_in',
                                      'got_stream',
                                      'status_updated',
                                      'conn_error',
                                      'infobox_dirty',
                                      ])
    def __init__(self, acct):
        self.stream_request_outstanding = True
        self.acct = acct
        self._init_apis()
        self.last_stream = True
        self.last_filter_key = self.filter_key
        EventMixin.__init__(self)

        self.social_feed = SocialFeed('facebook_' + self.acct.username,
                                      'newsfeed',
                                      self.get_post_feed,
                                      self.htmlize_posts,
                                      self.set_infobox_dirty)

    def set_infobox_dirty(self):
        self.event('infobox_dirty')

    def htmlize_posts(self, posts, stream_context):
        '''Convert one facebook newsfeed post into infobox HTML.'''
        t = FBIB(self.acct)
        #CAS: pull out the context stuff, the default FBIB grabs self.last_stream, not the one we have context for!
        return t.get_html(None, set_dirty=False,
                          file='posts.py.xml',
                          dir=t.get_context()['app'].get_res_dir('base'),
                          context=S(posts=posts))

    def get_post_feed(self):
        # TODO bring back feed context.
        return iter(self.last_stream.posts)

    @property
    def filter_key(self):
        return ['nf', 'lf', 'h'][self.acct.preferred_filter_key]

    @property
    def hidden_posts(self):
        return "and is_hidden=0" if self.acct.show_hidden_posts else ''

    def get_stream(self):
        self.stream_request_outstanding = True
        self.do_get_stream()

    def _init_apis(self):
        self._init_digsby()

    def _init_digsby(self, session_key='', secret='', uid=None):
        access_token = getattr(self.acct, 'access_token', None)
        uid = getattr(self.acct, 'uid', None),
        self.digsby = graphapi.LegacyRESTAPI(access_token, uid=uid)

    def do_get_stream(self, num_tries=0):
        from util import default_timer
        self.start_get_stream = default_timer()
        if not self.digsby.logged_in:
            return self.event('not_logged_in')
        #refresh full stream if pref has changed
        prev_filter_key, self.last_filter_key = self.last_filter_key, self.filter_key
        if not isinstance(self.last_stream, dict) or prev_filter_key != self.filter_key:
            kw = dict(success=lambda *a: self.get_stream_success(num_tries=num_tries, *a),
                      error  = lambda *a: self.get_stream_error(num_tries, *a))
            updated_time = 0
        else:
            kw = dict(success=self.update_stream_success,
                      error  = lambda *a: self.get_stream_error(num_tries, *a))
            updated_time = max(self.last_stream.posts + [S(updated_time=0)], key=lambda v: v.updated_time).updated_time
#        query = self.digsby.multiquery(prepare=True,
        self.last_run_multi = dict(
#                     birthdays = BIRTHDAY_QUERY % self.digsby.uid,
                     latest_posts = LATEST_POSTS_QUERY % (self.filter_key, self.hidden_posts),
                     posts = UPDATED_POSTS_QUERY % (('%d' % updated_time) + '+0'),
#                     now = NOW_QUERY % self.digsby.uid,
                     events = EVENTS_QUERY,
                     status = STATUS_QUERY,
                     notifications = NOTIFICATIONS_QUERY,
                     apps = APP_QUERY,
                     post_filter_keys = POST_FILTER_KEY_QUERY,
                     filter_keys = FILTER_KEY_QUERY,
                     **UPDATE_STREAM_QUERY)
        self.digsby.fql.multiquery(queries=self.last_run_multi, **kw)
#        alerts = self.digsby.notifications.get(prepare=True)
#        self.digsby.batch.run(method_feed=[alerts, query], **kw)

    def update_status(self):
        self.digsby.query(STATUS_QUERY, success=self.status_updated)

    def status_updated(self, status):
        status = status[0]
        if status is not None:
            status['uid'] = self.digsby.uid
        self.last_status = status
        self.event('status_updated')

    def update_stream_success(self, value):
        return self.get_stream_success(value, update=True)

    def get_stream_success(self, value, update=False, num_tries=0):
        from util import default_timer
        self.end_get_stream = default_timer()
        log.debug('stream get took %f seconds', self.end_get_stream - self.start_get_stream)
        stream = value
#        v = []
#        for val in value:
#            v.append(simplejson.loads(val, object_hook=facebookapi.storageify))
#        alerts, stream = v[:2]
        self.last_alerts = Alerts(self.acct)
        from facebookapi import simplify_multiquery
        try:
#            print stream
            new_stream = simplify_multiquery(stream,keys={'posts':None,
#                                                          'comments':None,
                                                          'latest_posts':None,
                                                          'profiles':'id',
#                                                          'now':None,
                                                          'events':list,
                                                          'status':None,
                                                          'notifications': None,
                                                          'apps' : 'app_id',
                                                          'post_filter_keys':None,
                                                           'filter_keys':'filter_key'})# 'birthdays':'uid',})
            import util.primitives.funcs as funcs
#            new_stream['comments'] = dict(funcs.groupby(new_stream['comments'], lambda x: x['post_id']))
            new_stream['comments'] = {}
            new_stream['post_ids'] = post_ids = {}
            for k, v in new_stream['filter_keys'].iteritems():
                if not v.get('name'):
                    v['name'] = KNOWN_APPS_LOOKUP.get(k, v.get('name'))
            new_stream['filter_keys'].update([(k, dict(name=d['name'],
                  icon_url=skin.get(d['icon_url']).path.url())) for k,d in FORCED_KEYS.items()])
            new_stream['post_filter_keys'] = dict((post_id, structures.oset(p['filter_key'] for p in vals))
                                             for post_id, vals in
                                             funcs.groupby(new_stream['post_filter_keys'], lambda x: x['post_id']))
            for post in new_stream['posts']:
                post['comments']['count'] = int(post['comments']['count'])
            new_stream['apps'], apps_str = {}, new_stream['apps']
            for app_id, app_dict in apps_str.items():
                new_stream['apps'][int(app_id)] = app_dict
            try:
                new_stream['now'] = new_stream['now'][0].values()[0]
            except (IndexError, KeyError) as _e:
#                print_exc()
                import time
                new_stream['now'] = time.time()
            self.last_alerts.event_invites &= set(new_stream['events'])
            self.last_status = (new_stream['status'][:1] or [Ostorage([('message', ''), ('status_id', 0), ('time', 0)])])[0]
            self.last_status['uid'] = self.digsby.uid
            if not isinstance(new_stream['posts'], list):
                log.error('stream: %r', stream)
                raise ValueError('Facebook returned type=%r of posts' % type(new_stream['posts']))
            for post in new_stream['posts']:     #get the new ones
                post_ids[post['post_id']] = post
            if 'notifications' in new_stream:
                import lxml
                for notification in new_stream['notifications']:
                    title_html = notification.get('title_html', None)
                    if title_html is None:
                        continue
                    s = lxml.html.fromstring(title_html)
                    s.make_links_absolute('http://www.facebook.com', resolve_base_href = False)
                    for a in s.findall('a'):
                        a.tag = 'span'
#                        _c = a.attrib.clear()
                        a.attrib['class'] = 'link notification_link'
                    [x.attrib.pop("data-hovercard", None) for x in s.findall(".//*[@data-hovercard]")]
                    notification['title_html'] = lxml.etree.tostring(s)
                self.last_alerts.update_notifications(new_stream['notifications'])
            if update:
                latest_posts = filter(None, (post_ids.get(post_id, self.last_stream.post_ids.get(post_id)) for post_id in
                                             structures.oset([post['post_id'] for post in new_stream['latest_posts']] +
                                              [post['post_id'] for post in self.last_stream.posts])))[:POSTS_LIMIT]
                new_stream['posts'] = latest_posts
                for post in new_stream['posts']:     #update the dict with the combined list
                    post_ids[post['post_id']] = post
                for key in self.last_stream.comments:
                    if key in post_ids and key not in new_stream.comments:
                        new_stream.comments[key] = self.last_stream.comments[key]
                for key in self.last_stream.profiles:
                    if key not in new_stream.profiles:
                        new_stream.profiles[key] = self.last_stream.profiles[key]
            trim_profiles(new_stream)
            for p in new_stream.posts: p.id = p.post_id # compatability hack for ads
            self.last_stream = new_stream
            self.social_feed.new_ids([p['post_id'] for p in self.last_stream.posts])
        except Exception, e:
            traceback.print_exc()
            return self.get_stream_error(num_tries=num_tries, error=e)
        self.event('got_stream')

    def get_stream_error(self, num_tries, error=None, *a): #*a, **k for other kinds of errors.
        if not_logged_in(error): #doesn't matter if it's really a facebook error; should fail this test if not
            return self.event('not_logged_in')
        elif num_tries < 2:
            Timer(2, lambda: self.do_get_stream(num_tries + 1)).start()
        else:
            self.event('conn_error')

    @callsback
    def addComment(self, post_id, comment, callback=None):
        self.digsby.stream.addComment(post_id=post_id, comment=comment,
                                      success = lambda resp: self.handle_comment_resp(resp, post_id, comment, callback),
                                      error   = lambda resp: self.handle_comment_error(resp, post_id, comment, callback))

    @callsback
    def removeComment(self, comment_id, callback=None):
        self.digsby.stream.removeComment(comment_id=comment_id,
                                         success = lambda resp: self.handle_comment_remove_resp(resp, comment_id, callback),
                                         error = lambda resp: self.handle_comment_remove_error(resp, comment_id, callback))

    @callsback
    def getComments(self, post_id, callback=None, limit=50, **k):
        self.digsby.multiquery(
            comments = 'SELECT fromid, text, time, post_id, id FROM comment WHERE post_id="%s" ORDER BY time DESC LIMIT %d' % (post_id, limit),
            count    = 'SELECT comments.count FROM stream where post_id="%s"' % post_id,
            profiles = """SELECT id, name, pic_square, url FROM profile WHERE id IN (SELECT fromid FROM #comments)""",
            success = lambda resp: self.handle_get_comments_resp(resp, post_id, callback),
            error = lambda req, resp = None: self.handle_get_comments_error(resp or req, post_id, callback)
            )

    def handle_get_comments_resp(self, resp, post_id, callback):
        from facebookapi import simplify_multiquery
        resp = simplify_multiquery(resp,
                                   {'comments':None,
                                   'count':None,
                                   'profiles':'id'}
                                   )
        resp['comments'].sort(key = lambda c: c['time'])
        try:
            count = resp['count'][0]['comments']['count']
            try:
                self.last_stream['post_ids'][post_id]['comments']['count'] = int(count)
            except Exception:
                traceback.print_exc()
        except Exception:
            num_comments = len(resp['comments'])
            if num_comments >= 50:
                count = -1
            else:
                count = num_comments
        self.last_stream['comments'][post_id] = resp['comments']
        self.last_stream['profiles'].update(resp['profiles'])
        callback.success(post_id, count)

    def handle_get_comments_error(self, resp, post_id, callback):
        callback.error(resp)

    def handle_comment_remove_resp(self, resp, comment_id, callback):
        if resp:
            for post_id, comments in self.last_stream['comments'].items():
                for i, comment in enumerate(comments):
                    if comment['id'] == comment_id:
                        c = comments.pop(i)
                        post = self.last_stream['post_ids'][post_id]
                        post['comments']['count'] -= 1
                        callback.success(post_id)
                        hooks.notify('digsby.facebook.comment_removed', c)
                        return

    def handle_comment_remove_error(self, resp, comment_id, callback):
        callback.error()

    @callsback
    def addLike(self, post_id, callback):
        self.digsby.stream.addLike(post_id=str(post_id),
                                   success = (lambda resp: self.handle_like_resp(resp, post_id, callback)),
                                   error   = (lambda resp: self.handle_like_error(resp, post_id, callback)))

    @callsback
    def removeLike(self, post_id, callback):
        self.digsby.stream.removeLike(post_id=post_id,
                                      success = (lambda resp: self.handle_unlike_resp(resp, post_id, callback)),
                                      error   = (lambda resp: self.handle_unlike_error(resp, post_id, callback)))

    def handle_like_resp(self, resp, post_id, callback):
        post = self.last_stream['post_ids'][post_id]
        post['likes'].update(user_likes=True)
        post['likes']['count'] += 1
        callback.success(post_id)
        hooks.notify('digsby.facebook.like_added', post_id)

    def handle_unlike_resp(self, resp, post_id, callback):
        post = self.last_stream['post_ids'][post_id]
        post['likes'].update(user_likes=False)
        post['likes']['count'] -= 1
        callback.success(post_id)
        hooks.notify('digsby.facebook.like_removed', post_id)
        #regen likes block, regen likes link block, send to callback
        #regen cached post html

    def handle_comment_resp(self, response, post_id, comment, callback):
        comment_id = response
        post = self.last_stream['post_ids'][post_id]
        post['comments']['count'] += 1
        import time
        comment_dict = S({'fromid': post['viewer_id'],
                        'id': comment_id,
                        'post_id': post_id,
                        'text': comment,
                        'time': time.time()})
        self.last_stream['comments'].setdefault(post_id, []).append(comment_dict)
        callback.success(post_id, comment_dict)
        hooks.notify('digsby.facebook.comment_added', comment_dict)
        #regen comment, regen comment link block
        #regen cached post html

    def handle_comment_error(self, response, post_id, comment, callback):
        callback.error(response)

    def handle_like_error(self, response, post_id, callback):
        callback.error(response)

    def handle_unlike_error(self, response, post_id, callback):
        callback.error(response)

    @callsback
    def get_user_name_gender(self, callback=None):
        def success(info):
            try:
                info = info[0]
            except Exception:
                traceback.print_exc()
                callback.error(info)
            else:
                if isinstance(info, dict):
                    callback.success(info)
                else:
                    callback.error(info)
        self.digsby.query('SELECT first_name, last_name, sex FROM user WHERE uid=' + str(self.digsby.uid), success=success, error=callback.error)


from .objects import Alerts

#not ready to mess with code that's 17000 revisions old.
#minimal subclass to get rid of the reference to a facebook object
#the only reason it is there is to grab the filters; not up to that point yet here.
#class Alerts(Alerts_Super):
#    def __init__(self, notifications_get_xml=None):
#        super(Alerts, self).__init__(None, notifications_get_xml)
#        if hasattr(self, 'fb'):
#            del self.fb
#
#    def __sub__(self, other):
#        ret = Alerts()
#        for attr in self.stuff:
#            setattr(ret, attr, getattr(self, attr) - getattr(other, attr))
#        return ret
#
#    def __getitem__(self, key):
#        return getattr(self, key)

login_error_codes = frozenset(
[100, #no session key
 102, #session invalid
 104, #signature invalid (likely the secret is messed up)
 ] +
 range(450, 455 + 1) + #session errors
 [612] #permission error
)

def not_logged_in(fb_error):
    return getattr(fb_error, 'code', None) in login_error_codes
