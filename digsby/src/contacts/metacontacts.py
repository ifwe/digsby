'''
Logic and storage for metacontacts.
'''

from contacts.BuddyListElement import BuddyListElement
from contacts.Group import DGroup
from common.actions import action
from common import profile,pref
from util import callsback, removedupes, Storage as S
from util.threads.bgthread import on_thread
from util.callbacks import do_cb
from pprint import pformat
from types import NoneType
from contacts.buddyinfo import binfoproperty
from contacts.Contact import ContactCapabilities as caps
import util.observe
from collections import defaultdict
from util.primitives import try_this
from common.Buddy import get_cached_icon, icon_path_for
from itertools import chain
from os import path
from path import path as path2
from traceback import print_exc
from util.primitives.structures import oset

'''
{0: {'alias': None,
     'contacts': [{'name': 'brokenhalo282',
                   'protocol': 'aim',
                   'username': 'digsby03'},
                  {'name': 'digsby01',
                   'protocol': 'aim',
                   'username': 'digsby03'}],
     'grouppath': ['dotsyntax'],
     'id': 0},
'''

from operator import attrgetter
readonly = lambda name: property(attrgetter(name))
from util.observe import Observable

def get_fakeroot_name():
    return pref('buddylist.fakeroot_name', default=_('Contacts')).lower()

def first(gen):
    try:
        return gen.next()
    except StopIteration:
        return None

class OfflineBuddy(Observable):
    def __init__(self, name, service):
        Observable.__init__(self)
        self.name = self.nice_name = name
        self._service  = service

        self._notify_dirty = True

        self.protocol = p = S(name = self.service,
                              self_buddy = S(name = name),
                              connected = False)

    status = 'offline'
    status_orb = 'unknown'
    sightly_status = _('Unknown')
    pretty_profile = u''

    email_hint = \
    property(lambda self: None)

    sms = property(lambda self: True)

    @property
    def history(self):
        return profile.logger.history_for_safe(self.protocol, self)

    @property
    def cache_path(self):
        # cached attributes go in TEMPDIR + the following path
        return path.join(self.protocol.name, self.name) + '.dat'

    @property
    def log_size(self):
        return profile.log_sizes[(self.name, self.service)]

    alias = readonly('name')
    remote_alias = alias

    def idstr(self):
        return u'/'.join(('', self.name, self.service))

    @property
    def info_key(self):
        return self.name + '_' + self.service

    @property
    def status_message(self):
        return ''

    online = \
    mobile = \
    idle = \
    away = \
    blocked = \
    online_time = \
    property(lambda self: False)

    def get_buddy_icon(self):
        pass

    def block(self, *a, **k):
        return False

    def unblock(self, *a, **k):
        return False

    service = readonly('_service')
    caps = frozenset((caps.IM, caps.EMAIL))

    def imwin_mode(self, mode):
        from gui.imwin import begin_conversation
        begin_conversation(self, mode = mode)

    @property
    def serviceicon(self):
        from gui import skin
        return skin.get('serviceicons.%s' % self.service)

    @property
    def buddy_icon(self):
        from gui.buddylist.renderers import get_buddy_icon
        return get_buddy_icon(self, 32, False)

    icon_bitmap = None #this needs to be settable
    @property
    def icon(self):
        if self.icon_bitmap is None:
            # check the disk for a cached icon
            bitmap, hash = get_cached_icon(self)
            # if nothing got loaded, flag that we tried and failed with -1
            self.icon_bitmap = bitmap if bitmap is not None else -1

        if self.icon_bitmap is not None and self.icon_bitmap is not -1:
            if isinstance(self.icon_bitmap, str) and self.icon_bitmap == "empty":
                return None
            else:
                return self.icon_bitmap
        else:
            return None

    @property
    def icon_path(self):
        return path2(icon_path_for(self))


def offline_contact(cinfo):
    protocol = S(name     = cinfo['protocol'],
                 service  = cinfo['protocol'],
                 username = cinfo['username'],
                 self_buddy = S(name = cinfo['username']),
                 connected = False)

    return OfflineBuddy(cinfo['name'], protocol)

#
# TODO: use objects as contact info descriptions, not dumb dictionaries.
#
def cinfotuple(c):
    return (c['name'], c['protocol'], c['username'])

def cinfodict(t):
    return {'name': t[0], 'protocol': t[1], 'username': t[2]}

def cdiff(cinfos, sub):
    cinfos = set(cinfotuple(cinfo) for cinfo in cinfos)
    sub    = set(cinfotuple(s) for s in sub)

    return [cinfodict(q) for q in cinfos - sub]


from logging import getLogger; log = getLogger('metacontacts'); info = log.info

class MetaContactManager(dict):
    'Stores MetaContacts.'

    def clear(self):
        dict.clear(self)
        self.metacontact_objs.clear()
        self.rebuild_buddy_mapping()
        self.blist._info_changed()
        self.blist.rebuild()

    def __init__(self, blist, mc_data = {}):
        'Creates a metacontact manager initiailzed with mc_data.'
        from .identity import Identity
        self.blist = blist
        if mc_data and not mc_data.values()[0].has_key('groups'):
            self.old_data = dict(mc_data)
            def cleanup():
                for key in mc_data.iterkeys():
                    idstr = '%s #%d' % (MetaContact.idstr_prefix, key)
                    self.blist.remove_contact_info(idstr)
            self.cleanup = cleanup
            mc_data = {}
        self.metacontact_objs = {}
        for id, meta in mc_data.iteritems():
            try:
                self[id] = Identity.unserialize(meta)
                self.metacontact_objs[id] = MetaContact(id, self)
            except Exception:
                log.critical('ignoring metacontact %r because of an exception while unserializing:', id)
                print_exc()

        self._built_with = mc_data
        self.rebuild_buddy_mapping()

    def rebuild_buddy_mapping(self):
        #map buddy description to set of metas
        b2m = self.buddies_to_metas = defaultdict(set)
        self.groupnames = mc_gnames = set()
        for id_, m1 in self.iteritems():
            mc_gnames.update(m1.groups)
            m = self.metacontact_objs[id_]
            for b in m1.buddies:
                b2m[(b.name.lower(), b.service)].add(m)

    def forid(self, id):
        if isinstance(id, basestring) and id.startswith('Metacontact'):
            # if "id" is an idstr for a MetaContact, int it
            id = int(id[13:])
        try:
            return self.metacontact_objs[id]
        except KeyError:
            return None

    def forbuddy(self, buddy, match_protocol = False, return_best = False):
        'Returns one, or a a sequence of MetaContact objects for a buddy.'
        if not hasattr(buddy, 'name') or not hasattr(buddy, 'service'):
            raise TypeError('metacontact.forbuddy takes a buddy, you gave a %s' % (buddy,))
        x = (buddy.name.lower(), buddy.service)
        return set(self.buddies_to_metas[x]) if x in self.buddies_to_metas else set()

    def contacts_for_group(self, groupname):
        '''
        If you delete a group that looks empty, it may not really be--a
        metacontact may have moved a contact out of the group.

        The code that deletes the group will ask this method for contacts
        in the group--this method will include those "hidden" contacts.
        '''
        if groupname is not None:
            groupname = groupname.lower()
        result = []
        for meta in self.metacontact_objs.values():
            group = list(meta.mcinfo.groups)[0][-1]
            for contact in list(meta) + list(meta.hidden):
                if isinstance(contact, OfflineBuddy):
                    continue

                cgroupname = contact.get_group()
                if cgroupname is not None:
                    cgroupname = cgroupname.lower()

                if groupname == cgroupname:
                    result.append((contact, group))
        return result

    def rename_group(self, oldname, newname):
        log.info('renaming all metacontacts in %r -> %r',
                 oldname, newname)
        marked = False
        for meta in self.itervalues():
            for grouppath in list(meta.groups):
                if grouppath[-1].lower() == oldname:
                    meta.groups.discard(grouppath)
                    newpath = list(grouppath[:-1])
                    newpath.append(newname)
                    meta.groups.add(tuple(newpath))
                    log.info('  - %r', meta.alias)
                    marked = True
        if marked:
            self.rebuild_buddy_mapping()
            self.blist._info_changed()
            self.blist.rebuild()


    def idstr(self, number):
        return u'%s #%d' % (MetaContact.idstr_prefix, number)

    def save_data(self):
        # assert all in self is primitive?
        mc_data = {}
        for id, meta in self.iteritems():
            mc_data[id] = meta.serialize()
        return mc_data

    def create(self, mc_alias, contacts, update = True):
        'Creates a new metacontact given a list of contacts.'
        print mc_alias, contacts, update
        from contacts import Contact

        if not isinstance(mc_alias, basestring): raise TypeError('alias must be a string')
        if not all(isinstance(c, Contact) for c in contacts):
            raise TypeError('not all contacts were Contact objects: %r' % contacts)

        id = self.new_id()

        self[id] = self.build_metacontact_info(id, mc_alias, contacts)
        self.metacontact_objs[id] = MetaContact(id, self)
        self.rebuild_buddy_mapping()

        self.blist._info_changed()

        info('created metacontact %r', mc_alias)
        info('\t\t%r', self[id])

        if update: self.blist.rebuild()
        return id

    def edit(self, metacontact, contacts = sentinel, alias = sentinel, grouppath = None):
        if not isinstance(metacontact, MetaContact): raise TypeError
        assert contacts is not sentinel or alias is not sentinel

        # Set new alias?
        if alias is not sentinel:
            metacontact.alias = alias
        else:
            alias = metacontact.mcinfo.alias

        # Set new contacts?
        if contacts is not sentinel:
            info('new contact order for %r: %r', alias, contacts)
            metacontact[:] = contacts
        else:
            contacts = metacontact[:]

        id = metacontact.id
        self[id] = self.build_metacontact_info(id, alias, contacts, grouppath = grouppath)
        info('edited metacontact %r', alias)
        info(pformat(self[id]))
        self.rebuild_buddy_mapping()
        self.blist._info_changed()
        self.blist.rebuild()

    def rearrange(self, mc, src, area, dest):
        if src is dest: return
        contacts = mc.mcinfo.contacts
        src, dest = contact_dict(src), contact_dict(dest)
        contacts.remove(src)
        contacts.insert(contacts.index(dest) + (1 if 'below' == area else 0), src)
        info('rearranged')
        info(pformat(contacts))

        self.blist._info_changed()
        self.blist.rebuild()

    def remove_group(self, groupname):
        groupname = groupname.lower()
        log.info('removing all metacontacts in %r',
                 groupname)
        marked = False
        for meta in self.values():
            for grouppath in list(meta.groups):
                if grouppath[-1].lower() == groupname:
                    meta.groups.discard(grouppath)
                    marked = True
            if len(meta.groups) == 0:
                self.explode(self.metacontact_objs[meta.id], update=True, cleanup=False)
        if marked:
            self.rebuild_buddy_mapping()
            self.blist._info_changed()
            self.blist.rebuild()

    def remove(self, mc, contact, explode = True, cleanup = True):
        if isinstance(mc, int):
            mcname = self.idstr(mc)
            if mc not in self:
                return
            contacts = self[mc].buddies
        else:
            mcname = mc.name
            contacts = mc.mcinfo.buddies

        log.info('removing %r from metacontact %r', contact, mcname)


        cd = contact_dict(contact)

        for d in list(contacts):
            if cd['name'] == d.name and cd['service'] == d.service:
                contacts.remove(d)

        # Contact inherits certain properties from the MetaContact.
        get, set = self.blist.get_contact_info, self.blist.set_contact_info
        sms, email = get(mcname, 'sms'), get(mcname, 'email')

        contact_obj = self.blist.contact_for_id(contact) if isinstance(contact, basestring) else contact
        def tolist(s):
            if isinstance(s, basestring): return [s]

        # "inherit" email addresses and sms numbers from the metacontact.
        if sms:
            new_sms = removedupes((tolist(get(mcname, 'sms')) or []) + sms)
            set(contact_obj, 'sms', new_sms)
        if email:
            new_email = removedupes((tolist(get(mcname, 'email')) or []) + email)
            set(contact_obj, 'email', new_email)

        info('removed %r from %r', contact, mc)
        if hasattr(self.blist, 'new_sorter'):
            on_thread('sorter').call(self.blist.new_sorter.removeContact, mcname)
        self.rebuild_buddy_mapping()
        self.blist._info_changed()

        if explode and len(contacts) == 1:
            self.remove(mc, contacts[0], True)
            self.remove_mc_entry(mc)
        elif explode and len(contacts) == 0:
            pass
        else:
            if cleanup:
                self.blist.rebuild()

    def explode(self, metacontact, update = True, cleanup=True):
        for contact in list(metacontact):
            self.remove(metacontact, contact, False, cleanup=cleanup)

        self.blist._info_changed()
        self.remove_mc_entry(metacontact, update)

    def remove_mc_entry(self, metacontact, update = True):
        id = getattr(metacontact, 'id', metacontact)
        self.pop(id)
        log.info('removed metacontact entry %d', id)

        # remove any server-side information (SMS, email) about this metacontact
        self.blist.remove_contact_info(self.idstr(id))
        self.metacontact_objs.pop(id, None)
        self.rebuild_buddy_mapping()
        if update: self.blist.rebuild()

    def collect(self, *roots):
        '''
        For contacts which are in metacontacts, remove them from the original
        protocol groups and add them to a new group.

        Returns that new group full of DGroups holding MetaContacts.
        '''

        # Remove meta contacts
        mc_root = DGroup('Root', protocols = [], ids = [])

        b2m = self.buddies_to_metas# =  = defaultdict(set) #map buddy description to set of metas

        groupnames = oset()

        # For each protocol root group
        cs = defaultdict(list)
        mc_gnames = self.groupnames
        metacontact_objs = self.metacontact_objs

        def maybe_remove_contact(contact, group):
            if (contact.name.lower(), contact.service) in b2m:
                for meta in b2m[(contact.name.lower(), contact.service)]:
                    cs[meta.id].append(contact)

                group.remove(contact)
                return True

            return False

        from contacts.Group import GroupTypes

        for root in roots:
            # Find the corresponding group
            for group in list(root):
                gflag = False

                if group is root:
                    continue

                if isinstance(group, GroupTypes):
                    for elem in list(group):
                        gflag |= maybe_remove_contact(elem, group)

                    if gflag and (group.name not in groupnames):
                        groupnames.add(group.name)
                else:
                    # contact
                    elem = group
                    if maybe_remove_contact(elem, root):
                        groupnames.add(get_fakeroot_name())

        assert not set(cs.keys()) - set(self.keys())

        for id in self.iterkeys():
            elems = cs[id]
            order = [b.tag for b in self[id].buddies]
            elems = list(sorted(elems, key = lambda elem: order.index((elem.name.lower(), elem.service))))

            out = []
            hidden = []
            for tag in order:
                online = False
                while elems and (elems[0].name.lower(), elems[0].service) == tag:
                    b = elems.pop(0)
                    if not online:
                        out.append(b)
                        online = True
                    else:
                        hidden.append(b)
                if not online:
                    old = [o for o in metacontact_objs[id] if
                           (isinstance(o, OfflineBuddy) and (o.name.lower(), o.service) == tag)]
                    if old:
                        out.append(old[0])
                    else:
                        out.append(OfflineBuddy(*tag))

            metacontact_objs[id].set_new(out, hidden)

        groups = {}
        for m in metacontact_objs.itervalues():
            if any(not isinstance(b, OfflineBuddy) for b in m):
                for gname in self[m.id].groups:
                    try:
                        g = groups[gname[0]]
                    except KeyError:
                        groups[gname[0]] = g = DGroup(gname[0])
                    g.append(m)

        glen = len(groups)
        nextroot = DGroup('Root')
        for gname in groupnames:
            if gname in groups:
                nextroot.append(groups.pop(gname))

        for gname in set(g[0] for g in mc_gnames) - set(groupnames):
            if gname in groups:
                nextroot.append(groups.pop(gname))

        mc_root.extend(nextroot)
#        assert len(nextroot) == glen
        return mc_root

    def build_metacontact_info(self, id, mc_alias, contacts, grouppath = None):
        assert isinstance(id, int) and isinstance(mc_alias, (basestring, NoneType))
        from .identity import Identity, Personality
        keys = [(c.name, c.service) for c in contacts]
        keys2 = []
        for k in keys:
            if k not in keys2:
                keys2.append(k)
        buddies = [Personality(*k) for k in keys2]
        mc = Identity(id, mc_alias, buddies=buddies)

        # Metacontact gets all emails/sms from buddy
        sms, email = [], []
        get, set_ = self.blist.get_contact_info, self.blist.set_contact_info
        for contact in contacts:
            email += get(contact, 'email') or []
            sms   += get(contact, 'sms')   or []
            set_(contact, 'email', None)
            set_(contact, 'sms', None)

        set_(id, 'email', removedupes(email))
        set_(id, 'sms',   removedupes(sms))

        if grouppath is None:
            grouppaths = [None if x is None else x.lower() for x in [contact.get_group() for contact in contacts]]
            mc.groups = set([(grouppaths[0],)])
        elif isinstance(grouppath, set):
            mc.groups = set(grouppath)
        else:
            mc.groups = set([tuple(grouppath)])

        # Contacts in the fake root group will return None for get_group.
        # Put the metacontact in that fake root group.
        if mc.groups == set([(None,)]):
            mc.groups = set([(get_fakeroot_name(),)])

        return mc


    def new_id(self):
        'Returns the lowest integer that is not a key in this dictionary.'

        c = 0
        for k in sorted(self.keys()):
            if c != k: break
            else: c += 1

        return c


#import contacts
class MetaContact(BuddyListElement, util.observe.ObservableList):
    'Multiple contacts.'


    idstr_prefix = 'Metacontact'

    "allows metacontact to record if it should be considered dirty based on just being created, "
    "or other conditions under which the meta contact requires the sorter to grab info from it again"
    meta_dirty   = True

    @property
    def history(self):
        '''Merges messages from all of this metacontact's buddies' histories.'''

        from util.merge import lazy_sorted_merge
        from datetime import datetime
        now = datetime.now()
        #doesn't have to be now, just need a common point to subtract from
        #to make the "largest" timestamp have the "smallest" timedelta for "min" heap
        return lazy_sorted_merge(*(b.history for b in self if not isinstance(b, OfflineBuddy)),
                                 **{'key':lambda x:now-x['timestamp']})

    def __init__(self, id, manager, contacts = None):
        if not isinstance(id, int):
            raise TypeError('id must be an int')

        self.id      = id
        self.manager = manager
        self.hidden  = []

        util.observe.ObservableList.__init__(self, contacts or [])

        for contact in self:
            contact._metacontact = self

    def set_new(self, contacts, hidden_contacts):
        if self[:] != contacts or self.hidden != hidden_contacts:
            self[:] = contacts
            self.hidden[:] = hidden_contacts
            self.meta_dirty = True

            # when the contents of a MetaContact changes, the sorter needs to invalidate
            # it's knowledge of it
            sorter = getattr(self.manager.blist, 'new_sorter', None)
            if sorter is not None:
                def invalidate_sorter_contact():
                    sorter.removeContact(self.name)

                if on_thread('sorter').now:
                    # if called from resort->collect, this is already true,
                    invalidate_sorter_contact()
                else: # but sometimes we call it on the console for testing
                    on_thread('sorter').call(invalidate_sorter_contact)

    def get_notify_dirty(self):
        return any(getattr(c, '_notify_dirty', True) for c in self[:] + self.hidden[:]) or self.meta_dirty

    def set_notify_dirty(self, value):
        for c in self[:] + self.hidden[:]:
            c._notify_dirty = value
        if not value:
            self.meta_dirty = False

    _notify_dirty = property(get_notify_dirty, set_notify_dirty)

    @property
    def service(self):
        f = self.first_online
        return f.service if f is not None else 'digsby'

    @property
    def sortservice(self):
        f = self.first_online
        return f.sortservice

    @property
    def serviceicon(self):
        from gui import skin
        f = self.first_online
        return f.serviceicon if f is not None else lambda: skin.get('serviceicons.digsby')

    @property
    def caps(self):
        return set(chain(*(b.caps for b in self)))

    @property
    def send_file(self):
        return self.file_buddy.send_file

    @property
    def file_buddy(self):
        for c in self:
            if c.online and hasattr(c, 'send_file') and caps.FILES in c.caps:
                return c
        raise AttributeError, "no online buddy with send_file found"

    @action()
    def edit_alerts(self):
        import gui.pref.prefsdialog as prefsdialog
        prefsdialog.show('notifications')

    def idstr(self):
        if isinstance(self.name, str):
            return self.name.decode('fuzzy utf8')
        else:
            return self.name

    @action(lambda self: not getattr(self, 'iswidget', False))
    def rename_gui(self):

        from gui.contactdialogs import MetaContactDialog
        from wx import FindWindowByName

        diag = MetaContactDialog(FindWindowByName('Buddy List'), list(self),self, self.alias)
        try:
            diag.Prompt()
        finally:
            diag.Destroy()

    #
    # Alias
    #
    def set_alias(self, alias):
        self.mcinfo.alias = alias if alias else None
        self.meta_dirty = True
        self.manager.blist._info_changed()
        self.manager.blist.rebuild()

    def get_alias(self):
        # First choice: the metacontact alias, if any.
        alias = try_this(lambda: self.mcinfo.alias, None)

        # Otherwise, the "first online's" alias.
        try:
            return alias if alias is not None else self.first_online.alias
        except AttributeError:
            return None

    alias = property(get_alias, set_alias)

    @property
    def status_orb(self):

        if pref('metacontacts.show_first_online_status',False):
            return self.first_online.status_orb

        statuses = self.by_status()
        if not statuses:
            return 'unknown'
        return statuses[0].status_orb


    @property
    def mcinfo(self):
        return self.manager[self.id]

    @property
    def num_online(self):
        return int(any(c.online for c in self))

    @property
    def name(self):
        return self.manager.idstr(self.id)

    @property
    def idle(self):
        sorted = self.by_status()
        if not sorted:
            return None

        # If available or mobile, do not show the idle time.
        if sorted[0].status_orb in ('available', 'mobile'):
            return None

        # Show the lowest idle time we can find.
        idle_times = []
        for c in self:
            idle = c.idle
            if isinstance(idle, (int, long)):
                idle_times.append(idle)

        if idle_times:
            return max(idle_times)

        # Otherwise return the most available buddy's idle attribute.
        return sorted[0].idle


    def __repr__(self):
        try:
            return '<MetaContact %r: %s>' % (self.alias, list.__repr__(self))
        except KeyError:
            return '<MetaContact %r: %s>' % (self.name, list.__repr__(self))

    def __hash__(self):
        return hash((self.name, self.id))
#        return hash(''.join(unicode(s) for s in [self.name, self.mcinfo['grouppath']]))
#
    def __eq__(self, other):
        return type(other) == type(self) and self.id == other.id

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def online(self):
        return any(contact.online for contact in self)

    @action()
    def explode(self, ask = True):
        if ask:
            import wx
            res = wx.MessageBox(_('Are you sure you want to split up this merged contact?'),
                                _('Split Contacts'),
                                style = wx.YES_NO)
            if res != wx.YES:
                return

        self.set_notify_dirty(True)
        self.manager.explode(self)

    @property
    def icon(self):
        for c in self:
            icon = c.icon
            if icon and icon.getextrema() != (0, 0):
                return icon

    @property
    def log_size(self):
        return sum(c.log_size for c in self)

    def by_status(self):
        from contacts.buddylistsort import STATUS_ORDER_INDEXES

        # don't include OfflineBuddy objects
        non_offline = (c for c in self if not isinstance(c, OfflineBuddy))

        def key(contact):
            return STATUS_ORDER_INDEXES[contact.status_orb]

        return sorted(non_offline, key = key) or sorted(self, key = key)

    @property
    def status(self):
        try:
            return self.by_status()[0].status
        except IndexError:
            return 'offline'

    @property
    def protocol(self):
        try:
            return self.by_status()[0].protocol
        except IndexError:
            return profile.connection

    def rename(self, new_alias):
        self.set_alias(new_alias)

    @property
    def away(self):
        # Are any contacts "Available" ? If so, we're not away.
        if any(c.status == 'online' for c in self):
            return False

        return any(c.away for c in self)

    @property
    def pending_auth(self):
        return False

    @property
    def mobile(self):
        f = self.first_online
        return f.mobile if f is not None else False

    @property
    def blocked(self):
        return all(c.blocked for c in self)

    @property
    def status_message(self):
        msg = ''
        for c in self:
            msg = c.status_message
            if msg: return msg

    @property
    def stripped_msg(self):
        try:
            for c in self:
                if c.status_message:
                    stripped_msg = getattr(c, 'stripped_msg', None)
                    if stripped_msg is not None:
                        return stripped_msg
            else:
                return ''
        except AttributeError:
            return ''

    @property
    def first_online(self):
        '''
        Returns the first contact found to be online, or the first contact in self.

        If self has no contact, returns None.
        '''
        return first(c for c in self if c.online) or self.first_real or first(iter(self))

    @property
    def first_real(self):
        return first(c for c in self if not isinstance(c, OfflineBuddy))

    @property
    def email_hint(self):
        f = self.first_online
        return f.email_hint if f is not None else ''

    @property
    def info_key(self):
        return self.name

    # these attributes are stored on the network.
    email = binfoproperty('email', default = lambda: [])
    sms   = binfoproperty('sms',   default = lambda: [])

    def imwin_mode(self, mode):
        from gui.imwin import begin_conversation
        begin_conversation(self, mode = mode)

    def chat(self):       self.imwin_mode('im')
    def buddy_info(self): self.imwin_mode('info')

    @action(lambda self: 'EMAIL' in self.caps) #@NoEffect
    def send_email(self): self.imwin_mode('email')

    @action(lambda self: 'SMS' in self.caps or None) #@NoEffect
    def send_sms(self):   self.imwin_mode('sms')


    def _block_predicate(self, setblocked=True, callback=None):
        return True if setblocked ^ self.blocked else None

    def _unblock_predicate(self, callback=None):
        return True if self.blocked else None

    @callsback
    def block(self, setblocked = True, callback = None):
        cbs = []
        for contact in self:
            @callsback
            def doblock(contact = contact, callback = None):
                contact.block(setblocked, callback = callback)

            if contact.blocked != setblocked:
                cbs += [doblock]

        do_cb(cbs, callback=callback)

    @callsback
    def unblock(self, callback = None):
        self.block(False, callback=callback)

    @callsback
    def move_to_group(self, groupname, order = None, callback = None):
        if not isinstance(groupname, basestring):
            raise TypeError('groupname must be a string')

        if len(self.mcinfo.groups) != 1:
            raise AssertionError('I thought metacontacts would only be in one group!')

        self.mcinfo.groups.clear()
        self.mcinfo.groups.add((groupname,))
        self.manager.rebuild_buddy_mapping()
        self.manager.blist._info_changed()
        self.manager.blist.rebuild()
        return callback.success()

groupkey = lambda a: a.name.lower()

def walk_group(root, path):
    from contacts.Contact import Contact

    # Is this the successful case? If so, return the group
    if not path: return root

    # Search. (this is O(n) now. should these be lookups?)
    next, path = path[0], path[1:]
    for elem in root:
        if not isinstance(elem, Contact) and groupkey(elem) == next.lower():
            return walk_group(elem, path)

    return None

def inflate_groups(grouppath):
    'Returns a DGroup tree given a sequence of names.'

    return [] if not grouppath else \
        DGroup(grouppath[0], protocols = None, ids = None,
               *inflate_groups(grouppath[1:]))



def contact_dict(contact):
    'Return a short dictionary for a contact.'

    return dict(name = contact.name,
                service = contact.service)

def underMeta(contact):
    'Returns True if the specified contact is in a metacontact.'

    c = contact_dict(contact)

    return any(c in meta['contacts']
               for _, meta in profile.blist.metacontacts.iteritems())

