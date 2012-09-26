from contacts.Group import DGroup
from common import pref
from logging import getLogger; log = getLogger('blistsort'); info = log.info

def grouping():
    s = pref('buddylist.sortby', 'none none').startswith

    return s('*status') or s('*service')

class SpecialGroup(DGroup):
    _renderer = 'DGroup'

    def groupkey(self):
        return self.__class__.__name__ + '_' + DGroup.groupkey(self)

    def renamable(self):
        return None


STATUS_ORDER = ['available',
                'away',
                'idle',
                'mobile',
                'invisible',
                'offline',
                'unknown']

STATUS_ORDER_INDEXES = dict((STATUS_ORDER[i], i) for i in xrange(len(STATUS_ORDER)))

