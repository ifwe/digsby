import hashlib

import util
import util.xml_tag
import msn
from logging import getLogger

log = getLogger('msn.object')

class MSNObject(object):
    '''
    MSNObject

    An abstract representation of an 'MSN object' which can refer to a
    wink, nudge, display picture, file transfer, scribble, sound clip,
    or some other stuff.
    '''
    __slots__ = '''creator size type location friendly sha1d sha1c
                _friendly _sha1d _sha1c stamp _stamp contenttype contentid avatarid
                avatarcontentid _avatarcontentid _xml _extra'''.split()

    EUF = "{A4268EEC-FEC5-49E5-95C3-F126696BDBF6}"

    types = {
             '2' : 'emoticons',
             '3' : 'icon',
             '5' : 'bg_image',
             '8' : 'wink',
             '11': 'sound',
             '12': 'state',
             }
    def __init__(self, Creator, Type, Location, Size, SHA1D, Friendly=u'\0', SHA1C=None,
                 contenttype=None, contentid=None, stamp=None, avatarid=None, avatarcontentid=None, **kwds):
        '''
        MSNObject(dict)

        Build an msn object from a dictionary. the good keys are:
            creator
            size
            type
            location
            friendly
            sha1d
            sha1c

        Generally, the required fields are creator, size, type, location,
        and sha1d. Or, create an empty MSNObject (no args) and call from_xml()
        on it
        '''
        object.__init__(self)
        self.creator = Creator
        self.type = Type
        self.size = Size
        self.location = Location
        self._sha1d = SHA1D
        self._friendly = Friendly
        self._sha1c = SHA1C or self.calc_sha1c()
        self._stamp = stamp
        self._avatarcontentid = avatarcontentid
        self.contenttype = contenttype
        self.contentid = contentid
        self.avatarid = avatarid
        self._xml = None
        self._extra = kwds

    def get_sha1d(self):
        return self._sha1d.encode('base-64').strip()

    def set_sha1d(self, new_val):
        self._sha1d = new_val.replace(' ', '+').decode('base-64')

    def get_friendly(self):
        return self._friendly.encode('utf-16-le').encode('base-64').strip()

    def set_friendly(self, new_val):
        self._friendly = new_val.decode('base-64').decode('utf-16-le')

    def calc_sha1c(self):
        to_hash = 'Creator%sSize%sType%sLocation%sFriendly%sSHA1D%s' % \
        (self.creator, self.size, self.type, self.location, self.friendly, self.sha1d)
        return hashlib.sha1(to_hash).digest()

    def get_sha1c(self):
        return self.calc_sha1c().encode('base-64').strip()

    def set_sha1c(self, new_val):
        if new_val != self.sha1c:
            raise ValueError, 'SHA1C hash is not correct'

    def get_stamp(self):
        return self._stamp if self._stamp is None else self._stamp.encode('base-64').strip()

    def set_stamp(self, new_val):
        if new_val is None:
            self._stamp = None
        else:
            self._stamp = new_val.decode('base-64')

    def get_avatarcontentid(self):
        return self._avatarcontentid \
                if self._avatarcontentid is None \
                else msn.util.base64_encode(self._avatarcontentid)

    def set_avatarcontentid(self, new_val):
        if new_val is None:
            self._avatarcontentid = None
        else:
            self._avatarcontentid = msn.util.base64_decode(new_val)


    friendly = property(get_friendly, set_friendly)
    sha1d = property(get_sha1d, set_sha1d)
    sha1c = property(get_sha1c, set_sha1c)
    stamp = property(get_stamp, set_stamp)
    avatarcontentid = property(get_avatarcontentid, set_avatarcontentid)

    def to_xml(self):
        #for attr in 'stamp avatarcontentid contenttype contentid avatarid'.split():
        #    val = getattr(self, attr)
        #    if val is not None:
        #        attrs[attr] = val

        if self._xml is None:

            # stupid libpurple doesnt know how to do XML.
            # so we have to put the attrs in the right order,
            # and we replace the " />" at the end with "/>".
            # note the missing space.

            t = util.xml_tag.tag('msnobj')
            t._attrs = util.odict()
            t._attrs['Creator'] = self.creator
            t._attrs['Size'] = self.size
            t._attrs['Type'] = self.type
            t._attrs['Location'] = self.location
            t._attrs['Friendly'] = self.friendly
            t._attrs['SHA1D'] = self.sha1d
            t._attrs['SHA1C'] = self.sha1c

            xml = t._to_xml(pretty=False).strip()
            xml = xml[:-3] + '/>'
            self._xml = xml

        return self._xml

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        try:
            for attr in ('creator', 'size', 'sha1d',):
                mine = getattr(self, attr)
                theirs = getattr(other, attr)
                if str(getattr(self, attr)) != str(getattr(other, attr)):
                    return False
        except AttributeError, e:
            return False
        else:
            return True

    def __repr__(self):
        try:
            return self.to_xml()
        except:
            return object.__repr__(self)

    @classmethod
    def parse(cls, xml):
        '''
        Build an MSNObject from an xml snippet that looks something like this:

        <msnobj Creator="x2ndshadow@hotmail.com" Size="5060" Type="3"
        Location="TFR2C.tmp" Friendly="AAA="SHA1D="i1MDZNjmU8UK6bQPBRhRQAkWMpI="
        SHA1C="5dVK3MdIIywHPlRKqrtOdZz/Vcw=" />
        '''
        t = util.xml_tag.tag(xml)

        o = cls(**t._attrs)
        o.stamp = t._attrs.get('stamp', None)
        o.avatarcontentid = t._attrs.get('avatarcontentid', None)
        o.friendly, o.sha1d = [t[k] for k in ['Friendly', 'SHA1D']]
        try:
            o.sha1c = t['SHA1C']
        except:
            o.sha1c = o.sha1c
        o._xml = xml
        return o
