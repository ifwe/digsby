from contacts.BuddyListElement import BuddyListElement
from common.Buddy import fileinfo
from util import strip_html,Storage #@UnresolvedImport

import common
import jabber
from common.actions import action #@UnresolvedImport
from common.Buddy import get_status_orb

GTALK = 'gtalk'
JABBER = 'jabber'

statuses=Storage(
    dnd=_('Do Not Disturb'),
    chat=_('Free for Chat'),
    xa=_('Extended Away')
)

def MOBILE_RESOURCES():
    if not common.pref('jabber.phone_is_mobile', type=bool, default=False):
        return []
    return ["android", "BlackBerry",
            "Mobile", #iphone
           ]

class JabberResource(BuddyListElement):
    __metaclass__ = common.ActionMeta
    def __init__(self, jabber, jid, presence):
        self.jid = jid
        self._set_presence(presence)
#        self.presence = presence
        self.name = self.jid.as_unicode()
        self.alias = self.name
        self.protocol = jabber
        self.sms = False

    def _set_presence(self, presence):
        self.status_msg = presence.get_status()
        self.show       = presence.get_show()
        self.priority   = presence.get_priority()


    def get_status_message(self):
        return self.status_msg

    def set_status_message(self, val):
        self.status_msg = val

    status_message = property(get_status_message, set_status_message)

    @property
    def stripped_msg(self):
        msg = self.status_message
        return strip_html(msg) if msg else u''

    @property
    def service(self):
        if self.jid.domain == 'gmail.com':
            return GTALK
        else:
            return JABBER

    @property
    def away(self):
        if self.away_is_idle:
            return not self.available and not self.idle
        else:
            return not self.available

    @property
    def available(self):
        return self.show in jabber.available_show_types

    @property
    def away_is_idle(self):
        return self.service == GTALK

    #begin crap to make MetaContact happy
    @property
    def idle(self):
        if self.away_is_idle:
            return self.show == "away"
        else:
            return False

    @property
    def mobile(self):
        return self.jid.resource is not None and any(self.jid.resource.startswith(r) for r in MOBILE_RESOURCES())

    @property
    def icon(self): return False

    @property
    def pending_auth(self): return False

    @property
    def online(self): return True

    @property
    def blocked(self): return False
    #end crap to make MetaContact happy

    @property
    def long_show(self): return None

    status_orb = property(lambda self: get_status_orb(self))


    @property
    def sightly_status(self):
        status=self.show
        if status:
            return statuses.get(status,status.title())
        else:
            return _('Available')


    def __repr__(self):
        return '<JabberResource %s>' % self.jid.as_unicode()

    @action()
    def send_file(self, filepath = None):
        if filepath is None:
            from hub import Hub
            filepath = Hub.getInstance().get_file('Sending file to %s' % self.name)

        if filepath:
            self.protocol.send_file(self, fileinfo(filepath))


