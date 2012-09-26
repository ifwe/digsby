'''
buddyliststore.py

    Stores buddylist information.

Blobs:
    This object's data BLOB (accessible on the console as "profile.buddylist")
    is sent/received in save_data and update_data.

Sorting:
    See contacts/buddylistsort.py and ext/src/BuddyList.

Ordering:
    The "rearrange" and "rearrange_group" methods order the buddylist manually.
    The relevant attribute is the "self.order" dictionary, which has the
    following structure:

    self.order = \
    { 'contacts':                        # Stores contact ordering
        { groupname1_lowercase:
            [ buddy1_idstring
              buddy2_idstring
              buddy3_idstring ]
          groupname2_lowercase: ...
        }
      'groups':                          # Stores group ordering
          [ group1_lower
            group2_lower
            group3_lower ]
    }

    idstrings come from the Contact.idstr() which generally does the right
    thing unless they need to be overridden in the Protocol's more specific
    contact object.

    Rearranging methods take an object to move, an object to move _near_, and
    a string specifying "above" or "below." This makes it easy to maintain
    "relative" order through an interface that may be filtering any number
    of elements before they're shown visually.

Contact Info:
    "Contact Info" refers to server-side extraneous information stored about a
    buddy, like email, or an SMS number. Local things are maintained in a
    dictionary in self.info.

Metacontacts:
    See contacts/metacontacts.py and the MetaContactManager class.

'''
from __future__ import with_statement
from common.protocolmeta import protocols
from collections import defaultdict
from logging import getLogger;
log = getLogger('bliststore')
#tofromlog = getLogger('tofrom')

from contacts.Group import Group, DGroup, GroupTypes, remove_duplicate_contacts
from contacts.metacontacts import MetaContactManager, MetaContact
from contacts.buddylistfilters import FakeRootGroup
from operator import itemgetter
from traceback import print_exc
from util import Storage, RepeatTimer
from util.primitives.error_handling import try_this, traceguard
from util.primitives.funcs import Delegate, find, isiterable
from util.primitives.structures import oset
from util.cacheable import DiskCache
from util.threads.bgthread import on_thread
from contacts.buddylistsort import SpecialGroup
S = Storage
from copy import deepcopy
from util.observe import Observable
from common import profile, netcall, pref
import blist
import hooks
import metrics
import sort_model

from contacts.identity import Personality

import sys
import wx
import re
import warnings

offline_nonempty_group_re = re.compile('.*\(0/[^0](.*\))$')


DisplayGroup = (DGroup, )

# how often, in seconds, to sync buddylist blob changes with the server.
UPDATE_FREQ_SECS = 60 * 5

# the to/from list updates on a different timer that fires less frequently,
# since sending IMs can change it
TOFROM_UPDATE_FREQ_SECS = 30

SEARCH_CONTACTS_GROUPNAME = _('Contacts')

from contacts.dispatch import ContactDispatcher, default_tofrom

class BuddyListStore(Observable):
    '''
    Stores Metacontact and ordering information for the buddylist.

    conn_accts must be an observable list of connected accounts
    '''

    DROP_END       = object()
    DROP_BEGINNING = object()

    def get_status(self, name, service):
        p = Personality(name, service)
        return getattr(self, 'personalities', {}).get(p, 'available')

    def __init__(self, conn_accts):
        Observable.__init__(self)

        self.dirty = False
        self.sorting_paused = True

        #self._listen_for_pref_load()

        self.rebuild_timer = wx.PyTimer(self.rebuild_later)
        self.rebuild_timer.StartRepeating(500)

        # Holds the final view that goes into the TreeList.
        self.view = DGroup('__root__', [], [])
        self.info = {}

        # Rootgroups are the "protocol" rootgroups with the original,
        # unmodified versions of the buddy list structure for each account
        self.rootgroups = []

        self.base_attrs = frozenset([None, 'alias', 'status', 'status_message', 'icon', 'icon_hash', 'entering', 'leaving', 'idle', 'away','mobile'])
        self.attrs = set(self.base_attrs)

        # conn_accts must be an observable list of connected accounts
        conn_accts.add_observer(self.on_connections_changed)

        self.metacontacts = MetaContactManager(self)
        self._init_order()
        self.contact_info_changed = Delegate()

        self.dispatch = ContactDispatcher()
        self.caches = dict(tofrom = DiskCache('im_history.dat', validator = validate_tofrom))
        self.load_local_data()

        # save local to/from data on exit
        hooks.register('digsby.app.exit', self.save_local_data)

        self._search_by = u''
        self._search_results = (0, 0) # number of contacts found in last two searches

        #todo: make then_bys based on a pref
        self.sort_models = sort_model.build_models(
                               then_bys = 1,
                               obj = self)
        self.sbw = sort_model.SortByWatcher(self.sort_models)

    def get_tofrom_copy(self):
        return self.dispatch.get_tofrom_copy()

    def _listen_for_pref_load(self):
        # resort checks profile.prefs_loaded to make sure we actually have prefs
        # before constructing the sorter. (there are events that can happen that
        # trigger a resort before prefs are loaded.) make sure to rebuild once
        # prefs are actually in.
        def on_prefs(_prefs):
            if getattr(self, '_prefs_did_load', False):
                return

            self._prefs_did_load = True
            self.rebuild()

        hooks.register('blobs.update.prefs', on_prefs)

    def __repr__(self):
        return '<BuddyListStore (%d metacontacts)>' % len(self.metacontacts)

    def contact_for_id(self, idstr):
        '''Returns a contact object for an idstr

        digsby/kevin@digsby.org/aaron@digsby.org => Contact
        '''

        _protocol_name, username, name = idstr.split('/')

        for acct in profile.account_manager.accounts:
            if acct.name == username and acct.connection:
                return acct.connection.buddies[name]

    def buddy_changed(self, buddy, attr):
        if attr is None or attr in self.attrs:
            self.rebuild()

    def contact_for_idstr(self, idstr):
        '''
        Returns a buddy object for a unique buddy id string. (See
        Buddy.idstr)
        '''
        contact = self.metacontacts.forid(idstr)
        if contact is None:
            service, acct_username, buddy_name = idstr.split('/')

            for acct in profile.connected_accounts:
                if acct.connection.username == acct_username and acct.protocol == service:
                    contact = acct.connection.get_buddy(buddy_name)
                    if contact is not None:
                        break

        return contact

    def online_popular_buddies(self):
        if not hasattr(blist, 'getLogSizes'):
            warnings.warn('this platform doesnt have blist.getLogSizes implemented yet')
            return []

        try:
            logsizes = self._logsizes
        except AttributeError:
            logsizes = self._logsizes = sorted(blist.getLogSizes(profile.logger.OutputDir).iteritems(),
                                               key=itemgetter(1), reverse=True)

        # combine log sizes for metacontacts
        logsizemap = defaultdict(int)
        for c, l in logsizes:
            contacts = self.contacts_for_nameservice([c])
            if contacts and contacts[0] is not None:
                logsizemap[contacts[0]] += l

        return [c for c, l in sorted(logsizemap.iteritems(), key=itemgetter(1), reverse=True)]

    def contacts_for_nameservice(self, nameservice_seq):
        metacontacts = self.metacontacts
        conn_accts = profile.connected_accounts
        contacts = []

        for nameserv in nameservice_seq:
            contact = metacontacts.forid(nameserv)
            if contact is None:
                i = nameserv.rfind('_')
                if i != -1:
                    name, service = nameserv[:i], nameserv[i+1:]

                    for acct in conn_accts:
                        try:
                            compat = im_service_compatible(acct.protocol, service)
                        except KeyError:
                            pass
                        else:
                            if compat:
                                proto = acct.connection
                                if proto is not None:
                                    if proto.has_buddy_on_list(S(name=name, service=service)):
                                        contact = proto.get_buddy(name)
                                        if contact is not None:
                                            break

            contacts.append(contact)

        return contacts

    def track_personalities(self, rootgroups):
        # collect IM contacts
        personalities = {}

        for root in rootgroups:
            for group in root:
                proto = root.protocol
                if isinstance(group, GroupTypes):
                    for contact in group:
                        ident = Personality(contact.name, contact.service)

                        try:
                            personalities[ident].add(proto)
                        except KeyError:
                            personalities[ident] = set([proto])
                else:
                    contact = group
                    ident = Personality(contact.name, contact.service)
                    try:
                        personalities[ident].add(proto)
                    except KeyError:
                        personalities[ident] = set([proto])

        return personalities

    def on_buddylist(self, buddy):
        personality = Personality(buddy.name, buddy.service)

        try:
            protos = self.personalities[personality]
        except KeyError:
            return False
        else:
            return len(protos) > 0

    Groupers = dict(status = 'ByStatus',
                    service = 'ByService')

    Sorters = dict(none    = 'UserOrdering',
                   name    = 'Alias',
                   log     = 'LogSize',
                   service = 'Service',
                   status  = 'Status',
                   online  = 'Online')

    BuddySortAttrs = dict(name = 'alias',
                          log  = 'log_size',
                          service = 'service')

    def _setup_blist_sorter(self):
        if hasattr(self, 'new_sorter'):
            return

        blist.set_group_type((DGroup, Group, MockGroup))
        self.new_sorter = blist.BuddyListSorter()
        self.update_order()

        # link prefs
        cb = self._on_blist_sort_pref
        link = profile.prefs.link
        for prefname in ('buddylist.fakeroot_name',
                         'buddylist.show_offline',
                         'buddylist.group_offline',
                         'buddylist.show_mobile',
                         'buddylist.hide_offline_groups',
                         'buddylist.sortby'):
            link(prefname, cb)

        cb()
        assert on_thread('sorter').now
        self._reconfig_sorter(False)

    def search(self, s, cb = None):
        if not hasattr(self, 'new_sorter'):
            return
        assert isinstance(s, basestring)
        self._search_by = s
        self.reconfig_sorter(rebuild=False)
        self.rebuild_now()

        if cb is not None:
            on_thread('sorter').call(lambda: wx.CallAfter(cb, self._search_results))

    @property
    def search_string(self):
        return getattr(self, '_search_by', '')

    def _on_blist_sort_pref(self, val=None):
        self.reconfig_sorter()

    @on_thread('sorter')
    def reconfig_sorter(self, rebuild = True):
        self._reconfig_sorter(rebuild = rebuild)

    def _reconfig_sorter(self, rebuild = True):
        if not hasattr(self, '_rebuild_sorter_count'):
            self._rebuild_sorter_count = 0
        log.debug('rebuilding sorter %d', self._rebuild_sorter_count)
        self._rebuild_sorter_count += 1

        sorts = pref('buddylist.sortby')
        assert isinstance(sorts, basestring)
        sorts = sorts.split()

        search = getattr(self, '_search_by', '')

        s = self.new_sorter
        s.clearSorters()

        show_offline = pref('buddylist.show_offline')
        group_offline = pref('buddylist.group_offline')
        show_mobile = pref('buddylist.show_mobile')
        hide_offline_groups = pref('buddylist.hide_offline_groups')

        if search:
            # search by
            show_offline = True
            s.addSorter(blist.ByGroup(False, 2))
            s.addSorter(blist.BySearch(search, SEARCH_CONTACTS_GROUPNAME))
        else:
            if not sorts[0].startswith('*'):
                s.addSorter(blist.ByFakeRoot(pref('buddylist.fakeroot_name', default=_('Contacts'))))
            s.addSorter(blist.ByGroup(not sorts[0].startswith('*'), 2))


        #until status grouper can do it, always add a mobile filter.
        #mobile needs to happen before the status grouper (otherwise you may see a mobile group for now)
        if not search and not show_mobile:
            s.addSorter(blist.ByMobile(show_mobile))

        # Add any necessary groupers
        added_status_grouper = False
        if not search and sorts[0].startswith('*'):
            show_groups = True
            sorter = sorts[0][1:]
            grouper = self.Groupers.get(sorter)
            if grouper is not None:
                if sorter == 'status':
                    # pass showOffline flag to ByStatus grouper
                    args = (show_offline, )
                    added_status_grouper = True
                else:
                    args = ()

                grouper_obj = getattr(blist, grouper)(show_groups, *args)

                if sorter == 'service':
                    # Set group names on the ByService grouper
                    for service, protocolinfo in protocols.iteritems():
                        grouper_obj.setGroupName(service, protocolinfo['name'])

                s.addSorter(grouper_obj)

        # Comparators
        sorters = [blist.CustomOrder]

        if search:
            # move offline buddies to the bottom when searching, and sort alphabetically
            sorts = ['online', 'name']
        else:
            # If we're grouping offline buddies, or filtering them out,
            # and we didn't add a ByStatus grouper, then we need to add a simpler
            # ByOnline grouper that accomplish the same things.
            # And, btw, we're "always" grouping offline buddies, we need the counts.
            if not added_status_grouper:
                s.addSorter(blist.ByOnline(group_offline, show_offline))

        # Always sort by user order.
        if sorts[-1] != 'none':
            sorts.append('none')

        self.attrs = set(self.base_attrs)
        cmpnames = []
        for sort in sorts:
            if sort.startswith('*'):
                #continue
                sort = sort[1:]
            cmpname = self.Sorters[sort]
            cmpnames.append(cmpname)

            # make sure we rebuild when buddy attributes change that are important
            # to the sorter
            sort_attr = self.BuddySortAttrs.get(sort, None)
            if sort_attr is not None:
                self.attrs.add(sort_attr)

            sorters.append(getattr(blist, cmpname))

        log.debug('comparators are: %s', ', '.join(cmpnames))

        self.comparators = sorters
        s.setComparators(sorters)
        if pref('buddylist.hide_offline_dependant', False, bool):
            s.setPruneEmpty(not pref('buddylist.show_offline') and pref('buddylist.hide_offline_groups'))
        else:
            s.setPruneEmpty(pref('buddylist.hide_offline_groups'))

        if rebuild:
            self.rebuild_threaded()

    def rebuild(self, *a):
        'Triggers a full buddylist update.'

        if on_thread('sorter').now:
            # sorter thread should never trigger a rebuild
            return

        self.dirty = True

    def rebuild_later(self, *a):
        if not self.dirty: return
        self.dirty = False
        self.rebuild_threaded()

    def rebuild_now(self):
        self.dirty = False
        self.rebuild_threaded()

    @on_thread('sorter')
    def rebuild_threaded(self):
        if getattr(self, 'disable_gui_updates', False):
            return

        view = self.resort()
        wx.CallAfter(self.setnotify, 'view', view)

    def by_log_size(self):
        'Returns a list of MetaContacts and Contacts by log size.'

        sorter = blist.BuddyListSorter()
        sorter.addSorter(blist.ByGroup(False))
        sorter.addSorter(blist.ByOnline(True, False))
        sorter.setComparators([blist.LogSize])
        return remove_contacts_in_metacontacts(self.use_sorter(sorter))

    def safe_metacontacts(self, rootgroups, use_cached=False):
        default = lambda: DGroup('Root', [], [], [])
        if use_cached:
            try:
                return self.collected_metacontacts
            except AttributeError:
                pass

        try:
            self.collected_metacontacts = metacontacts = self.metacontacts.collect(*rootgroups)
        except Exception:
            # If there was an exception collecting metacontacts,
            # just proceed.
            print_exc()
            metacontacts = DGroup('Root', [], [], [])

        return metacontacts

    def use_sorter(self, sorter):
        rootgroups = [display_copy(g) for g in self.rootgroups if isinstance(g, GroupTypes)]
        newroots = rootgroups[:] + [self.safe_metacontacts(rootgroups, use_cached=True)]
        for i, root in enumerate(newroots):
            root.name = "Root" + str(i)
            root._root = True

        root = DGroup('none', [], [], newroots)
        sorter.set_root(root)
        view = get_view_from_sorter(sorter)
        for g in view:
            remove_duplicate_contacts(g)
        return view

    def resort(self, mock = False):
        assert on_thread('sorter').now

        rootgroups = [display_copy(g) for g in self.rootgroups if isinstance(g, GroupTypes)]
        self.personalities = self.track_personalities(rootgroups)

        metacontacts = self.safe_metacontacts(rootgroups)

        # Always collect metacontacts, but exit early here if sorting is paused.
        if self.sorting_paused:# or not profile.prefs_loaded:
            return

        metrics.event('Buddylist Sort')

        self._setup_blist_sorter()

        # invalidate all sorter knowledge of contacts.
        # results in more CPU usage, but until we put metacontact combining into the sorter
        # this might be necessary.
        self.new_sorter.removeAllContacts()

        newroots = rootgroups[:] + [metacontacts]
        for i, root in enumerate(newroots):
            root.name = "Root" + str(i)
            root._root = True
        root = DGroup('none', [], [], newroots)
        if mock: self.mock_root = make_mocklist(root)
        self.new_sorter.set_root(root)

        view = get_view_from_sorter(self.new_sorter)

        if getattr(self, '_search_by', ''):
            if len(view) > 0:
                contacts_group = view[0]

                # don't allow renaming, etc of the search "Contacts" group
                contacts_group._disallow_actions = True
                num_contacts = len(contacts_group)
            else:
                num_contacts = -1

            self._search_results = self._search_results[1], num_contacts
        else:
            if pref('buddylist.hide_offline_dependant', False, bool):
                hide_offline_groups = not pref('buddylist.show_offline') and pref('buddylist.hide_offline_groups')
            else:
                hide_offline_groups = pref('buddylist.hide_offline_groups')
            if hide_offline_groups:
                view[:] = filter((lambda g: not offline_nonempty_group_re.match(g.display_string)), view)

        for g in view: remove_duplicate_contacts(g)

        self.add_search_entries(view)

        hooks.notify('buddylist.sorted', view)

        return view

    def add_search_entries(self, view):
        search = getattr(self, '_search_by', '')
        if not search:
            return

        if not getattr(self, '_did_search_link', False):
            self._did_search_link = True
            profile.prefs.link('search.external', self.on_search_pref)

        from gui.searchgui import add_search_entries
        add_search_entries(view, search)

    def on_search_pref(self, val):
        self.rebuild_now()

    @on_thread('sorter')
    def set_fake_root(self, root):
        self.new_sorter.set_root(root)

        try:
            old_view = self._old_view
        except AttributeError:
            pass
        else:
            self.new_sorter._done_gather(old_view)

        self._old_view = _rootgroup = self.new_sorter._gather()
        view = _newsortgroups_to_dgroups(_rootgroup)
        wx.CallAfter(self.setnotify, 'view', view)

    def imaccts_for_buddy(self, buddy, contacts, force_has_on_list=False):
        '''
        For a buddy, returns a tuple of

        - the best account to IM that buddy from, given history (may be None)
        - a list of connected accounts which can message that buddy (may be empty)
        '''

        return self.dispatch.imaccts_for_buddy(buddy, contacts, force_has_on_list)

    #
    # buddylist ordering
    #

    def rearrange(self, clist_obj, area, to_group, drop_to):
        'Rearranges manual ordering.'

        with traceguard: log.info('moving %s %s %s', clist_obj, area, drop_to)

        self._update_order_from_sorter()

        # get the list of ordered keys for a group
        grp_key = to_group.groupkey()

        # HACK: effectively, groups that share a name with the fake root group do not exist.
        # side effect: if you rename the fake root group w/o being logged into another account that
        # has a group which shares it's name, the ordering for that group is lost.
        if grp_key.lower() == pref('buddylist.fakeroot_name', default=_('Contacts')).lower():
            grp_key = FAKE_ROOT_GROUP_KEY
        # end HACK.

        order = self.order['contacts'][grp_key]

        # rearrange a Contact, using it's idstr
        obj = clist_obj.idstr()

        # index of the thing you're moving, otherwise end
        i = try_this(lambda: order.index(obj), len(order))

        # index of where to insert
        if drop_to is self.DROP_BEGINNING:
            j = 0
        elif drop_to is self.DROP_END:
            j = len(order)
        else:
            j = try_this(lambda: order.index(drop_to.idstr()) +
                                     (1 if area == 'below' else 0), 0)

        #if destination is farther than current position,
        #we will leave a hole, account for it.
        if  j > i: j -= 1

        with traceguard:
            log.info('rearranging buddies in %s (groupkey=%s): %d -> %d',
                     to_group.name, grp_key, i, j)

        if i != len(order):
            order.pop(i)

        order.insert(j, obj)
        self._info_changed()
        self.update_order()
        self.rebuild_now()

    def rearrange_group(self, group, area, togroup):
        '''
        Move a group above or below another group.

        area should be "above" or "below"
        '''

        if not isinstance(group, DisplayGroup) or not isinstance(togroup, DisplayGroup):
            raise TypeError('group and togroup must be DisplayGroups: %r %r' % (group, togroup))

        order = self.order['groups']

        try: i = order.index(groupkey(group))
        except ValueError: found = False
        else: found = True


        #index of where to insert
        j = try_this(lambda: order.index(groupkey(togroup)) + (1 if area == 'below' else 0), 0)
        if found and j > i:
            j -= 1

        #log.info('moving group %r from %r to %r', group, i, j)

        if found:
            popped = order.pop(i)
        else:
            popped = groupkey(group)

        order.insert(j, popped)

        self._info_changed()
        self.update_order()
        self.rebuild_now()

    def merge_server_list(self, protocol):
        'Merges server-side changes with local data.'
        # from #513
        #x If a buddy is no longer in on the list, remove them from the merged buddy list
        #x If a buddy was added, add them to the merged buddy list object
        #x If a buddy is in another group, move them in the merged buddy list object
        #  If that buddy was in a metacontact, split them off as if the user did it (keeps events, sms numbers, email addresses of the metacontact)
        #x If a buddy is in a different position, move them as best as we can.

        root = getattr(protocol, 'root_group', None)
        if not root:
            log.error('merge_server_list: %s has no root_group', protocol)
            return False

        idstr_prefix = protocol.name + '/' + protocol.username

        # Contact orderings
        corder = self.order['contacts']

        # a set of all contact id strings
        all_contacts = set(c.idstr() for group in root if isinstance(group, DisplayGroup) for c in group)

        # lookup dict of { contact id string : metacontact entry }
        def cdict_to_idstr(s): return '/'.join([s['protocol'], s['username'], s['name']])

        metas = dict((cdict_to_idstr(contact_dict), (id, meta))
                     for id, meta in self.metacontacts.iteritems()
                     for contact_dict in meta['contacts'])

        for group in root:
            if not isinstance(group, DisplayGroup): continue
            order        = corder[group.groupkey()]
            server_order = [c.idstr() for c in group]

            # Add any new buddies from the server.
            before = None
            network_cids = set()
            for cid in server_order:
                network_cids.add(cid)

                try:
                    before = order.index(cid)
                except ValueError:
                    # this contact is new. insert it into the ordering at the
                    # correct location
                    order.insert(find(order, before) + 1, cid)
                    before = cid

            if protocol.contact_order:
                # attempt to order based on the server list as much as possible.
                order_lists(order, order_for_account(protocol, server_order))

            # if buddy is no longer in the buddy list, remove them
            for cid in list(order):
                if cid.startswith(idstr_prefix) and cid not in network_cids:
                    log.info(cid + ' has moved out of group %s', group.name)
                    if cid in metas:
                        # remove the contact from its metacontact, if it's in one.
                        self.metacontacts.remove(metas[cid][0], cid)

                    order.remove(cid)

        return True

    #
    # to/from history list
    #

    def add_tofrom(self, history_type, to, from_):
        'Add a new entry in the to/from history list.'

        self.dispatch.add_tofrom(history_type, to, from_)
        self._info_changed('tofrom_timer', TOFROM_UPDATE_FREQ_SECS)

    def get_from(self, tobuddy, connected=True):
        'Return the preferred account to message a buddy from, based on message history.'

        return self.dispatch.get_from(tobuddy, connected=connected)

    def get_tofrom_email(self, buddy):
        '''
        Given an email address, returns the last email account to have "Composed"
        an email to that address.
        '''

        return self.dispatch.get_tofrom_email(buddy)

    def get_tofrom_sms(self, buddy):
        return self.dispatch.get_tofrom_sms(buddy)

    def rename_group(self, old_name, new_name):
        '''
        Renames a group in the buddylist order.
        '''
        self._update_order_from_sorter()

        old_name = old_name.lower()
        new_name = new_name.lower()
        grps = self.order['groups']

        self.metacontacts.rename_group(old_name, new_name)
        try:
            i = grps.index(old_name)
        except ValueError:
            pass
        else:
            try:
                j = grps.index(new_name)
            except ValueError:
                grps[i] = new_name
            else:
                grps[i] = new_name
                grps.pop(j)
            self._info_changed()



    #
    # contact info methods
    #

    def set_contact_info(self, contact, attr, val):
        'Set server-side information for a contact.'

        _contact = contact

        if not isinstance(attr, basestring): raise TypeError('attr must be a string')

        if isinstance(contact, int):
            key = self.metacontacts.idstr(contact)
        else:
            key = getattr(contact, 'info_key', contact)

        if key is None:
            with traceguard:
                assert False, 'set_contact_info is trying to store data for a None contact: called with contact=%r, attr=%r, val=%r' % (_contact, attr, val)
            return

        log.info("info[%r][%r] = %r", key, attr, val)

        # None removes the key.
        if val is None:
            self.info[key].pop(attr, None)
        else:
            self.info[key][attr] = val

        self.contact_info_changed(key, attr, val)
        self._info_changed()

    def get_contact_info(self, contact, attr):
        'Get server-side information for a contact.'

        if isinstance(contact, int):
            contact = self.metacontacts.idstr(contact)

        key = getattr(contact, 'info_key', contact)

        if key in self.info:
            info = self.info[key]
            if attr in info:
                return info[attr]

    def remove_contact_info(self, contact):
        'Remove server-side information for a contact.'

        self._update_order_from_sorter()

        try:
            info_key = getattr(contact, 'info_key', contact)
            del self.info[info_key]

            found_one = False
            for l in self.order['contacts'].itervalues():
                if info_key in l:
                    l.remove(info_key)
                    found_one = True

            if found_one:
                self.update_order()
        except KeyError:
            log.info("remove_contact_info: there was no contact info for %s", contact)

    def on_connections_changed(self, *a):
        'Invoked when the DigsbyProfile connected_accounts attribute changes size.'

        accts = [a for a in profile.account_manager.accounts + [profile] if a.is_connected]

        log.info('connected accounts changed, getting root groups from %r', accts)

        rebuild = self.rebuild

        # unobserve all old rootgroups
        for grp in self.rootgroups:
            grp.remove_observer(rebuild)

        self.rootgroups = filter(lambda g: g is not None,
                                 [getattr(a.connection, 'root_group', None) for a in accts])

        # observe all new rootgroups
        for grp in self.rootgroups:
            grp.add_observer(rebuild)

        self.rebuild()

    #
    # server syncing
    #

    def _info_changed(self, timer_name = 'network_timer', update_frequency = UPDATE_FREQ_SECS):
        '''
        Called when information in the buddylist store object changes.

        It resets a timer, and every so many seconds after no changes have occurred,
        the changes are synced with the server.
        '''

        t = getattr(self, timer_name, None)
        if t is None:
            t = RepeatTimer(update_frequency, lambda: self._on_timer(timer_name))
            setattr(self, timer_name, t)
            t.start()
        else:
            t.reset()

    def _on_timer(self, timer_name):
        t = getattr(self, timer_name, None)
        if t is not None:
            t.stop()

        if timer_name == 'network_timer':
            log.info('timer fired. saving buddylist blob...')
            netcall(lambda: profile.save('buddylist'))
        elif timer_name == 'tofrom_timer':
            log.info('local timer fired. saving tofrom to disk')
            wx.CallAfter(self.save_local_data)
        else:
            assert False, 'invalid timer name'

    def reset_tofrom(self):
        '''clears tofrom data'''

        self.dispatch.set_tofrom(default_tofrom())
        self._info_changed('tofrom_timer', TOFROM_UPDATE_FREQ_SECS)

    def load_local_data(self):
        self.dispatch.set_tofrom(self.caches['tofrom'].safe_load(default_tofrom))
        log.info('TOFROM: loaded to/from data')

    def save_local_data(self):
        log.info('TOFROM: saving tofrom data')

        with self.dispatch.lock_all_data():
            self.caches['tofrom'].save(self.dispatch.tofrom)

    def update_data(self, data):
        """
        Updates this store's current state with incoming data from the network.

        data should be a mapping containing 'metacontacts', 'order', and 'info'
        structures (see comment at top of file)
        """
        rebuild = False

        # This method needs to substitute some defaultdicts for the normal
        # dictionaries that come back from the server.

        # Metacontact information

        #if data['metacontacts']
        mc_dict = data.get('metacontacts', {})
        if not isinstance(mc_dict, dict):
            log.critical('invalid metacontacts dictionary')
            mc_dict = {}

        # Contact information like SMS numbers and email addresses.
        self.info = defaultdict(dict)

        si = self.info
        if 'info' in data:
            for (k, v) in data['info'].iteritems():
                if isinstance(k, str):
                    cmpk = k.decode('utf8')
                else:
                    cmpk = k

                if not isinstance(cmpk, unicode):
                    continue

                if cmpk.startswith('Meta') or any((cmpk.endswith('_' + prot)
                                                   for prot in protocols.iterkeys())):
                    if any(v.values()):
                        si[k] = v

            for c, v in si.iteritems():
                for attr in ('email', 'sms'):
                    if attr in v:
                        self.contact_info_changed(c, attr, v[attr])

        self.metacontacts = MetaContactManager(self, mc_dict)
        if hasattr(self, 'new_sorter'):
            on_thread('sorter').call(self.new_sorter.removeAllContacts)
        rebuild = True

        # Manual ordering of groups
        try:
            self.order = deepcopy(data['order'])
            self.order['groups'] = list(oset(self.order['groups']))
            contacts = self._filtered_contacts()
            self.order['contacts'] = defaultdict(list)
            self.order['contacts'].update(contacts)
        except Exception:
            log.critical('error receiving order')
            self._init_order()

        # note: loading tofrom data from the network is deprecated. this data
        # now goes out to disk. see save/load_local_data
        if 'tofrom' in data and isinstance(data['tofrom'], dict) and \
            'im' in data['tofrom'] and 'email' in data['tofrom']:
            self.dispatch.set_tofrom(deepcopy(data['tofrom']))

        if rebuild:
            self.rebuild()

        self.update_order()

    @property
    def user_ordering(self):
        '''
        Returns True when the buddies should be partially ordered by their
        server-side ordering. (i.e., when the user has "None" selected)
        '''
        return all(cmp in (blist.CustomOrder, blist.UserOrdering) for cmp in getattr(self, 'comparators', ()))

    def update_order(self):
        'Sends order to the sorter.'

        if hasattr(self, 'new_sorter'):
            order = deepcopy(self.order['contacts'])
            order['__groups__'] = self.order['groups']
            on_thread('sorter').call(self.new_sorter.set_contact_order, order)

    def _update_order_from_sorter(self):
        'Retrieves order from the sorter.'

        # TODO: the sorter is not threadsafe. its internal contact order map needs a lock.

        if hasattr(self, 'new_sorter'):
            order = self.new_sorter.get_contact_order()
            self.order['groups'] = order.pop('__groups__', [])
            contacts = defaultdict(list)
            contacts.update(order)
            self.order['contacts'] = contacts

    def _filtered_contacts(self):
        return dict((groupname, filter(lambda c: not c.endswith('guest.digsby.org'), list(oset(ordering))))
                            for groupname, ordering in self.order['contacts'].iteritems())


    def _init_order(self):
        groups = []

        # Initialize a "group by status" order
        from contacts.buddylistsort import STATUS_ORDER
        for status in STATUS_ORDER:
            groups.append(SpecialGroup(status).groupkey())

        self.order = dict(groups   = groups,
                          contacts = defaultdict(list),
                          info     = {})

    def save_data(self):
        "Returns the data to saved to the Digsby server."

        self._update_order_from_sorter()

        return dict(metacontacts = self.metacontacts.save_data(),
                    order = dict(contacts = self._filtered_contacts(),
                                 groups   = self.order['groups']),

                    # leaves out default dict emptiness
                    info = dict(((k, v) for k, v in self.info.iteritems()
                                 if v and any(v.values()) and k is not None)))

    def set_sort_paused(self, paused):
        '''
        All sorting will be paused if you pass True.
        Passing False triggers a rebuild.
        '''
        if self.sorting_paused == paused:
            return

        self.sorting_paused = paused
        log.debug('setting sort paused: %r', paused)
        if not paused:
            # Call rebuild_threaded here, so the sort happens instantly, instead
            # of maybe after .5 secs.
            self.rebuild_now()

from common.protocolmeta import SERVICE_MAP

def display_copy(group):
    'Turns Groups into DGroups.'

    elems = []

    for elem in group:
        if isinstance(elem, Group):
            elems.append(display_copy(elem))
        else:
            elems.append(elem)

    return DGroup(group.name, [group.protocol], [group.id], elems)

# Return the unique "hash" for a group.
groupkey = lambda a: a.groupkey()

def _flatten(L, forbidden = ()):
    # some loop variables
    i, size = 0, len(L)

    while i < size:
        if isiterable(L[i]) and not isinstance(L[i], forbidden):
            L[i:i+1] = L[i]
            size = len(L)
        else:
            i += 1

    return L

def order_lists(seq, ref):
    def idx(seq, ref, elem):
        try:
            return ref.index(elem)
        except ValueError:
            try:
                return len(ref) + seq.index(elem)
            except ValueError:
                return len(ref)

    seq.sort(key = lambda elem: idx(seq, ref, elem))

def order_for_account(protocol, ordering):
    from util import repr_exception

    proto, un = protocol.name, protocol.username
    filtered = []

    for cid in ordering:
        if '/' not in cid and cid.startswith(MetaContact.idstr_prefix):
            pass
        else:
            with repr_exception(cid):
                protocol_name, username = cid.split('/')[:2]

            if proto == protocol_name and un == username:
                filtered.append(cid)

    return filtered

tofrom_entry_length = dict(
    im = 4,
    email = 3,
    sms = 3,
)

def validate_tofrom(tofrom):
    '''
    Validate the data in a "tofrom" dict.

    {'im': [('buddy', 'service', 'buddy', 'service'), ...],
     'email':
     'sms'}
    '''
    if not isinstance(tofrom, dict):
        raise TypeError('tofrom should be a dict, instead is a %r: %r' % (tofrom.__class__, tofrom))

    for key in ('im', 'email', 'sms'):
        for history_entry in tofrom[key]:
            if not isinstance(history_entry, list):
                raise TypeError

            entries = []
            if len(history_entry) != tofrom_entry_length[key]:
                raise TypeError('invalid length')
            elif not all(isinstance(s, basestring) for s in history_entry):
                raise TypeError('each history entry should be a sequence of strings')

    return tofrom

def im_service_compatible(to_service, from_service):
    '''
    Returns True if a buddy on to_service can be IMed from a connection to from_service.
    '''

    return to_service in protocols[from_service].compatible

def get_account_name(a):
    # TODO: profile.name is different than any other account.name in that it doesn't include name@digsby.org
    if a is profile():
        return a.name + '@digsby.org'
    else:
        return a.name

def rearrange_meta_by_first_online(metacontact):
    '''
    Given a metacontact, return a list of Contacts with the Metacontact's
    first_online buddy first.
    '''

    first = getattr(metacontact, 'first_online', None)

    if first is not None:
        metacontact = list(metacontact)
        try:
            metacontact.remove(first)
        except ValueError:
            pass
        metacontact.insert(0, first)

    return metacontact

def best_im_connection(metacontact, connected_accounts, tofrom):
    '''
    Returns a (buddy, connection) pair best suited for IMing with any of the buddies in metacontact,
    a sequence of buddy objects.

    "Best" here is defined as the most recent buddy you IMed, based on the to/from history.

    If a best contact cannot be found that way, then the first compatible connection (defined by the
    im_service_compatible function) with the first possible buddy in the metacontact sequence is
    returned.
    '''

    # Search for tobuddy in the listing of IM history
    for bname, bservice, fromname, fromservice in tofrom:
        for bud in metacontact:
            if bud.online and bud.name == bname and bud.service == bservice:
                # if listing found see if the associated account is online
                for acct in connected_accounts:
                    if get_account_name(acct) == fromname and acct.protocol == fromservice:
                        return bud, acct.connection

    # Make sure the first online buddy is first in the sequence.
    metacontact = rearrange_meta_by_first_online(metacontact)

    # If no to/from history could find an exact match for this buddy, see if
    # any currently connected accounts are compatible.
    for acct in connected_accounts:
        for bud in metacontact:
            if im_service_compatible(bud.service, acct.protocol):
                return bud, acct.connection

    return metacontact[0], None

FAKE_ROOT_GROUP_KEY = blist.fakeRootGroupKey()

class SortGroup(DGroup):
    def __init__(self, name, protocols = [], ids = [], groupkey=None,*children):
        DGroup.__init__(self, name, protocols, ids, *children)
        self._groupkey = groupkey

    def groupkey(self):
        if self._groupkey is None:
            return DGroup.groupkey(self)
        return self._groupkey

    def renamable(self):
        from gui.buddylist.buddylistrules import SpecialGroup_TEST
        if not SpecialGroup_TEST(self):
            return True
        #else: return None #(not visible)

def _newsortgroups_to_dgroups(g):
    '''
    While we transition to C++ sorting, we still need to make DGroups
    to keep the rest of Digsby happy.
    '''
    protocol_ids = g._protocol_ids

    if protocol_ids is not None:
        protos, ids = g._protocol_ids
    else:
        protos, ids = [], []

    children = []
    for elem in g:
        if isinstance(elem, blist.Group):
            elem = _newsortgroups_to_dgroups(elem)
        children.append(elem)

    groupkey = g.groupkey()
    if groupkey == FAKE_ROOT_GROUP_KEY:
        group = SpecialGroup(g.name, [None] + protos, ['__fakerootgroup__'] + ids, children)
        group.__class__ = FakeRootGroup
        assert group.groupkey() == groupkey
    else:
        group = SortGroup(g.name, protos, ids, groupkey, children)
    group._new_display_string = g.display_string
    return group

buddy_attrs = ('name', 'alias', 'log_size', 'status', 'service', 'mobile')

###

class MockBuddy(object):
    def __init__(self, **attrs):
        self.__dict__.update(attrs)
        self.attrs = attrs.keys()

    def __repr__(self):
        attrs_str = ', '.join('%s=%r' % (k, getattr(self, k))
                              for k in self.attrs)

        return 'MockBuddy(%s)' % attrs_str

    _notify_dirty = property(lambda self: True, lambda self, val: None)

def make_mockbuddy(b):
    buddy = MockBuddy(**dict((a, getattr(b, a)) for a in buddy_attrs))
    buddy.protocol = make_mockprotocol(b.protocol)
    buddy.attrs.append('protocol')

    return buddy

class MockGroup(list):
    def __init__(self, name, protocol, id, children=None):
        self.name = name
        self.protocol = protocol
        self.id = id
        if children:
            self[:] = children

    def __repr__(self):
        return 'MockGroup(%r, %r, %r, %s)' % \
                (self.name, self.protocol, self.id, list.__repr__(self))

def make_mockgroup(g):
    return MockGroup(g.name, make_mockprotocol(g.protocol), str(g.id))

class MockProtocol(object):
    def __init__(self, username, service):
        self.username = username
        self.service = service

    def __repr__(self):
        return 'MockProtocol(%r, %r)' % (self.username, self.service)

def make_mockprotocol(p):
    if p is None:
        return p

    return MockProtocol(p.username, p.service)

def make_mocklist(root):
    if isinstance(root, GroupTypes):
        res = make_mockgroup(root)
        res.extend([make_mocklist(c) for c in root])
    else:
        res = make_mockbuddy(root)

    return res

def mocklist():
    from common import profile

    profile.blist.resort(mock=True)
    return profile.blist.mock_root

def dump_elem_tree(e, indent = 0, maxwidth=sys.maxint):
    s = ''

    from contacts.Group import Group, DGroup
    import blist

    GroupTypes = (Group, DGroup, blist.Group)
    space = '  |-' * indent
    s += space
    if isinstance(e, GroupTypes):
        s += e.display_string[:maxwidth] + '\n'
        s += ''.join(dump_elem_tree(a, indent + 1, maxwidth) for a in e)
    else:
        s += repr(e)[:maxwidth] + '\n'

    return s

def get_view_from_sorter(sorter):
    _rootgroup = sorter._gather()
    try:
        view = _newsortgroups_to_dgroups(_rootgroup)

    finally:
        sorter._done_gather(_rootgroup)

        # tracebacks trying to repr(_rootgroup) will crash
        del _rootgroup

    return view

def remove_contacts_in_metacontacts(view):
    '''Removes any contacts in "view" that are also in MetaContacts in the view.'''

    metacontacts = set()
    for contact in view:
        if isinstance(contact, MetaContact):
            metacontacts.update(c for c in contact)
    return [c for c in view if c not in metacontacts]


