
from peak.events import trellis
from hashlib import md5
import struct
from pprint import pformat, pprint
from operator import attrgetter
from collections import defaultdict

class Viewer(trellis.Component):
    model = trellis.attr(None)

    @trellis.perform
    def view_it(self):
        if self.model is not None:
            pprint( list(self.model))


class Buddy(trellis.Component):

    name       = trellis.attr()
    status     = trellis.attr()
    status_msg = trellis.attr()
    log_size   = trellis.attr()
    service    = trellis.attr()

    def __repr__(self):
        return '<Buddy name:%(name)s, status:%(status)6s, status_msg:%(status_msg)8s, log_size:%(log_size)05d, service:%(service)s>' % \
                dict((a,getattr(self, a)) for a in 'name status status_msg log_size service'.split())

buddy_num = 0

services = ['foo', 'bar', 'quux']
statuses = ['woot', 'blargh', 'wtf']
status_messages = ['hi', 'bye', 'not here', 'lunch', 'go away']

buddies = {}

import random

def make_buddies(num):
    global buddy_num
    global services
    global buddies
    ret = []
    for _i in xrange(num):
        name = "buddy %2d" % buddy_num
        b = Buddy(name = name, log_size = struct.unpack('H', md5(name).digest()[:2])[0],
                  service = services[buddy_num % len(services)],
                  status = statuses[(buddy_num -1) % len(statuses)],
                  status_msg = status_messages[(buddy_num -2) % len(status_messages)],
                  )
        buddies[buddy_num] = b
        ret.append(b)
        buddy_num += 1
    return ret

class NameSorter(trellis.Component):

    input = trellis.make(list)

    @trellis.maintain(optional=True)
    def output(self):
#        print 'name output running', id(self)
        return sorted(self.input, key = lambda x: x.name)

def merge(left, right, cmp=cmp, key = lambda x: x):
    result = []
    i ,j = 0, 0
    while(i < len(left) and j < len(right)):
        if cmp(key(left[i]), key(right[j])) <= 0:
            result.append(left[i])
            i = i + 1
        else:
            result.append(right[j])
            j = j + 1
    result += left[i:]
    result += right[j:]
    return result

class Merger(trellis.Component):
    input = trellis.make(list)
    key   = trellis.attr() #attrgetter('name')

    @trellis.maintain
    def output(self):
        if len(self.input) > 1:
            return reduce(lambda *a, **k: merge(*a, **dict(key=self.key)), self.input)
        elif len(self.input):
            return self.input[0]
        else:
            return []

class Splitter(trellis.Component):
    input = trellis.make(list)
    basesort = trellis.attr() #NameSorter
    spliton  = trellis.attr() #attrgetter('status')

    @trellis.maintain
    def output(self):
#        print "partitions running"
        if not self.input:
            return {}
        ret = dict()
        for b in self.input:
            stat = self.spliton(b)
            if stat not in ret:
                ret[stat] = n = self.basesort()
            else:
                n = ret[stat]
            n.input.append(b)
#        print len(ret), "partitions"
        return ret

class Splitter1(object):
    def __init__(self, in_=None, splitfuncs=()):
        self.in_ = in_ or []
        self.funcs = splitfuncs
    def output(self):
        if not self.funcs:
            return self.in_
        f = self.funcs[0]
        d = defaultdict(lambda: Splitter1(splitfuncs=self.funcs[1:]))
        for x in self.in_:
            d[f(x)].in_.append(x)
        return d

class DJoiner(trellis.Component):
    input = trellis.make(list)

    @trellis.maintain
    def output(self):
        d = defaultdict(list)
        for splitter in self.input:
            o = splitter.output
            for key, val in o.iteritems():
                d[key].append(val.output)
        for k,v in d.iteritems():
            d[k] = Merger(input=v, key = attrgetter('name'))
        return dict(d)

class Sum(trellis.Component):
    sortfunc = lambda self, x: x
    input = trellis.make(dict)
    @trellis.maintain
    def output(self):
        return sum([self.input[k].output for k in sorted(self.input.keys(),
                                                    key = self.sortfunc)], [])


#    @trellis.maintain
#    def output(self):
#        print 'status output running'
#        parts = self.partitions
#        return sum([parts[k].output for k in sorted(parts.keys())], [])


#    @trellis.perform
#    def set_output(self):
#        self._output = self.output

buds = make_buddies(10)
buds2 = make_buddies(10)
random.shuffle(buds)
random.shuffle(buds2)

#pprint(buds)

print '*' * 100
import time
a = time.clock()
foobar = Sum(input=DJoiner(input=[Splitter(input = buds,
                                 spliton = attrgetter('status'),
                                 basesort = NameSorter)]).output
                )
b = time.clock()
#pprint(foobar.output)
foobar.output
print b - a
a = time.clock()
buddies[3].service='foobarfoo'
b = time.clock()
#pprint(foobar.output)
foobar.output
print b - a

