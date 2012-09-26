from tests import TestCase, test_main
from util import Storage as S
from contacts.dispatch import ContactDispatcher

class MockProfile(object):
    def __init__(self):
        self.connected_accounts = []
        self.account_manager = S(connected_accounts = self.connected_accounts)

class MockBuddy(object):
    def __init__(self, name, service):
        self.name = name
        self.service = service

B = MockBuddy

class MockAccount(object):
    def __init__(self, username, name):
        self.username = username
        self.protocol = self.name = name
        self.connection = S(
            protocol = name,
            username = username
        )

A = MockAccount

class TestDispatch(TestCase):
    def test_dispatch(self):
        profile = MockProfile()
        dispatch = ContactDispatcher(profile=profile)

        a = A('digsby13', 'aim')
        b = B('digsby01', 'aim')
        dispatch.add_tofrom('im', b, a)

        profile.connected_accounts[:] = [a]
        _b, proto = dispatch.get_from(b)

        self.assertEquals(b, _b)
        self.assertEquals(a.connection, proto)

if __name__ == '__main__':
    test_main()
