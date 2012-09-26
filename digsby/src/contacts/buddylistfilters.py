'''
Buddylist manipulators that rearrange and filter the buddylist before it makes
it to the screen.
'''

from contacts.Group import DGroup, Group
from contacts.buddylistsort import SpecialGroup
from common import pref

class OfflineGroup(SpecialGroup):
    'Used as a place to collect all offline buddies.'

    _renderer = 'DGroup'

    def __init__(self):
        DGroup.__init__(self, _('Offline'), [None], [Group.OFFLINE_ID], [])

    def __str__(self):
        return u'%s (%d)' % (self.name, len(self))

    def groupkey(self):
        return SpecialGroup.__name__ + '_' + type(self).__name__.lower()

class FakeRootGroup(SpecialGroup):
    '''Used as a place to collect buddies who aren't in other groups'''
    _renderer = 'DGroup'

    PREF = 'buddylist.fakeroot_name'
    PREFDEFAULT = _('Contacts')

    def __init__(self):
        DGroup.__init__(self, pref(self.PREF, default=self.PREFDEFAULT), [None], [Group.FAKEROOT_ID], [])

    def _rename(self, new_name, callback):
        self.name = new_name
        return SpecialGroup._rename(self, new_name, callback)

    def _get_name(self):
        return pref(self.PREF, default=self.PREFDEFAULT)

    def _set_name(self, new_val):
        if pref(self.PREF, default=self.PREFDEFAULT) != new_val:
            # calling setpref triggers a notify; only do it if it's different
            from common import setpref
            setpref('buddylist.fakeroot_name', new_val)

    def groupkey(self):
        return SpecialGroup.__name__ + '_' + type(self).__name__.lower()

    name = property(_get_name, _set_name)

    def renamable(self):
        return True


