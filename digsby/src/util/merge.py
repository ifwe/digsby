'''

For merging mappings recursively.

>>> d, d2 = {1: {2: 3}}, {1: {2: 4}}
>>> res = merge(d, d2)
>>> assert res == {1: {2: 4}}

'''

from operator import isMappingType, isSequenceType
from heapq import heapreplace, heappop

from .primitives import Storage
S = Storage

if 'sentinel' not in globals():
    sentinel = object()

def merge(*mappings, **opts):
    '''
    Merges all mappings given as arguments.

    opts can have {'keyeq': predicate}
    '''

    d = {}

    keytransform = opts.get('keytransform', lambda k: k)

    for elem in mappings:
        if isMappingType(elem):
            # {key: value, key: value, ...}
            items = elem.iteritems()
        elif isSequenceType(elem):
            # [(key, value), (key, value), ...]
            if not all(len(s) == 2 for s in elem):
                raise TypeError('mapping sequences must be sequences of (key,'
                                'value) pairs: %s %s' % (type(elem), repr(elem)))

            items = elem
        else:
            raise TypeError('all arguments to merge must be mappings: %r' % elem)

        for key, value in items:
            merge_values(d, keytransform(key), value, keytransform)

    return d

def merge_values(mapping, key, value, keytransform = None):
    '''
    Exactly like mapping.update({key: value}) except that if both values are
    mappings, then they are merged recursively.
    '''
    assert isMappingType(mapping)
    assert key is not sentinel and value is not sentinel

    if keytransform is None:
        keytransform = lambda k: k

    curval = mapping.get(key, sentinel)
    if curval is not sentinel and isMappingType(curval) and isMappingType(value):
        # key exists in old and new, and both values are mappings--recursively
        # merge those mappings
        for subkey, subvalue in value.iteritems():
            merge_values(curval, keytransform(subkey), subvalue)
    else:
        # new value doesn't exist in mapping or both values are not mappings--
        # so overwrite the old value with the new one
        mapping[keytransform(key)] = value


def lower_if_string(s):
    try:
        return s.lower()
    except AttributeError:
        return s

def merge_keys(d, maptype=Storage):
    'Recursively merges all keys of d (and its sub dictionaries), case insensitively.'

    if not d: return d
    return tolower(merge(d, keytransform = lower_if_string), maptype=maptype)

def tolower(mapping, maptype=Storage):
    'Returns a copy of a mapping tree with all string keys lowercased.'

    return maptype((getattr(k, 'lower', lambda k: k)(), tolower(v, maptype) if isMappingType(v) else v)
             for k, v in mapping.iteritems())

def imerge(*iterlist, **key):
    """Merge a sequence of sorted iterables.

    Returns pairs [value, index] where each value comes from
iterlist[index], and the pairs are sorted
    if each of the iterators is sorted.
    Hint use groupby(imerge(...), operator.itemgetter(0)) to get
the items one by one.
    """
    # thanks http://mail.python.org/pipermail/python-bugs-list/2005-August/029983.html
    if key.keys() not in ([], ["key"]):
        raise TypeError("Excess keyword arguments for imerge")

    key = key.get("key", lambda x:x)

    # initialize the heap containing (inited, value, index, currentItem, iterator)
    # this automatically makes sure all iterators are initialized, then run, and finally emptied
    heap = [(False, None, index, None, iter(iterator))
            for index, iterator in enumerate(iterlist)]

    while heap:
        inited, item, index, value, iterator = heap[0]
        if inited: yield value, index
        try: item = iterator.next()
        except StopIteration: heappop(heap)
        else: heapreplace(heap, (True, key(item), index, item, iterator))

def lazy_sorted_merge(*iterables, **k):
    return (value for value, index in imerge(*iterables, **k))

