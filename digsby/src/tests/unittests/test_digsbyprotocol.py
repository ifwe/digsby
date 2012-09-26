from tests import TestCase, test_main
from digsby.DigsbyProtocol import conditional_messages

from pyxmpp.stanza import Stanza
from libxml2 import parseDoc

class MockAccount(object):
    def __init__(self, protocol):
        self.protocol = protocol


class TestDigsbyProtocol(TestCase):
    def test_conditional_messages(self):
        '''
        test handling of conditional server messages
        '''

        self.assert_raises(Exception, conditional_messages, None)

        def make_stanza(m):
            return Stanza(parseDoc(m).children)

        # options sent to the conditional_messages function
        default_options = dict(
            revision = 20000,
            all_accounts = [MockAccount(protocol = 'aim'),
                            MockAccount(protocol = 'yahoo')]
        )

        def test_stanza(m, **opts):
            msgopts = default_options.copy()
            msgopts.update(opts)
            return conditional_messages(make_stanza(m), **msgopts)

        # empty conditional
        empty = '''\
<message from="digsby.org" to="kevin@digsby.org/Digsby.eb1iqe" type="normal">
  <subject>announce to all online users</subject>
  <body>test message</body>
  <x xmlns="http://www.digsby.org/conditions/v1.0"/>
</message>'''

        self.assert_(not test_stanza(empty))

        fail_because_no_aolmail = '''\
<message from="digsby.org" to="kevin@digsby.org/Digsby.eb1iqe" type="normal">
  <subject>multiple</subject>
  <body>test</body>
  <x xmlns="http://www.digsby.org/conditions/v1.0">
    <condition type="has-account-type">aolmail</condition>
  </x>
</message>'''

        self.assert_(test_stanza(fail_because_no_aolmail))

        succeed_revision = '''\
<message from="digsby.org" to="kevin@digsby.org/Digsby.eb1iqe" type="normal">
  <subject>test</subject>
  <body>abc</body>
  <x xmlns="http://www.digsby.org/conditions/v1.0">
    <condition type="revision-above-eq">15</condition>
    <condition type="revision-below-eq">0</condition>
  </x>
</message>'''

        self.assert_(not test_stanza(succeed_revision))

        succeed_revision_2 = '''\
<message from="digsby.org" to="kevin@digsby.org/Digsby.eb1iqe" type="normal">
  <subject>test</subject>
  <body>abc</body>
  <x xmlns="http://www.digsby.org/conditions/v1.0">
    <condition type="revision-above-eq">0</condition>
    <condition type="revision-below-eq">500000</condition>
  </x>
</message>'''

        self.assert_(not test_stanza(succeed_revision_2))


        fail_revision = '''\
<message from="digsby.org" to="kevin@digsby.org/Digsby.eb1iqe" type="normal">
  <subject>test</subject>
  <body>abc</body>
  <x xmlns="http://www.digsby.org/conditions/v1.0">
    <condition type="revision-above-eq">50000000</condition>
    <condition type="revision-below-eq">0</condition>
  </x>
</message>'''

        self.assert_(test_stanza(fail_revision))

        fail_revision_2 = '''\
<message from="digsby.org" to="kevin@digsby.org/Digsby.eb1iqe" type="normal">
  <subject>test</subject>
  <body>abc</body>
  <x xmlns="http://www.digsby.org/conditions/v1.0">
    <condition type="revision-above-eq">0</condition>
    <condition type="revision-below-eq">20</condition>
  </x>
</message>'''

        self.assert_(test_stanza(fail_revision_2))

if __name__ == '__main__':
    test_main()
