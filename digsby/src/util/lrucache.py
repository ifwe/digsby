from __future__ import with_statement

# thanks ASPN Python Cookbook
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/498245

from collections import deque
from threading import RLock
from functools import wraps
from pprint import pformat
from timeit import default_timer

def lru_cache(maxsize):
    '''Decorator applying a least-recently-used cache with the given maximum size.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    '''

    lck = RLock()
    def decorating_function(f):
        cache = {}              # mapping of args to results
        queue = deque()         # order that keys have been accessed
        refcount = {}           # number of times each key is in the access queue

        @wraps(f)
        def wrapper(*args, **kwargs):
            with lck:
                # localize variable access (ugly but fast)
                _cache=cache; _len=len; _refcount=refcount; _maxsize=maxsize
                queue_append=queue.append; queue_popleft = queue.popleft
                #print wrapper.hits, '/', wrapper.misses

                # get cache entry or compute if not found

                key = args#+tuple(sorted(kwargs.items()))

                try:
                    result = _cache[key]
                    #wrapper.hits += 1
                except KeyError:
                    result = _cache[key] = f(*args, **kwargs)
                    #wrapper.misses += 1

                # record that this key was recently accessed
                queue_append(key)
                _refcount[key] = _refcount.get(key, 0) + 1

                # Purge least recently accessed cache contents
                while _len(_cache) > _maxsize:
                    k = queue_popleft()
                    _refcount[k] -= 1
                    if not _refcount[k]:
                        del _cache[k]
                        del _refcount[k]

                # Periodically compact the queue by duplicate keys
                if _len(queue) > _maxsize * 4:
                    for i in [None] * _len(queue):
                        k = queue_popleft()
                        if _refcount[k] == 1:
                            queue_append(k)
                        else:
                            _refcount[k] -= 1
                    assert len(queue) == len(cache) == len(refcount) == sum(refcount.itervalues())

            return result

        return wrapper
    return decorating_function



class MyDoublyLinkedListNode(object):
    __slots__ = ['data', 'prev', 'next']

    def __init__(self, data, prev=None, next=None):
        self.data = data
        self.prev = prev
        self.next = next

    def remove(self):
        assert self.next is not None

        if self.prev is not None:
            self.prev.next = self.next

        self.next.prev = self.prev

    def append(self, node):
        if self.next is not None:
            raise NotImplementedError("I don't have use for real insertion")

        self.next = node
        node.prev = self

    def __repr__(self):
        return '%s(%r, %r)' % (self.__class__.__name__, self.data, self.next)

class LRU(dict):
    # thanks http://www.algorithm.co.il/blogs/

    node_class = MyDoublyLinkedListNode
    def __init__(self, limit):
        self._limit = limit

        self._init()

    def _init(self):
        # Use order initialization
        self._ll_head = self._ll_last = self.node_class(None)
        self._ll_mapping = {}
        self.lock = RLock()

    def __setitem__(self, key, value):
        with self.lock:
            # if key is last node (most recent), nothing needs to be done
            if self._ll_last.data == key:
                return dict.__setitem__(self, key, value)

            if key in self:
                # remove from llist (in order be appended to the end)
                self._ll_mapping[key].remove()
            elif len(self) == self._limit:
                # remove least recently used item
                self.pop_lru_key()

            # append to llist and update mapping
            new_node = self.node_class(key)
            self._ll_last.append(new_node)
            self._ll_last = new_node
            self._ll_mapping[key] = new_node

            # Actually set the item
            dict.__setitem__(self, key, value)

            assert len(self) == len(self._ll_mapping), (self, self._ll_mapping)
            assert len(self) <= self._limit, self

    def pop_lru_key(self):
        key = self._ll_head.next.data
        try:
            dict.__delitem__(self, key)
        except KeyError:
            pass

        try:
            del self._ll_mapping[key]
        except KeyError:
            pass

        self._ll_head.next.remove()
        return key

    def __delitem__(self, key):
        raise NotImplementedError("Not necessary for LRU Cache")


class MyTimedDoublyLinkedListNode(MyDoublyLinkedListNode):
    __slots__ = MyDoublyLinkedListNode.__slots__ + ['created']

    def __init__(self, data, prev=None, next=None):
        super(MyTimedDoublyLinkedListNode, self).__init__(data, prev, next)
        self.created = default_timer()

class ExpiringLRU(LRU):
    node_class = MyTimedDoublyLinkedListNode

    def __init__(self, time_limit):
        self.time_limit = time_limit
        self._init()

    @property
    def _limit(self):
        return len(self)

    def pop_lru_key(self):
        #base case, can't kill the last node
        while len(self) > 1:
            key = self._ll_head.next.data
            try:
                val = self[key]
            except KeyError:
                pass
            else:
                if self._ll_head.next.created + self.time_limit >= default_timer():
                    return
            try:
                dict.__delitem__(self, key)
            except KeyError:
                pass

            try:
                del self._ll_mapping[key]
            except KeyError:
                pass
            self._ll_head.next.remove()

if __name__ == "__main__":
    c = LRU(3)
    print c

    c['a'] = 1
    c['b'] = 2
    c['c'] = 3

    print c

    c['c'] = 5
    print c
    c['a'] = 6
    print c

    print '#'*20
    d = ExpiringLRU(1)
    d['a'] = 1
    d['b'] = 2
    print d
    import time
    print 'sleeping'
    time.sleep(1.5)
    print d
    d['c'] = 3
    d['d'] = 4
    print d
    print 'sleeping'
    time.sleep(1.5)
    print d
    d['e'] = 5
    d['c'] = 7
    print d
    d['f'] = 6
    print d
