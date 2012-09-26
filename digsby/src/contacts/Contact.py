import traceback

from util import callsback
import common.actions
action = common.actions.action
ObservableActionMeta = common.actions.ObservableActionMeta
from common import profile
from logging import getLogger; log = getLogger('Contact')

objget = object.__getattribute__

CONTACT_ATTRS = set(['id', 'buddy', 'remove', 'watched', '__repr__',
                     'rename_gui', 'rename', 'edit_alerts', 'alias', 'get_group', 'move_to_group'
                     '__getattr__', '__hash__', '__cmp__', 'sort', '_notify_dirty',
                     ])

class Contact(object):
    '''
    Contact. Represents an entry on a protocol buddy list.

    Several contacts may point to the same Buddy object.
    Ex: AIM when a buddy is in 2+ groups - same buddy in both
    places but each has its own SSI.
    '''

    watched = 'online '.split()
    __metaclass__ = ObservableActionMeta

    def __init__(self, buddy, id):
        self.buddy, self.id = buddy, id
        self._metacontact = None

    def remove(self):
        self.protocol.remove_buddy(self.id)

    def _compatible_accounts(self):
        from common.protocolmeta import is_compatible
        result = []
        for account in profile.connected_accounts:
            if is_compatible(account.protocol, self.buddy.service):
                result.append(account)

        return result

    def _all_buddies(self, check_if_has=False):
        result = []
        for account in self._compatible_accounts():
            connection = account.connection
            if connection:
                if not check_if_has or connection.has_buddy(self.buddy.name):
                    # don't let a protocol create the buddy
                    buddy = connection.get_buddy(self.buddy.name)
                    if buddy is not None:
                        result.append(buddy)

        return result


    def _is_blocked(self):
        buddies = [buddy.blocked for buddy in self._all_buddies(check_if_has=True)]
        return bool(buddies and all(buddies))

    blocked = property(_is_blocked)

    def _block_pred(self, block=True, **k):
        return True if bool(block) ^ self._is_blocked() else None
    def _unblock_pred(self, *a, **k):
        return True if self._is_blocked() else None

    @action(_block_pred)
    def block(self, block=True, **k):
        for buddy in self._all_buddies():
            if bool(block) ^ bool(buddy.blocked):
                buddy.block(block, **k)

    @action(_unblock_pred)
    def unblock(self, *a,**k):
        self.block(False,*a,**k)

    def get_notify_dirty(self):
        return self.buddy._notify_dirty

    def set_notify_dirty(self, value):
        self.buddy._notify_dirty = value

    _notify_dirty = property(get_notify_dirty, set_notify_dirty)

    @action()
    def rename_gui(self):
        from gui.toolbox import GetTextFromUser

        localalias = self.alias
        if localalias is None:
            localalias = ''

        s = GetTextFromUser(_('Enter an alias for %s:') % self.name,
                                           caption = _('Rename %s') % self.name,
                                           default_value = localalias )
        if s is not None:
            if s == '' or s.strip():
                # dialog returns None if "Cancel" button is pressed -- that means do nothing

                # rename expects None to mean "no alias" and anything else to mean an alias--so
                # do the bool check to turn '' into None here.
                self.rename(s if s else None)
                return s

    def rename(self, new_alias):
        log.info('setting alias for %r to %r', self, new_alias)
        profile.set_contact_info(self, 'alias', new_alias)
        self.buddy.notify('alias')

    @action()
    def edit_alerts(self):
        import gui.pref.prefsdialog as prefsdialog
        prefsdialog.show('notifications')

    @property
    def alias(self):
        a = profile.get_contact_info(self, 'alias')
        if a: return a

        for attr in ('local_alias', 'remote_alias', 'nice_name'):
            try:
                a = getattr(self, attr, None)
            except Exception:
                traceback.print_exc()
                continue

            if a: return a

        return self.name

    def get_group(self):
        g = self.protocol.group_for(self)
        assert isinstance(g, (basestring, type(None))), 'Is %s' % type(g)
        return g

    @callsback
    def move_to_group(self, groupname, index = 0, callback = None):
        if not isinstance(groupname, basestring):
            raise TypeError, 'groupname must be a string: %r' % groupname

        self.protocol.move_buddy_creating_group(self, groupname, self.get_group(),
                                                index, callback = callback)

    def __getattr__(self, attr):
        if attr in CONTACT_ATTRS:
            return objget(self, attr)
        else:
            return getattr(objget(self, 'buddy'), attr)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.buddy)

    def __hash__(self):
        # First part of this hash should match Buddy.idstr()
        b = self.buddy
        id = self.id
        if isinstance(id, bytes):
            id = id.decode('fuzzy utf-8')
        return hash(u'/'.join((b.protocol.name, b.protocol.username, b.name, unicode(id))))

    def __cmp__(self, other):
        if self is other:
            return 0
        else:
            return cmp((self.buddy, self.id), (getattr(other, 'buddy', None), getattr(other, 'id', None)))

class ContactCapabilities:
    'Buddy capabilities. Exposed as common.caps'

    INFO          = 'INFO'

    IM            = 'IM'
    'Instant messaging.'

    FILES         = 'FILES'
    'Sending and receiving files.'

    PICTURES      = 'PICTURES'
    'Sharing pictures over a direct connection.'

    SMS           = 'SMS'
    'Sending messages directly to a cell phone.'

    BLOCKABLE     = 'BLOCKABLE'
    'Blocking buddies.'

    EMAIL         = 'EMAIL'
    'Sending email.'

    BOT = 'BOT'
    'User is a bot, and will join the Machines when Skynet turns on the human race. Be vigilant.'

    VIDEO = 'VIDEO'
    'Video chat.'
