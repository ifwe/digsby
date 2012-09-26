import weakref
import operator
import traceback
import logging
import simplejson as json
import time
import calendar
import feedparser

import datetime
import constants

import common
import util
import util.htmlutils as htmlutils

#if datetime.datetime.today() < datetime.datetime(2009, 8, 20):
#    TIMEZONE_FIX = 8 * 60 * 60
#else:
# they fixed it!
TIMEZONE_FIX = 0

log = logging.getLogger('myspace.new.objects')

class InputType(object):
    JSON = 'json'
    XML = 'xml'
    ATOM = 'atom'

class MyspaceObject(object):
    def __init__(self, ):
        pass

    def populate(self, x, input_type):
        if input_type == InputType.JSON:
            self.from_json(x)

        elif input_type == InputType.XML:
            self.from_xml(x)

        elif input_type == InputType.ATOM:
            self.from_atom(x)

        else:
            raise NotImplementedError

        return self.__dict__

    def from_json(self, x):
        raise NotImplementedError

    def from_xml(self, x):
        raise NotImplementedError

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, ' '.join('%s=%r' % i for i in sorted(vars(self).items())))

    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_user', None)
        d.pop('acct', None)
        d.pop('icon', None)
        return json.dumps(d, default = lambda o: o.__dict__)

    def __setstate__(self, x):
        def _object_hook(d):
            o = MyspaceObject()
            o.__dict__.update(d)
            return o.__dict__
        self.__dict__.update(json.loads(x, object_hook = _object_hook))

    def __eq__(self, other):
        return self.id == getattr(other, 'id', object())

    def __ne__(self, other):
        return not self.__eq__(other)

class CommentableMyspaceObject(MyspaceObject):
    def __init__(self):
        MyspaceObject.__init__(self)
        self.comments = []
        self.commentsRetrievedDate = 0

    def user_likes(self, userid):
        if not self.comments:
            return False

        try:
            int(userid)
        except ValueError:
            pass
        else:
            userid = 'myspace.com.person.%s' % userid

        for comment in self.comments:
            if comment.is_like and comment.userid == userid:
                return True

        return False

    def user_dislikes(self, userid):
        if not self.comments:
            return False

        try:
            int(userid)
        except ValueError:
            pass
        else:
            userid = 'myspace.com.person.%s' % userid

        for comment in self.comments:
            if comment.is_dislike and comment.userid == userid:
                return True

        return False

    def get_likers(self):
        if self.likable:
            return set(x.userid for x in self.comments if x.is_like)
        else:
            return []

    def get_dislikers(self):
        if self.dislikable:
            return set(x.userid for x in self.comments if x.is_dislike)
        else:
            return []

    def get_comments(self):
        return sorted([x for x in self.comments if not ((self.likable and x.is_like) or (self.dislikable and x.is_dislike))], key = lambda x: x.postedDate_parsed)

    @property
    def likable(self):
        return self.supports_comments and common.pref('myspace.like_enabled', type = bool, default = True)

    @property
    def dislikable(self):
        return self.supports_comments and common.pref('myspace.dislike_enabled', type = bool, default = True)

class ActivitySource(MyspaceObject):
    def from_xml(self, x):
        self.title = unicode(x.title)
        id_tag = getattr(x, 'id', None)
        if id_tag is None:
            self.id = None
        else:
            self.id = unicode(id_tag)

        link_tag = getattr(x, 'link', None)
        if link_tag is None:
            self.url = None
        else:
            self.url = link_tag.attrib.get('href')

    def __eq__(self, other):
        return self.url == getattr(other, 'url', object())

class AtomItem(CommentableMyspaceObject):
    def __init__(self):
        CommentableMyspaceObject.__init__(self)

    def from_xml(self, x):
        atomget = lambda k, default = None: getattr(x, '{%s}%s' % (constants.NS.Atom, k), default)
        id = unicode(atomget('id') or '')
        title = unicode(atomget('title') or '')

        author_tag = atomget('author')
        if author_tag is None:
            author_name = author_id = author_url = author_tag
        else:
            author_name = unicode(author_tag.name)
            author_id = author_url = unicode(author_tag.uri)

        source_tag = atomget('source')
        if source_tag is None:
            source = None
        else:
            source = ActivitySource()
            source.populate(source_tag, InputType.XML)

        icon_url = None
        preview_url = None
        url = None

        links = atomget('link', [])
        for link in links:
            rel = link.attrib.get('rel')
            if rel == 'icon':
                icon_url = unicode(link.attrib.get('href'))

            if rel == 'preview':
                preview_url = unicode(link.attrib.get('href'))

            if rel == 'alternate' and url is None:
                url = unicode(link.attrib.get('href'))

        contents = []
        for content in atomget('content', []):
            contents.append((unicode(content.attrib.get('type')), htmlutils.render_contents(content)))

        self.__dict__.update(
                             id = id,
                             title = title,
                             author_id = author_id,
                             author_url = author_url,
                             author_name = author_name,
                             source = source,

                             url = url,
                             icon_url = icon_url,
                             preview_url = preview_url,

                             contents = contents,
                             )

class ActivityObject(AtomItem):
    def from_xml(self, x):
        AtomItem.from_xml(self, x)
        type_uri = x['object-type']
        self.type_uri = unicode(type_uri)
        self.type = constants.Object.get_name(self.type_uri)

class Activity(AtomItem):
    def from_xml(self, x):
        AtomItem.from_xml(self, x)
        updated = unicode(x.updated)
        published = unicode(x.published)
        updated_parsed = feedparser._parse_date(updated)
        published_parsed = feedparser._parse_date(published)

        activity_type = unicode(x.category.attrib.get('label'))

        verb = unicode(getattr(x, '{%s}verb' % constants.NS.ActivityStreams, None))
        object_tags = list(getattr(x, '{%s}object' % constants.NS.ActivityStreams, None))

        objects = []
        for object_tag in object_tags:
            if object_tag is not None:
                object = ActivityObject()
                object.populate(object_tag, InputType.XML)
                objects.append(object)
                source = object.source
            else:
                object = None
                source = None

        # context things

        # TODO: get an example and parse out all the values from a location
        # so we don't pass around lxml objects
        #location = getattr(x, '{%s}location', None)
        mood = getattr(x, '{%s}mood' % constants.NS.ActivityContext, None)
        if mood is None:
            mood_text = mood_icon = None
        else:
            mood_text = unicode(mood)
            mood_icon = unicode(mood.attrib.get('icon'))

        object.mood_text = mood_text
        object.mood_icon = mood_icon

        self.__dict__.update(
                             verb = verb,
                             source = source,
                             objects = [],
                             updated = updated,
                             published = published,
                             updated_parsed = int(calendar.timegm(updated_parsed)) + TIMEZONE_FIX,
                             published_parsed = int(calendar.timegm(published_parsed)) + TIMEZONE_FIX,
                             activity_type = activity_type,
                             )

    @property
    def supports_comments(self):
        return getattr(self, 'comments', None) is not None or self.activity_type == 'StatusMoodUpdate'

class StatusUpdate(CommentableMyspaceObject):
    SPACER_URL = 'http://x.myspacecdn.com/modules/common/static/img/spacer.gif'

    activity_type = 'DigsbyStatusUpdate' # to differentiate it from a StatusUpdate from activities.atom

    def __init__(self, acct):
        CommentableMyspaceObject.__init__(self)
        self.acct = weakref.ref(acct)

    @property
    def author_name(self):
        user = self.acct().user_from_id(self.author_id)
        return getattr(user, 'displayName', getattr(user, 'name', None))

    @property
    def author_uri(self):
        user = self.acct().user_from_id(self.author_id)
        return getattr(user, 'profileUrl', getattr(user, 'webUri', ''))

    @property
    def title(self):
        name = self.author_name
        if name is None:
            name = _(u"Private user")
        return u'%s %s' % (self.author_name.decode('xml'), self.body.decode('xml')) # TODO: strip html

    def from_json(self, js):
        # hooray for utc
        updated = self.updated = self.published = getattr(js, 'moodLastUpdated', getattr(js, 'moodStatusLastUpdated', 0))
        if self.updated == 0:
            self.updated_parsed = self.published_parsed = updated
        else:
            try:
                self.updated_parsed = self.published_parsed = int(updated)
            except (ValueError, TypeError):
                updated_parsed = feedparser._parse_date(updated)
                self.updated_parsed = self.published_parsed = int(calendar.timegm(updated_parsed))

        user = getattr(js, 'user', None)
        if user is None:
            self.author_id = js.userId
        else:
            self.author_id = user.userId

        log.info_s("status json: %r", js)
        self.id = js.statusId
        moodimage_url = getattr(js, 'moodPictureUrl', getattr(js, 'moodimageurl', None))
        if moodimage_url == self.SPACER_URL:
            moodimage_url = None
        #self.icon_url = user.image
        #self.icon_url = moodimage_url
        self.icon_url = None

        self.contents = [(u'xhtml', js.status)]
        self.body = js.status
        self.mood_text = getattr(js, 'moodName', getattr(js, 'mood', None))
        self.mood_icon = moodimage_url
        self._numComments = 0
        try:
            self._numComments = int(getattr(js, 'numComments', None) or getattr(js, '_numComments', None))
        except (AttributeError, ValueError, TypeError):
            self._numComments = None

        self.comments = map(MyspaceComment.from_json, js.get('comments', []))

    @property
    def numComments(self):
        if self.commentsRetrievedDate:
            self._numComments = len(self.get_comments())

        return self._numComments

    @property
    def supports_comments(self):
        return True

class MyspaceComment(MyspaceObject):
    LIKE = _(u'Like! (via http://lnk.ms/C5dls)')
    DISLIKE = _(u'Dislike! (via http://lnk.ms/C5dls)')

    def __init__(self, data):
        self.userid = data.author.id
        self.text = data.body
        self.commentId = data.commentId
        if getattr(data, 'postedDate', None) is not None:
            self.postedDate = data.postedDate
            self.postedDate_parsed = int(calendar.timegm(feedparser._parse_date(self.postedDate)))
        else:
            self.postedDate_parsed = data.postedDate_parsed

        try:
            int(self.userid)
        except ValueError:
            pass
        else:
            self.userid = 'myspace.com.person.%s' % self.userid

    @property
    def is_like(self):
        return self.text == self.LIKE

    @property
    def is_dislike(self):
        return self.text == self.DISLIKE

    @classmethod
    def from_json(self, js):
        if isinstance(js, MyspaceComment):
            return js
        return MyspaceComment(util.Storage(
                                   author = util.Storage(id = js.get('userid')),
                                   body = js['text'],
                                   commentId = js['commentId'],
                                   postedDate = js.get('postedDate', None),
                                   postedDate_parsed = js.get('postedDate_parsed', None)
                              ))
