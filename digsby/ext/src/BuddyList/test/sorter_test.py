#__LICENSE_GOES_HERE__
from __future__ import with_statement

from contacts import Group, Buddy, Protocol, RootGroup
from unittest import TestCase, main
import blist
import gc
import sip
import sys

from sortertestdata import test_contact_order

blist.set_group_type(Group)


# SIP can show diagnostic traces for these categories
class SipTrace(object):
    VIRTUAL      = 0x0001
    CONSTRUCTOR  = 0x0002
    DESTRUCTOR   = 0x0004
    PY_INIT      = 0x0008
    PY_DEL       = 0x0010
    PY_METHOD    = 0x0020

SipTrace.ALL = (SipTrace.VIRTUAL | SipTrace.CONSTRUCTOR | SipTrace.DESTRUCTOR
                | SipTrace.PY_INIT | SipTrace.PY_DEL | SipTrace.PY_METHOD)

sip.settracemask(SipTrace.ALL)
def leakcheck(func, *args):
    '''
    Run func(*args), checking that the refcounts of all objects in args remains
    equal before and after.
    '''

    before = [sys.getrefcount(obj) for obj in args]
    func(*args)
    gc.collect()
    after = [sys.getrefcount(obj) for obj in args]

    def objrepr(o):
        return repr(o)[:60].replace('\n', ' ')

    failures = []
    for i in xrange(len(before)):
        before_ref, after_ref = before[i], after[i]
        if before_ref > after_ref:
            failures.append('    -%d: %s' % (before_ref - after_ref, objrepr(args[i])))
        elif after_ref > before_ref:
            failures.append('    +%d: %s' % (after_ref - before_ref, objrepr(args[i])))

    if failures:
        raise AssertionError('\n'.join(['%r leaked:' % func.__name__] + failures))

test_protocol = Protocol(u'digsby01', u'aim')
test_buddy = Buddy(u'digsby13', test_protocol)
test_root_group = Group(u'root', test_protocol, 'root',
    Group(u'buddies', test_protocol, 'buddies',
        test_buddy
    )
)


class TestSorter(TestCase):
    def test_sorts_by(self):
        import blist
        s = blist.BuddyListSorter()
        assert s.sortsBy(blist.Name)
        assert not s.sortsBy(blist.LogSize)

    def test_leaks(self):
        '''
        test that python conversion methods don't leak refcounts
        '''

        sorter = blist.BuddyListSorter()
        leakcheck(sorter.set_contact_order, test_contact_order)
        leakcheck(sorter.set_contact_order, {})

    def test_invalid_input(self):
        sorter = blist.BuddyListSorter()
        self.assertRaises(TypeError, sorter.set_contact_order, None)

    def test_group_counts(self):
        sorter = blist.BuddyListSorter()
        sorter.addSorter(blist.ByFakeRoot("Contacts"))
        sorter.addSorter(blist.ByGroup(True, 2))
        sorter.addSorter(blist.ByOnline(True, True))

        p = Protocol('aim', 'digsby01')
        sorter.set_root(Group('root', p, 'root',
                          Group('root1', p, 'root1',
                              Buddy('abc', p),
                              Buddy('def', p),
                              Group('Contacts', p, 'Contacts',
                                  ))))

        n = sorter._gather()
        try:
            # TODO: make 0 and 2 properties here.
            assert '0/2' in n[0].display_string
        finally:
            sorter._done_gather(n)

    def test_nodes(self):
        sorter = blist.BuddyListSorter()
        sorter.set_root(test_root_group)

        root = sorter.root()


        assert root.name == 'root', root.name

        assert len(root) == 1
        group = root[0]

        assert group.name == 'buddies', group.name

        assert len(group) == 1
        offline_group = group[0]
        root.destroy()

    def test_missing(self):
        '''
        Test missing counts.
        '''
        s = blist.BuddyListSorter()
        s.addSorter(blist.ByGroup(False, 2))
        s.addSorter(blist.ByService(True))
        s.addSorter(blist.ByOnline(True, True))
        cmps = [blist.CustomOrder, blist.Service, blist.UserOrdering, blist.UserOrdering]
        s.setComparators(cmps)

        p = Protocol('digsby01', 'aim')
        p2 = Protocol('steve', 'digsby')

        def show(root_group):
            s.set_root(root_group)
            g = s._gather()
            try:
                print
                dump_elem_tree(g)
            finally:
                s._done_gather(g)
        
        root_group = Group('root', p, 'root',
            RootGroup('root1', p, 'root1',
                Group('aim group', p, 'aim group',
                    Buddy('abc', p, status='available'),
                    Buddy('abc', p, status='away'),
                    Buddy('def', p, status='offline'),
                    Buddy('def', p, status='offline'),
                    Buddy('ghi', p, status='away')),
                    Buddy('12345', p, service='icq', status='offline'),
                    Buddy('12345', p, service='aim', status='offline'),
                    Buddy('fadjkls', p, status='mobile'),
                Group('group #2', p, 'group #2',
                    Buddy('wut', p, status='mobile')),
            RootGroup('root2', p2, 'root2',
                Group('digsby group', p2, 'digsby group',
                    Buddy('ninjadigsby', p2, status='away'),
        ))))

        leakcheck(show, root_group)

    def test_sorter_ownership(self):
        s = blist.BuddyListSorter()
        b = blist.ByGroup()
        s.addSorter(b)

        assert not sip.ispyowned(b)

    def test_group_ownership(self):
        s = blist.BuddyListSorter()
        s.addSorter(blist.ByGroup(True))

        p = Protocol('aim', 'digsby01')
        s.set_root(Group('root', p, 'root',
            Group('subgroup', p, 'root',
                Buddy('abc', p))))

        root = s._gather()
        assert root.name == 'root'
        subgroup = root[0]
        assert subgroup.name == 'subgroup'
        assert subgroup[0].name == 'abc'
        s._done_gather(root)

    def test_filter_offline(self):
        s = blist.BuddyListSorter()
        s.addSorter(blist.ByGroup(True))
        s.addSorter(blist.ByMobile(True))
        s.addSorter(blist.ByOnline(False, False))

        s.setComparators([blist.Name])

        p = Protocol('aim', 'digsby01')

        s.set_root(Group('root', p, 'root',
                    Buddy('abc', p, status='available'),
                    Buddy('def', p, status='offline')))

        root = s._gather()
        s._done_gather(root)
        del s


def dump_elem_tree(e, indent = 0):
    space = '  ' * indent
    print space,
    if isinstance(e, blist.Group):
        print e.display_string
        for a in e:
            dump_elem_tree(a, indent + 1)
    else:
        print e

def main2():

    sorter = blist.BuddyListSorter()
    sorter.set_root(test_root_group)
    sorter.dump_root()

    sorter.root()

class DGroup(list):
    def __init__(self, name, *children):
        self.name = name
        if children: self[:] = children

def test_workingsetsize():
    from weakref import ref
    from testutils import wss
    def foo():
        s = blist.BuddyListSorter()
        s.addSorter(blist.ByFakeRoot('Contacts'))
        s.addSorter(blist.ByGroup(True, 2))
#        s.addSorter(blist.ByMobile(False))
#        s.addSorter(blist.ByOnline(False))
        p = Protocol('aim', 'digsby01')
        root = Group('root', p, 'root',
                Group('root1', p, 'root1',
                    Group('Contacts', p, 'subgroup'),
                    Buddy('abc', p)),
                    )

        root_ref = ref(root)
        proto_ref = ref(p)
        sorter_ref = ref(s)

        s.set_root(root)

        gathered = s._gather()
        gathered_ref = ref(gathered)

        protocols, ids = gathered._protocol_ids
        #assert protocols == [p]
        #assert ids == ['root'], repr(ids)

        assert not sip.ispyowned(gathered)
        s._done_gather(gathered)
        del gathered
        del s
        del protocols, ids

        del p, root

        assert root_ref() is None
        assert proto_ref() is None

        assert sorter_ref() is None
        assert gathered_ref() is None

        '''
        root = s.gather()
        assert root.name == 'root'
        assert sip.ispyowned(root)
        subgroup = root[0]
        del root
        assert subgroup.name == 'subgroup'
        assert subgroup[0].name == 'abc'
        '''

    # Loop lots of times, checking RAM usage
    for x in xrange(1000000):
        foo()
        if x % 500 == 0:
            print '%s MB' % (wss() / 1024.0 / 1024.0), x, 'runs'

if __name__ == '__main__':
    main()
    #test_workingsetsize()

