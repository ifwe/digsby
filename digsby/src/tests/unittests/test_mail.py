from tests import TestCase, test_main
from mail.emailobj import unicode_hdr

class TestMail(TestCase):
    def test_header_decode(self):
        header = r'You=?UTF8?Q?=E2=80=99?=re HOT, brian@thebdbulls.com =?UTF8?Q?=E2=80=93?= See if Someone Searched for You'
        unicode_hdr(header)

if __name__ == '__main__':
    test_main()
