from __future__ import with_statement
from util import autoassign
from common.slotssavable import ObservableSlotsSavable
from logging import getLogger; log = getLogger('statusmessage')

MAX_TITLE_CHARS = 60

def acct_reduce(account):
    'Return a string representation for an account.'

    return account.protocol + '_' + account.name

def proto_reduce(proto):
    return proto.name + '_' + proto.username

def simple(status_string, protocol):
    '''
    Given a status string like "Free For Chat", returns the "simplified"
    version, which is just 'available' or 'away'.
    '''

    from common.protocolmeta import protocols
    statuses = protocols[protocol.name].statuses
    if status_string in [s.lower() for s in statuses[0]]:
        return 'available'
    else:
        return 'away'

# Used to show the status (not the message) in the GUI.
nice_statuses = dict(
    online    = _('Available'),
    available = _('Available'),
    away      = _('Away'),
    invisible = _('Invisible'),
    offline   = _('Offline'),
)

class StatusMessage(ObservableSlotsSavable):
    'A saved status message with a title, a state, and possible exceptions.'

    __slots__ = 'title status message exceptions editable format edit_toggle'.split()

    online_statuses = ('online', 'available', 'free for chat')

    @classmethod
    def is_available_state(cls, state):
        if not isinstance(state, basestring):
            raise TypeError('is_available_state takes a string')

        return state.lower() in (s.lower() for s in cls.online_statuses)

    @classmethod
    def icon_for(cls, status):
        'Returns an icon for a status or status string.'

        from gui import skin
        return skin.get('statusicons.' + cls.icon_status(status))

    @classmethod
    def icon_status(cls, status):
        if isinstance(status, StatusMessage) or hasattr(status, 'status'):
            status = status.status

        status = status.lower()

        if cls.is_available_state(status):
            s = 'available'
        elif status == 'invisible':
            s = 'invisible'
        elif status == 'offline':
            s = 'offline'
        elif status == 'idle':
            s =  'idle'
        else:
            s = 'away'

        return s

    @property
    def icon(self):
        return self.icon_for(self.status)

    def __init__(self, title, status, message, exceptions = None, editable = True, format = None, edit_toggle = True, **k):
        ObservableSlotsSavable.__init__(self)

        if exceptions is None:
            exceptions = {}

        autoassign(self, locals())

        self.check_types()
        self.cap_title_len()

    def check_types(self):
        for attr in ('title', 'status', 'message'):
            if not isinstance(getattr(self, attr, None), basestring):
                setattr(self, attr, u'')
        from util.primitives import Storage
        if self.format is not None:
            assert isinstance(self.format, dict)
            if not isinstance(self.format, Storage):
                self.format = Storage(self.format)
        if not self.exceptions: #StatusMessageException's have a tuple
            return
        for ex,exobj in self.exceptions.items():
            if not isinstance(exobj, StatusMessage):
                assert isinstance(exobj, dict)
                self.exceptions[ex] = StatusMessageException(**exobj)

    @property
    def hint(self):
        return _(self.status)

    edit_toggle = True

    def __setstate__(self, *a, **k):
        ObservableSlotsSavable.__setstate__(self, *a, **k)
        self.check_types()
        self.cap_title_len()

    def __getstate__(self, network=False, *a, **k):
        ret = ObservableSlotsSavable.__getstate__(self, *a, **k)
        if ret['format'] is not None:
            ret['format'] = dict(ret['format'])
        exceptions = ret['exceptions']
        if network:
            ret.pop('edit_toggle', None)
        if not exceptions: #could be a tuple
            return ret
        exceptions = dict(exceptions) #do not want to change our own state
        for ex, exobj in exceptions.items():
            exceptions[ex] = exobj.__getstate__(network=network)
        ret['exceptions'] = exceptions
        return ret

    def cap_title_len(self):
        if len(self.title) > MAX_TITLE_CHARS:
            self.title = _('{truncatedtitle}...').format(truncatedtitle = self.title[:MAX_TITLE_CHARS])

    def copy(self, title = None, status = None, message = None, hint = None, editable=True, edit_toggle = True):
        if isinstance(self.exceptions, dict):
            exceptions = {}
            for key, ex in self.exceptions.iteritems():
                exceptions[key] = ex.copy(editable=None)
        else:
            assert self.exceptions == ()
            exceptions = self.exceptions
        return self.__class__(title = self.title   if title is   None else title,
                              status = self.status  if status is  None else status,
                              message = self.message if message is None else message,
                              exceptions = exceptions,
                              editable = (self.editable if editable is None else editable),
                              edit_toggle = (self.edit_toggle if edit_toggle is None else edit_toggle),
                              format   = self.format)

    @property
    def use_exceptions(self):
        '''
        Property is true if this status message has one or more exceptions
        defined.
        '''
        return bool(self.exceptions)

    @property
    def invisible(self):
        return self.status.lower() == StatusMessage.Invisible.status.lower()

    @property
    def offline(self):
        return self.status.lower() == StatusMessage.Offline.status.lower()

    @property
    def away(self):
        return not any((self.available, self.invisible, self.offline))

    @property
    def idle(self):
        return self.status == StatusMessage.Idle.status

    @property
    def available(self):
        return type(self).is_available_state(self.status)

    def for_account(self, acct):
        'Returns the status message (or exception) for a given Account or Protocol.'

        from common.Protocol import Protocol
        from digsbyprofile import Account, DigsbyProfile

        key = None
        if isinstance(acct, Protocol):
            key = proto_reduce(acct)
        elif isinstance(acct, Account):
            key = acct_reduce(acct)
        elif isinstance(acct, DigsbyProfile):
            pass
        else:
            log.error('Got unknown object for status message. object was %r (%r)', acct, type(acct))

        return self.exceptions.get(key, self)

    def ToggleStatus(self):
        self.status = 'Available' if self.away else 'Away'

        # TODO: this won't work after i18n
        if self.message in ('Available', 'Away'):
            self.message = self.status

    @property
    def nice_status(self):
        try:
            return nice_statuses[self.status.lower()]
        except KeyError:
            # TODO: On the Phone, etc?
            return nice_statuses['away']

    def __repr__(self):
        attrs = ', '.join('%s=%r' % (slot, getattr(self, slot, '')) for slot in self.__slots__)
        return '<%s %s>' % (type(self).__name__, attrs)

# Singleton status messages.
StatusMessage.Available  = StatusMessage(_('Available'),   'Available', u'')
StatusMessage.Away       = StatusMessage(_('Away'),        'Away',      u'')
StatusMessage.Idle       = StatusMessage(_('Idle'),        'Idle',      u'')
StatusMessage.Invisible  = StatusMessage(_('Invisible'),   'Invisible', u'', editable = False)
StatusMessage.Offline    = StatusMessage(_('Offline'),     'Offline',   u'', editable = False)

StatusMessage.SpecialStatuses = [
    StatusMessage.Available,
    StatusMessage.Away,
    StatusMessage.Idle,
    StatusMessage.Invisible,
    StatusMessage.Offline,
]

class StatusMessageException(StatusMessage):
    def __init__(self, status, message, format = None,
                 title=False, exceptions=False, editable=False, edit_toggle = False): #these four aren't used.
        StatusMessage.__init__(self, None, status, message, exceptions =(), format = format)

if __name__ == '__main__':

    st = StatusMessage('my title', 'my status', 'some message',
                       StatusMessageException('msn away', 'my msn is away'))
    st2 = StatusMessage('my title', 'my status', 'some message',
                       StatusMessageException('msn away', 'my msn is away'))

    print st.__hash__()
    print st2.__hash__()

    print st == st2
