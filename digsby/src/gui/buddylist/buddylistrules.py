'''
rules for drag and drop feedback when moving items around on the buddylist
'''

from common import pref
from contacts.buddylistsort import SpecialGroup
from common import buddy
from contacts import Contact
from contacts.metacontacts import MetaContact
from contacts.Group import Group, DGroup
from common import profile
from contacts.buddylistfilters import OfflineGroup, FakeRootGroup

# TODO: don't import everything here. instead, have an interface that
# buddylist elements conform to.
from gui.searchgui import SearchEntry

SERVICES_WITHOUT_GROUPS = []

def user_ordering():
    '''
    Returns True if user ordering is affecting the current sort algorithm.
    '''

    return profile.blist.user_ordering

def can_drop_buddy_group(group):
    if SpecialGroup_TEST(group) and not FakeRootGroup_TEST(group):
        return False

    return user_ordering()

def above_below_middle(percent):
    border_space = pref('buddylist.border_space', 35) / 100.0

    if percent < border_space:
        return 'above'
    elif percent > 1 - border_space:
        return 'below'
    else:
        return 'middle'

def above_below(percent):
    if percent <= .50:
        return 'above'
    else:
        return 'below'

def buddy_buddy(model, frm, to, i, position, parent_position, percent):
    if position in ('above', 'below'):
        parent = model.parent_of(to)
        frmparent = model.parent_of(frm)
        if can_drop_buddy_group(parent) and not OfflineGroup_TEST(frmparent): #does this check sorting or not? I think probably. must also check what kind of group, duh.
#            to = parent
            return to, position
#            if position is 'above':
#                return buddy_group(model, frm, to, i, position='foo')
#            else:
#                return buddy_group(model, frm, to, i, position='foo')
        else:
            return buddy_buddy(model, frm, to, i, position='middle', parent_position=parent_position, percent=percent)
    elif position == 'middle':
        return to, 'middle' #yup, try to drop it on this buddy, though still decide if that's possible

def group_buddy(model, frm, to, i, position, parent_position, percent):
    to = model.parent_of(to)
    return group_group(model, frm, to, model.index_of(to), position, parent_position, percent)

def group_group(model, frm, to, i, position, parent_position, percent):
    #find position of cursor, group bounding box, recalculate percent.
    #if user ordering, then ok, except for offline group.
    if OfflineGroup_TEST(to):
        if i != 0:
            return item(model, frm, model[i-1], i-1, position='below', parent_position='below', percent=percent)
    return to, parent_position

def buddy_group(model, frm, to, i, position, parent_position, percent):
#    if not can_drop_buddy_group(to) and position in ('middle', 'below'):
#        return to, position
    if OfflineGroup_TEST(model.parent_of(frm)):
        return to, 'middle'

    if position == 'above':
        if i == 0: #hit the top of the list
            return to, 'middle' #target is group, position -1
        else:
            #if item above is a collapsed group, drop on this group
            if not model.is_expanded(i-1):
                return to, 'middle'
            else:
                return item(model, frm, model[i-1], i-1, position='below', parent_position=parent_position, percent=percent)
    elif position == 'below':
        #if item below is a collapsed group, drop on this group
        if not model.is_expanded(i):
            return to, 'middle'
        else:
            return to, 'below'
    elif position == 'middle':
        return to, 'middle'
    else:
        raise AssertionError, "buddy_group needs a valid" \
                              " position (above/below/middle), got %r" % position


BUDDY = (MetaContact, Contact, buddy)
GROUP = (DGroup, )

OFFLINEGROUP = (OfflineGroup,)

def OfflineGroup_TEST(obj):
    if isinstance(obj, OFFLINEGROUP):
        return True
    elif hasattr(obj, 'groupkey'):
        retval = obj.groupkey() == 'SpecialGroup_offlinegroup'
        return retval
    else:
        return False

def SpecialGroup_TEST(obj):
    if isinstance(obj, SpecialGroup):
        return True
    elif hasattr(obj, 'groupkey'):
        retval = obj.groupkey().startswith('SpecialGroup_')
        return retval
    else:
        return False

def FakeRootGroup_TEST(obj):
    return isinstance(obj, FakeRootGroup)

TYPES = (BUDDY, GROUP, SearchEntry)

def target_search(model, frm, to, i, position, parent_position, percent):
    return to, above_below(percent)

origin = {(BUDDY, BUDDY) : buddy_buddy,
          (BUDDY, GROUP) : buddy_group,
          (GROUP, BUDDY) : group_buddy,
          (GROUP, GROUP) : group_group,
          (SearchEntry, SearchEntry) : target_search,
          }

def to_type(obj):
    for typ in TYPES:
        if isinstance(obj, typ):
            return typ
    return sentinel

def item(model, frm, to, i, position=None, parent_position=None, percent=None):
    typ_to  = to_type(to)
    typ_frm = to_type(frm)
    if (typ_to, typ_frm) not in origin:
        return sentinel
    else:
        return origin[(typ_frm, typ_to)](model, frm, to, i, position, parent_position, percent)

def target(model, frm, to, i, percent, parent_percent):
    position = above_below_middle(percent)
    parent_position = above_below(parent_percent[1])
    result = item(model, frm, to, i, position, parent_position, percent)
    if result is sentinel:
        return to, DISALLOW
    return result

ITEM_BOX    = 'box'
GROUP_BOX   = 'group_box'
ABOVE       = 'above'
BELOW       = 'below'
BELOW_GROUP = 'below_group'
DISALLOW    = 'disallow'

FEEDBACK_TYPES = set([ITEM_BOX,
                      GROUP_BOX,
                      ABOVE,
                      BELOW,
                      BELOW_GROUP,
                      DISALLOW])


def feed_buddy_buddy(model, frm, to, position):
    assert position in ('above', 'middle', 'below')
    if getattr(to, 'iswidget', False):
        return DISALLOW
    if OfflineGroup_TEST(model.parent_of(to)) and not OfflineGroup_TEST(model.parent_of(frm)):
        return DISALLOW
    if getattr(frm, 'service', None) in SERVICES_WITHOUT_GROUPS and not isinstance(frm, MetaContact):
        return ITEM_BOX
    if position == 'middle':
        return ITEM_BOX
    return position

def feed_buddy_group(model, frm, to, position):
    assert position in ('middle', 'below')
    if getattr(frm, 'service', None) in SERVICES_WITHOUT_GROUPS and not isinstance(frm, MetaContact):
        return DISALLOW
    if SpecialGroup_TEST(to):
        if to.id == Group.FAKEROOT_ID:
            return GROUP_BOX
        else:
            return DISALLOW
    if OfflineGroup_TEST(model.parent_of(frm)):
        return DISALLOW
    if position == 'middle':
        return GROUP_BOX
    else:
        # based on user ordering
        if user_ordering():
            return BELOW
        else:
            return GROUP_BOX

def feed_group_buddy(model, frm, to, position):
    assert False
    pass

def feed_group_group(model, frm, to, position):
    assert position in (ABOVE, BELOW)
    if OfflineGroup_TEST(to):
        return DISALLOW
    if position == BELOW:
        return BELOW_GROUP
    return position


def feed_search(model, frm, to, position):
    if position == 'middle':
        return DISALLOW
    else:
        return position

feedback_types = {(BUDDY, BUDDY) : feed_buddy_buddy,
                  (BUDDY, GROUP) : feed_buddy_group,
                  (GROUP, BUDDY) : feed_group_buddy,
                  (GROUP, GROUP) : feed_group_group,
                  (SearchEntry, SearchEntry) : feed_search,
                  }

def feedback(model, frm, to, position):
    typ_to  = to_type(to)
    typ_frm = to_type(frm)
    if to is frm or not allow_drag(frm):
        return DISALLOW
    if (typ_to, typ_frm) not in feedback_types:
        return DISALLOW
    result = feedback_types[(typ_frm, typ_to)](model, frm, to, position)
    assert result in FEEDBACK_TYPES
    return result


def allow_drag(frm):
    if getattr(frm, 'iswidget', False):
        return False
    if OfflineGroup_TEST(frm):
        return False
    return True

