#__LICENSE_GOES_HERE__

import common
import logging
from skypekit import SkypeKit
import SkyLib
from contacts import Group, Contact
from util.observe import observable_dict
from common.Protocol import OfflineReason
from common.Buddy import Buddy
from .skylibchat import SkyLibConversation

APP_TOKEN = ''.join('''
AAAgBobH4q2OPAaCX6vWseC82MmHZ1Cpayj61rbYlh0uenHxFByJ/lLu9HSN5nT3TjS91/2RQMAS
lCmZUCM5zINkR3nQ1240JpB0yNfYfzxXm8EyE9p9gWAGU7spUMvuROxoQR0042VUR4dCRW/kYr3y
eYiYOXW0poxxwg+esEbX8W1tqing25kfjUVsij6+T+dxtV8t/B1yGpTiT1okj9FoBvZgnwDoEGEy
wG5xeJTGLuFtHGALqa7gwvj9rulf7TuM1Q==
'''.split())

def GetSkypeKit(port):
    kit = SkypeKit(has_event_thread = True, host = '127.0.0.1',
                   port = port, logging_level = logging.NOTSET, logtransport = False)
    kit.logger = logging.getLogger('SkypeKitLogger')
    kit.logger.setLevel(logging.INFO)
    return kit

libs = {}

def GetSkyLib(port):
    global libs
    if port in libs:
        return libs[port]
    lib = SkyLib.SkyLib(GetSkypeKit(port))
    lib.SetApplicationToken(APP_TOKEN)
    libs[port] = lib
    return lib

class SkyLibOfflineReasons(OfflineReason):
    pass

DIGSBY_REASON_MAP = {
    'LOGOUT_CALLED'                                     : 'NONE',
    'HTTPS_PROXY_AUTH_FAILED'                           : 'CONN_FAIL',
    'SOCKS_PROXY_AUTH_FAILED'                           : 'CONN_FAIL',
    'P2P_CONNECT_FAILED'                                : 'CONN_FAIL',
    'SERVER_CONNECT_FAILED'                             : 'CONN_FAIL',
    'SERVER_OVERLOADED'                                 : 'CONN_LOST',
    'DB_IN_USE'                                         : 'CONN_FAIL',
    'INVALID_SKYPENAME'                                 : 'BAD_PASSWORD',
    'INVALID_EMAIL'                                     : 'BAD_PASSWORD',
    'UNACCEPTABLE_PASSWORD'                             : 'BAD_PASSWORD',
    'SKYPENAME_TAKEN'                                   : 'BAD_PASSWORD',
    'REJECTED_AS_UNDERAGE'                              : 'BAD_PASSWORD',
    'NO_SUCH_IDENTITY'                                  : 'BAD_PASSWORD',
    'INCORRECT_PASSWORD'                                : 'BAD_PASSWORD',
    'TOO_MANY_LOGIN_ATTEMPTS'                           : 'RATE_LIMIT',
    'PASSWORD_HAS_CHANGED'                              : 'BAD_PASSWORD',
    'PERIODIC_UIC_UPDATE_FAILED'                        : 'CONN_LOST',
    'DB_DISK_FULL'                                      : 'CONN_FAIL',
    'DB_IO_ERROR'                                       : 'CONN_FAIL',
    'DB_CORRUPT'                                        : 'CONN_FAIL',
    'DB_FAILURE'                                        : 'CONN_FAIL',
    'INVALID_APP_ID'                                    : 'CONN_FAIL',
    'APP_ID_BLACKLISTED'                                : 'CONN_FAIL',
    'UNSUPPORTED_VERSION'                               : 'CONN_FAIL',
    }

for key in SkyLib.Account.LOGOUTREASON:
    if isinstance(key, bytes):
        setattr(SkyLibOfflineReasons, key, key)
    for k,v in DIGSBY_REASON_MAP.items():
        setattr(SkyLibOfflineReasons, k, getattr(OfflineReason, v))

class SkyLibProtocol(common.protocol):
    name = service = protocol = 'skype'
    Reasons = SkyLibOfflineReasons

    @property
    def caps(self):
        from common import caps
        return [caps.INFO, caps.IM]

    def set_buddy_icon(self, *a, **k):
        pass

    def __init__(self, username, password, msgHub, server=None,
                 login_as='online', *a, **k):
        super(SkyLibProtocol, self).__init__(username, password, msgHub)
        self.skylib = None
        self.skyacct = None
        self.root_group = Group('Root', self, 'Root')
        self.buddies = observable_dict()
        self.conversations = observable_dict()

    def Connect(self, invisible=False):
        import skylibdriver
        port = skylibdriver.start(self)
        import time; time.sleep(2)
        self.skylib = GetSkyLib(port)
        self.skyacct = self.skylib.GetAccount(self.username)
        self.skyacct.OnPropertyChange = self.OnPropertyChange
        self.skyacct.LoginWithPassword(self.password, False, False)

    def OnConversationListChange(self, conversation, type, added):
        if type != 'DIALOG':
            return
        if not added:
            return
        for p in conversation.GetParticipants():
            b = self.get_buddy(p.identity)
            if b is not self.self_buddy and b not in self.conversations:
                convo = self.conversations.setdefault(b,
                                  SkyLibConversation(self, b))
                convo.buddy_join(self.self_buddy)
                convo.buddy_join(b)

    def OnPropertyChange(self, prop):
        print self, prop, getattr(self.skyacct, prop)
        if prop == 'status' and self.skyacct.status in ('LOGGED_IN', 7):
            self.change_state(self.Statuses.LOADING_CONTACT_LIST)
            self.self_buddy = SkypeBuddy(self.skylib.GetContact(
                                         self.skyacct.skypename), self)
            d = {self.self_buddy.name:  self.self_buddy}
            g = []
            for c in self.skylib.GetHardwiredContactGroup('SKYPE_BUDDIES').GetContacts():
                b = SkypeBuddy(c, self)
                d[b.name] = b
                g.append(Contact(b, b.name))
            self.buddies.update(d)
            with self.root_group.frozen():
                self.root_group[:] = g
            self.cs = []
            for c in self.skylib.GetConversationList('ALL_CONVERSATIONS'):
                c.OnMessage = self.a_message
                self.cs.append(c)
            self.change_state(self.Statuses.ONLINE)
        if prop == 'status' and self.skyacct.status == 'LOGGED_OUT':
            print self.skyacct.logoutreason
            self.set_offline(getattr(self.Reasons, self.skyacct.logoutreason))

    def Disconnect(self):
        self.skyacct.Logout(True)
        super(SkyLibProtocol, self).Disconnect()

    def get_buddy(self, name):
        return self.buddies[name]

    def convo_for(self, buddy):
        if not isinstance(buddy, SkypeBuddy):
            buddy = buddy.buddy
        if buddy in self.conversations:
            convo = self.conversations[buddy]
        else:
            convo = self.conversations.setdefault(buddy,
                         SkyLibConversation(self, buddy))
            convo.buddy_join(self.self_buddy)
            convo.buddy_join(buddy)
        return convo

    def set_invisible(self, invisible):
        self.invisible = invisible
        self.set_message(None, 'invisible')

    def set_message(self, message, status, format = None, default_status='away'):
#        state = self.status_state_map.get(status.lower(), default_status)
        if status.lower() == 'away':
            a = 'AWAY'
        else:
            a = 'ONLINE'
        if getattr(self, 'invisible', False):
            a = 'INVISIBLE'
        self.skyacct.SetAvailability(a)
        if message is not None:
            self.skyacct.SetStrProperty('mood_text', message)

    def a_message(self, message):
        print message
#        if message.type != 'POSTED_TEXT':
#            return
        buddy = self.get_buddy(message.author)
        assert buddy not in self.conversations
        convo = self.convo_for(buddy)
        convo.OnMessage(message)

DIGSBY_AVAILABLE_MAP = {
    'UNKNOWN'                                           : 'unknown',
    'PENDINGAUTH'                                       : 'unknown',
    'BLOCKED'                                           : 'unknown',
    'BLOCKED_SKYPEOUT'                                  : 'unknown',
    'SKYPEOUT'                                          : 'available',
    'OFFLINE'                                           : 'offline',
    'OFFLINE_BUT_VM_ABLE'                               : 'offline',
    'OFFLINE_BUT_CF_ABLE'                               : 'offline',
    'ONLINE'                                            : 'available',
    'AWAY'                                              : 'away',
    'NOT_AVAILABLE'                                     : 'away',
    'DO_NOT_DISTURB'                                    : 'away',
    'SKYPE_ME'                                          : 'available',
    'INVISIBLE'                                         : 'invisible',
    'CONNECTING'                                        : 'available',
    'ONLINE_FROM_MOBILE'                                : 'available',
    'AWAY_FROM_MOBILE'                                  : 'away',
    'NOT_AVAILABLE_FROM_MOBILE'                         : 'away',
    'DO_NOT_DISTURB_FROM_MOBILE'                        : 'away',
    'SKYPE_ME_FROM_MOBILE'                              : 'available',
    }

class SkypeContact(Contact):
    pass

class SkypeBuddy(Buddy):
    service = 'skype'

    def __init__(self, skylib_contact, protocol):
        self.skycontact = skylib_contact
        self.skycontact.OnPropertyChange = self.OnPropertyChange
        self._status_message = None
        super(SkypeBuddy, self).__init__(self.skycontact.skypename, protocol)

    def OnPropertyChange(self, prop):
        if prop == 'availability':
            self.notify('status')

    @property
    def status(self):
        return DIGSBY_AVAILABLE_MAP[self.skycontact.availability]

    @property
    def status_message(self):
        if self._status_message is not None:
            return self._status_message
        return self.skycontact.mood_text or ''

    @status_message.setter
    def status_message(self, val):
        self._status_message = val

    @property
    def idle(self):
        return False

    @property
    def online(self):
        return self.status not in ('offline', 'unknown')

    @property
    def mobile(self):
        return 'MOBILE' in self.skycontact.availability

    @property
    def away(self):
        return self.status == 'away'

    @property
    def blocked(self):
        return 'BLOCKED' in self.skycontact.availability
