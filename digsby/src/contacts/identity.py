from util import removedupes

class Identity(object):
    __slots__ = ['id', 'alias', 'groups', 'buddies']

    def __init__(self, id, alias=None, groups = None, buddies = None):
        if groups is None:  groups = set()
        if buddies is None: buddies = []

        self.id      = id
        self.alias   = alias
        self.groups  = groups

        # None is not a valid group name...for now.
        none_tuple = (None,)
        if any(g == none_tuple for g in groups):
            raise ValueError('groups had a None')

        self.buddies = removedupes(buddies)

    def serialize(self):
        buds = [buddy.serialize() for buddy in self.buddies]
        buds2 = []
        for bud in buds:
            if bud not in buds2:
                buds2.append(bud)
        return dict(id = self.id, alias = self.alias,
                    groups = self.groups, buddies = buds2)

    @classmethod
    def unserialize(cls, d):
        buds = [Personality.unserialize(buddy) for buddy in d['buddies']]
        d['buddies'] = buds
        return cls(**d)

    def __repr__(self):
        return "<Identity %r groups: %r, buddies: %r>" % (self.alias, self.groups, self.buddies)

class Personality(object):
    __slots__ = ['name', 'service']

    def __init__(self, name, service):
        self.name    = name.lower()
        self.service = service

    def serialize(self):
        return dict(name = self.name.lower(), service = self.service)

    @property
    def tag(self):
        return (self.name.lower(), self.service)

    def __hash__(self):
        return hash(self.tag)

    def __cmp__(self, other):
        if other is self:
            return 0
        if not isinstance(other, type(self)):
            return -1
        return cmp(self.tag, other.tag)

    @classmethod
    def unserialize(cls, d):
        return cls(**d)

    def __repr__(self):
        return "<Personality %s %s>" % (self.name.lower(), self.service)


