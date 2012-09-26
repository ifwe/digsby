from common import profile
from logging import getLogger; log = getLogger('buddyinfo')


class BuddyInfo(object):
    __slots__ = ['protocol_name', 'protocol_username', 'buddy_name']

    def __init__(self, buddy):
        protocol = buddy.protocol
        self.protocol_name = protocol.name
        self.protocol_username = protocol.username
        self.buddy_name = buddy.name

    def __eq__(self, obj):
        s = object()
        for slot in self.__slots__:
            if getattr(self, slot) != getattr(obj, slot, s):
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash('_'.join(getattr(self, slot) for slot in self.__slots__))

    def buddy(self):
        protocol = profile.account_manager.get_im_account(self.protocol_username, self.protocol_name)
        if protocol is None or not protocol.connected:
            return None

        return protocol.connection.get_buddy(self.buddy_name)

    def isbuddy(self, buddy):
        return (buddy.name == self.buddy_name and
                buddy.protocol.username == self.protocol_username and
                buddy.protocol.name == self.protocol_name)

    def __repr__(self):
        return '<BuddyInfo %s (on %s:%s)>' % (self.buddy_name, self.protocol_name, self.protocol_username)


class binfoproperty(object):
    '''
    server-side buddy information
    '''

    def __init__(self, name, default = sentinel):
        if not isinstance(name, basestring):
            raise TypeError

        self.name = name
        self.default = default

    def __get__(self, obj, objtype):
        res = profile.blist.get_contact_info(obj, self.name)
        if res is None and self.default is not sentinel:
            res = self.default()
            log.info('%s: %s not found, placing default %s', obj.name, self.name, res)
            profile.blist.set_contact_info(obj, self.name, res)

        return res

    def __set__(self, obj, value):
        return profile.blist.set_contact_info(obj, self.name, value)
