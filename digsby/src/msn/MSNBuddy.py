import common
import contacts
import util.threads as threads
from util import Storage, to_storage, dyn_dispatch, odict, threaded
from util.primitives.funcs import get
from util.xml_tag import tag
from util.cacheable import urlcacheopen, cproperty
from util.observe import ObservableProperty
from common.sms import validate_sms, normalize_sms
from util.callbacks import callsback
from MSNUtil import url_decode
import time, datetime
import logging
log = logging.getLogger('msn.buddy')

yesterday = lambda: datetime.datetime.today() - datetime.timedelta(1)

import sys; thismod = sys.modules[__name__]; del sys
try:
    _
except:
    _ = lambda s:s


statuses=Storage(
    brb=_('Be Right Back'),
    phone=_('On the Phone'),
    lunch=_('Out to Lunch')
)

class MSNBuddy(common.buddy):
    '''
    MSNBuddy class, inherits from Buddy

    An abstract representation of an MSNBuddy
    '''

    __slots__ = \
    """
    status_message
    msn_obj
    _idle_start
    pending_auth
    phone_home
    phone_work
    phone_mobile
    allow_mobile
    enable_wireless
    remote_alias
    has_blog
    client_id
    role_ids
    get_profile
    _space
    membersoap
    contactsoap
    """.split()

    def __init__(self, msn, name=None):
        '''
        MSNBuddy(msn, name=None)

        Create a new MSNBuddy object with an MSN 'owner' object and
        (optionally) a name. MSNBuddies default to not blocked, offline,
        not mobile, and idle since the start of the UNIX epoch.

        @param msn:
        @param name:
        '''
        self._status = 'unknown'
        self._status_message = ''
        self._got_presence = False

        self.phone_home       = \
        self.phone_work       = \
        self.phone_mobile     = \
        self.allow_mobile     = \
        self.enable_wireless  = \
        self.remote_alias     = \
        self.has_blog         = None

        self.msn_obj = None
        self._idle_start = 0
        self.info = {}
        self.role_ids = {}
        self.pending_auth = False

        fixedname = ''.join(url_decode(name).split())
        common.buddy.__init__(self, fixedname, msn)

        if self is self.protocol.self_buddy:
            from common import profile
            profile.account_manager.buddywatcher.unregister(self)

        #assert is_email(fixedname), fixedname
        self.CID = 0

        self.space = None
        if self._space:
            try:
                self.update_contact_card(tag(self._space))
            except:
                self._space = None

        self.mships = {}
        self.contactsoap = None
        self.membersoap = None

        self._btype = 1

        #self.get_profile()

    @property
    def supports_group_chat(self):
        import msn.AddressBook as MSNAB
        return (self.protocol.supports_group_chat and
                self._btype in (MSNAB.ClientType.PassportMember,
                                MSNAB.ClientType.ChatMember,
                                MSNAB.ClientType.CircleMember,))

    @property
    def type(self):
        return self._btype

    def __hash__(self):
        # TODO: figure out why this is necessary.
        return common.buddy.__hash__(self)

    def _get_status_code(self):
        import MSN
        return MSN.MSNClient.status_to_code.get(self.status, 'AWY')

    def _set_status_code(self, val):
        import MSN
        self.status = MSN.MSNClient.code_to_status.get(val, 'away')

    status_code = property(_get_status_code, _set_status_code)

    @property
    def sms(self):
        if validate_sms(self.phone_mobile):
            return self.phone_mobile
        else:
            return False

    def _get_phone_mobile(self):
        return getattr(self, '_phone_mobile', None)
    def _set_phone_mobile(self, val):
        if val and val.startswith('tel:'):
            val = val[4:]
        self._phone_mobile = val

    phone_mobile = property(_get_phone_mobile, _set_phone_mobile)

    @property
    def id(self):

        if self.contactsoap is not None:
            v = self.contactsoap.ContactId
            if v: return v

        return self.guid or self.name

    def _get_guid(self):
        return getattr(self, '_guid', None)
    def _set_guid(self, val):
        if not (val is None or isinstance(val, self.protocol.ns.cid_class)):
            raise TypeError("Was expecting type %r for guid, got %r (type=%r)", self.protocol.ns.cid_class, val, type(val))

        self._guid = val
    guid = property(_get_guid, _set_guid, doc =
                    'Contact ID, which takes the form of a UUID in modern versions of MSNP.'
                    'In the past, it was simply the passport name of the contact.'
                    )

    def get_caps(self):
        "Returns this buddy's capabilities."
        from common import caps

        # otherwise fall back to the protocol
        buddy_caps = set(self.protocol.caps)

        # remove "files" if offline
        if not self.online:
            buddy_caps.discard(caps.FILES)

        return buddy_caps

    caps = property(get_caps)

    def _set_contactsoap(self, val):

        self._contactsoap = val

        if self.contactsoap is not None:
            phs = self.contactsoap.ContactInfo.Phones
            if phs is not None and phs.ContactPhone is not None:
                for phone in phs.ContactPhone:
                    if phone.ContactPhoneType == 'ContactPhoneMobile':
                        try:
                            num = normalize_sms(phone.Number)
                        except:
                            continue
                        else:
                            if not validate_sms(num):
                                continue

                        self.phone_mobile = num

    def _get_contactsoap(self):
        return self._contactsoap

    contactsoap = property(_get_contactsoap, _set_contactsoap)

    @property
    def online(self):
        '''
        get_online()

        returns True if this buddy is not offline
        '''
        # XXX: comment these two lines below to have mobile count as "offline"
        if self.mobile:
            return True

        return self._got_presence and self._status not in ('offline', 'unknown')

    def set_status(self, newval):
        oldstatus, self._status = self._status, newval
        if oldstatus != newval and self._got_presence:
            self.notify('status', oldstatus, newval)

    def get_status(self):
        if not self._got_presence:
            return 'unknown'

        if self._status == 'idle':
            return 'idle'
        if self.away:
            return 'away'

        # XXX: comment these two lines below to have mobile count as "offline"
        if self.mobile:
            return 'mobile'

        return self._status

    status = ObservableProperty(get_status, set_status, observe=('_status',))

    @property
    def profile(self):
        return None

    @property
    def away(self):
        return self._status in ['busy', 'brb', 'away', 'phone', 'lunch',]

    @property
    def blocked(self):
        return self in self.protocol.block_list

    def _set_status_message(self, val):
        self._got_presence = True
        self._status_message = val

    def _get_status_message(self):
        return self._status_message

    status_message = property(_get_status_message, _set_status_message)

    @property
    def mobile(self):
        return (self.sms and (self.allow_mobile == 'Y')) and self._status == 'offline'

    @common.action(lambda self: True)
    def get_profile(self):
        #self.update_contact_card(tag(CONTACT_CARD))
        self.protocol.get_profile(self)

    @property
    def sightly_status(self):

        if self.status == 'mobile':
            return _('Mobile')
        else:
            return statuses.get(self._status,self._status.title())

    @callsback
    def block(self, _block=True, callback = None):
        self.protocol.block_buddy(self, _block, callback = callback)

    @callsback
    def unblock(self, callback = None):
        self.protocol.block_buddy(self, False, callback = callback)

    @property
    def service(self):

        num_or_str = get(self, '_btype', 1)
        num = get(dict(msn=1,mob=4,fed=32), num_or_str, num_or_str)

        if num == 32 and self.name.endswith('yahoo.com'):
            prot_name = 'yahoo'
        else:
            prot_name = self.protocol.name

        return prot_name

    def __repr__(self):
        '''
        A string representation of this buddy
        '''
        return "<%s %s>" % (type(self).__name__, self.name)

    def __str__(self):
        '''
        How this buddy should be printed or otherwise turned into a string
        '''
        return repr(self)
#
#    def __setattr__(self, field, val):
#        '''
#        buddy.field = val
#        setattr(buddy, field, val)
#
#        set a member of this buddy. If status is not idle, the _idle_start time
#        will be set to now.
#
#        @param field:    the field to set. must be a __slot__ of MSNBuddy or Buddy
#        @param val:      the val to set it to.
#        '''
#        common.buddy.__setattr__(self, field, val)
#        if hasattr(self, 'status') and self.status != 'online':
#            common.buddy.__setattr__(self, '_idle_start', int(time.time() - 60))
#        else:
#            common.buddy.__setattr__(self, '_idle_start', False)

    def get_idle(self):
        'returns whether or not this buddy is idle.'

        return self.status == 'idle'

    def set_idle(self, val):
        pass

    idle = ObservableProperty(get_idle, set_idle, observe=('status',))

    def update(self, new):
        '''
        update(new)

        update this buddy from another buddy. Not really needed any more, but
        still around

        @param new:    the buddy to get the new information from
        '''
        if not new: return

        for field in new.__dict__:
            newval = getattr(new, field)
            if newval:
                setattr(self, field, newval)
                self.setnotifyif()

    def update_contact_card(self, card):
        if not card: return
        self._space = card._to_xml(pretty=False)#.replace('&', '&amp;')
        self.space = MSNSpace(self, card)
#        self.space.displayName = card._attrs.get('displayName', self.alias)
#        self.space.displayPictureUrl = card._attrs.get('displayPictureUrl','')
#
#        for elt in card.elements:
#            self._update_ccard_elt(elt, elt['type'])

    def _update_ccard_elt(self, elt, kind):
        return dyn_dispatch(self, '_update_ccard_%s' % kind.lower(), elt)

    def _update_ccard_spacetitle(self, elt):
        self.space.update((e._name, e._cdata) for e in elt if 'type' not in e._attrs)

    def _update_ccard_album(self, elt):
        photos = []
        for subel in elt:
            if subel._attrs.get('type', '') == 'Photo':
                photos.append(Storage((e._name, e._cdata) for e in subel))

        album = self.space.setdefault('album',Storage())
        album.update((e._name, e._cdata) for e in elt if 'type' not in e._attrs)
        album.photos = photos

    _space = cproperty('')

    def _update_ccard_musiclist(self, elt):
        musiclist = self.space.setdefault('musiclist', Storage())
        songs = []

        for song in elt:
            if song._attrs.get('type', '') == 'MusicListEntry':
                songs.append(Storage((e._name, e._cdata) for e in song))

        musiclist.update((e._name, e._cdata) for e in elt if 'type' not in e._attrs)
        musiclist.songs = songs

    def _update_ccard_booklist(self, elt):
        booklist = self.space.setdefault('booklist',Storage())
        books = []

        for book in elt:
            if book._attrs.get('type','') == 'BookListEntry':
                books.append(Storage((e._name, e._cdata) for e in book))

        booklist.update((e._name, e._cdata) for e in elt if 'type' not in e._attrs)
        booklist.books = books

    def _update_ccard_genericlist(self, elt):
        gen_lists = self.space.setdefault('gen_lists', [])

        entries = []
        for entry in elt:
            if entry._attrs.get('type','') == 'GenericListEntry':
                entries.append(Storage((e._name, e._cdata) for e in entry))

        new_list = Storage((e._name, e._cdata) for e in elt if 'type' not in e._attrs)
        new_list.entries = entries
        gen_lists.append(new_list)

    def _update_ccard_blog(self, elt):
        blog = self.space.setdefault('blog',Storage())

        posts = []

        for post in elt:
            if post._attrs.get('type','') == 'Post':
                posts.append(Storage((e._name, e._cdata) for e in post))

        blog.update((e._name, e._cdata) for e in elt if 'type' not in e._attrs)
        blog.posts = posts

    def _update_ccard_profile(self, elt):
        profiles = self.space.setdefault('profiles',Storage())

        for profile in elt:
            p_type = profile._attrs.get('type','')
            if p_type.endswith('Profile'):
                prof = profiles.setdefault(p_type.lower()[:-7], Storage())
                prof.update((e._name, e._cdata) for e in profile)

        profiles.update((e._name, e._cdata) for e in elt if 'type' not in e._attrs)

    def _update_ccard_livecontact(self, elt):
#        print elt._to_xml()
        pass

    def __cmp__(self, other):
        try:
            if other is self:
                return 0

            return cmp((self.name, self.protocol), (other.name, other.protocol))

        except:
            return -1



    @property
    def pretty_profile(self):
#        p = odict()
#
#        if self.space is None:
#            return p
#
#        booklists = []
#
#        for elt in self.space.contents:
#            if isinstance(elt, BookListElt):
#                books = []
#                booklists.append(books)
#                for entry in elt:
#                    pass
#
#
#        return p

        d = {}

        if self.remote_alias and self.alias != self.remote_alias:
            d[_('Display Name:')] = self.remote_alias

        if self.space is None: return d
        else:
            p = self.space.pretty_profile

            for key in [validkey for validkey in p.keys() if p[validkey] and filter(None,p[validkey])]:
                i=p.keys().index(key)
                if i!=0:
                    sepkey=''.join('sepb4'+key)
                    p[sepkey]=4
                    p.move(sepkey,i)


            return p

    @property
    def contact(self):
        return self.protocol.ns.contact_list.GetContact(self.name, type = self.type)

class CircleBuddy(MSNBuddy):
    def __init__(self, *a, **k):
        import msn.AddressBook as MSNAB
        MSNBuddy.__init__(self, *a, **k)
        self._Members = []
        self._Pending = []
        self.circle = None
        self.remote_alias = 'TempCircle'
        self.guid = None
        self._got_presence = True
        self.status = 'online'
        self._btype = MSNAB.ClientType.Chat
        self.sem = threads.InvertedSemaphore(0)

    @property
    def nice_name(self):
        return self.remote_alias

    def get_role_names(self, role):
        names = []
        if self.circle is None:
            return names

        return [x.account for x in self.circle.GetContactsForRole(role)]

    def get_state_names(self, state):
        return [x.account for x in self.circle.GetContactsForState(state)]

    @property
    def pretty_profile(self):
        d = odict()

        import msn.AddressBook as MSNAB
        CPMR = MSNAB.CirclePersonalMembershipRole

        members = self.get_role_names(CPMR.Member)
        admins = self.get_role_names(CPMR.Admin)
        assistant_admins = self.get_role_names(CPMR.AssistantAdmin)
        pending = list(set(self.get_role_names(CPMR.StatePendingOutbound) +
                           self._get_invited_names() +
                           self.get_state_names(MSNAB.RelationshipStates.Left) +
                           self.get_state_names(MSNAB.RelationshipStates.WaitingResponse)))

        for name in pending:
            for _list in (members, admins, assistant_admins):
                if name in _list:
                    _list.remove(name)

        names_to_pp = lambda l: [['\n', name] for name in l] + ['\n']

        if admins:
            d[_('Administrators:')] = names_to_pp(admins)
        if assistant_admins:
            d[_('Assistant Administrators:')] = names_to_pp(assistant_admins)
        if members:
            d[_('Members:')] = names_to_pp(members or [_('(none)')])
        if pending:
            d[_('Invited:')] = names_to_pp(pending)

        return d

    def _get_Members(self):
        if True or self.type == 'temp':
            return self._Members
        else:
            return self.circle.MemberNames

    def _set_Members(self, val):
        if True or self.type == 'temp':
            self._Members = val
        else:
            raise AttributeError

    Members = property(_get_Members, _set_Members)

    def _get_Pending(self):
        if True or self.type == 'temp':
            return self._Pending
        else:
            return self.circle.PendingNames

    def _set_Pending(self, val):
        if True or self.type == 'temp':
            self._Pending = val
        else:
            raise AttributeError

    Pending = property(_get_Pending, _set_Pending)

    @classmethod
    def from_msnab(cls, C, protocol):
        B = cls(protocol, C.account)
        B.update_from_msnab(C)
        return B

    def update_from_msnab(self, C):
        import msn.AddressBook as MSNAB
        self.remote_alias = C.NickName
        self.guid = self.protocol.ns.cid_class(C.abid)
        self._btype = MSNAB.ClientType.Circle
        self.circle = C

    @property
    def buddy_names(self):
        if False and self.type != 'temp':
            assert self.circle is not None
            return self.circle.MemberNames

        names = []

        if self.circle is None:
            more_members = []
        else:
            more_members = [c.account for c in self.circle.contactList.contacts.values()]

        for x in self.Members: # + more_members:
            if x in self.Pending:
                continue

            name = x.split(':', 1)[-1]
            if not name.lower().startswith(str(self.guid)) and name not in names:
                names.append(name)

        return names

    def _get_invited_names(self):
        names = []
        for x in self.Pending:
            name = x.split(':', 1)[-1]
            if not name.lower().startswith(str(self.guid)) and name not in names:
                names.append(name)
        return names

class MSNSpaceElement(object):
    def __init__(self, elt):
        object.__init__(self)
        for attr in ('title', 'url','description', 'tooltip'):
            setattr(self, attr, str(getattr(elt, attr, '')).decode('utf-8'))

        self.last_check = yesterday()
        self.last_update = yesterday()

    def __repr__(self):
        res = ['<%s ' % type(self).__name__]
        for attr in ('title', 'url','description', 'tooltip'):
            myval = getattr(self, attr)
            if myval: res.append('%s=%s, ' % (attr.capitalize(), myval))

        res[-1] = res[-1][:-2] + '>'

        return ''.join(res)

    def __iter__(self):
        def attrs():
            for attr in ('title', 'url','description', 'tooltip'):
                val = getattr(self, attr)
                if val:
                    yield (attr, val)

        import itertools
        return itertools.chain(attrs(), iter(self.contents))

    @property
    def pretty_profile(self, p=None):
        p = p or odict()
        #p[(self.title, self.url)] = self.description
        p[self.title+':'] = ['\n',(self.url, self.description)]
        return p

    def to_tag(self):
        table = tag('table')
        tr = tag('tr')

        a = tag('a', href=self.url)
        a._add_child(tag('b', self.title + ':'))

        tr._add_child(a)
        tr._add_child(tag('td',self.description))

        table._add_child(tr)
        return table

class SpaceTitleElt(MSNSpaceElement):
    def to_tag(self):
        a = tag('a', href=self.url)
        a._add_child('b', self.title)
        return a

    @property
    def pretty_profile(self):
        return {}

class GenericListElt(list, MSNSpaceElement):
    def __init__(self, elt):

        MSNSpaceElement.__init__(self, elt)
        list.__init__(self, [getattr(thismod, '%sElt'%subel['type'])(subel)
                             for subel in elt if 'type' in subel._attrs])

#    def __iter__(self):
#        def attrs():
#            for attr in ('title', 'url','description', 'tooltip'):
#                val = getattr(self, attr)
#                if val:
#                    yield (attr, val)
#
#        import itertools
#        return itertools.chain(attrs(), list.__iter__(self))

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, list.__repr__(self))

    def __iter__(self):
        return list.__iter__(self)

    @property
    def pretty_profile(self):
        return odict(MSNSpaceElement.pretty_profile.fget(self).items())

    def to_tag(self):
        p = MSNSpaceElement.to_tag(self)

        for thing in self:
            p._add_child(thing.to_tag())

        return p

class MSNSpace(MSNSpaceElement):
    _name = 'MSN Space'
    def __init__(self, buddy, contact_card):
        MSNSpaceElement.__init__(self, contact_card)
        self.last_update = str(contact_card.lastUpdate)
        self.title = contact_card._attrs.get('displayName', buddy.name).strip().decode('fuzzy utf-8')
        self.buddy = buddy
        self.dp_url = contact_card._attrs.get('displayPictureUrl', '')
        self.contents = []

        for element in contact_card.elements:
            type_ = element['type']
            cls = getattr(thismod, '%sElt'% type_, MSNSpaceElement)
            self.contents.append(cls(element))

    @property
    def pretty_profile(self):
        #p = odict(MSNSpaceElement.pretty_profile.fget(self).items())
        p = odict()
        for thing in self.contents:
            p.update(thing.pretty_profile.items())

        url = self.contents[0].url
        if not url and self.buddy.CID:
            url = ('http://spaces.live.com/Profile.aspx?cid=%s' % self.buddy.CID)
        elif not self.buddy.CID:
            return p

        assert url

        p['Profile URL:'] = ['\n', (url, url)]
        return p

    def to_tag(self):
        p = tag('p')#MSNSpaceElement.to_tag(self)

        for thing in self.contents:
            p._add_child(thing.to_tag())

        return p

class GenericListEntryElt(MSNSpaceElement):
    def __init__(self, elt):
        MSNSpaceElement.__init__(self, elt)
        self.last_update = elt['lastUpdated']
        self.title = str(elt.title).strip().decode('utf-8')

    @property
    def pretty_profile(self):
        return odict({self.title:'\n'})

class MusicListElt(GenericListElt):
    @property
    def pretty_profile(self):
        songlist=[x.pretty_profile for x in self]

        songlist.insert(0,'\n')
        return odict({'Songs:': songlist})

class MusicListEntryElt(GenericListEntryElt):
    def __init__(self, elt):
        GenericListEntryElt.__init__(self, elt)
        self.artist = str(elt.artist).decode('utf-8')
        self.song = str(elt.song).decode('utf-8')

    @property
    def pretty_profile(self):
        return (self.url, _(u'{song:s} by {artist:s}').format(song=self.song, artist=self.artist) +u'\n')


class BookListElt(GenericListElt):
    def to_tag(self):
        p = tag('p')

        p._add_child(tag('a', self.title, href=self.url))

        for thing in self:
            p._add_child(thing.to_tag())

        return p

class BookListEntryElt(GenericListEntryElt):
    def to_tag(self):
        return tag('p', '%s<br />%s' % (self.title, self.description))

class BlogElt(GenericListElt):
    def to_tag(self):
        p = tag('p')

        for thing in self:
            p._add_child(thing.to_tag())

        return p

    @property
    def pretty_profile(self):
        return odict([post.pretty_profile for post in self])

class PostElt(GenericListEntryElt):
    def to_tag(self):
        link = tag('a', self.title, href=self.url)
        return tag('p', 'New post: %s<br />%s' % (link._to_xml(), self.description))

    @property
    def pretty_profile(self):
        return (self.title+':',['\n',(self.url, self.description)])

class AlbumElt(GenericListElt):
    def to_tag(self):
        p = tag('p')
        tr = tag('b', 'Photos Album:')
        for photo in self:
            tr._add_child(photo.to_tag())
        p._add_child(tr)
        return p

    @property
    def pretty_profile(self):
        piclist=[x.pretty_profile for x in self]

        piclist.insert(0,'\n')
        return odict({'Photos:': piclist})

class PhotoElt(GenericListEntryElt):
    WIDTH, HEIGHT = 20,20
    def __init__(self, elt):
        GenericListEntryElt.__init__(self, elt)
        self.thumbnail_url = str(elt.thumbnailUrl)
        self.web_url = str(elt.webReadyUrl)
        self.album_name = str(elt.albumName).decode('utf-8')

        self.img_sm = None
        self.img_lg = None

        self.loadimages()

    def to_tag(self):
        a = tag('a', href=self.url)
        a._add_child(tag('img', src=self.web_url, alt=self.tooltip,
                         width=self.WIDTH, height=self.HEIGHT))
        return a

    @property
    def pretty_profile(self):
        from common import pref
        sz = pref('msn.spaces.photosize',20)

        if self.img_sm is None:
            return (self.url, u'%s - %s' % (self.album_name, self.title+u'\n'))

        return dict(data=self.img_sm, alt=self.tooltip,
                    height=sz, width=sz, href=self.url)

    @threaded
    def loadimages(self):
        try:
            self.img_sm = urlcacheopen(self.thumbnail_url)
        except:
            self.imb_sm = 'javascript'

        if self.img_sm and 'javascript' in self.img_sm:
            self.img_sm = None

        try:
            self.img_lg = urlcacheopen(self.web_url)
        except:
            self.img_lg = 'javascript'

        if self.img_lg and 'javascript' in self.img_lg:
            self.img_lg = None

class MSNContact(contacts.Contact):
    _renderer = 'Contact'
    inherited_actions = [MSNBuddy]

    def __init__(self, buddy, group_obj_or_id):
        group_id = getattr(group_obj_or_id, 'name', group_obj_or_id)

        contacts.Contact.__init__(self, buddy, (buddy.name, group_id))

    def __repr__(self):
        return '<MSN' + contacts.Contact.__repr__(self)[4:]

    @common.action(contacts.Contact._block_pred)
    def block(self, *a,**k):
        return contacts.Contact.block(self, *a, **k)
    @common.action(contacts.Contact._unblock_pred)
    def unblock(self, *a,**k):
        return contacts.Contact.unblock(self, *a, **k)

    @common.action()
    def remove(self):
        if getattr(self.buddy, 'type', None) == 'circle':
            self.protocol.LeaveCircle(self.id)
        else:
            self.protocol.remove_buddy(self.id)

    def is_appearing_offline(self):
        import msn.AddressBook as MSNAB
        return self.buddy.contact.HasList(MSNAB.MSNList.Hidden)

    @common.action(lambda self: None if self.is_appearing_offline() else True)
    def appear_offline(self):
        self.protocol.appear_offline_to(self.buddy)

    @common.action(lambda self: None if (not self.is_appearing_offline()) else True)
    def appear_online(self):
        self.protocol.appear_online_to(self.buddy)

def from_mime(mime_info, email, msn, friendlyname=None):
    '''
    from_mime(mime_info, email, msn, friendlyname=None)
    Update a buddy from a MIME profile packet.

    @param mime_info:    the mime header dictionary
    @param email:        thier email address
    @param msn:          msn to add them to
    @param friendlyname: thier friendlyname, defaults to None
    '''

    b = msn.get_buddy(email)
    if friendlyname:
        b.remote_alias = friendlyname.decode('url').decode('fuzzy utf8') or None
        assert isinstance(b.remote_alias, unicode)
    info = to_storage(mime_info)
    for k, v in info.items():
        k = k.replace(" ", "_").replace("-", "_").lower()
        setattr(b, k, v)

    b.info = dict(info.items())

    return b

def from_lst(msn, N, **kwargs):
    '''
    from_lst(msn, **kwargs)

    create an MSNBuddy from a LST command, which are in the format:
        N=email
        C=guid
        F=friendlyname
        etc.

    @param msn:        the owner of the buddy object
    @param N:          required, because there is no way to update a buddy
                       without an email address.
    @param **kwargs:   more stuff to put in the buddy object.
    '''
    email = N
    kwargs = to_storage(kwargs)
    b = msn.get_buddy(email)
    if 'F' in kwargs:
        b.remote_alias = kwargs['F'].decode('url').decode('fuzzy utf8') or None
    if 'C' in kwargs:
        b.guid = msn.cid_class(kwargs['C'])

    return b


CONTACT_CARD = '''

<contactCard>
  <storageAuthCache>
    1pqFlR36RzjW-X1jmTbKjKRsUpCe4cq9KHls4whqQIXlnjXVMidNbandYSmy0QEqm17M7xLIb2Fvo
  </storageAuthCache>
  <elements returnedMatches="3" displayName="shaps" totalMatches="3" displayPictureUrl="http://shared.live.com/jdIfE-NNCwZHMseiLFdi12c3U3v1VRQA5Wr8zoyj4Q0IBYQYt0pq5GcGiVCgriAz-mQjoThX0wVn7RxL!igd-A/base/3379/Controls/img/ContactControl/WLXLarge_default.gif">
    <element type="SpaceTitle">
      <title>
        Steve's Space
      </title>
      <url>
        http://shaps776.spaces.live.com/?owner=1
      </url>
      <totalNewItems>
        0
      </totalNewItems>
    </element>
    <element type="BookList">
      <subElement type="BookListEntry" lastUpdated="0001-01-01T00:00:00">
        <description>
          stuff for description
        </description>
        <title>
          book title 3
        </title>
        <tooltip>
          Title: book title 3
          Author: author
          Description: stuff for description
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Lists/cns!2DB0770EAE61F13!106?owner=1
        </url>
      </subElement>
      <subElement type="BookListEntry" lastUpdated="0001-01-01T00:00:00">
        <description>
          lkj lkj l
        </description>
        <title>
          book title 2
        </title>
        <tooltip>
          Title: book title 2Author: author 2Description: lkj lkj l
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Lists/cns!2DB0770EAE61F13!106?owner=1
        </url>
      </subElement>
      <title>
        Book List
      </title>
      <url>
        http://shaps776.spaces.live.com/Lists/cns!2DB0770EAE61F13!106?owner=1
      </url>
      <description>
        book title 3
      </description>
      <totalNewItems>
        0
      </totalNewItems>
    </element>
    <element type="Album">
      <subElement type="Photo" lastUpdated="2007-04-17T09:35:32.31-07:00">
        <description>
          Photos
        </description>
        <title>
          10.png
        </title>
        <tooltip>
          January 1710.png
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/photos/cns!2DB0770EAE61F13!138/cns!2DB0770EAE61F13!151?owner=1
        </url>
        <thumbnailUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxszOikmaP3r3dXbFG7ToyO0hMKW-WHHHJ2D9Lmff30X2Jo-2STreLVcNjaEogTUoBTZHMxhbwHv0ZBeHMwOnEdJcPytZWhE0nfg
        </thumbnailUrl>
        <webReadyUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxszOikmaP3r3dlq-_0irNxa_2G2Gzp9ZgHOfSTUGN79t1IYnjSY5DKTXfP4ADxmBKN0Z5m0I7P6TUjGRafqU4NPz05iaCqzwJRA
        </webReadyUrl>
        <albumName>
          January 17
        </albumName>
      </subElement>
      <subElement type="Photo" lastUpdated="2007-04-17T09:35:32.107-07:00">
        <description>
          Photos
        </description>
        <title>
          9.gif
        </title>
        <tooltip>
          January 179.gif
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/photos/cns!2DB0770EAE61F13!138/cns!2DB0770EAE61F13!150?owner=1
        </url>
        <thumbnailUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxswE_zjzklXeXVqyaBoOfjid5rjfn8g0bSHcgQmQ5AoqTuNtwMzT-XNFSFv_IKj8mcZZ-ENJcOYB3XWJYb3U0wC4RSwlFUqeGfw
        </thumbnailUrl>
        <webReadyUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxswE_zjzklXeXVJfE1Gdeox-zkKou9QwXud_dSI32qXsAnPABY4K57fs1bpWbe7JSZdhHJwEQ0psi7lGPBDLpdW0_3sUHaRDjuA
        </webReadyUrl>
        <albumName>
          January 17
        </albumName>
      </subElement>
      <subElement type="Photo" lastUpdated="2007-04-17T09:35:31.967-07:00">
        <description>
          Photos
        </description>
        <title>
          8.gif
        </title>
        <tooltip>
          January 178.gif
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/photos/cns!2DB0770EAE61F13!138/cns!2DB0770EAE61F13!149?owner=1
        </url>
        <thumbnailUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxs1s-Updfv0-X7Rk9c9exySfJ-2PozaK6BKKyP9v8DAcv5xxyZSZ0OK9wirfRd2yWEEX7VzZS2mvvBkUWbtz0VXbLead2Ybs5OA
        </thumbnailUrl>
        <webReadyUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxs1s-Updfv0-XLAU_ZUH4P33y-NaJII-4uupQ0uoxjOCQJwxrL6sA1Xa9X3mdKUNYrj95_CVyrr5QVP7BXWFFyd2avflir6OhOA
        </webReadyUrl>
        <albumName>
          January 17
        </albumName>
      </subElement>
      <subElement type="Photo" lastUpdated="2007-04-17T09:35:08.043-07:00">
        <description>
          Photos
        </description>
        <title>
          7.png
        </title>
        <tooltip>
          January 177.png
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/photos/cns!2DB0770EAE61F13!138/cns!2DB0770EAE61F13!148?owner=1
        </url>
        <thumbnailUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxsyrdesm1gzDOdiW3uJUFNjo3H7f9H4uLtkj7u-akJEORhy2lLsKpM01wmbQvBUA-OEZdfQLdJi-NouMArPt5N0CW4nYHxW51UA
        </thumbnailUrl>
        <webReadyUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxsyrdesm1gzDO9TYtPpGT2JsdnYIUZw7Lo5-yTazqwfIGHa6vu-Ku9OIMA0gLptXjy6IMXfr-CV5cag2FJKcqo_rVuPRT2t_t7w
        </webReadyUrl>
        <albumName>
          January 17
        </albumName>
      </subElement>
      <subElement type="Photo" lastUpdated="2007-04-17T09:35:07.933-07:00">
        <description>
          Photos
        </description>
        <title>
          6.jpg
        </title>
        <tooltip>
          January 176.jpg
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/photos/cns!2DB0770EAE61F13!138/cns!2DB0770EAE61F13!147?owner=1
        </url>
        <thumbnailUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxs-wyD9TggUJ_4XM7tDqJ6CINNBLXvtT4Lfwr7ikxskuBzMQNerpK-oV8CvyWk9BbashoZg1H9afsvyl576NJp4I0FWfrI4hwBw
        </thumbnailUrl>
        <webReadyUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxs-wyD9TggUJ_C3BxBY1m6WsjbKXjpxDULsHHHEg8yAl2WLKDzSqb99OBxXaSetCdU-p8o6ScLb807p2QFAWr4gtH6OvBof2EBg
        </webReadyUrl>
        <albumName>
          January 17
        </albumName>
      </subElement>
      <subElement type="Photo" lastUpdated="2007-04-17T09:35:07.81-07:00">
        <description>
          Photos
        </description>
        <title>
          5.jpg
        </title>
        <tooltip>
          January 175.jpg
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/photos/cns!2DB0770EAE61F13!138/cns!2DB0770EAE61F13!146?owner=1
        </url>
        <thumbnailUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxs49JgAmSpKyqet5yR2Upi4Nn_X5ewL5gr6Tst7QFxHUmmjxQJpMpldLBUCWxs5dXLddQfHtjnSJTjycfX0vvZYvb9vVzlON9OA
        </thumbnailUrl>
        <webReadyUrl>
          http://blufiles.storage.msn.com/x1pPHu2K6HCG6qh_ATHNyPxs49JgAmSpKyq-H9kk6kls9jjKFGLEr9AWb3NdQAxCcI6ta_72H6Ct25Dzjm1lkz7_xgUUuKboUy37TR0hveNy5ZRjhJ1eMUzcw
        </webReadyUrl>
        <albumName>
          January 17
        </albumName>
      </subElement>
      <title>
        Photos:
      </title>
      <url>
        http://shaps776.spaces.live.com/Photos/?owner=1
      </url>
      <totalNewItems>
        0
      </totalNewItems>
    </element>
    <element type="Blog">
      <subElement type="Post" lastUpdated="2007-01-16T13:55:01.013-08:00">
        <description>
          sfljks dflkjsdflkjsdflkjs dflkjsad flks jdaflsa dkjflsadkfjsadlfkj
        </description>
        <title>
          NEWNEWNEW
        </title>
        <tooltip>
          sfljks dflkjsdflkjsdflkjs dflkjsad flks jdaflsa dkjflsadkfjsadlfkj
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Blog/cns!2DB0770EAE61F13!130.entry?owner=1
        </url>
      </subElement>
      <title>
        Blog:
      </title>
      <url>
        http://shaps776.spaces.live.com/?owner=1
      </url>
      <totalNewItems>
        0
      </totalNewItems>
    </element>
    <element type="Profile">
      <subElement type="GeneralProfile" lastUpdated="2007-01-16T09:01:51.533-08:00">
        <description />
        <title>
          General profile info updated
        </title>
        <tooltip>
          This person has recently added or updated General profile information.
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Profile.aspx?cid=205766389534170899&mkt=en-us&action=view
        </url>
      </subElement>
      <subElement type="PublicProfile" lastUpdated="2006-12-21T16:06:47.47-08:00">
        <description />
        <title>
          Public profile info updated
        </title>
        <tooltip>
          This person has recently added or updated Public profile information.
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Profile.aspx?cid=205766389534170899&mkt=en-us&action=view
        </url>
      </subElement>
      <subElement type="SocialProfile" lastUpdated="2006-05-31T09:54:52.59-07:00">
        <description />
        <title>
          Social profile info updated
        </title>
        <tooltip>
          This person has recently added or updated Social profile information.
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Profile.aspx?cid=205766389534170899&mkt=en-us&action=view
        </url>
      </subElement>
      <title>
        Profile
      </title>
      <url>
        http://shaps776.spaces.live.com/Profile.aspx?cid=205766389534170899&mkt=en-us&action=view
      </url>
      <description>
        General profile info updated
      </description>
      <totalNewItems>
        3
      </totalNewItems>
    </element>
    <element type="LiveContact">
      <subElement type="ProfessionalContactProfile" lastUpdated="2006-12-21T16:06:47.47-08:00">
        <description />
        <title>
          Business contact info updated
        </title>
        <tooltip>
          This person has recently added or updated Business contact information.
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Profile.aspx?cid=205766389534170899&mkt=en-us&action=view&mode=activecontacts
        </url>
      </subElement>
      <subElement type="PersonalContactProfile" lastUpdated="2006-12-21T16:06:47.47-08:00">
        <description />
        <title>
          Personal contact info updated
        </title>
        <tooltip>
          This person has recently added or updated Personal contact information.
        </tooltip>
        <url>
          http://shaps776.spaces.live.com/Profile.aspx?cid=205766389534170899&mkt=en-us&action=view&mode=activecontacts
        </url>
      </subElement>
      <title>
        Contact Info
      </title>
      <url>
        http://shaps776.spaces.live.com/Profile.aspx?cid=205766389534170899&mkt=en-us&action=view&mode=activecontacts
      </url>
      <description>
        Business contact info updated
      </description>
      <totalNewItems>
        2
      </totalNewItems>
    </element>
  </elements>
  <lastUpdate>
    2007-04-18T08:20:01.167-07:00
  </lastUpdate>
  <theme>
    <name>
      personalspacegree
    </name>
    <titleBar foreground="333333" fontFace="" background="f4fbf7" />
    <clientArea foreground="444444" backgroundImage="http://shared.live.com/jdIfE-NNCwb0XZTwVBd6PpCWk!2k7FEfmc0OX5OC0rZ-I0WjzyccY5aYuUiTkMo2blaFQRxUooU/personalspacegree/3379/img/green_card_bkgd.gif" fontFace="" background="FFFFFF" />
    <toolbar foreground="333333" fontFace="" background="f4fbf7" />
    <border topLeftImage="http://sc1.sclive.net/11.01.3810.0000/Web/Contacts/images/card_ul.gif" bottomLeftImage="http://sc2.sclive.net/11.01.3810.0000/Web/Contacts/images/card_ll.gif" bottomRightImage="http://sc4.sclive.net/11.01.3810.0000/Web/Contacts/images/card_lr.gif" outline="7F7F7F" topRightImage="http://sc3.sclive.net/11.01.3810.0000/Web/Contacts/images/card_ur.gif" />
  </theme>
  <liveTheme>
    <themeName>
      personalspacegree
    </themeName>
    <head backgroundImage="http://shared.live.com/jdIfE-NNCwb0XZTwVBd6PpCWk!2k7FEfmc0OX5OC0rZ-I0WjzyccY5aYuUiTkMo2blaFQRxUooU/personalspacegree/3379/img/SmallBannerImage.jpg" textColor="333333" linkColor="006629" backgroundColor="f4fbf7" />
    <body accordionHoverColor="aad2ba" secondaryLinkColor="7F7F7F" dividerColor="8ed4ab" backgroundImage="" backgroundColor="f4fbf7" linkColor="006629" textColor="333333" />
    <actions linkColor="333333" backgroundColor="f4fbf7" />
  </liveTheme>
</contactCard>
'''.strip().replace('&', '&amp;')

if __name__ == '__main__':

    b = Storage(name='shaps776@hotmail.com')
    card = MSNSpace(b, tag(CONTACT_CARD))
    print card.to_tag()._to_xml()
