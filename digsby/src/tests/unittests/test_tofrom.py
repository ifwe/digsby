from tests import TestCase, test_main
import contacts.buddyliststore as bl
import contacts.tofrom as tofrom

class Contact(object):
    def __init__(self, name, service):
        self.name = name
        self.service = service
        self.protocol = object()

    def __repr__(self):
        return '<Contact %s %s>' % (self.name, self.service)

class Account(object):
    def __init__(self, name, service):
        self.name = name
        self.service = service
        self.protocol = service
        self.connection = object()

    def __repr__(self):
        return '<Account %s %s>' % (self.name, self.service)

class ToFromTests(TestCase):
    'Test to/from history'

    def test_validator(self):
        'Test the to/from validator'

        should_pass = [
            bl.default_tofrom(),
            {u'im': [[u'aaron@digsby.org', u'digsby', u'kevin@digsby.org', u'digsby']],
             u'sms': [],
             u'email': []},
        ]

        should_fail = [
            None,
            [],
            [[]],
            {u'im': [[5, u'digsby', u'kevin@digsby.org', u'digsby']],
             u'sms': [],
             u'email': []},
        ]

        for entry in should_pass:
            self.assert_(bl.validate_tofrom(entry))

        for entry in should_fail:
            self.assert_raises(TypeError, bl.validate_tofrom, entry)
    
    def test_tofrom_history_lookup(self):
        '''
        To: First online so the user can choose what service they prefer
        From: Last one I used so it remembers my preference (that is where storing to/from is useful)
        '''

        contact = Contact('digsby01', 'aim')

        accounts = [
            Account('digsby03', 'aim')
        ]

        # check the failing case
        tofrom_table = []
        assert None is tofrom.lookup_tofrom_account(contact, accounts, tofrom_table)

        # Check that when you're connected to two different AIM accounts,
        # that lookup_tofrom_account returns the last one you messaged a contact
        # with.
        foo, bar = Account('foo', 'aim'), Account('bar', 'aim')
        accounts = [foo, bar]

        tofrom_table = [('digsby01', 'aim', 'bar', 'aim')]
        assert bar is tofrom.lookup_tofrom_account(contact, accounts, tofrom_table)

        tofrom_table = [('digsby01', 'aim', 'foo', 'aim')]
        assert foo is tofrom.lookup_tofrom_account(contact, accounts, tofrom_table)

        # Make sure a non-matching from service is ignored.
        tofrom_table = [
            ('digsby01', 'aim', 'foo', 'jabber'),
            ('digsby01', 'aim', 'foo', 'aim')
        ]
        assert foo is tofrom.lookup_tofrom_account(contact, accounts, tofrom_table)

        # Make sure an offline from account is ignored.
        accounts = [bar]
        tofrom_table = [
            ('digsby01', 'aim', 'foo', 'aim'),
            ('digsby01', 'aim', 'bar', 'aim'),
        ]
        assert bar is tofrom.lookup_tofrom_account(contact, accounts, tofrom_table)

    def test_compatible_im_accounts(self):
        foo, bar = Account('foo', 'yahoo'), Account('bar', 'msn')
        accounts = [foo]
        contact = Contact('digsby03', 'msn')
        tofrom_table = []

        # Make sure Yahoo can talk to MSN
        assert tofrom.im_service_compatible('msn', 'yahoo')

        # Make sure choose_from understands IM compatibility
        self.assertEqual(foo, tofrom.choose_from(contact, accounts, tofrom_table))



if __name__ == "__main__":
    test_main()

