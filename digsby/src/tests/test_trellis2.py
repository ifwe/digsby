from collections import defaultdict
import string

input1 = ['z', '4', 'B', '8', '1', '3', 'A', 'c', 'w', '5']
input2 = ['z', 'B', 'A', 'c', 'w', '4', '8', '1', '3', '5']

assert set(input1) == set(input2)

#fs = ((lambda x: 'letters' if x in string.ascii_letters else 'other'), (lambda x: 'low' if x in string.ascii_lowercase else 'other'))
from operator import attrgetter
fs = (lambda x: -x.log_size, attrgetter('status'))

from util import odict

class SplitterS(object):
    def __init__(self, input, funcs):
        self.funcs = funcs
        self._partitions = self._old_partitions = None
        self.input = input

    def set_input(self, input):
        self.new_input = input
        self.repartition()

    def repartition(self):
        self._old_partitions = self._partitions
        self._partitions = self.partitions()

    def partitions(self):
        f = self.funcs[0]
        if f is None:
            return self.input
        d = defaultdict(list)
        for x in self.input:
            d[f(x)].append(x)
        return d

    def _output(self):
        if not self.funcs:
            return self.input
        d = {}
        old = self.last_output #get our old value
        parts = self._partitions #localize
        for x in parts:
            if x and x in old: #reuse, for caching purposes.
                d[x] = old[x]
                d[x].input = parts[x]
                continue
            d[x] = SplitterS(input=parts[x], funcs = self.funcs[1:])
        self.last_output = d
        return d

class Splitter(trellis.Component):
    input = trellis.attr()

    def __init__(self, **k):
        self.funcs = k.pop('funcs', ())
        trellis.Component.__init__(self, **k)

    @trellis.compute
    def partitions(self):
        f = self.funcs[0]
        if f is None:
            return self.input
        d = defaultdict(list)
        for x in self.input:
            d[f(x)].append(x)
        return d

    @trellis.maintain(initially={})#(optional=True)
    def output(self):
        if not self.funcs:
            return self.input
        d = {}
        old = self.output #get our old value
        parts = self.partitions #localize + depend on the partitions
        for x in parts:
            if x in old: #reuse, for caching purposes.
                d[x] = old[x]
                d[x].input = parts[x] #only need to set the input, trellis does the rest
                continue
            d[x] = Splitter(input=parts[x], funcs = self.funcs[1:])
        return d

    def __repr__(self):
        return "<Splitter>"

class GroupSplitterS(object):
    def __init__(self, input, funcs):
        self.groups = input
        self.funcs = funcs
        self.output = self._output()

    def _output(self):
        funcs = self.funcs
        return dict((g.name, SplitterS(input=g, funcs=funcs)) for g in self.groups)

class GroupSplitter(trellis.Component):
    input = trellis.attr()
    def __init__(self, **k):
        self.funcs = k.pop('funcs', ())
        trellis.Component.__init__(self, **k)

    @trellis.maintain(initially={})
    def output(self):
        funcs = self.funcs
        return dict((g.name, Splitter(input=g, funcs=funcs)) for g in self.input)

    def __repr__(self):
        return "<GroupSplitter>"

class RootGroupSplitterS(object):
    def __init__(self, input, funcs):
        self.input = input
        self.funcs = funcs
        self.output = self._output()

    def _output(self):
        funcs = self.funcs
        return [GroupSplitterS(input=g, funcs=funcs) for g in self.input]

class RootGroupSplitter(trellis.Component):
    input = trellis.attr()
    def __init__(self, **k):
        self.funcs = k.pop('funcs', ())
        trellis.Component.__init__(self, **k)

    @trellis.maintain
    def output(self):
        funcs = self.funcs
        return [GroupSplitter(input=g, funcs=funcs) for g in self.input]

    def __repr__(self):
        return "<RootGroupSplitter>"

class accumulator_dict(defaultdict):
    def __init__(self):
        defaultdict.__init__(self, list)

    def accumulate(self, d):
        for k in d:
            self[k].append(d[k])

class GroupJoiner(trellis.Component):
    input = trellis.attr()

    @trellis.maintain
    def output(self):
        a = accumulator_dict()
        for g in self.input:
            a.accumulate(g.output)
        for k in a:
            a[k] = SplitterJoiner(input=a[k])
        return dict(a)

    def __repr__(self):
        return "<GroupJoiner>"

class GroupJoinerS(object):
    def __init__(self, input):
        self.input = input
        self.output = self._output()

    def _output(self):
        a = accumulator_dict()
        for g in self.input:
            a.accumulate(g.output)
        for k in a:
            a[k] = SplitterJoinerS(input=a[k])
        return dict(a)

    def __repr__(self):
        return "<GroupJoiner>"

#g = RootGroupSplitter(input=p.blist.rootgroups, funcs = fs)
#gj = GroupJoiner(input=g.output)
#d = {}
#for k in gj.output:
#    d[k] = dlocal = accumulator_dict()
#    list_of_splitters = gj.output[k]
#    for splitter in list_of_splitters:
#        dlocal.accumulate(splitter.output)

class SplitterJoiner(trellis.Component):
    input = trellis.attr()

    @trellis.maintain
    def output(self):
        #accumulate in order, then sorting the keys should do the job.
        d = accumulator_dict()
        #1.  base case
        if not isinstance(self.input[0].output, dict):
            #leaf merge here!
            return sum([x.output for x in self.input], [])
        #2.  recursion
        for splitter in self.input:
            d.accumulate(splitter.output)
        for k in d:
            d[k] = SplitterJoiner(input=d[k])

        #3.  output
        ret = []
        #sorted(d) would have key/cmp method(s)
        for k in sorted(d):
            ret.extend(d[k].output)
        return ret


    def __repr__(self):
        return "<Joiner>"

class SplitterJoinerS(object):
    def __init__(self, input):
        self.input = input
        self.output = self._output()

    def _output(self):
        #accumulate in order, then sorting the keys should do the job.
        d = accumulator_dict()
        #1.  base case
        if not isinstance(self.input[0].output, dict):
            #leaf merge here!
            return sum([x.output for x in self.input], [])
        #2.  recursion
        for splitter in self.input:
            d.accumulate(splitter.output)
        for k in d:
            d[k] = SplitterJoinerS(input=d[k])

        #3.  output
        ret = []
        #sorted(d) would have key/cmp method(s)
        for k in sorted(d):
            ret.extend(d[k].output)
        return ret


    def __repr__(self):
        return "<Joiner>"
