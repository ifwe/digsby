from __future__ import with_statement
from util.primitives import odict
from util.primitives.structures import oset
from digsby_chatlogs.interfaces import IAliasProvider
import struct
import oscar
import contacts
import warnings
import logging
from oscar.OscarBuddies import OscarBuddy

import common
from contacts import Contact

log = logging.getLogger('oscar.ssiitem')
byteswap = lambda x: struct.unpack('<H', struct.pack('>H', x))[0]

class OscarContact(Contact):
    _renderer = 'Contact'

    inherited_actions = [OscarBuddy]

    def __init__(self, *a, **k):
        Contact.__init__(self, *a, **k)
        self.ssis = self.protocol.ssimanager.ssis
        self.remote_alias #side effects on buddy
#        self.buddy.notify('remote_alias')

    @property
    def group(self):
        return self.ssis.get_group(self.id[0])

    def get_remote_alias(self):
        try:
            friendly = self.ssis[self.id].get_alias().decode('fuzzy utf-8')

            # hack: set the friendly name in the buddy
            if self.buddy._friendly_name is None:
                self.buddy._friendly_name = friendly

            return friendly
        except KeyError:
            # GUI/model out of sync...return None
            return None

    def set_remote_alias(self, newname):
        self.protocol.set_remote_alias(self, newname)

    remote_alias = property(get_remote_alias, set_remote_alias)

    @common.action()
    def rename_gui(self):
        s = Contact.rename_gui(self)
        if s is not None:
            self.remote_alias = s

    @common.action(Contact._block_pred)
    def block(self, *a,**k):
        return Contact.block(self, *a, **k)
    @common.action(Contact._unblock_pred)
    def unblock(self, *a,**k):
        return Contact.unblock(self, *a, **k)

class SSIItem(object):
    def __init__(self, name, group_id, item_id, type_=None, tlvs=None, **k):
        if not isinstance(name, str):
            raise TypeError('SSIItem.name must be str, not %s' % type(name))

        type_ = k.pop('type', type_)
        if k:
            raise Exception('Only one extra keyword argument ("type") is allowed for SSIItems')

        self.name     = name
        self.group_id = group_id
        self.item_id  = item_id
        self.type     = type_     or 0  #default to a Buddy
        self.tlvs     = odict(tlvs or {}) #default to no tlvs (maybe this should be storage/named tlvs)

        self.c8_to_ints()

    def set_name(self, name):
        if not isinstance(name, str):
            raise TypeError('setting SSIItem.name to something that is not str: %s' % type(name))
        self._name = name

    def get_name(self):
        return self._name

    name = property(get_name, set_name)

    @property
    def tlv_tuple(self):
        return (self.group_id, self.item_id)


    def to_bytes(self):
        tlvs_string = ''
        for type, val in self.tlvs.items():
            if type != 0xc8:
                if hasattr(val, 'value'):
                    tlvs_string += oscar.util.tlv(val.type, val.length, val.value)
                else:
                    tlvs_string += oscar.util.tlv(type, val)
            else:
                tlvs_string += oscar.util.tlv(type, "".join([struct.pack('!H', short)
                                              for short in val]))


        if not isinstance(self.name, str):
            raise TypeError('SSIItem.name should always be str, but it is %s' % type(self.name))

        nlen, tlen = len(self.name), len(tlvs_string)
        return struct.pack("!H%dsHHHH%ds" % (nlen, tlen),
                           nlen, self.name, self.group_id,
                           self.item_id, self.type, tlen, tlvs_string)


    def c8_to_ints(self):
        if 0xc8 in self.tlvs and isinstance(self.tlvs[0xc8], basestring):

            try:
                self.tlvs[0xc8] = oscar.unpack((('list', 'list', 'H'),),
                                               self.tlvs[0xc8])[0]
            except Exception:
                import traceback
                traceback.print_exc()
                # ssis.update will be called afterwards and fix the C8 tlv
                self.tlvs[0xc8] = []

    def clone(self):
        return oscar.unpack((('ssi','ssi'),),self.to_bytes())[0]

    def add_item_to_group(self, id_to_add, position=0):
        if self.type != 1:
            raise AssertionError(repr(self) + " is not a group")
        else:

            self.tlvs.setdefault(0xc8, []).insert(position, id_to_add)


    def remove_item_from_group(self, id_to_remove):
        if self.type != 1:
            raise AssertionError(repr(self) + " is not a group")


        try:
            self.tlvs.setdefault(0xc8, [id_to_remove]).remove(id_to_remove)
        except ValueError:
            # id not in list, so our job is done
            pass

        if not self.tlvs[0xc8]: del self.tlvs[0xc8]

    def get_item_position(self, id_to_find):
        if self.type != 1:
            raise AssertionError(repr(self)+ " is not a group")
        try:
            return self.tlvs.get(0xc8, []).index(id_to_find)
        except ValueError:
            # id not in list
            return None

    def move_item_to_position(self, id_to_move, position):
        curposition = self.get_item_position(id_to_move)
        if curposition is None:
            raise AssertionError(repr(self) +
                                 " does not contain %d" % id_to_move)
        if position != curposition:
            self.remove_item_from_group(id_to_move)
            self.add_item_to_group(id_to_move, position)

    def get_alias(self):
        return self.tlvs.get(0x131, None)

    def set_alias(self, alias):
        if alias: self.tlvs[0x131] = alias
        else:    self.remove_alias()

    def remove_alias(self):
        self.remove_tlv(0x131)

    alias = property(get_alias, doc="this is the alias of the buddy")

    def get_comment(self):
        return self.tlvs.get(0x013C, None)

    def set_comment(self, comment):
        if comment: self.tlvs[0x013C] = comment
        else:       self.remove_comment()

    def remove_comment(self):
        self.remove_tlv(0x013C)

    comment = property(get_comment, doc="this is the comment about the buddy")

    def remove_tlv(self, type):
        try: del self.tlvs[type]
        except KeyError: pass


    def __repr__(self):
        return "<SSI Item: name: %s, group_id: %d, item_id: %d, type: %d>" % \
                (self.name, self.group_id, self.item_id, self.type)

class OscarSSIs(dict):
    def __init__(self, manager):
        self.manager = manager
        self.root_group = SSIGroup(None, self.manager)
        self.groups = {(0,0):self.root_group}
        return dict.__init__(self)

    def __setitem__(self, key, ssi, modify=False):
        tupled_key = tuple_key(ssi)
        if isinstance(key, SSIItem):
            assert(key == ssi)
        else:
            assert(key == tupled_key)
        if ssi.type == 1:
            with self.root_group.frozen():
                if tupled_key in self.groups:
                    self.groups[tupled_key].set_ssi(ssi)
                else:
                    self.groups[tupled_key] = SSIGroup(ssi, self.manager)
        elif modify and ssi.type == 0:
            if 0x015c in ssi.tlvs or 0x015d in ssi.tlvs:
                self.manager.o.get_buddy_info(ssi)
        else:
            pass #log.info("skipping %r / %r", ssi.name, ssi)
        return dict.__setitem__(self, tupled_key, ssi)

    def get_group(self, key):
        #try:
        return self.groups[tuple_key(key)]
        #except (KeyError,):
        #    return contacts.Group('Loading...', self, None)

    def __getitem__(self, key):
        return dict.__getitem__(self, tuple_key(key))

    def __contains__(self, key):
        return dict.__contains__(self, tuple_key(key))

    def __delitem__(self, key):
        return dict.__delitem__(self, tuple_key(key))

    def update(self, hash, modify=False):
        with self.root_group.frozen():
            for k,v in hash.items():
                self.__setitem__(k,v, modify=modify)
            self.fix_group_c8()

    def fix_group_c8(self):
        '''
        Sometimes SSI group index ids (0xc8) are little endian instead of the
        expected big endian.

        This function attempts to guess when that is happening, and fix them.
        '''
        groups = [key for key in self if key[1] == 0]
        dgi = dict.__getitem__

        for g_id, i_id in groups:
            if not g_id: #root group
                #find all group ssis
                members = [key for key in groups if key != (0, 0)]
                #extract group ids
                m_ids = set(x[0] for x in members)
                assert (g_id, i_id) == (0, 0)
                #get group ids from root group
                gm_ids = dgi(self, (0, 0)).tlvs.get(0xc8, [])
            else:
                #find all the ssis which match this group id
                members = [key for key in self if key[0] == g_id and key[1] != 0]
                #extract member item ids
                m_ids = set(x[1] for x in members)
                #grab the member ids the group thinks it has
                gm_ids = dgi(self, (g_id, i_id)).tlvs.get(0xc8, [])
                #if they're the same, move on.
            if m_ids == set(gm_ids) and len(m_ids) == len(gm_ids):
                continue

            #map the group's ids to their position in the known list.
            known_locs = dict((y,x) for x,y in enumerate(oset(gm_ids)))
            locations = {}
            for possible in m_ids:
                #for each real id:
                if possible in known_locs:
                    #if the group has a location for it, use that one.
                    locations[possible] = known_locs[possible]
                    continue
                #otherwise, see if we have an inverted location for it.
                inverted = byteswap(possible)
                #even if somehow there was a collision, they'll just be put next to each other.
                #close enough.
                if inverted in known_locs:
                    locations[possible] = known_locs[inverted]
                    continue
                #otherwise, throw it at the end.
                locations[possible] = len(m_ids)
            new_gm_ids = sorted(m_ids, key = locations.__getitem__)
            #setting this should do no harm, since the only thing that can happen to an
            #ssi is deletion or modification.  deleted doesn't matter, modified fixes this
            #on the server as well.
            dgi(self, (g_id, i_id)).tlvs[0xc8] = new_gm_ids

def tuple_key(key):
    try:
        # it's already a tuple of ints
        a, b = key
        int(a), int(b)
        return key
    except (TypeError, ValueError):
        try:
            # it's an SSIItem: return (key.group_id, key.item_id)
            t = key.group_id, key.item_id
            return t
        except AttributeError:
            try:
                # it's a group: return (key, 0)
                int(key)
                return key, 0
            except TypeError:
                raise AssertionError(repr(key) + " is not a valid ssi key")

class SSIGroup(contacts.Group):

    _renderer = 'Group'

    def __init__(self, new_ssi, ssi_manager):
        self.my_ssi = new_ssi
        self.ssi_manager = ssi_manager
        if self.my_ssi is None:
            self.my_ssi = SSIItem('root', 0,0,1)
        assert(self.my_ssi.type == 1)

        # Group objects get unicode
        groupname = self.my_ssi.name.decode('utf-8', 'replace')

        contacts.Group.__init__(self, groupname, ssi_manager.o, self.my_ssi.group_id)

    def set_ssi(self, new_ssi):
        oldname = self.my_ssi.name
        self.my_ssi = new_ssi
        assert(self.my_ssi.type == 1)
        self.name = self.my_ssi.name.decode('utf-8', 'replace')
        if oldname != self.name:
            self.notify('name', oldname, self.name)

    def __getitem__(self, index):
        assert(type(index) == int)
        g_id = self.my_ssi.group_id
        tlv = self.my_ssi.tlvs.get(0xc8, [])
        start_index = index
        ssi = None
        while ssi is None:
            try:
                i_id = tlv[index]
            except IndexError:
                break

            if g_id:
                try:
                    ssi = self.ssi_manager.ssis[(g_id, i_id)]
                except KeyError, e:
                    index += 1
                    continue
                else:
                    return OscarContact(self.ssi_manager.o.buddies[ssi.name], (g_id, i_id))
            else:
                return self.ssi_manager.ssis.get_group((i_id, 0))

        if ssi is None: # pretty much guaranteed to be if we're here...
            warnings.warn('Error finding SSI %r in group (id=%r)' % (start_index, g_id)) # use warnings so it only prints once.
            raise IndexError("SSI Item not found in group(id=%r): %r", index, g_id)



    def __iter__(self):
        for i in xrange(len(self)):
            try:
                thing = self[i]
                if self.my_ssi.group_id == 0 and not getattr(thing, 'should_show', lambda: True)():
                    continue
                yield thing
            except (KeyError, IndexError), e:
                # this really only happens when we are doing
                # privacy edits and stuff. usually the cause is
                # removing an SSI before changing the order tlv (0xc8)
                warnings.warn("Error iterating over group: %r" % e)
                continue

    @property
    def online(self):
        return bool(self.num_online)

    @property
    def num_online(self):
        ss = self.ssi_manager.ssis
        bs = self.ssi_manager.o.buddies
        total = 0
        g_id = self.my_ssi.group_id
        tlv = self.my_ssi.tlvs.get(0xc8, [])
        if g_id:
            total += len([s for s in (ss.get((g_id, elem), None) for elem in tlv)
                           if s and bs[s.name].online])
        else:
            groups = [ss.get_group(group_id) for group_id in tlv]
            for group in groups:
                total += group.num_online
        return total

    def find(self, obj):
        return list.find(self, obj)

    def __len__(self):
        return len(self.my_ssi.tlvs.get(0xc8, []))

    def is_facebook_group(self):
        # AOL recently added facebook connect support. it populates the SSIs with groups named
        # the same as your facebook friendlists, and also adds an SSI of type 0x1c and name = "FB SG:groupname".
        # So, we look for those SSIs and if found, this is a facebook group.
        return len(self.ssi_manager.find(type = 0x1c, name = "FB SG:%s" % self.my_ssi.name)) > 0

    def should_show(self):
        return bool(len(self) or (not self.is_facebook_group()))
