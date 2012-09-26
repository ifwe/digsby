'Yahoo buddylist objects.'

from logging import getLogger; log = getLogger('yahoo.buddy'); info = log.info
from common.actions import action
from contacts import Contact
from util.observe import ObservableProperty as oproperty
from operator import attrgetter
from util.cacheable import cproperty
from util import odict, is_email
from util.primitives.funcs import do
from util.callbacks import callsback
from time import time
import common
from . import yahooprofile

__all__ = ['YahooBuddy, YahooContact']
objget = object.__getattribute__

class YahooBuddy(common.buddy):
    'A Yahoo! Messenger buddy.'

    __slots__ = ['location',
                 'status_message',
                 'pending_auth',
                 'blocked',           # appear permanently offline to this contact
                 'stealth_perm',
                 'stealth_session',
                 'idle',
                 'contact_info',
                 '_service']

    def __init__(self, name, protocol):
        # Yahoo buddy names are case insensitive.
        self._nice_name = name
        name = name.lower()

        self.status  = 'unknown'
        self.status_message = ''
        self.idle = None
        self._service = 'yahoo'
        common.buddy.__init__(self, name, protocol)
        self.icon_hash = None #force yahoo buddies to find out what the current checksum is

        do(setattr(self, slot, None) for slot in YahooBuddy.__slots__)
        self._service = 'yahoo'
        self.contact_info = {}

        self.stealth_perm    = False
        self.stealth_session = True

    nice_name = property(lambda self: self._nice_name)

    y360hash    = cproperty(None)
    y360updates = cproperty([])

    @property
    def service(self):
        return self._service

    def set_remote_alias(self, alias):
        return #this definitely doesn't work right yet.
        self.protocol.set_remote_alias(self, alias)

    def get_remote_alias(self):
        info = self.contact_info

        if info:
            nick = info._attrs.get('nname', info._attrs.get('nn', None))
            # Return a nickname if there is one.
            if nick:
                return nick
            else:
                # Otherwise return their name, if it is specified.
                name = u' '.join([info._attrs.get('fn', ''), info._attrs.get('ln', '')])
                if name.strip(): return name

    def update_cinfo(self, ab):
        if ab['request-status'] == 'OK':
            log.info('address book result: OK')

            from pprint import pprint
            pprint(ab._to_xml())

            log.info('replacing contact info')
            if ab.ct:
                self.contact_info = ab.ct
            else:
                log.warning("address book didn't have a CT tag!")

            self.notify()
        else:
            log.warning('error address book result: %s', ab['rs'])

    def update_cinfo_raw(self, ct):
        log.debug('replacing contact info raw for %r', self)
        self.contact_info = ct
        self.notify()

    remote_alias = property(get_remote_alias, set_remote_alias)

    profile = cproperty(odict)

    @property
    def pretty_profile(self):
        #none = u'No Profile'
        if self.service != 'yahoo':
            return None

        if self.y360hash:
            p = odict(self.profile)

            now = time()
            filteredupdates = []

            for update_and_time in self.y360updates:
                try: update, tstamp = update_and_time
                except: continue
                if now - tstamp <= 60 * 60 * 24:
                    filteredupdates.append((update, tstamp))

            self.y360updates = filteredupdates

            ups = [u for u, t in self.y360updates]
            withnewlines = []
            if ups:
                for i, u in enumerate(ups):
                    withnewlines.append(u)
                    if i != len(ups) - 1: withnewlines.append('\n')
            else:
                withnewlines.append(_('No Updates'))

            from . import yahoo360
            profilelink = (yahoo360.profile_link(self.y360hash), _('View Profile'))
            p[_('Yahoo! 360:')] = ['(', profilelink, ')','\n'] + list(reversed(withnewlines))

            # Place Yahoo! 360 at the beginning.
            p.move(_('Yahoo! 360:'), 0)

        else:
            p=self.profile

        URL = ''.join([u'http://profiles.yahoo.com/', self.name])

        if p is not None:
            p[_(u'Directory URL:')] = ['\n',(URL,URL)]

        return self.reorder_profile(p) or None

    def reorder_profile(self,p):
        orderedkeys=[
                     _('Yahoo! 360:'),
                     _('Real Name:'),
                     _('Nickname:'),
                     _('Location:'),
                     _('Age:'),
                     _('Sex:'),
                     _('Marital Status:'),
                     _('Occupation:'),
                     _('Email:'),
                     _('Home Page:'),
                     _('Hobbies:'),
                     _('Latest News:'),
                     _('Favorite Quote:'),
                     _('Links:'),
                     _('Member Since '),
                     _('Last Update: '),
                     _('Directory URL:')
        ]
        toc=[key for key in orderedkeys if key in p.keys() if p[key] and filter(None,p[key])]
#        print p.keys(),'\n',toc
        p._keys=toc

        if _('Yahoo! 360:') in p.keys() and filter(None,p[_('Yahoo! 360:')]):
            i=p.keys().index(_('Directory URL:'))
            p['sep360']=4
            p.move('sep360',1)

        for key in p.keys():
            i=p.index(key)
#            print key,(p[key].replace('\n','(newline)\n').encode('ascii','ignore') if isinstance(p[key],basestring) else p[key])
            if key in [_('Hobbies:'),_('Latest News:'),_('Favorite Quote:'),_('Links:')] and p[key] and filter(None,p[key]):
                if isinstance(p[key],list) and p[key][0]!='\n':
                    p[key]=p[key].insert(0,'\n')
                elif isinstance(p[key],basestring) and p[key][0]!='\n':
                    p[key]=''.join(['\n',p[key]])


                if i!=0 and not isinstance(p[p.keys()[i-1]],int):
#                    print 'Key: ',key,' index: ',i, ' value: ',p[key]
#                    if i>0: print 'PrevKey: ',p.keys()[i-1],' value: ',p[p.keys()[i-1]]
                    sepkey='sepb4'+key
                    p[sepkey]=4
                    p.move(sepkey,i)

            if key in [_('Member Since '),_('Last Update: '),_('Directory URL:')]:
                i=p.keys().index(key)
                if i!=0 and not isinstance(p[p.keys()[i-1]],int):
                    sepkey='sepb4'+key
                    p[sepkey]=4
                    p.move(sepkey,i)
                break

        i=p.keys().index(_('Directory URL:'))
        p['sepb4URL']=4
        p.move('sepb4URL',i)

        return p
    def request_info(self):
        if self.service == 'yahoo':
            yahooprofile.get(self.name, success = lambda p: setattr(self, 'profile', p))
        else:
            self.profile = odict()

    @property
    def _status(self):
        return self.status_orb

    def get_online(self):
        return self.status not in ('offline', 'unknown')

    online = oproperty(get_online, observe= ['status', 'pending_auth'])

    @property
    def away(self):
        return self.status == 'away'

    @property
    def mobile(self):
        return self.status_message and self.status_message.startswith("I'm mobile")

    def get_alias(self):
        return self.remote_alias or self.name

    def set_alias(self, new_alias):
        self.modify_addressbook(nname = new_alias)


    def modify_addressbook(self, **attrs):
        "Sets attributes in this contact's serverside addressbook entry."

        from urllib2 import urlopen

        if not hasattr(self, 'dbid'):
            return log.warning('no dbid in %r', self)

        url =  'http://insider.msg.yahoo.com/ycontent/?addab2=0&'

        # Add some mystery params, and my database Id.
        url += 'ee=1&ow=1&id=%s&' % self.dbid

        # Add params for each keyword argument.
        url += '&'.join('%s=%s' % (k,v) for k,v in attrs.iteritems())
        url += '&fname=test'
        url += '&yid=' + self.name

        info('setting addressbook entry: %s', url)
        print urlopen(url).read()


    def signoff(self):
        'Signs off this buddy.'

        self.status_message = ''
        self.status = 'offline'
        #self.setnotifyif('status_message', '')
        #self.setnotifyif('status', 'offline')
        self.notify()

    #
    # block / unblock - IGNORECONTACT
    #
    @callsback
    def block(self, setblocked = True, callback = None):
        func = self.protocol.block_buddy if setblocked else self.protocol.unblock_buddy
        return func(self, callback = callback)

    @callsback
    def unblock(self, callback = None):
        self.protocol.unblock_buddy(self, callback = callback)

    def set_stealth_session(self, session):
        # False means appear visible to the buddy while you are invisible

        # clear any permanent block if there is one
        if self.stealth_perm:
            self.protocol.set_stealth_perm(self, False)

        self.protocol.set_stealth_session(self, session)

    def set_stealth_perm(self, perm):
        self.protocol.set_stealth_perm(self, perm)

    def __repr__(self):
        return u'<YahooBuddy %s %d>' % (self.name, id(self))

    def __str__(self):
        return self.name
#
#
#

class YahooContact(Contact):
    'A Yahoo buddy entry on a buddy list.'
    inherited_actions = [common.buddy]

    def __init__(self, buddy, group):
        Contact.__init__(self, buddy, (group, buddy.name))
        self.group = group


    @action(needs = \
            lambda self: ((unicode, 'Username to invite', self.name),
                          (unicode, 'Invitation Message', 'Join me in chat!'),
                          (unicode, 'Chat room')))
    def invite_to_chat(self, usernames, message, roomname = None):
        self.protocol.invite_to_conference(usernames, roomname, message)

    def __repr__(self):
        return '<YahooContact %s, %s>' % (self.buddy.name, self.group.name)

    @action()
    def remove(self):
        self.protocol.remove_buddy(self)

    @action(lambda self: self.online)
    def join_in_chat(self):
        self.protocol.join_in_chat(self)

    def __hash__(self):
        return hash('%s_%s_%s' % (id(self.protocol), self.name, self.id[0].name))

    def __cmp__(self, other):
        if type(self) is not type(other):
            return -1
        if self is other:
            return 0
        else:
            return cmp((self.buddy.name, self.group.name), (other.buddy.name, other.group.name))

    @action(Contact._block_pred)
    def block(self, *a,**k):
        return Contact.block(self, *a, **k)
    @action(Contact._unblock_pred)
    def unblock(self, *a,**k):
        return Contact.unblock(self, *a, **k)
