from __future__ import with_statement
from common.actions import action
from util.observe import ObservableList
from threading import RLock
import collections
from BuddyListElement import BuddyListElement
from itertools import izip

import traceback

from traceback import print_exc

from util.callbacks import callsback
from util.primitives.error_handling import traceguard
from util.primitives.funcs import do
from common import netcall

no_offline_group = lambda self, *a, **k: True if self.id != Group.OFFLINE_ID else None

def SpecialGroup_TEST(self, *a, **k):
    from gui.buddylist.buddylistrules import SpecialGroup_TEST
    return SpecialGroup_TEST(self)

from logging import getLogger
log = getLogger('groups')

class Group(BuddyListElement, ObservableList):
    'A Group. Represents a group on the protocol/network level.'

    OFFLINE_ID = '__digsbyoffline__'
    FAKEROOT_ID = '__fakerootgroup__'

    def __init__(self, name, protocol, id, *children):
        BuddyListElement.__init__(self)
        ObservableList.__init__(self, *children)
        self.name = name
        self.protocol = protocol
        self.id = id
        self.watching = set()

    def __str__(self):
        return u"%s (%d/%d)" % (self.name, self.num_online, len(self))

    def __repr__(self):
        try:
            return '<Group: %r [%s]>' % (self.name, u',\n'.join(repr(item) for item in self))
        except:
            return '<Group: ???>'

    @action(no_offline_group,
            needs = (unicode, 'buddyname'))
    def add_buddy(self, buddy_name, service=None):
        self.protocol.add_buddy(buddy_name, self.id, service=service)

    def __eq__(self, other):
        if self is other:
            return True
        elif hasattr(other, 'name') and self.name == other.name and (self is self.id or self.id == other.id):
            return ObservableList.__eq__(self, other)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def groupkey(self):
        return self.name.lower()

    def __hash__(self):
        'Something about this could be bad...'

        return hash(self.name)

class moving_truck(object):
    @callsback
    def __init__(self, size, callback=None):
        self.lock = RLock()
        self.size = size
        self.counter = 0
        self.successes = 0
        self.failures = 0
        self.callback = callback

    def success(self, *a, **k):
        with self.lock:
            self.counter += 1
            self.successes += 1
            self.check_done()

    def check_done(self):
        if self.counter == self.size:
            self.callback.success()
        elif self.counter > self.size:
            traceback.print_stack()
            raise AssertionError("too many results")

    def error(self, *a, **k):
        with self.lock:
            self.counter += 1
            self.failures += 1
            self.check_done()


class DGroup(BuddyListElement, ObservableList):
    '''
    Groups in multiple protocols with the same name.

    Instead of "protocol" and "id" it has "protocols" and "ids."
    '''

    inherited_actions = [Group]

    def __init__(self, name, protocols = [], ids = [], *children):

        if not isinstance(name, basestring):
            raise TypeError('name must be a string, it was %s' %type(name))
        if len(protocols) != len(ids):
            raise AssertionError('protocols and ids must have same length: '
                                 '%d %d' % (len(protocols), len(ids)))

        BuddyListElement.__init__(self)
        ObservableList.__init__(self, *children)

        # assert that the incoming name string is a unicode object, or can
        # be converted to one trivially
        self.name = unicode(name)

        self.protocols = protocols
        self.ids = ids
        self.id_lookup = dict(izip(protocols, ids)) # stores {protocol: id}

        # This will store the number of buddies moved out of this group during
        # the filter process so __str__ can still return an accurate offline
        # count.
        self._offline_moved = 0

        # Whether or not to show the offline count, i.e. the 6 in Buddies (5/6)
        self._show_offline_count = True

    @action(lambda self, *a, **k: (not SpecialGroup_TEST(self)) and no_offline_group(self, *a, **k) or None)
    def delete(self, force = False):
        from common import profile
        log.info('Deleting DGroup %r. force=%r', self.name, force)
        profile.blist.metacontacts.remove_group(self.name)

        if not force:
            to_move = profile.blist.metacontacts.contacts_for_group(self.name)
            to_move = filter(lambda c: c[0].get_group().lower() != c[1], to_move)
            if to_move:
                mover = moving_truck(len(to_move), success = lambda: self.delete(True))

                for contact, groupname in to_move:
                    log.info('Moving %r to %r', contact, groupname)
                    contact.move_to_group(groupname, success = mover.success,
                                          error = mover.error, timeout=mover.error)
                return

        errors = []
        for proto in self.protocols:
            try:
                log.info('Removing %r from %r', self.id_lookup[proto], proto)
                proto.remove_group(self.id_lookup[proto])
            except Exception, e:
                errors.append(e)
                traceback.print_exc()

        if errors:
            raise Exception(errors)


    @action(no_offline_group)
    def add_contact(self, name, account):
        if not isinstance(self.name, unicode):
            raise TypeError('DGroup.name must always be unicode')

        if not isinstance(name, basestring):
            raise TypeError('name must be a string: %s' % type(name))

        from common import profile
        import hub
        x = (name, account.connection.service)
        if x in profile.blist.metacontacts.buddies_to_metas:
            id = list(profile.blist.metacontacts.buddies_to_metas[x])[0].id
            m = profile.blist.metacontacts[id]
            alias = m.alias
            group = list(m.groups)[0][-1]
            message = _('That buddy is already part of metacontact '
                        '"{alias}" in group "{group}."').format(alias=alias, group=group)
            hub.get_instance().user_message(message, _('Add Contact'))


        if account.connection:
            proto = account.connection

            def do_add(groupid):
                proto.add_contact(name, groupid)
                self.protocols.append(proto)
                self.ids.append(groupid)
                self.id_lookup[proto] = groupid

            if proto not in self.protocols:
                # the group doesn't exist yet
                netcall(lambda: proto.add_group(self.name, success = do_add))
            else:
                # the group already exists.
                netcall(lambda: do_add(self.id_lookup[proto]))

    @callsback
    def remove_contact(self, buddy, callback = None):
        if buddy.protocol in self.protocols:
            netcall(lambda: buddy.protocol.remove_buddy(buddy, callback = callback))

    def renamable(self):
        return True

    @action(lambda self, callback=None: type(self).renamable(self))
    @callsback
    def rename_gui(self, callback = None):

        from gui.toolbox import GetTextFromUser
        new_name = GetTextFromUser(_('Enter a new name for {name}:'.format(name=self.name)),
                                           caption = _('Rename Group'),
                                           default_value = self.name)
        if not new_name:
            return callback.success()

        else:
            return self._rename(new_name, callback)

    def _rename(self, new_name, callback):
        old_name = self.name

        from common import profile
        profile.blist.rename_group(old_name, new_name)

        for protocol in self.protocols:
            if protocol is not None:
                with traceguard:
                    protocol.rename_group(self.id_lookup[protocol], new_name)

        self._fix_expanded_state(new_name)

        return new_name

    def _fix_expanded_state(self, new_name):
        # TODO: resolve this horrible layering violation

        # change the expanded state in the buddylist if necessary
        from gui.treelist import expanded_id
        import wx; blist = wx.FindWindowByName('Buddy List').buddyListPanel.blist
        collapsed = blist.model.collapsed

        eid = expanded_id(self)

        if eid in collapsed:
            # rename self and insert it's expanded ID back into the list
            collapsed.discard(eid)
            self.name = new_name
            collapsed.add(expanded_id(self))
        blist.model.update_list()

    @action()
    def add_group(self):
        from gui.protocols import add_group
        add_group()

    @property
    def protocol(self):
        #assert len(self.protocols) == 1, self.protocols
        return self.protocols[0] if self.protocols else None

    @property
    def id(self):
        return self.ids[0] if len(self.ids) else None

    def __repr__(self):
        try:
            return u'<%s %r %s>' % (type(self).__name__, getattr(self, 'name', '<no name>'), list.__repr__(self))
        except:
            try:
                traceback.print_exc_once()
            except:
                return '<DGroup (print_exc error)>'

            try:
                return '<%s %r ???>' % (type(self).__name__, self.name,)
            except:
                return '<DGroup ????>'

    def remove_duplicates(self, hash = lambda contact: contact.info_key):
        newlist = []
        unique  = set()

        for c in self:
            h = hash(c)
            if h not in unique:
                unique.add(hash(c))
                newlist.append(c)

        self[:] = newlist

    def __str__(self):
        try:
            # The new sorter sets this manually.
            return self._new_display_string
        except AttributeError:
            pass

        if not getattr(self, '_show_offline_count', True):
            from contacts import buddylistsort
            if buddylistsort.grouping() and self.name == 'Offline':
                return '%s (%d)' % (self.name, len(self))
            else:
                return '%s (%d)' % (self.name, self.num_online)
        else:
            return '%s (%d/%d)' % (self.name, self.num_online,
                                   len(self) + getattr(self, '_offline_moved', 0))

    def groupkey(self):
        return self.name.lower()

    @property
    def display_string(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.name)# + str(self.ids))

GroupTypes = (Group, DGroup)

def group_hash(g):
    name = g.name.lower()

    if hasattr(g, 'ids'):
        if g.ids == [Group.OFFLINE_ID]:
            name += g.id
    else:
        if g.id == Group.OFFLINE_ID:
            name += g.id

#    #TODO: ask chris why oscar's root group is named '' sometimes...

    return 'root' if name == '' else name

def remove_duplicate_contacts(group):
    from contacts.Contact import Contact

    if not isinstance(group, DGroup): return

    unique = set()
    i = 0
    for con in group[:]:
        if isinstance(con, Contact):
            chash = con.info_key

            if chash in unique:
                group.pop(i)
            else:
                unique.add(chash)
                i += 1
        else:
            i += 1

def merge_groups(root, grouphash=group_hash, depth=0):
    '''
    if hash(group1) == hash(group2) the contents of both are put
    into a new group.
    '''
    from contacts.metacontacts import MetaContact
    assert callable(grouphash)

    group_contents = collections.defaultdict(list)
    is_group = {True: [], False: []}
    do(is_group[isinstance(x, GroupTypes)].append(x) for x in root)
    ordered_names = []
    for g in is_group[True]:
        group_contents[grouphash(g)].append(g)
        if grouphash(g) not in ordered_names:
            ordered_names.append(grouphash(g))

    del root[:]

    newlist = []
    for _, groups in ((name, group_contents[name]) for name in ordered_names):
        # Create a DGroup which preserves information from the original
        # protocol groups.
        def plural(objects, attr):
            ret = []
            for g in objects:
                if hasattr(g, attr + 's'):
                    ret.extend(getattr(g, attr + 's'))
                else:
                    ret.append(getattr(g, attr))
            return ret

        protos = plural(groups, 'protocol')
        ids    = plural(groups, 'id')

        newgroup = DGroup(groups[0].name,   # Choose a name
                          protos, ids,      # All the protocols and ids
                          sum(groups, []))  # and all the contents.

        merged = merge_groups(newgroup, depth = depth+1)
        newlist.append(merged)

    root.extend(newlist)

    # remove "duplicate" contacts--that is, contacts with the same on the same
    # protocol that appear under different accounts. If functionality in the
    # right click menu is required, we'll have to make some kind of "DContact"
    # with multiple protocols.
    unique = set()
    for con in is_group[False]:
        chash = con.info_key
        if chash not in unique:
            unique.add(chash)
            root.append(con)

    return root

def remove_group(profile, group_name, force = False):
    group_name = group_name.lower()

    # Remove all metacontacts in this group.
    profile.blist.metacontacts.remove_group(group_name)

    def network(accts):
        for acct in accts:
            try:
                acct.connection.remove_group(group_name)
            except Exception, e:
                print_exc()

    netcall(lambda: network(profile.connected_accounts))

