from tests import TestCase, test_main
import oscar.rendezvous.chat

class TestOscar(TestCase):
    def test_oscar_chatinvite(self):
        data = "\x00\n\x00\x02\x00\x01\x00\x0f\x00\x00\x00\x0c\x00\x00'\x11\x00\x19\x00\x04\x14!aol://2719:10-4-tst\x00\x00"
        invite_msg, chatcookie = oscar.rendezvous.chat.unpack_chat_invite(data)

if __name__ == '__main__':
    test_main()
