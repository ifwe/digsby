import unittest
from oscar.ssi import item
import oscar
from struct import pack

class SSITestingSuite(unittest.TestCase):

    def testSSIItemto_bytes(self):
        testdata = pack("!H", 5) + "hello" + \
                   pack("!HH", 23, 0) + pack("!H", 0) + pack("!H", 0)
        testSSI = item('hello', 23, 0)

        self.assertEquals(testdata, testSSI.to_bytes())

    def testSSIItemto_bytes2(self):
        testSSI1 = item('hello', 23, 0, 1)
        testSSI1.add_item_to_group(15)
        testdata = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 6) + \
                    pack("!HH", 0xc8, 2) + pack("!H", 15)
        self.assertEquals(testdata, testSSI1.to_bytes())

    def testSSIadditemtogroup1(self):
        testSSI1 = item('hello', 23, 0, 1)
        testSSI1.add_item_to_group(15)
        testSSI1.add_item_to_group(30)
        testdata2 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 8) + \
                    pack("!HH", 0xc8, 4) + pack("!H", 30) + pack("!H", 15)
        self.assertEquals(testdata2, testSSI1.to_bytes())

    def testSSIadditemtogroup2(self):
        #item type 0 means this is a buddy, not a group
        testSSI = item('hello', 23, 45, 0)
        self.assertRaises(AssertionError, testSSI.add_item_to_group, 15)

    def testSSIadd_item_to_group_with_position_1(self):
        testSSI1 = item('hello', 23, 0, 1)
        testSSI1.add_item_to_group(15)
        testSSI1.add_item_to_group(30)
        testdata2 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 8) + \
                    pack("!HH", 0xc8, 4) + pack("!H", 30) + pack("!H", 15)
        self.assertEquals(testdata2, testSSI1.to_bytes())

    def testSSIadd_item_to_group_with_position_2(self):
        testSSI1 = item('hello', 23, 0, 1)
        testSSI1.add_item_to_group(15)
        testSSI1.add_item_to_group(30, 1)
        testdata2 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 8) + \
                    pack("!HH", 0xc8, 4) + pack("!H", 15) + pack("!H", 30)
        self.assertEquals(testdata2, testSSI1.to_bytes())

    def testSSIremoveitemfromgroup1(self):
        testSSI1 = item('hello', 23, 0, 1)
        testdata2 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 0)
        testSSI1.remove_item_from_group(15)
        self.assertEquals(testdata2, testSSI1.to_bytes())

    def testSSImove_item_to_position1(self):
        testdata1 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 8) + \
                    pack("!HH", 0xc8, 4) + pack("!H", 30) + pack("!H", 15)
        testSSI1 = oscar.unpack((('ssi','ssi'),),testdata1)[0]
        testSSI1.move_item_to_position(15, 0)
        testdata2 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 8) + \
                    pack("!HH", 0xc8, 4) + pack("!H", 15) + pack("!H", 30)

        self.assertEquals(testdata2, testSSI1.to_bytes())

    def testSSI_clone1(self):
        testdata1 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 0) + pack("!H", 8) + \
                    pack("!HH", 0xc8, 4) + pack("!H", 30) + pack("!H", 15)
        testSSI1 = oscar.unpack((('ssi','ssi'),),testdata1)[0]
        testSSI2 = testSSI1.clone()

        self.assertNotEquals(testSSI1, testSSI2)
        self.assertEquals(testSSI1.to_bytes(), testSSI2.to_bytes())

    def testSSI_Alias1(self):
        testSSI1 = item('hello', 23, 45, 0, {0x131:"Aliasness"})
        testSSI2 = item('hello', 23, 45, 0)

        self.assertEquals(testSSI1.alias, "Aliasness")
        self.assertEquals(len(testSSI1.alias), 9)
        self.assertEquals(testSSI1.alias, testSSI1.get_alias())

        self.assertEquals(testSSI1.alias, testSSI1.get_alias())
        self.assertNotEquals(testSSI1.alias, "blah")
        self.assertRaises(AttributeError, stupid_assign_alias, testSSI1)
        self.assertNotEquals(testSSI1.alias, "blah")
        testSSI1.set_alias("blah")
        self.assertEquals(testSSI1.alias, "blah")
        self.assertEquals(testSSI1.get_alias(), testSSI1.get_alias())

        self.assertNotEquals(testSSI1.to_bytes(), testSSI2.to_bytes())

        self.assertTrue(testSSI1.alias)
        testSSI1.remove_alias()
        self.assertFalse(testSSI1.alias)

        self.assertEquals(testSSI1.to_bytes(), testSSI2.to_bytes())

    def testSSI_Comment1(self):
        testSSI1 = item('hello', 23, 45, 0, {0x13C:"Comment"})
        testSSI2 = item('hello', 23, 45, 0)


        self.assertEquals(testSSI1.comment, "Comment")
        self.assertEquals(len(testSSI1.comment), 7)
        self.assertEquals(testSSI1.comment, testSSI1.get_comment())

        self.assertEquals(testSSI1.comment, testSSI1.get_comment())
        self.assertNotEquals(testSSI1.comment, "blah")
        self.assertRaises(AttributeError, stupid_assign_comment, testSSI1)
        self.assertNotEquals(testSSI1.comment, "blah")
        testSSI1.set_comment("blah")
        self.assertEquals(testSSI1.comment, "blah")
        self.assertEquals(testSSI1.get_comment(), testSSI1.get_comment())

        self.assertNotEquals(testSSI1.to_bytes(), testSSI2.to_bytes())

        self.assertTrue(testSSI1.comment)
        testSSI1.remove_comment()
        self.assertFalse(testSSI1.comment)

        self.assertEquals(testSSI1.to_bytes(), testSSI2.to_bytes())

#        def get_item_position(self, idToFind):
    def testSSIget_item_position1(self):
        testSSI1 = item('hello', 23, 0, 1, {0xc8:[30,15]})

        self.assertEquals(testSSI1.get_item_position(15),1)
        testSSI1.move_item_to_position(15, 0)
        testdata2 = pack("!H", 5) + "hello" + \
                    pack("!HH", 23, 0) + pack("!H", 1) + pack("!H", 8) + \
                    pack("!HH", 0xc8, 4) + pack("!H", 15) + pack("!H", 30)

        self.assertEquals(testdata2, testSSI1.to_bytes())

        self.assertEquals(testSSI1.get_item_position(15),0)


def stupid_assign_alias(ssi):
    ssi.alias = "blah"

def stupid_assign_comment(ssi):
    ssi.comment = "blah"

if __name__ == "__main__":
    unittest.main()