'''
Python types for various models from LinkedIn's API.

Primitive properties are defined with etree_attrs and py_attrs. etree_attrs are key-paths into the XML document, and
py_attrs are the destination attribute on the python object.

Most types also have a 'content_body' method which returns the appropriate text for the infobox.

Various other methods are also provided for necessary functionality on appropriate objects.
'''
import logging

import util
import util.primitives.error_handling as EH

import lxml.etree as etree
import common

import operator
import traceback

log = logging.getLogger("linkedin.objects")

PRIVATE = "private"
class PrivacyException(Exception):
    pass

def _populate(cls, attrgetters, o):
    vals = {}

    pyattrs = cls.py_attrs
    etattrs = cls.etree_attrs

    for attr, etattr, getter in zip(pyattrs, etattrs, attrgetters):
        k = attr
        try:
            child = getter(o)
        except AttributeError:
            v = None
        else:
            if getattr(child, 'pyval', None) is None:
                v = child
            else:
                v = child.pyval

        vals[k] = v

    try:
        return cls(**vals)
    except Exception, e:
        log.error("Error populating %r: %r: %r", cls.__name__, e, etree.tostring(o, pretty_print = True))


class LinkedInObject(object):
    etree_attrs = ()
    py_attrs = ()

    def __init__(self, **kw):
        self.__dict__.update(kw)

    @classmethod
    def get_attr_getters(cls):
        ags = None
        if ags is None:
            ags = cls.etree_attrgetters = map(operator.attrgetter, cls.etree_attrs)

        return ags

    @classmethod
    def from_etree(cls, o):
        attrgetters = cls.get_attr_getters()
        x = _populate(cls, attrgetters, o)
        if x is not None:
            x.orig = o

        return x

class LinkedInFriend(LinkedInObject):
    etree_attrs = ('id',
                   'first-name',
                   'last-name',
                   'headline',
                   'location.name',
                   'location.country.code',
                   'industry',
                   'site-standard-profile-request.url',
                   'picture-url',
                   'current-status',
                   )

    py_attrs = ('id',
                'first_name',
                'last_name',
                'headline',
                'location_name',
                'location_country',
                'industry',
                'profile_url',
                'picture_url',
                'status',
                )

    def __init__(self, **k):
        LinkedInObject.__init__(self, **k)
        if self.id == PRIVATE:
            raise PrivacyException()
        self.status = unicode(self.status)

    @property
    def name(self):
        if self.first_name and self.last_name:
            return u"%s %s" % (self.first_name, self.last_name)

        if bool(self.first_name) ^ bool(self.last_name):
            return self.first_name or self.last_name

        return u"Unknown User"

    def __repr__(self):
        return '<%s id=%r name=%r>' % (type(self).__name__,
                                       getattr(self, 'id', None),
                                       self.name)


class LinkedInGroup(LinkedInObject):
    etree_attrs = LinkedInObject.etree_attrs + (
        'id',
        'name',
        'site-group-request.url',
    )

    py_attrs = LinkedInObject.py_attrs + (
        'id',
        'name',
        'url',
    )

class LinkedInComment(LinkedInObject):
    #LIKE = _(u'Like! (via <a href="http://digsby.com/lil">Digsby</a>)')
    #DISLIKE = _(u'Dislike! (via <a href="http://digsby.com/lidl">Digsby</a>)')
    LIKE = _(u'Like! (via http://digsby.com)')
    DISLIKE = _(u'Dislike! (via http://digsby.com)')

    etree_attrs = (
        'sequence-number',
        'comment',
        'person',
    )

    py_attrs = (
        'sequence_number',
        'text',
        'person',
    )

    def __init__(self, **kw):
        LinkedInObject.__init__(self, **kw)
        if not isinstance(self.person, LinkedInObject):
            self.person = LinkedInFriend.from_etree(self.person)

        if self.person is None:
            raise PrivacyException()

    @property
    def is_like(self):
        return self.text == self.LIKE and common.pref('linkedin.like_enabled', type = bool, default = True)

    @property
    def is_dislike(self):
        return self.text == self.DISLIKE and common.pref('linkedin.dislike_enabled', type = bool, default = True)

    @property
    def userid(self):
        return self.person.id

class LinkedInNetworkUpdate(LinkedInObject):
    _subclasses = {}
    etree_attrs = (
        'timestamp',
        'update-type',
        'update-key',
        'update-content.person',
        'is-commentable',
        'update-comments',
    )
    py_attrs = (
        'timestamp',
        'type',
        'update_key',
        'person',
        'supports_comments',
        'comments',
    )

    def __init__(self, **kw):
        LinkedInObject.__init__(self, **kw)
        self.timestamp /= 1000

        self.person = LinkedInFriend.from_etree(self.person)
        if self.person is None:
            raise PrivacyException()
        self.load_comments(self.comments)

    def load_comments(self, comments_element):
        if comments_element is not None:
            try:
                self.num_comments = int(comments_element.attrib["total"])
            except Exception, e:
                self.num_comments = 0

        comment_list = getattr(comments_element, 'update-comment', [])

        comments = []
        for c in comment_list:
            try:
                comment = LinkedInComment.from_etree(c)
            except Exception, e:
                import traceback; traceback.print_exc()
            else:
                if comment is not None:
                    comments.append(comment)

        self.comments = comments

    @classmethod
    def from_etree(cls, o):
        cls = cls._subclasses.get(getattr(o, 'update-type').pyval, cls)
        attrgetters = cls.get_attr_getters()

        x = _populate(cls, attrgetters, o)
        if x is not None:
            x.orig = o

        return x

    @property
    def id(self):
        update_key = getattr(self, 'update_key', None)
        if update_key is not None:
            return update_key

        return "%s-%s-%s" % (self.type, self.timestamp, self.person.id)

    @classmethod
    def register_update_type(cls, name):
        def wrapper(c):
            cls._subclasses[name] = c
            return c
        return wrapper

    def user_likes(self, userid):
        if not self.comments:
            return False

        for comment in self.comments:
            if comment.is_like and comment.userid == userid:
                return True

        return False

    def user_dislikes(self, userid):
        if not self.comments:
            return False

        for comment in self.comments:
            if comment.is_dislike and comment.userid == userid:
                return True

        return False

    def get_likers(self):
        return [x.userid for x in self.comments if x.is_like]

    def get_dislikers(self):
        return [x.userid for x in self.comments if x.is_dislike]

    def get_comments(self):
        return [x for x in self.comments if not (x.is_like or x.is_dislike)]

@LinkedInNetworkUpdate.register_update_type('ANSW')
class LINU_Answ(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.question.answers.answer.id',
        'update-content.question.answers.answer.web-url',
        'update-content.question.answers.answer.author',
        'update-content.question.title',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'answer_id',
        'url',
        'person',
        'question_title',
    )

    def content_body(self):
        return _(u"answered the question \"%s\"") % self.question_title

class LINU_App(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.person.person-activities.activity.body',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'body',
    )

@LinkedInNetworkUpdate.register_update_type('APPS')
@LinkedInNetworkUpdate.register_update_type('APPM')
class LINU_Appm(LINU_App):
    def content_body(self):
        return util.strip_html(self.body.decode('fuzzy utf8'))

@LinkedInNetworkUpdate.register_update_type('CONN')
class LINU_Conn(LinkedInNetworkUpdate):
    '''
    A new connection was added to friend_id
    '''

    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.person.connections.person',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'connection_list',
    )

    def __init__(self, **kw):
        LinkedInNetworkUpdate.__init__(self, **kw)
        #cs = getattr(self, 'connection_list', [])
        if len(self.connection_list) != 0:
            people = self.connection_list
        else:
            people = []

        connections = []
        for person in people:
            try:
                new_friend = LinkedInFriend.from_etree(person)
            except PrivacyException:
                pass
            except Exception, e:
                traceback.print_exc()
            else:
                if new_friend is not None:
                    connections.append(new_friend)

        self.connection_list = connections

        if len(self.connection_list) == 0:
            raise PrivacyException()

    def content_body(self):
        names = ''
        if len(self.connection_list) > 2:
            names += ', '.join(conn.name for conn in self.connection_list[:-2])

        if len(self.connection_list) >= 2:
            names += _(u'%s and ') % self.connection_list[-2].name

        names += self.connection_list[-1].name

        return _(u"is now connected to %s") % (names,)

@LinkedInNetworkUpdate.register_update_type('NCON')
class LINU_Ncon(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
    )

    def content_body(self):
        return _("is now a connection")

@LinkedInNetworkUpdate.register_update_type('CCEM')
class LINU_Ccem(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
    )

    def __init__(self, **kw):
        LinkedInNetworkUpdate.__init__(self, **kw)

    def content_body(self):
        return _(u"joined LinkedIn")

@LinkedInNetworkUpdate.register_update_type('JOBS')
class LINU_Jobs(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
    )

@LinkedInNetworkUpdate.register_update_type('JOBP')
class LINU_Jobp(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.job.position.title',
        'update-content.job.company.name',
        'update-content.job.site-job-request.url',
        'update-content.job.job-poster.id',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'position_title',
        'company_name',
        'url',
        'friend_id',
    )

    def content_body(self):
        return _(u"posted a job: {position_title:s} at {company_name:s}").format(
                 position_title=self.position_title, company_name=self.company_name)

@LinkedInNetworkUpdate.register_update_type('JGRP')
class LINU_Jgrp(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.person.member-groups.member-group',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'group_list',
    )

    def __init__(self, **kw):
        LinkedInNetworkUpdate.__init__(self, **kw)
        self.group_list = filter(None, [LinkedInGroup.from_etree(x) for x in self.group_list])

    def content_body(self):
        names = ''
        if len(self.group_list) > 2:
            names += ', '.join(group.name for group in self.group_list[:-2])

        if len(self.group_list) >= 2:
            names += _(u'%s and ') % self.group_list[-2].name

        names += self.group_list[-1].name

        return _(u"is now a member of %s") % (names,)


@LinkedInNetworkUpdate.register_update_type('PICT')
class LINU_Pict(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
    )

@LinkedInNetworkUpdate.register_update_type('PICU')
class LINU_Picu(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
    )

    def content_body(self):
        return _(u'has a new profile photo')

@LinkedInNetworkUpdate.register_update_type('RECU')
class LINU_Recu(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
    )


@LinkedInNetworkUpdate.register_update_type('PREC')
@LinkedInNetworkUpdate.register_update_type('SVPR')
class LINU_Prec(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.person.recommendations-given.recommendation.recommendee',
        'update-content.person.recommendations-given.recommendation.web-url',
        'update-content.person.recommendations-received.recommendation.recommender',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'recommended',
        'url',
        'recommender',
        #'recommender_url',
    )

    def __init__(self, **k):
        LinkedInNetworkUpdate.__init__(self, **k)
        if self.recommended is not None:
            self.recommended = LinkedInFriend.from_etree(self.recommended)
        if self.recommender is not None:
            self.recommender = LinkedInFriend.from_etree(self.recommender)

        if (self.recommended, self.recommender) == (None, None):
            raise PrivacyException()

    def content_body(self):
        if self.recommended is not None:
            return _(u"has recommended %s") % self.recommended.name
        else:
            return _(u"was recommended by %s") % self.recommender.name

@LinkedInNetworkUpdate.register_update_type('PROF')
@LinkedInNetworkUpdate.register_update_type('PRFU')
class LINU_Prfu(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
    )

    def content_body(self):
        return _(u'has an updated profile')

@LinkedInNetworkUpdate.register_update_type('QSTN')
class LINU_Qstn(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.question.author',
        'update-content.question.title',
        'update-content.question.web-url',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'author',
        'title',
        'url',
    )

    def __init__(self, **k):
        LinkedInNetworkUpdate.__init__(self, **k)
        self.author = LinkedInFriend.from_etree(self.author)

        if self.author is None:
            raise PrivacyException()

    def content_body(self):
        return _(u"asked a question: %s") % self.title

@LinkedInNetworkUpdate.register_update_type('STAT')
class LINU_Stat(LinkedInNetworkUpdate):
    etree_attrs = LinkedInNetworkUpdate.etree_attrs + (
        'update-content.person.current-status',
    )

    py_attrs = LinkedInNetworkUpdate.py_attrs + (
        'status',
    )

    def __init__(self, **k):
        LinkedInNetworkUpdate.__init__(self, **k)
        self.status = unicode(self.status)

    def content_body(self):
        return self.status


# Other Types:
# (* = observed)
#answ
#apps  *
#appm  *
#conn  *
#ncon
#ccem
#jobs
#jobp
#jgrp  *
#pict
#picu
#recu
#prec  *
#prfu
#prof  *
#qstn  *
#stat  *
