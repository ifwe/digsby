from __future__ import with_statement

digsby =      frozenset(('digsby',))
ebuddy_caps = frozenset(('chat_service', 'file_xfer', 'utf8_support'))
aim5_caps =   frozenset(('add_ins', 'avatar', 'buddy_list_transfer', 'chat_service', 'direct_im', 'file_xfer', 'voice_chat'))
pidgin_caps = frozenset(('avatar', 'chat_service', 'direct_im', 'file_xfer')) # used to include 'utf8_support'
ichat_caps =  frozenset(list(pidgin_caps) + ['file_share'])
meebo_caps =  frozenset(('avatar', 'chat_service', 'extended_msgs', 'icq_xtraz', 'mtn', 'utf8_support'))
aim6_caps =   frozenset(('avatar', 'chat_service', 'direct_im', 'file_xfer', 'voice_chat'))
icq6_caps =   frozenset(('buddy_list_transfer', 'chat_service', 'icq_html_msgs', 'icq_tzers', 'mtn', 'rtc_audio'))

icq7_caps =   frozenset(('icq7_unknown', ))

clients_supporting_html = frozenset(('aim60', 'aim59', 'purple', 'digsby', 'miranda-aim', 'ichat', 'icq7'))

import struct
import time, datetime

from util.observe import ObservableDict, ObservableProperty; oproperty = ObservableProperty
import common
from common import profile
from common.actions import action
from logging import getLogger; log = getLogger('oscar.buddies')
import util
import oscar
from util.cacheable import cproperty
from util.callbacks import callsback
from util.lrucache import lru_cache
from util.primitives.funcs import get
from util.primitives.mapping import Storage, FilterDict
from util.primitives.strings import dequote, preserve_whitespace, strip_html2

from traceback import print_exc

strip_html2 = lru_cache(80)(strip_html2)

import re
body_pattern = re.compile('<(body|BODY)[^>]*?((bgcolor|BGCOLOR)=(.*?))? ?>')
font_back_pattern = re.compile('<(font|FONT)[^>]*?((back|BACK)=\s*[\'"]?(#[0-f]{6})[\'"]?).*?>')
blast_group_re = re.compile(r'\[.*\]')

import oscar.capabilities

statuses=Storage({
    'free for chat':_('Free for Chat'),
    'busy':_('Occupied'),
    'unknown': _('Offline'),
})

# used to replace special strings in statuses and profiles
special_msg_strings = {
    '%n': lambda buddy: buddy.protocol.username,
    '%d': lambda buddy: datetime.date.today().strftime('%m/%d/%Y'), # 3/7/2007
    '%t': lambda buddy: datetime.datetime.now().strftime('%I:%M:%S %p') #12:20:07 PM
}

def magic_string_repl(s, buddy):
    # TODO: re.replace
    for key, substitute_func in special_msg_strings.iteritems():
        if key in s:
            s = s.replace(key, substitute_func(buddy))
    return s

# if set to True, action preconditions will allow operations like file transfers
# and direct IMs regardless of the capabilities buddies are reporting.
IGNORE_CAPABILITIES = False

def sanitize_aim_html(html):
    html, bgcolor = _remove_html_cruft(html)
    return html

def _remove_html_cruft(s):
    '''
    Attempts to fix up some of the badly formatted HTML catastrophes that emerge
    from Pidgin and other AIM clients.

    For example:

<html><body><font color="#00FF00"><body bgcolor="#000000"><font size="3"><font back="#000000">class/work</font></font></body></font></body></html>

    Returns a tuple: (bgcolor, sanitized_string)
    '''
    lower = s.lower()

    # Strip HTML tags
    s = s[6:] if lower.startswith('<html>') else s
    s = s[:-7] if lower.endswith('</html>') else s

    match = body_pattern.search(s)

    # find last BODY tag with a bgcolor, and save it
    bgcolor = u''
    while match:
        # remove body tags as we go
        s = s[:match.start()] + s[match.end():]
        groups = match.groups()
        if groups[-1]:
            bgcolor = groups[-1].strip() or bgcolor
        match = body_pattern.search(s)

    # remove body end tag(s!)
    s = s.replace('</body>','').replace('</BODY>','').replace('<br/>', '<br />')

    # "BACK" isn't a real attribute to a FONT tag, replace it with the CSS equivalent
    match = font_back_pattern.search(s)
    while match:
        backcolor = match.group(4)
        s = ''.join((s[:match.start(2)], 'style="background-color:', backcolor, ';"', s[match.end(2):]))
        match = font_back_pattern.search(s)

    if isinstance(s, str):
        s = s.decode('fuzzy utf8')

    return s, bgcolor

def aim_to_xhtml(s):
    '''Wraps AIM HTML which might have <html> and <body> with a <span>.'''

    s, bgcolor = _remove_html_cruft(s)

    if bgcolor:
        bgstyle = ' style="background: %s;"' % dequote(bgcolor)
    else:
        bgstyle = ''

    return u'<div%s>%s</div>' % (bgstyle, preserve_whitespace(s))

def make_dgetter(obj):
    def dgetter(key):
        '''
        Returns a unicode string by getting the attribute/item
        'key' from 'obj'. in debug mode will raise assertion errors
        if the returned value is not unicode.
        '''
        val = get(obj, key, u'') # will getitem or getattr
        if not val:
            # To fix None-type objects
            val = u''

        try:
            assert isinstance(val, unicode), (key, val, obj)
        except:
            print_exc()

        if not isinstance(val, unicode):
            return val.decode('fuzzy utf8')
        return val
    return dgetter

def make_pretty_addr(d):
    addrkeys = ('street', 'city', 'state', 'zip', 'country')
    get = make_dgetter(d)

    def addytemplate(d):
        fields = []
        for k in addrkeys:
            fields.append(get(k))

        return 'http://maps.google.com/maps?q=' + (u' '.join(filter(None, fields)).encode('utf-8').encode('url'))

    country = get('country')
    zip = get('zip')
    state = get('state')
    city = get('city')
    street = get('street')

    res = []
    add = lambda s: res.insert(0, s)

    if country:
        add(u'\n' + country)

    if zip:
        add(zip)

    if state:
        if zip:
            add(u', ')
        add(state)

    if city:
        if (state or zip):
            add(u', ')
        add(city)

    if street:
        if (city or state or zip):
            add(u'\n')
        add(street)

    if res: add([u'(', (addytemplate(d), u'map'), u')\n'])

    return res


class OscarBuddy(common.buddy):
    _name = None
    def __init__(self, name, protocol):
        self._status = 'unknown'
        self._idle_time = None
        self._friendly_name = None # will be set by OscarContact
        self._avail_msg  = self._away_msg = None

        self._user_class = \
        self.create_time = \
        self.signon_time = 0

        common.buddy.__init__(self, oscar._lowerstrip(name), protocol)
        if isinstance(self.name, unicode):
            self.name = self.name.encode('utf8')

        self.account_creation_time = \
        self.online_time = None

        self.user_status_icq = 'offline'
        self.external_ip_icq = 0

        self._dc_info = util.Storage()
        self._capabilities = []
        self.userinfo = {}

        if self._profile is False:
            self._profile = None

        self._away_updated = self._mystery_updated = 0

        self._waiting_for_presence = True

    def _get_name(self):
        return self._name
    def _set_name(self, val):
        self._name = val
        assert isinstance(val, bytes)
    name = property(_get_name, _set_name)

    def __hash__(self):
        return common.buddy.__hash__(self)

    @property
    def sightly_status(self):
        if self.mobile:
            return _('Mobile')
        else:
            if self.service=='aim':
                return statuses.get(self.status, _(self.status.title()))
            else:
                return statuses.get(self._status, _(self._status.title()))

    @property
    def pretty_profile(self):
        from util import odict

        if self.service=='aim':
            try:
                return self._pretty_profile
            except AttributeError:
                prof = [(aim_to_xhtml(self.profile) if self.profile else None)]

                from common import pref
                if pref('infobox.aim.show_profile_link', True):
                    # shows an aimpages.com profile link
                    linkage=odict()
                    linkage['space']=4
                    url=''.join(['http://www.aimpages.com/',self.name,'/profile.html'])
                    linkage[_('Profile URL:')]=['\n',(url,url)]

                    prof += [linkage]

                self._pretty_profile = prof
                return prof
        else:

            ok=False

            profile=odict()

            bget = make_dgetter(self)

            if bget('first') or bget('last'):
                profile[_('Full Name:')]=' '.join([self.first,self.last])
                ok=True

            personal = getattr(self, 'personal', {})
            if personal:
                pget = make_dgetter(personal)
                homeaddr = make_pretty_addr(personal)
            else:
                pget = lambda s:''
                homeaddr = ''

            keylabels = {'gender' : _('Gender'),
             'birthday' : _('Birthday')}
            for key in keylabels:
                if getattr(personal,key,False):
                    profile[_('{label}:').format(label = keylabels[key])] = pget(key)
                    ok=True


            p_web = pget('website')
            if p_web:
                profile[_('Website:')] = (p_web, p_web)
                ok=True


            prof = bget('profile')
            if prof:
                if ok: profile['sep1']=4

                try:
                    profstr = u'\n'+ prof
                except Exception:
                    pass
                else:
                    profile[_('Additional Information:')] = profstr

                ok=True

            if homeaddr:
                if ok: profile['sep2']=4
                profile[_('Home Address:')] = homeaddr
                ok=True

            work = getattr(self, 'work', {})
            if work:
                wget = make_dgetter(work)
                workaddr = make_pretty_addr(work)
            else:
                wget = lambda s:''
                workaddr =''

            if workaddr:
                if ok: profile['sep3']=4
                profile[_('Work Address:')] = workaddr
                ok=True

            if ok:
                profile['sep4']=4
                ok=False

            keylabels = {'company' : _('Company'), 'department' : _('Department'), 'position' : _('Position')}
            for key in keylabels:
                if getattr(work,key,False):
                    profile[_('{label}:').format(label = keylabels[key])] = wget(key)
                    ok=True

            w_web = wget('website')
            if w_web:
                profile[_('Work Website:')] = (w_web, w_web)
                ok=True

            if ok:
                ok=False
                profile['sep5']=4

            url=''.join([u'http://people.icq.com/people/about_me.php?uin=',self.name])
            profile[_('Profile URL:')]=['\n',(url,url)]


            return profile

    @property
    def service(self):
        return 'icq' if self.name.isdigit() else 'aim'

    @property
    def icq(self):
        return self.service == 'icq'

    def update(self, userinfo):
        self._idle_time = None

        notifyattrs = set()
        notify_append = notifyattrs.add
        is_self_buddy = self.protocol.self_buddy is self

        with self.frozen():
            for k, v in userinfo.iteritems():
                if isinstance(k, basestring):
                    if k == 'status':
                        if is_self_buddy:
                            continue
                        if v == 'online':
                            v = 'available'
                        self.status = v
                        notify_append('status')
                    elif k == 'avail_msg':
                        self._set_avail_msg(v, False)
                        notify_append('status_message')
                    else:
                        try:
                            setattr(self, k, v)
                            notify_append(k)
                        except AttributeError, e:
                            print_exc()

                else:
                    self.userinfo[k] = v

        if self._status != 'away':
            self._waiting_for_presence = False

        notify = self.notify

        if self._status == 'unknown':
            notify_append('status')
            self.status = 'offline'

        for attr in notifyattrs:
            notify(attr)

    def _get_status_orb(self):

        if self.idle:
            return 'idle'
        elif self.away:
            return 'away'
        elif self.status == 'unknown':
            return 'offline'
        else:
            from common.Buddy import get_status_orb
            return get_status_orb(self)

    status_orb = oproperty(_get_status_orb, observe = 'status')

    def get_profile(self):
        p = self._profile
        if p is not None:
            p = magic_string_repl(p, self)

        return p

    def set_profile(self, profile):
        'Invoked by the network upon a new incoming profile for this buddy.'

        try:
            del self._pretty_profile
        except AttributeError:
            pass

        self._profile = profile

    profile = property(get_profile, set_profile,
                       doc = "This buddy's AIM profile or ICQ 'about me'.")

    # stores a timestamp for the profile's last updated time.
    _profile_updated = cproperty(0)

    def set_profile_updated(self, netint):
        self._profile_updated = struct.unpack('!I', netint)[0] \
            if isinstance(netint, basestring) else netint

    profile_updated = property(lambda b: b._profile_updated, set_profile_updated)

    def set_away_updated(self, netint):
        old = self._away_updated
        self._away_updated = struct.unpack('!I', netint)[0] \
            if isinstance(netint, basestring) else netint

        if old != self._away_updated:
            self.protocol.get_buddy_info(self)

    away_updated = property(lambda b: b._away_updated, set_away_updated)

    def set_mystery_updated(self, netint):
        self._mystery_updated = struct.unpack('!I', netint)[0] \
            if isinstance(netint, basestring) else netint

    mystery_updated = property(lambda b: b._mystery_updated, set_mystery_updated)

    @property
    def sms(self):
        return self.name.startswith('+')

    # stores the profile string, cached to disk.
    _profile = cproperty(None)

    def request_info(self, profile, away):
        "Request this buddy's profile or away message from the server."

        if not profile and not away: return

        self.protocol.get_buddy_info(self, profile = profile, away = away)


    def set_nice_name(self, name):
        self._nice_name = name

    def get_nice_name(self):
        return getattr(self, '_nice_name', self.name)

    nice_name = property(get_nice_name, set_nice_name)


    def _set_capabilities(self, newval):
        if self is self.protocol.self_buddy:
            #
            # incoming family_x01_x0f packets were calling self_buddy.update and setting this
            # value to None, I think...clearing the list.
            #
            # TODO: can the server ever set our capabilities for us?
            #
            return

        caps = []
        while newval:
            caphi, caplo, newval = oscar.unpack((('caphi', 'Q'),
                                                 ('caplo', 'Q')),
                                                newval)
            caps.append(struct.pack('!QQ', caphi, caplo))


        if (self._capabilities) and (len(caps) == 1) and (caps[0] == oscar.capabilities.by_name['chat_service']):
            log.info('Received dummy capabilities for %r, not setting them', self.name)
            return

        self._capabilities = caps

        log.debug('%r\'s guessed client is %r. caps are: %r', self, self.guess_client(), self.pretty_caps)

    capabilities = ObservableProperty(lambda self: self._capabilities, _set_capabilities, observe = '_capabilities')

    @property
    def pretty_caps(self):
        return map(lambda x:oscar.capabilities.by_bytes.get(x, x), self._capabilities)

    @property
    def caps(self):

        from common import caps as digsbycaps
        import oscar.capabilities as oscarcaps
        protocaps = list(self.protocol.caps) # copy it so we don't modify the protocol's copy.
        mycaps = [oscarcaps.by_bytes.get(x, None) for x in self.capabilities]

        if 'file_xfer' not in mycaps:
            #protocaps.remove(digsbycaps.FILES)
            pass

        if oscar._lowerstrip(self.name) in self.protocol.bots or blast_group_re.match(oscar._lowerstrip(self.name)):
            protocaps.append(digsbycaps.BOT)

        return protocaps

    @property
    def accepts_html_messages(self):
        # This should technically be:
        #    return 'xhtml_support' in self.pretty_caps
        # BUT pidgin supports HTML (their IM window is an HTML widget)
        # and they don't report that capability. So, we have to guess what
        # type of client they are on based on the capabilities.
        #
        # Lucky for us, the main thing to be concerned about is official
        # ICQ clients, and they have very bizarre capability sets.

        # If any of these are true, they probably have HTML support
        client = self.guess_client()
        selficq = self.protocol.icq

        if client == 'digsby':
            return True

        if client == 'miranda-icq' and not selficq:
            return True

#        if selficq and not self.icq and client == 'purple':
#            return True
        if client == 'purple' and selficq:
            return not self.icq

        if client == 'ebuddy':
            return True

        if client == 'icq7':
            return False

        if client == 'qip-2005':
            return not (selficq and self.icq)

        caps = set(self.pretty_caps)
        if 'xhtml_support' in caps:
            return True

        if 'icq_html_msgs' in caps and not selficq:
            return True

        if client in clients_supporting_html:
            return True

        if 'rtf_support' in caps:
            return False

        if client == 'unknown':
            return not (selficq and self.icq)

        return False

    @property
    def sends_html_messages(self):
        return self.get_sends_html_messages(False)

    def get_sends_html_messages(self, ischat=False):
        client = self.guess_client()
        selficq = self.protocol.icq

        if client == 'digsby':
            return True

        if (not selficq) and client in ('miranda-icq',):
            return True

        if client == 'miranda-aim':
            return True

        if client in ('icq7',):
            return False

        if selficq ^ self.icq and client in ('icq6', 'purple'):
            return True

        if self.icq and client in ('purple', 'icq6', 'qip-2005', 'miranda-icq', 'icq7'):
            if client == 'purple' and ischat: # meebo sends ICQ chat messages as HTML
                return True
            elif client == 'icq7' and ischat:
                return True
            else:
                return False

        if selficq and ischat:
            return True

        if client == 'qip-2005':
            return False

        if client == 'ebuddy':
            return True

        return self.accepts_html_messages


    def guess_client(self):
        '''
        Guess a buddy's client based on capabilities.
        '''

        # Hopefully this combination will seperate the official ICQ clients
        # from others
        caps = set(self.pretty_caps)

        might_be_icq = False
        if caps.issuperset(icq6_caps):
            might_be_icq = True

        if any(x.startswith('Miranda') for x in caps):
            if caps.issuperset(('mtn', 'icq_xtraz')):
                return 'miranda-icq'
            else:
                return 'miranda-aim'
        elif caps.issuperset(meebo_caps):
            return 'purple'
        elif caps.issuperset(icq7_caps):
            return 'icq7'
        elif any('QIP 2005' in x for x in caps):
            return 'qip-2005'
        elif caps.issuperset(aim5_caps):
            return 'aim59'
        elif 'digsby' in caps:
            return 'digsby'
        elif caps.issuperset(aim6_caps) or 'aim6_unknown1' in caps:
            return 'aim60'
        elif caps.issuperset(ichat_caps):
            return 'ichat'
        elif caps.issuperset(pidgin_caps):
            return 'purple'
        elif self.mobile or self.sms:
            return 'mobile'
        elif caps.issuperset(ebuddy_caps):
            if might_be_icq:
                return 'icq6'
            else:
                return 'ebuddy'
        else:
            if might_be_icq:
                return 'icq6'
            else:
                return 'unknown'

    def _set_dc_info(self, newval):
        dc_info, data = oscar.unpack((('_', 'dc_info'),), newval)
        if data: print 'extra data on dc_info for %s: %s' % (self.name, util.to_hex(data))

        self._dc_info = dc_info

    dc_info = ObservableProperty(lambda self: self._dc_info, _set_dc_info, observe = '_dc_info')

    def _set_user_class(self, newval):
        self._user_class = struct.unpack('!H', newval)[0]

    user_class = ObservableProperty(lambda self: self._user_class,
                                    _set_user_class, observe = '_user_class')

    def _set_avail_msg(self, newval, notify=True):

        old = self._avail_msg
        tflvs = {}        # type, flag, length, value
        try:
            tflvs_list, newval = oscar.unpack((('values', 'tflv_list'),), newval)
        except Exception:
            return

        for tflv in tflvs_list:
            tflvs[tflv.t] = tflv.v

        if 1 in tflvs:
            self.setnotifyif('icon_hash', tflvs[1])
        if 2 in tflvs:

            if len(tflvs[2]) > 0:
                fmt = (
                    ('msglen','H'),
                    ('msg', 's', 'msglen'),
                    ('numtlvs', 'H'),
                    ('tlvs', 'tlv_list', 'numtlvs'),
                    )

                try:
                    __, msg, __, tlvs, tflvs[2] = oscar.unpack(fmt, tflvs[2])
                except Exception, e:
                    log.error('Error unpacking available message. (exc=%r, data=%r)', e, tflvs[2])
                    msg = None

                if self is self.protocol.self_buddy:
                    # Much like capabilities, we don't want to allow this to be
                    # set from the network. we know what our status message is,
                    # thank you very much.

                    # Of course this doesn't really work when signed in from another location.
                    # Keep that a secret, 'kay?
                    return

                if msg is None:
                    self._avail_msg = None
                    self._cached_status_message = None
                    return

                codecs = ['fuzzy', 'utf-8']

                if tlvs:
                    log.info('Got extra tlvs for availmsg: %r', tlvs)
                    codecs[1:1] = [tlv.v for tlv in tlvs]

                self._avail_msg = msg.decode(' '.join(codecs))
                self._cached_status_message = None
            else:
                self._avail_msg = None
#        else:
#            notify = self._avail_msg is not None
#            self._avail_msg = None

        if notify:
            self.notify('avail_msg', old, self._avail_msg)

    def _get_avail_msg(self):
        return self._avail_msg
    avail_msg = property(_get_avail_msg, _set_avail_msg)

    def __repr__(self):
        return '<OscarBuddy %r>' % oscar._lowerstrip(self.name)

    def get_idle(self):
        'Returns a unix time or None.'

        return self._idle_time

    def set_idle(self, val):
        self._idle_time = val

    idle = ObservableProperty(get_idle, set_idle, observe = '_idle_time')

    def set_idle_time(self, netidle):
        if isinstance(netidle, basestring):
            self._idle_time = int(time.time() - 60*struct.unpack('!H', netidle)[0])
        elif isinstance(netidle, int):
            self._idle_time = netidle
        elif netidle is None:
            self._idle_time = None
        else:
            log.warning('set_idle_time received %r', netidle)

    def get_idle_time(self):
        i = self._idle_time
        return None if i is None else int(i)

    idle_time = property(get_idle_time, set_idle_time, None, 'Set by the network.')

    def get_status(self):
        if self._status == 'offline':
            if self.mobile:
                return 'mobile'
            else:
                return 'offline'

        if self._status == 'unknown' or self._waiting_for_presence:
            return 'unknown'
        elif self.away or self._status == 'away':
            return 'away'
        elif self.idle or self._status == 'idle':
            return 'idle'
        else:
            return 'available'

    def set_status(self, newval):
        if self._status != newval:
            try:
                # invalidate any cached formatted profile
                del self._pretty_profile
            except AttributeError:
                pass

        self._status = newval

    status = ObservableProperty(get_status, set_status, observe = '_status')

    def set_away_msg(self, away_msg):
        if not isinstance(away_msg, (basestring, type(None))):
            raise TypeError(str(type(away_msg)))

        self._waiting_for_presence = False
        self._away_msg = away_msg

    def get_away_msg(self):
        return self._away_msg

    away_msg = property(get_away_msg, set_away_msg)



    def get_online(self):
        'Returns True if the buddy is not offline'
        return self._status != 'offline' and self._status != 'unknown'

    online = ObservableProperty(get_online, observe = '_status')

    #
    # away: a buddy is online and the away flag is set
    #

    def _away(self):
        if self.user_class:
            v = bool(self.user_class & 0x20)
        else:
            v = self._status == 'away'

        return self.online and v

    away = ObservableProperty(_away, observe = 'user_class')

#    @action(lambda self: IGNORE_CAPABILITIES or
#            oscar.capabilities.by_name['direct_im'] in self.capabilities)
    def direct_connect(self):
        return self.protocol.direct_connect(self)

    def _get_invisible(self):
        return bool(self.user_class & 0x00000100)

    def _set_invisible(self, invis):
        if invis:
            self._user_class |= 0x00000100
        else:
            self._user_class &= 0xFFFFFEFF

    invisible = ObservableProperty(_get_invisible, _set_invisible, observe = 'user_class')

    def _get_stripped_msg(self):
        msg = strip_html2(self.status_message or '')
        try:
            return msg.decode('xml')
        except Exception:
            return msg

    stripped_msg = ObservableProperty(_get_stripped_msg, observe = 'status_message')

    def get_status_message(self):
        if self.away and self.away_msg and self.away_msg.strip():
            return aim_to_xhtml(magic_string_repl(self.away_msg, self))
        elif self.avail_msg and self.avail_msg.strip():
            return aim_to_xhtml(magic_string_repl(self.avail_msg.encode('xml'), self))
        else:
            return None

#    def get_status_message(self):
#        if getattr(self, '_cached_status_message', None) is None:
#            self._cached_status_message = self._cache_status_message()
#
#        return self._cached_status_message

    def set_status_message(self, val):
        if not isinstance(val, (basestring, type(None))):
            raise TypeError(str(type(val)))
        self.away_msg = self._avail_msg = val

    status_message = ObservableProperty(get_status_message, set_status_message,
                                        observe = ['away_msg', '_avail_msg'])


    def _mobile(self):
        # Don't include self buddy as it can never be mobile if we are logged in - however,
        # something gets confused sometimes and it appears mobile without this check.
        return (len(self.capabilities) == 0) and (self.user_class and (self.user_class & 0x80 != 0)) and self.protocol.self_buddy != self
    mobile = ObservableProperty(_mobile, observe = 'user_class')

    def _set_online_time(self, val):
        if isinstance(val, str) and len(val) == 4:
            self._online_time = time.time() - struct.unpack('!I', val)[0]
        else:
            self._online_time = val

    def _get_online_time(self):
        return self._online_time

    online_time = ObservableProperty(_get_online_time, _set_online_time, observe = '_online_time')

    def __str__(self):
        return self.name

    def __cmp__(self, other):

        if not isinstance(other, self.__class__):
            return -1

        a, b = oscar._lowerstrip(self.name), oscar._lowerstrip(other.name)
        return cmp(a,b)

    def get_buddy_icon(self):
        self.protocol.get_buddy_icon(self.name)

    @property
    def blocked(self):
        if not self.protocol.icq:
            return oscar._lowerstrip(self.name) in self.protocol.block_list
        else:
            return oscar._lowerstrip(self.name) in self.protocol.ignore_list

    @property
    def pending_auth(self):
        '''Subclasses can override this to indicate that the buddy is waiting
        for a user's authorization.'''
        return False

    def get_remote_alias(self):
        a = getattr(self, 'nick', None)

        if not a:
            a = '%s %s' % (getattr(self, 'first', ''), getattr(self, 'last', ''))
            a = a.strip() or None

        return a

    remote_alias = oproperty(get_remote_alias, observe=['first', 'last', 'nick'])

    first = cproperty()
    last  = cproperty()
    nick  = cproperty()
    personal = cproperty()
    work = cproperty()

    def get_alias(self):
        # overridden from Buddy.alias property to show nice_name
        val = None
        a = profile.get_contact_info(self, 'alias')
        if a and a.strip():
            val = a
        else:
            for attr in ('local_alias', 'remote_alias', '_friendly_name', 'nice_name'):
                val = getattr(self, attr, None)
                if val:
                    break
            else:
                val = self.name

        return val.decode('fuzzy utf-8')

    alias = oproperty(get_alias, observe = ['local_alias', 'remote_alias', 'nice_name'])

    @callsback
    def block(self, set_blocked=True, callback = None):
        return self.protocol.block(self, set_blocked, callback = callback)

    @callsback
    def unblock(self, callback = None):
        return self.block(False, callback = callback)

    def permit(self, set_allowed=True):
        return self.protocol.permit(self, set_allowed)

    def unpermit(self):
        return self.permit(False)


    def warn(self, anon=True):
        return self.protocol.warn(self, anon)


class OscarBuddies(ObservableDict, FilterDict):
    _dead = False

    def __init__(self, protocol):
        ObservableDict.__init__(self)
        FilterDict.__init__(self, oscar._lowerstrip)
        self.protocol = protocol

    def __getitem__(self, k):
        #you shouldn't be getting a buddy from a disconnected protocol
        #note: this assert will get hit if you disconnect while still logging in.
        assert not self._dead
        try:
            return FilterDict.__getitem__(self, k)
        except (KeyError,):
            return self.setdefault(self.ff(k), OscarBuddy(k, self.protocol))

    def update_buddies(self, infos):
        'Updates one or more buddies.'

        for info in infos:
            self[info.name].update(info)

    def kill(self):
        self._dead = True

