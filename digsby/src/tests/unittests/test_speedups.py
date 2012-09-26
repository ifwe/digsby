from tests import TestCase, test_main

class TestSpeedups(TestCase):
    def test_simplejson_speedups(self):
        import simplejson.encoder
        import simplejson.decoder

        assert simplejson.encoder.c_make_encoder is not None
        assert simplejson.encoder.c_encode_basestring_ascii is not None
        assert simplejson.decoder.c_scanstring is not None

    def test_pyxmpp_speedups(self):
        import _xmlextra

    def test_protocols_speedups(self):
        import protocols
        import _speedups

if __name__ == '__main__':
    test_main()
