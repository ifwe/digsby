from __future__ import with_statement
from contextlib import contextmanager
import oscar.snac as snac
import oscar
import common
import struct
from oscar.ssi  import item, OscarSSIs, SSIException, ssi_err_types
from util import gen_sequence, lookup_table, callsback
from oscar.ssi.SSIItem import tuple_key

from logging import getLogger
log = getLogger("oscar.ssis")

#from functools import partial

property_tlv_types = lookup_table(alias=0x0131,
                                  email=0x0137,
                                  SMSnum=0x013A,
                                  comment=0x013C)

def _lowerstrip(s):
    return oscar._lowerstrip(s)


class SSIManager(object):
    def __init__(self, protocol):
        self.o = protocol
        self.ssis = OscarSSIs(self)
        self.ssi_edits_out = 0
        self.generated_ssi_ids = []

#    @gen_sequence
#    @callsback
    @gen_sequence
    def add_modify(self, new_ssi): #, callback=None):
        '''
        not to be used for things you need to hear back from!
        @param new_ssi:
        '''
        me = (yield None)
        with self.ssi_edit():
            if new_ssi in self.ssis: self._modify_ssi(new_ssi, me())
            else:                     self._add_ssi(new_ssi, me())

        errors = (yield None)
        if not errors[0]:
            self.ssis[new_ssi] = new_ssi
#            callback.success()
        else:
#            callback.error()
            raise SSIException("Error adding/modifying SSI: " +
                               ",".join([ssi_err_types[err] for err in errors]))

    def new_ssi_item_id(self, group):
        newid = 0x100
        used_ids = set(self.generated_ssi_ids + self.ssis.keys())
        while (group, newid) in used_ids:
            newid += 1
        self.generated_ssi_ids += [(group, newid)]
        return newid

    def new_ssi_group_id(self):
        newid = 0x100
        used_ids = set(self.generated_ssi_ids + self.ssis.keys())
        while (newid, 0) in used_ids:
            newid += 1
        self.generated_ssi_ids += [(newid,0)]
        return newid

    def get_ssis_in_group(self, group_id, with_group=False):
        '''
        get all SSIs in a group
        '''
        if with_group:
            return [ssi for ssi in self.ssis.values()
                    if ssi.group_id == group_id]
        else:
            return [ssi for ssi in self.ssis.values()
                    if ssi.group_id == group_id
                    and ssi.item_id != 0]

    def get_ssis_by_type(self, type):
        return [ssi for ssi in self.ssis.values()
                    if ssi.type == type]

    @gen_sequence
    def _ssi_action(self, action, new_ssis, parent):
        me = (yield None)
        with self.ssi_edit():
            if isinstance(new_ssis, item): new_ssis = [new_ssis]
            self.o.send_snac(0x13, action,
                             "".join(s.to_bytes() for s in new_ssis),
                             req=True,cb=me.send)
        parent.send(self.o.gen_incoming((yield None)))

    @gen_sequence
    def _ssi_double_action(self, action1, new_ssis1,
                                    action2, new_ssis2, parent):
        me = (yield None)
        with self.ssi_edit():
            if isinstance(new_ssis1, item): new_ssis1 = [new_ssis1]
            if isinstance(new_ssis2, item): new_ssis2 = [new_ssis2]

            #these have expanded arguments because me.send can't take kwargs
            #priority is explicitly set to the default of 5
            self.o.send_snac(0x13, action1,
                             "".join(s.to_bytes() for s in new_ssis1),
                             5,True, me.send, action1)
            self.o.send_snac(0x13, action2,
                             "".join(s.to_bytes() for s in new_ssis2),
                             5,True, me.send, action2)
        sock1, snac1, ret_action1 = (yield None)
        sock2, snac2, ret_action2 = (yield None)
        incoming1 = self.o.gen_incoming((sock1, snac1))
        incoming2 = self.o.gen_incoming((sock2, snac2))
        parent.send((incoming1, ret_action1, incoming2, ret_action2))

    def _add_ssi(self, *a, **k):
        self._ssi_action(0x08, *a, **k)

    def _modify_ssi(self, *a, **k):
        self._ssi_action(0x09, *a, **k)

    def _remove_ssi(self, *a, **k):
        self._ssi_action(0x0a, *a, **k)

    @gen_sequence
    @callsback
    def add_new_ssi(self, name, group_protocol_object=None, position=0, type_=None,
                    authorization=False, callback = None):
        me = (yield None)
        if not isinstance(name, str):
            name = name.encode('utf-8')

        if group_protocol_object is not None:
            #adding a buddy:
            group_protocol_object = tuple_key(group_protocol_object)
            group_id=group_protocol_object[0]
            item_id = self.new_ssi_item_id(group_protocol_object[0])
            if type_ is None:
                type_ = 0
        else:
            #adding a group
            group_id = self.new_ssi_group_id(); item_id=0;
            if type_ is None:
                type_ = 1

        #create ssi+
        new_ssi = item(name, group_id, item_id, type_)

        if group_protocol_object is not None and authorization:
            new_ssi.tlvs[0x66] = ""
        with self.ssi_edit(): #needed until group mod is sent
            #send buddy to server
            errors = (yield self._add_ssi(new_ssi, me()))

            if not errors[0]:
                #update local buddylist
                self.ssis[new_ssi] = new_ssi
                ids = group_protocol_object or (0,0)
                #buddy if adding to a group, else new group
                id_to_add = new_ssi.item_id if group_protocol_object \
                                             else new_ssi.group_id
                self._add_to_group(ids, id_to_add, position) #end with block
            else:
                callback.error()
                if errors[0] != 0xE:
                    raise SSIException('%s: Error adding SSI %r to server list' % (
                                       ",".join([ssi_err_types[err] for err in errors]), new_ssi))

        try:    log.info (','.join(g.name for g in self.ssis.root_group))
        except: log.error('error repr-ing groups')

        self.ssis.root_group.notify()
        callback.success(new_ssi)

    @gen_sequence
    @callsback
    def add_privacy_record(self, buddy, type_, callback = None):
        """
        Adds a buddy to your blocklist.

        buddy can be an OscarBuddy object or a string screenname.
        """
        me = (yield None)
        name = common.get_bname(buddy)

        with self.ssi_edit():
            if not self.find(lambda s: _lowerstrip(s.name) == _lowerstrip(name), type=type_):
                log.critical("adding " + name + " to your privacy list")
                buddy_ssi = item(name, 0 , self.new_ssi_item_id(0),
                                 type_)
                buddy_errs = (yield self._add_ssi(buddy_ssi, me()))
                log.critical("ACK PRIVACY MOD!" + name)
                if not buddy_errs[0]:
                    self.ssis[buddy_ssi] = buddy_ssi
                    #self.o.buddies[name].setnotify('status', 'offline')
                else:
                    callback.error()
                    raise SSIException("Error adding buddy to privacy list. " +
                           ",".join([ssi_err_types[err] for err in buddy_errs]))
            else:
                callback.error()
                raise SSIException("Buddy already in that privacy list.")

        callback.success()
        self.ssis.root_group.notify()

    @callsback
    def block_buddy(self, buddy, callback = None):
        self.add_privacy_record(buddy, oscar.ssi.deny_flag, callback = callback)

    def allow_buddy(self, buddy):
        self.add_privacy_record(buddy, oscar.ssi.permit_flag)


    @callsback
    def ignore_buddy(self, buddy, callback=None):
        self.add_privacy_record(buddy, 0xe, callback=callback)

    @callsback
    def unignore_buddy(self, buddy, callback=None):
        self.remove_privacy_record(buddy, type_=0xe, callback = callback)

    @gen_sequence
    @callsback
    def remove_privacy_record(self, buddy, type_, callback = None):
        """
        Remove the specified buddy from your block list.
        """
        me = (yield None)
        name = _lowerstrip(common.get_bname(buddy))

        buds_matching = self.find(name=name, type=type_)
        errors = []
        if buds_matching:
            with self.ssi_edit():
                log.critical("REMOVING PRIVACY RECORD FOR " + name)
                self._remove_ssi(buds_matching, me())
            errors = (yield None)

        for err, ssi in zip(errors, buds_matching):
            if not err:
                del self.ssis[ssi]

        real_errors = filter(None, errors)
        if not buds_matching:
            log.critical("Can't remove privacy record; no ssi in root group for %r (type = %r).", name, type_)
        if real_errors:
            callback.error()
            raise SSIException('Problem removing privacy ssi for %s.' % name +
                              ",".join([ssi_err_types[err] for err in errors]) )

        # On success, notify buddy listeners.
        callback.success()
        self.o.buddies[name].notify('blocked')
        self.ssis.root_group.notify()

    @callsback
    def unblock_buddy(self, buddy, callback = None):
        self.remove_privacy_record(buddy, oscar.ssi.deny_flag, callback = callback)

    def unallow_buddy(self, buddy):
        self.remove_privacy_record(buddy, oscar.ssi.permit_flag)

#    @gen_sequence
#    def ignore_buddy(self, buddy):
#        me = (yield None)
#        name = common.get_bname(buddy)
#        with self.ssi_edit():
#            [self.remove_buddy_ssi(ssi) for ssi in self.find(type=0, name=buddy)]
#            new_ssi = item(name, 0, self.new_ssi_item_id(0), type_=0x0e)
#            errors = (yield self._add_ssi(new_ssi, me))
#            if errors[0]:
#                raise SSIException("Error adding %s to ignore list" % name)


    def get_privacy_ssi(self):
        # search for PDINFO ssi items
        PDINFO = 0x04
        privacy_infos = [s for s in self.ssis.values() if s.type == PDINFO]

        # if there's no privacy entry
        if len(privacy_infos) == 0:
            # Add one, with "block list" enabled
            pinfo_ssi = item('', 0, self.new_ssi_item_id(0), PDINFO)
        elif len(privacy_infos) == 1:
            # there's already one--modify it to include "block list"
            pinfo_ssi = privacy_infos[0]
        else:
            log.critical("There was more than one privacy SSI:")
            log.critical(str(privacy_infos))
            raise SSIException("There was more than one privacy SSI:")

        return pinfo_ssi

    def blocklist(self):
        """
        Returns a list of stripped buddy names which are blocked.

        This list is defined as any SSI item in group 0 (root) with an item type
        of 3 (deny).
        """
        return [s.name.lower().replace(' ','')
                for s in self.ssis.values()
                if s.group_id == 0 and s.type == 3]

    def ignorelist(self):
        return [s.name.lower().replace(' ','')
                for s in self.ssis.values()
                if s.group_id == 0 and s.type == 0xe]

    def find(self, f=lambda x:True, **kwds):
        results = []
        for ssi in self.ssis.values():
            for kwd in kwds:
                if kwd == "name":
                    if _lowerstrip(getattr(ssi, kwd, sentinel)) != _lowerstrip(kwds[kwd]):
                        break
                elif getattr(ssi, kwd, sentinel) != kwds[kwd]:
                    break
            else:
                if f(ssi): results.append(ssi)

        return results

    @gen_sequence
    def _add_to_group(self, group_ids, id_to_add, position):
        me = (yield None)
        try:
            groupclone = self.ssis[group_ids].clone()
        except KeyError:
            raise SSIException("Could not find SSI with group_id == %r", group_ids)
        groupclone.add_item_to_group(id_to_add, position)
        errors = (yield self._modify_ssi(groupclone, me()))
        if errors[0] == 0x0000:
            self.ssis[group_ids].add_item_to_group(id_to_add, position)
        else:
            raise SSIException('Error adding item to group: '+
                               ", ".join([ssi_err_types[err] for err in errors]))
        self.ssis.root_group.notify()

    @gen_sequence
    def _remove_from_group(self, key):
        me = (yield None)
        group_id, item_id = tuple_key(key)
        log.info('removing (%d, %d)', group_id, item_id)
        #if it's a set of group ids we got, flip them, because then the
        #rest of the code is identical
        if not item_id:
            group_id, item_id = item_id, group_id
        group_clone = self.ssis[(group_id, 0)].clone()
        group_clone.remove_item_from_group(item_id)
        error = (yield self._modify_ssi(group_clone, me()))
        if not error[0]:
            self.ssis[(group_id, 0)].remove_item_from_group(item_id)
        else:
            raise SSIException('Error removing item from group: '+
                               ",".join([ssi_err_types[err] for err in error]))
        self.ssis.root_group.notify()

    @gen_sequence
    def remove_group(self, group_protocol_object):
        me = (yield None)
        group_protocol_object = getattr(group_protocol_object, 'id', group_protocol_object)
        ssis_to_del = self.get_ssis_in_group(group_protocol_object)#[0])
        log.info('Going to remove: %r', ssis_to_del)
        group_to_del = self.ssis[tuple_key(group_protocol_object)]
        groupclone = group_to_del.clone()
        groupclone.tlvs = {}
        ssis_to_del.append(groupclone)
        with self.ssi_edit(): #needed untill group mod is sent out
            self._remove_ssi(ssis_to_del, me())
            errors = (yield None)
            for (ssi, error) in zip(ssis_to_del, errors):
                if not error and ssi in self.ssis: del self.ssis[ssi]
            if group_protocol_object not in self.ssis:
                self._remove_from_group(group_protocol_object) #end with block
        real_errors = filter(None, errors)
        if real_errors: raise SSIException("Error removing group from list: "+
                               ",".join(ssi_err_types[err] for err in real_errors))
        self.ssis.root_group.notify()

    @gen_sequence
    @callsback
    def remove_buddy_ssi(self, ids, callback = None):
        me = (yield None)
        with self.ssi_edit(): #needed untill group mod is sent out
            buddy_clone = self.ssis[ids].clone()
            error = (yield self._remove_ssi(buddy_clone, me()))
            if not error[0]:
                self._remove_from_group(ids) #end with block
                del self.ssis[ids]
                callback.success()
            else:
                callback.error()
                raise SSIException("Error removing object from list: "+
                               ",".join([ssi_err_types[err] for err in error]))
        self.ssis.root_group.notify()

    @gen_sequence
    def rename_ssi(self, protocol_object, name):
        me = (yield None)
        new_ssi = self.ssis[protocol_object].clone()
        new_ssi.name = name.encode('utf-8')
        errors = (yield self._modify_ssi(new_ssi, me()))
        if errors[0]:
            raise SSIException("Error renaming object: "+
                               ",".join([ssi_err_types[err] for err in errors]))
        else:
            ssiobj = self.ssis[protocol_object]
            ssiobj.name = name.encode('utf-8')
            self.ssis.get_group(protocol_object).set_ssi(ssiobj)
        self.ssis.root_group.notify()

    @gen_sequence
    def alias_ssi(self, contact, name):
        me = (yield None)
        buddy, id = contact.buddy, contact.id
        new_ssi = self.ssis[id].clone()

        name = name.encode('utf-8') if name else None
        new_ssi.set_alias(name) # accepts None to delete

        errors = (yield self._modify_ssi(new_ssi, me()))
        if errors[0]:
            raise SSIException("Error setting alias: " +
                               ",".join(ssi_err_types[err] for err in errors))
        else:
            self.ssis[id].set_alias(name)

        self.ssis.root_group.notify()


    @gen_sequence
    @callsback
    def move_ssi_to_position(self, item_ids, position, group_to_ids=None, callback = None):
        me = (yield None)

        # If we are passed numbers for groups, turn them into group tuples.
        item_ids = tuple_key(item_ids)
        if group_to_ids:
            group_to_ids = tuple_key(group_to_ids)
            if group_to_ids[1]:
                raise SSIException("Can't move items into something which is "
                                   "not a group.")

        if not item_ids[0]:
            #if group == root group
            raise AssertionError("Atttempted to move something in the " +
                                 "SSI root group (this is impossible, " +
                                 "since they don't have position).")
        elif not item_ids[1]:
            # moving a group
            group_from_ids = (0,0)
            if group_to_ids and group_to_ids != (0,0):
                raise SSIException("Can't move group into a group which is "
                                   "not the root group.")
            id_to_move = item_ids[0]
        else:
            # moving a buddy
            group_from_ids = (item_ids[0],0)
            id_to_move = item_ids[1]
        if not group_to_ids or group_from_ids == group_to_ids:
            #move within group/move a group within root group
            groupclone = self.ssis[group_from_ids].clone()
            groupclone.move_item_to_position(id_to_move, position)
            errors = (yield self._modify_ssi(groupclone, me()))
            if not errors[0]:
                self.ssis[group_from_ids]. \
                move_item_to_position(id_to_move, position)
            else:
                raise SSIException('Error moving item: '+
                               ",".join([ssi_err_types[err] for err in errors]))
        else:
            #moving between groups
            del id_to_move
            if not group_to_ids[0]:
                #if there is a group to go to, make sure it's not the root group
                raise AssertionError("atttempted to move something to the " +
                                     "SSI root group (this is impossible, " +
                                     "since they don't have position)")
            else:
                # valid from, valid to
                # do crazy delete/add/modify x2 here
                old_ssi = self.ssis[item_ids]
                new_ssi = old_ssi.clone()
                new_ssi.group_id = group_to_ids[0]
                new_ssi.item_id  = self.new_ssi_item_id(group_to_ids[0])
                with self.ssi_edit(): #needed untill last group mod is sent out
                    del_errors, action1, add_errors, action2 = \
                    (yield self._ssi_double_action(
                                                    0x0a, old_ssi, 0x08, new_ssi, me()))
                    if action1 != 0x0a:
                        del_errors, add_errors = add_errors, del_errors

                    del_group_clone, add_group_clone = None, None

                    if not del_errors[0]:
                        del self.ssis[old_ssi]
                        del_group_clone = self.ssis[(old_ssi.group_id,0)].clone()
                        del_group_clone.remove_item_from_group(old_ssi.item_id)
                    if not add_errors[0]:
                        self.ssis[new_ssi] = new_ssi
                        add_group_clone = self.ssis[(new_ssi.group_id,0)].clone()
                        add_group_clone.add_item_to_group(new_ssi.item_id, position)
                    mod_ssis = filter( None, [del_group_clone, add_group_clone])
                    self._modify_ssi(mod_ssis, me()) #end with block
                mod_errors = (yield None)

                del_mod_error = None
                add_mod_error = None
                if not del_errors[0]:
                    del_mod_error = mod_errors[0]
                    mod_errors = mod_errors[1:]
                    if not del_mod_error:
                        self.ssis[(old_ssi.group_id,0)] \
                            .remove_item_from_group(old_ssi.item_id)
                if not add_errors[0]:
                    add_mod_error = mod_errors[0]
                    if not add_mod_error:
                        self.ssis[(new_ssi.group_id,0)] \
                            .add_item_to_group(new_ssi.item_id, position)

                # error handling

                errors = filter(None, (add_errors[0], del_errors[0], del_mod_error, add_mod_error))

                if errors:
                    err_string = ''
                    if del_errors[0]:
                        if err_string: err_string += ", "
                        err_string += "deleting " + old_ssi.name + " in group " + \
                        self.ssis[(old_ssi.group_id,0)].name
                    if del_mod_error:
                        if err_string: err_string += ", "
                        err_string += "removing " + old_ssi.name + " from group " + \
                        self.ssis[(old_ssi.group_id,0)].name + " list"
                    if add_errors[0]:
                        if err_string: err_string += ", "
                        err_string += "adding " + old_ssi.name + " in group " + \
                        self.ssis[(new_ssi.group_id,0)].name
                    if add_mod_error:
                        if err_string: err_string += ", "
                        err_string += "adding " + old_ssi.name + " to group " + \
                        self.ssis[(new_ssi.group_id,0)].name + " list"

                    callback.error()
                    raise SSIException("ERROR %s: %r" % (err_string,
                                                         ",".join([ssi_err_types[err] for err in errors])))

        #from util import Timer
        #Timer(1, callback.success).start()
        callback.success((new_ssi.group_id, new_ssi.item_id))
        self.ssis.root_group.notify()


    def _edit_server_list_start(self, import_transaction=False):
        '''
        start editing SSIs!
        '''
        if not self.ssi_edits_out:
            self.o.send_snac(*snac.send_x13_x11(import_transaction))
        self.ssi_edits_out += 1

    def _edit_server_list_end(self):
        '''
        done editing SSIs
        '''
        self.ssi_edits_out -= 1
        if not self.ssi_edits_out:
            self.o.send_snac(*snac.send_x13_x12())

    @contextmanager
    def ssi_edit(self, import_transaction=False):
        self._edit_server_list_start(import_transaction)
        try:
            yield self
        finally:
            self._edit_server_list_end()
