import simplejson

#    +---------------+-------------------+
#    | JSON          | Python            |
#    +===============+===================+
#    | object        | dict              |
#    +---------------+-------------------+
#    | array         | list              |
#    +---------------+-------------------+
#    | string        | unicode, !str     |
#    +---------------+-------------------+
#    | number (int)  | !int, !long       |
#    +---------------+-------------------+
#    | number (real) | !float            |
#    +---------------+-------------------+
#    | true          | True              |
#    +---------------+-------------------+
#    | false         | False             |
#    +---------------+-------------------+
#    | null          | None              |
#    +---------------+-------------------+

#    +---------------------+---------------+
#    | Python              | JSON          |
#    +=====================+===============+
#    | dict                | object        |
#    +---------------------+---------------+
#    | list, !tuple        | array         |
#    +---------------------+---------------+
#    | !str, unicode       | string        |
#    +---------------------+---------------+
#    | !int, !long, !float | number        |
#    +---------------------+---------------+
#    | True                | true          |
#    +---------------------+---------------+
#    | False               | false         |
#    +---------------------+---------------+
#    | None                | null          |
#    +---------------------+---------------+
def serialize(thing):
    if type(thing) is dict:
        return dict((serialize(a), serialize(b)) for a,b in thing.iteritems())
    elif isinstance(thing, str):
        return '__str__' + thing
    elif isinstance(thing, unicode):
        return '__unicode__' + thing
    elif isinstance(thing, bool):
        if thing:
            return '__True__'
        else:
            return '__False__'
    elif isinstance(thing, (int, long)):
        return '__int__' + str(thing)
    elif isinstance(thing, float):
        return '__float__' + repr(thing)
    elif isinstance(thing, type(None)):
        return '__None__'
    elif type(thing) is tuple:
        return {'__tuple__' : list(serialize(foo) for foo in thing)}
    elif type(thing) is list:
        return list(serialize(foo) for foo in thing)
    elif type(thing) is set:
        return {'__set__' : [serialize(foo) for foo in sorted(thing)]}
    elif type(thing) is frozenset:
        return {'__frozenset__' : [serialize(foo) for foo in sorted(thing)]}
    else:
        assert False, (type(thing), thing)

def unserialize(thing):
    if type(thing) in (unicode, str):
        if thing.startswith('__str__'):
            return str(thing[7:])
        if thing.startswith('__unicode__'):
            return unicode(thing[11:])
        if thing.startswith('__int__'):
            return int(thing[7:])
        if thing.startswith('__float__'):
            return float(thing[9:])
        if thing == '__None__':
            return None
        if thing == '__True__':
            return True
        if thing == '__False__':
            return False
        assert False, 'all incoming unicode should have been prepended'
        return thing
    if type(thing) is dict:
        return dict((unserialize(foo),unserialize(bar)) for foo,bar in thing.iteritems())
    elif type(thing) is set:
        return set(unserialize(foo) for foo in thing)
    elif type(thing) is frozenset:
        return frozenset(unserialize(foo) for foo in thing)
    elif type(thing) is tuple:
        return tuple(unserialize(foo) for foo in thing)
    elif type(thing) is list:
        return list(unserialize(foo) for foo in thing)
    else:
        assert False, type(thing)

def untupleset(obj):
    if '__tuple__' in obj:
        assert len(obj) == 1
        return tuple(obj['__tuple__'])
    elif '__set__' in obj:
        assert len(obj) == 1
        return set(obj['__set__'])
    elif '__frozenset__' in obj:
        assert len(obj) == 1
        return frozenset(obj['__frozenset__'])
    return obj

def pydumps(obj):
    return simplejson.dumps(serialize(obj), sort_keys=True, separators=(',', ':'))

def pyloads(obj):
    return unserialize(simplejson.loads(obj, object_hook=untupleset))

__all__ = ['pydumps', 'pyloads']

if __name__=='__main__':
    #TODO: this needs test cases
    pass

