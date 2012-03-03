from pacman.fields import FieldProperty, UBByteSequence, UBInt8
from pacman.message import BaseMessage
import unittest


class TestFieldProperty(unittest.TestCase):

    def test_basic_setget(self):
        # define the message
        class MyMessage(BaseMessage):
            _version = UBByteSequence(2)
            version = FieldProperty(_version,
                                    onget=lambda v: "%d.%02d" % (v[0], v[1]),
                                    onset=lambda v: tuple(int(x) for x
                                                          in v.split(".", 1)))

        msg = MyMessage()
        msg.unpack('\x10\x03')
        self.assertEqual(msg._version,(16, 3))
        self.assertEqual(msg.version, "16.03")
        
        msg.version = "22.7"
        self.assertEqual(msg._version, (22, 7))
        self.assertEqual(msg.version, "22.07")


class TestByteSequence(unittest.TestCase):
    
    def test_bubyte_sequence(self):
        class MySeqMessage(BaseMessage):
            type = UBInt8()
            byte_values = UBByteSequence(16)

        msg = MySeqMessage()
        msg.type = 0
        msg.byte_values = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
        self.assertEqual(msg.pack(),
                         '\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
                         '\t\n\x0b\x0c\r\x0e\x0f')

if __name__ == "__main__":
    unittest.main()