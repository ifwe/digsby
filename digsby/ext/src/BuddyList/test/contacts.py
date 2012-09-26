#__LICENSE_GOES_HERE__
'''
mock objects for unittests
'''

class Group(list):
    def __init__(self, name, protocol, id, *children):
        self.name = name
        self.protocol = protocol
        self.id = id
        if children: self[:] = children

class RootGroup(Group):
    def __init__(self, name, protocol, id, *children):
        Group.__init__(self, name, protocol, id, *children)
        self._root = True

class Buddy(object):
    def __init__(self, name, protocol, service = None, **kws):
        self.name = name
        self.alias = name
        self.protocol = protocol
        self.service = service if service is not None else protocol.service
        self.status = "offline"
        self.__dict__.update(kws)
        self.status_orb = self.status
        self.mobile = self.status_orb == 'mobile'
        self._notify_dirty = True

    def __repr__(self):
        return '<Buddy %s %s>' % (self.name, self.service)

class Account(object):
    def __init__(self, username, service):
        self.name = username
        self.protocol = service

class Protocol(object):
    def __init__(self, username, service):
        self.username = username
        self.service = service
        self.account = Account(username, service)

    def __repr__(self):
        return '<Protocol %s %s>' % (self.username, self.service)
