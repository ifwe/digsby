from common.actions import ActionMeta
import jabber
import common.actions
from common.actions import action #@UnresolvedImport
import contacts
from util import callsback

import logging
log = logging.getLogger('jabber.contact')

contact_attrs = ('watched','buddy_changed','__repr__', 'group', 'buddy', 'remove_from_group')

no_widget = lambda self, *a, **k: None if getattr(self.buddy, 'iswidget', False) else True

cgetattr = contacts.Contact.__getattribute__

objget = object.__getattribute__

class JabberContact(common.actions.ActionType, contacts.Contact):
    'An entry on a buddy list.'

    inherited_actions = [jabber.jbuddy]
    __metaclass__ = ActionMeta

    _renderer = 'Contact'

    def __init__(self, buddy, group):
        self.group = group
        contacts.Contact.__init__(self, buddy, buddy.id)


    @action()
    @callsback
    def remove(self, callback = None):
        if len(self.buddy.groups) <= 1:
            # If this buddy is only in one (or no) group(s), unsubscribe.
            return self.buddy.remove(callback = callback)
        else:
            return self.remove_from_group(callback = callback)

    @action(no_widget)
    def rename_gui(self):
        return contacts.Contact.rename_gui(self)

    @callsback
    def remove_from_group(self, callback = None):
        'Only removes this contact from the Group.'
        log.info('remove_from_group %s: %s', self.group, self)

        item = self.protocol.roster.get_item_by_jid(self.buddy.jid).clone()
        item.groups.remove(self.group)
        query = item.make_roster_push()

        self.protocol.send_cb(query, callback=callback)

    @callsback
    def replace_group(self, new_group, callback = None):
        item = self.protocol.roster.get_item_by_jid(self.buddy.jid).clone()
        if self.group is not None:
            item.groups.remove(self.group)
        if new_group not in item.groups:
            item.groups.append(new_group)
        query = item.make_roster_push()
        self.protocol.send_cb(query, callback = callback)

    @action(no_widget)
    def view_past_chats(self, *a, **k):
        self.buddy.view_past_chats(*a, **k)

    def __iter__(self):
        "Returns an iterator for this contact's resources."

        return iter(self.buddy)

    def __getattr__(self, attr):
        if attr in contact_attrs:
            return cgetattr(self, attr)
        else:
            return getattr(cgetattr(self, 'buddy'), attr)

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.buddy.name)

    @action(lambda self: None)
    def block(self):
        pass

    unblock = block
