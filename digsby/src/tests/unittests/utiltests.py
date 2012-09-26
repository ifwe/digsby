import unittest
import util
import util.primitives.structures as structures
import struct

class UtilTestingSuite(unittest.TestCase):

    def testUnpackNames(self):
        testdata = struct.pack("!HIB", 1,4000L,3) + "some extraneous data"
        magic_hash = structures.unpack_named("!HIBR", "one", "four thousand long", "three", "extra", testdata)

        self.assertEquals(magic_hash['extra'], 'some extraneous data')

    def testStorage(self):
        s = util.Storage({ "key": "value" })
        self.assertEquals(s.key, "value")

    def testdocs(self):
        import doctest
        doctest.testmod(util)

#    def test_named_structs(self):
#        network_format = (
#            'magic',    '4s',
#            'version',  'H',
#            'size',     'I',
#            'cookie',   'Q',
#            'type',     'H',
#        )
#
#        AIMPacket = util.NamedStruct(network_format)
#
#        packet_dict = util.Storage(magic='AIM3', version=4, size=3200,
#                           cookie=4532432L, type=0x03)
#
#        packet_bytes  = AIMPacket.pack(packet_dict)
#        unpacked_dict, data = AIMPacket.unpack(packet_bytes)
#
#        self.assertEqual(packet_dict, unpacked_dict)
#        self.assertEqual(packet_dict.cookie, 4532432L)

if __name__ == "__main__":
    unittest.main()
