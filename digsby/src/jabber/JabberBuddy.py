from peak.util.imports import lazyModule
import common, hashlib
import jabber
from jabber import JID, Presence
from util import callsback, Storage as S, odict, threaded
from util.cacheable import urlcacheopen, cproperty
from  common.actions import action #@UnresolvedImport
from jabber.objects.nick import NICK_NS, Nick
from common import pref
skin = lazyModule('gui.skin')
from urllib import quote

# if you make a string class...make it act like a string, damnit.
from pyxmpp.jabber.vcard import VCardString
VCardString.decode = lambda s, *a: s.value.decode(*a)
from jabber import VCard
from util.observe import ObservableProperty as oproperty

import logging; log = logging.getLogger('jabber.buddy')

GTALK = 'gtalk'
GTALK_MOBILE_DOMAINS = ('sms.talk.google.com',)
GTALK_DOMAINS = ('gmail.com', 'googlemail.com',) + GTALK_MOBILE_DOMAINS
JABBER = 'jabber'

def isGTalk(resource):
    if not isinstance(resource, basestring):
        return False
    reslower = resource.lower()
    return any(reslower.startswith(x) for x in
               ('talk.', 'gmail.', 'talkgadget', 'ics'))

no_widget = lambda self: None if getattr(self, 'iswidget', False) else True

# vcard lookup keys
ADDRESS_KEYS = 'street,extadr,locality,region,pcode,ctry'.split(',')
WORK_KEYS    = 'company department postition role'.split()

SUBSCRIPTION_TO = ('to', 'both')
SUBSCRIPTION_FROM = ('from', 'both')

class JabberBuddy(common.buddy):
    resource_class = jabber.resource
    def __init__(self, jabber_, jid, rosteritem=None):
        self.jid = JID(jid).bare()
        self._set_username()

        self.resources = {}
        self.subscription = rosteritem.subscription if rosteritem else None
        self.rostername = rosteritem.name if rosteritem else None
        if rosteritem:
            self.notify('rostername')
            self.notify('remote_alias')
        self.ask = rosteritem.ask if rosteritem else None
        self.groups = rosteritem.groups if rosteritem else []
        self.profile = False
        common.buddy.__init__(self, self.username, jabber_)
        self._gen_pretty_profile()

        self.pending_adds = set()

    def _set_username(self):
        uname = JID(self.jid).bare().as_unicode()
        self.username = uname

    def __call__(self, item):
        """
        send a new roster item to the buddy
        updates relevant data (subscription/ask status, groups)
        """

        self.subscription = item.subscription
        self.ask = item.ask
        self.rostername = item.name
        self.groups = item.groups
        self.check_subscription()

#        log.info('%r info updated:',  self)
#        log.info(' subscription: %s', self.subscription)
#        log.info('          ask: %s', self.ask)
#        log.info('       groups: %s', self.groups)
        self.notify('rostername')
        self.notify('remote_alias')

        return self

    def check_subscription(self):
        if self.subscription not in SUBSCRIPTION_TO and self.resources and \
           self is not getattr(self.protocol, 'self_buddy', sentinel):
            self.resources.clear()
            self.notify()

    @property
    def service(self):
        if self.jid.domain in GTALK_DOMAINS:
            return GTALK
        else:
            return JABBER

    @property
    def serviceicon(self):
        #show gtalk, but service will still be jabber (for non gmail gtalk users)
        service = self.service
        if service is GTALK or self.protocol.service == 'gtalk' \
            or any(isGTalk(j.resource) for j in self.resources):
            service = GTALK
        return skin.get('serviceicons.' + service)

    @property
    def id(self): return self.jid

    def equals_chat_buddy(self, chat_buddy):
        if hasattr(chat_buddy, 'user'):
            user = chat_buddy.user
            if user.real_jid is not None:
                return user.real_jid.bare() == self.jid.bare()

        return common.buddy.equals_chat_buddy(self, chat_buddy)

    @property
    def away(self):
        if self.away_is_idle:
            return self.resources and not self.idle and not any(r.available
                                          for r in self.resources.itervalues())
        else:
            return self.resources and all(r.away
                                          for r in self.resources.itervalues())

    @property
    def mobile(self):
        return (self.jid.domain in GTALK_MOBILE_DOMAINS or
                (self.resources and
                 all(r.mobile for r in self.resources.itervalues())))

    @property
    def blocked(self): return False

    @property
    def online(self):
        #HAX: Nothing else seemed to work, so now checks if the protocol is connected
        return bool(self.resources) and self.protocol.is_connected

    @property
    def away_is_idle(self):
        return self.service == GTALK

    @property
    def idle(self):
        if self.away_is_idle:
            return self.resources and all(r.idle
                                          for r in self.resources.itervalues())
        else:
            return False

    def get_caps(self):
        caps = common.buddy.get_caps(self)

        for r in self.resources.values():
            res = r.jid.resource
            if res and not isGTalk(res):
                #TalkGadget is the flash client and ICS is for the blackberry version
                break
        else:
            caps.discard(common.caps.FILES)

        return caps

    caps = property(get_caps)

    def _gen_pretty_profile(self):
        profile = odict()
        ok = False

        fullname = self.vcard_get('fn')
        if fullname:
            profile[_('Full Name:')]=fullname
            ok=True

        mapping = {'birthday':('bday',),
               'email_address':('email', 'address'),
               'phone':('tel', 'number'),
               'company':('org', 'name'),
               'department':('org', 'unit'),
               'postition':('title',),
               'role':('role',),}

        keylabels = {'birthday' : _('Birthday:'), 'email_address' : _('Email Address:'), 'phone' : _('Phone:')}
        for key in keylabels:
            val = self.vcard_get(*mapping[key])
            if val is not None:
                profile[keylabels[key]]=val
                ok=True

        homepage = self.vcard_get('url')
        if homepage:
            profile[_('Website')]=(homepage,homepage)
            ok=True

        about = self.vcard_get('desc')
        if about:
            if ok:
                profile['sep1']=4
            profile[_('Additional Information:')]=''.join(['\n',about])

        def prettyaddy(addict):
            addy = []
            add = lambda s: addy.insert(0, s)


            mstr = _('{street} {extra_adress} {locality} {region} {postal_code} {country}').format(street        = addict['street'],
                                                                                                   extra_address = addict['extadr'],
                                                                                                   locality      = addict['locality'],
                                                                                                   region        = addict['region'],
                                                                                                   postal_code   = addict['pcode'],
                                                                                                   country       = addict['ctry'])
            if isinstance(mstr, unicode):
                mstr = mstr.encode('utf-8')
            murl='http://maps.google.com/maps?q=' + quote(mstr)

            if addict.ctry: add('\n'+addict.ctry)

            if addict.pcode: add(addict.pcode)

            if addict.region:
                if addict.pcode:
                    add(' ')
                add(addict.region)

            if addict.locality:
                if (addict.region or addict.pcode):
                    add(', ')
                add(addict.locality)

            if addict.extadr:
                if any((addict.locality, addict.region, addict.pcode)):
                    add('\n')
                add(addict.extadr)

            if addict.street:
                if any((addict.locality, addict.region, addict.pcode, addict.extadr)):
                    add('\n')
                add(addict.street)

            if addy: add(['(',(murl, 'map'),')\n'])

            return addy

        #horrible
        address = self.vcard_get('adr')
        if address is not None:
            if ok:
                profile['sep2']=4

            ladr = [(key,self.vcard_get('adr', key)) for key in ADDRESS_KEYS]
            if any(v for k,v in ladr):
                profile[_('Home Address:')]=prettyaddy(S(ladr))

        if ok: profile['sep3']=4

        for key in WORK_KEYS:
            val = self.vcard_get(*mapping[key])
            profile[key.title()+':']=val

        self.last_pretty_profile = profile
        return profile

    @property
    def pretty_profile(self):
        profile = getattr(self, 'last_pretty_profile', lambda: self._gen_pretty_profile())

        for key in profile.keys():
            if not key.startswith('sep') and profile[key]:
                break
        else:
            return None

        return profile

    def get_status_message(self):
        try:
            res = self.get_highest_priority_resource()
            if res  : return res.status_message or ''
            else    : return ''
        except Exception, e:
            log.warning('status_message(self) on %r: %r', self, e)
            raise

    def set_status_message(self, value):
        r = self.get_highest_priority_resource()
        if r:
            old = r.status_message
            r.status_message = value
            self.notify('status_message', old, value)

    status_message = property(get_status_message, set_status_message)

    @property
    def status(self):
        if self.mobile:
            return 'mobile'
        elif self.subscription not in SUBSCRIPTION_TO and \
           self is not getattr(self.protocol, 'self_buddy', sentinel):
            return 'unknown'
        elif not getattr(self, 'resources', []):
            return "offline"
        elif self.idle:
            return 'idle'
        elif not self.away:
            return "available"
        else:
            return "away"

    def update_presence(self, presence, notify=True, buddy=None):
#        presence = dupe_presence(presence)
        buddy = presence.get_from() or buddy
        presence_type = presence.get_type()

        if not presence_type or presence_type == "available":
            old_length = len(self.resources)

            self.resources[buddy] = self.resource_class(self.protocol, buddy, presence)

            children = presence.xmlnode.get_children()
            if children is not None:
                photos = [c for c in children if c.name == "photo"]
                if photos: self.icon_hash = photos[0].getContent()

            nicks = jabber.jabber_util.xpath_eval(presence.xmlnode,
                                       'n:nick',{'n':NICK_NS})
#           nicks.extend(jabber.jabber_util.xpath_eval(presence.xmlnode,
#                                       'ns:nick'))
            if nicks:
                self.nick = Nick(nicks[0]).nick
                self.notify('nick')
                self.notify('remote_alias')

            self._presence_updated(presence)

        elif presence_type == "unavailable":
            if buddy in self.resources:
                del self.resources[buddy]
        if notify:
            self.notify('status')

    def _presence_updated(self, presence):
        if self.jid.domain not in pref('digsby.guest.domains', ['guest.digsby.org']):
            # don't retreive VCard/Icons from guests.
            self.protocol.get_buddy_icon(self.username)

    def get_highest_priority_resource(self):
        return self[0] if getattr(self, 'resources',[]) else None

#        retval = None
#        for res in self.resources.itervalues():
#            if not retval or (res.presence.get_priority() > retval.presence.get_priority()):
#                retval = res
#        return retval

    def set_vcard(self, stanza):
        log.info('incoming vcard for %s', self)
        self._vcard_incoming = False

        q = stanza.get_query()
        if not q: return
        try:
            vc = self.vcard = jabber.VCard(q)
        except ValueError:
            pass
        else:
            self._incoming_icon(vc.photo)
        self._gen_pretty_profile()
        self.notify('vcard')
        self.notify('remote_alias')

    def set_vc(self, vcard):
        self._vcard = vcard

    def get_vc(self): return self._vcard

    vcard = property(get_vc, set_vc)

    #this does a good enough job at the moment,
    #and means we only need to cache one thing.  It is not perfect,
    #the old way was worse
    _vcard = cproperty(None, (lambda o: o.rfc2426() if o is not None else None),
                       (lambda o: VCard(o) if o is not None else None))

    def vcard_get(self, *stuffs):
        if self.vcard:
            stuff = stuffs[0]; stuffs = stuffs[1:]
            thing = getattr(self.vcard, stuff, None)
            if isinstance(thing, list) and thing:
                thing = thing[0]
                while stuffs:
                    thing = getattr(thing, stuffs[0])
                    stuffs = stuffs[1:]
            elif thing:
                if stuffs:
                    log.warning_s('%r', stuffs)
                    log.warning_s(self.vcard.as_xml())
                assert not stuffs
            return unicode(thing) if thing else thing

    nick         = cproperty(None)

    def _incoming_icon(self, photos):
        'Handles the "photos" section of a VCard.'

        if photos and photos[0].image:
            img = photos[0].image
            self._update_photo_image(img)
        elif photos and photos[0].uri:
            def success(result):
                _response, content = result
                #buddy.icon_data = content
                self._update_photo_image(content)
            meth = threaded(urlcacheopen)
            meth.verbose = False
            meth(photos[0].uri, success=success)


    def _update_photo_image(self, data):
        hash = hashlib.sha1(data).hexdigest()
        self.cache_icon(data, hash)
        self.icon_hash = hash

    def get_remote_alias(self):
        for attr in ('rostername','nick',):
            nick = getattr(self, attr, None)
            if nick: return unicode(nick)
        for attr in ('nickname', 'fn'):
            nick = self.vcard_get(attr)
            if nick: return unicode(nick)
        return None

    remote_alias = oproperty(get_remote_alias, observe=['vcard', 'rostername', 'nick'])

    @action(needs = ((unicode, "Group name"),))
    @callsback
    def add_to_group(self, groupname, callback = None):
        log.info('%s add_to_group %s', self, groupname)
        pending = self.pending_adds

        # Prevent excessive add requests.
        if groupname in pending:
            log.info('ignoring request.')
        else:
            pending.add(groupname)

        item = self.protocol.roster.get_item_by_jid(self.id).clone()

        if groupname not in item.groups:
            item.groups.append(groupname)
            query = item.make_roster_push()

            def onsuccess(_s):
                pending.discard(groupname)
                callback.success()

            def onerror(_s = None):
                pending.discard(groupname)
                log.warning("error adding %r to %s", self.id, groupname)

            self.protocol.send_cb(query, success = onsuccess, error = onerror, timeout = onerror)

    @action()
    @callsback
    def remove(self, callback=None):
        try:
            item = self.protocol.roster.get_item_by_jid(self.id).clone()
        except KeyError:
            return
        else:
            item.subscription = 'remove'
            self.protocol.send_cb(item.make_roster_push(), callback=callback)

    @action(lambda self: None if no_widget(self) is None else
            (None if self.subscription in SUBSCRIPTION_FROM else True))
    def subscribed(self):
        'Send Authorization'
        self.protocol.send_presence(Presence(to_jid=self.id,
                                           stanza_type='subscribed'))

    @action(lambda self: None if no_widget(self) is None else
            (None if self.subscription not in SUBSCRIPTION_FROM else True))
    def unsubscribed(self):
        'Send Removal of Authorization'
        self.protocol.send_presence(Presence(to_jid=self.id,
                                           stanza_type='unsubscribed'))

    @action(lambda self: None if no_widget(self) is None else
            (None if self.subscription in SUBSCRIPTION_TO else True))
    def subscribe(self):
        'Re-send Subscription Request'
        self.protocol.send_presence(Presence(to_jid=self.id,
                                           stanza_type='subscribe'))

    @action(lambda self: None if no_widget(self) is None else
            (None if self.subscription not in SUBSCRIPTION_TO else True))
    def unsubscribe(self):
        'Send Unsubscription Request'
        self.protocol.send_presence(Presence(to_jid=self.id,
                                           stanza_type='unsubscribe'))


    def appear_offline_to(self):
        'Sends an offline presence stanza to this buddy.'

        self.protocol.send_presence(Presence(stanza_type = 'unavailable',
                                             status      = 'Logged Out',
                                             to_jid = self.id))

    @action()
    def expand(self):
        print "expand %r" % self

    def sorted_resources(self):
        return sorted(self.resources.itervalues(),
               key=lambda r: (r.priority, r.jid), reverse=True)

    def __iter__(self):
        return iter(self.sorted_resources())

    def __len__(self):
        return len(self.resources)

    def __getitem__(self, index):
        return self.sorted_resources()[index]

    def __repr__(self):
        try:
            res = len(self.resources)
        except Exception:
            res = 0
        try:
            n = self.name
        except Exception:
            n = ''
        return '<%s %r %d>' % (type(self).__name__, n, res)

def dupe_presence(p):
    '''
    duplicates a presence object

    @param p: pyxmpp.presence.Presence object
    '''
    assert False #gettting rid of this function
    #using the node directly makes
    # libxml2.xmlNode.docCopyNode(libxml2.newDoc("1.0"),1)
    # happen deep inside pyxmpp.stanza, resulting what seems to be a perfect
    # and useable copy. p.copy() or Presence(p) does not provide a useable copy
    return Presence(p.get_node())

