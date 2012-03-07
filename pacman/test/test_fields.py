from StringIO import StringIO
from pacman.fields import FieldProperty, UBInt8Sequence, UBInt8, \
    VariableRawPayload, LengthField, UBInt16, DispatchField, DispatchTarget, \
    DependentField, BitField, BitNum
from pacman.message import BaseMessage
import unittest


class TestFieldProperty(unittest.TestCase):

    def test_basic_setget(self):
        # define the message
        class MyMessage(BaseMessage):
            _version = UBInt8Sequence(2)
            version = FieldProperty(_version,
                                    onget=lambda v: "%d.%02d" % (v[0], v[1]),
                                    onset=lambda v: tuple(int(x) for x
                                                          in v.split(".", 1)))

        msg = MyMessage()
        msg.unpack('\x10\x03')
        self.assertEqual(msg._version, (16, 3))
        self.assertEqual(msg.version, "16.03")

        msg.version = "22.7"
        self.assertEqual(msg._version, (22, 7))
        self.assertEqual(msg.version, "22.07")


class BasicMessage(BaseMessage):
    b1 = UBInt8()
    b2 = UBInt8()


class TestInstancePrototyping(unittest.TestCase):

    def test_independence(self):
        msg1 = BasicMessage()
        msg1.b1 = 10
        msg1.b2 = 20

        msg2 = BasicMessage()
        msg2.b1 = 20
        msg2.b2 = 30

        self.assertNotEqual(msg2.b1, msg1.b1)
        self.assertNotEqual(msg2.b2, msg1.b2)


class TestLengthField(unittest.TestCase):

    class MyMuiltipliedLengthMessage(BaseMessage):
        length = LengthField(UBInt8(), multiplier=8)
        payload = VariableRawPayload(length)

    class MyLengthyMessage(BaseMessage):
        length = LengthField(UBInt16())
        payload = VariableRawPayload(length)

    def test_basic_length_pack(self):
        msg = self.MyLengthyMessage()
        payload = "Hello, world!"
        msg.payload = payload
        self.assertEqual(msg.pack(), "\x00\x0DHello, world!")

    def test_basic_length_unpack(self):
        msg = self.MyLengthyMessage()
        msg.unpack('\x00\x0DHello, world!')
        self.assertEqual(msg.length, 13)
        self.assertEqual(msg.payload, "Hello, world!")

    def test_multiplied_length_pack(self):
        msg = self.MyMuiltipliedLengthMessage()
        payload = ''.join(chr(x) for x in xrange(8 * 4))
        msg.payload = payload
        self.assertEqual(msg.pack(), chr(4) + payload)

    def test_bad_modulus_multiplier(self):
        cls = self.MyMuiltipliedLengthMessage
        msg = self.MyMuiltipliedLengthMessage()
        payload = '\x01'  # 1-byte is not modulo 8
        msg.payload = payload
        self.assertRaises(ValueError, msg.pack)

    def test_multiplied_length_unpack(self):
        msg = self.MyMuiltipliedLengthMessage()
        msg.unpack(chr(4) + ''.join([chr(x) for x in xrange(8 * 4)]))
        self.assertEqual(msg.length, 4)
        self.assertEqual(msg.payload,
                         ''.join([chr(x) for x in xrange(8 * 4)]))


class TestByteSequence(unittest.TestCase):

    def test_fixed_sequence(self):
        class MySeqMessage(BaseMessage):
            type = UBInt8()
            byte_values = UBInt8Sequence(16)

        msg = MySeqMessage()
        msg.type = 0
        msg.byte_values = (0, 1, 2, 3, 4, 5, 6, 7, 8,
                           9, 10, 11, 12, 13, 14, 15)
        self.assertEqual(msg.pack(),
                         '\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
                         '\t\n\x0b\x0c\r\x0e\x0f')

    def test_variable_sequence(self):
        class MyVarSeqMessage(BaseMessage):
            type = UBInt8()
            length = LengthField(UBInt8())
            seq = UBInt8Sequence(length)

        msg = MyVarSeqMessage()
        msg.type = 0
        msg.seq = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

        self.assertEqual(msg.pack(),
                         '\x00\n\x01\x02\x03\x04\x05\x06\x07\x08\t\n')
        msg2 = MyVarSeqMessage()
        msg2.unpack(msg.pack())
        self.assertEqual(msg2.length, 10)
        self.assertEqual(msg2.seq, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))


class MyTargetMessage(BaseMessage):
    # inherited from the parent message
    _length = LengthField(DependentField('length'))
    payload = VariableRawPayload(_length)


class MyOtherTargetMessage(BaseMessage):
    #: Inherited from the parent message
    _length = LengthField(DependentField('length'))
    sequence = UBInt8Sequence(_length)


class MyBasicDispatchMessage(BaseMessage):
    type = DispatchField(UBInt8())
    length = LengthField(UBInt16())
    body = DispatchTarget(length, type, {
        0x00: MyTargetMessage,
        0x01: MyOtherTargetMessage
    })


class TestMessageDispatching(unittest.TestCase):

    def test_dispatch_packing(self):
        msg = MyBasicDispatchMessage()
        target_msg = MyTargetMessage()
        target_msg.payload = "Hello, world!"
        msg.body = target_msg
        self.assertEqual(msg.pack(), "\x00\x00\rHello, world!")

        msg2 = MyBasicDispatchMessage()
        target_msg = MyOtherTargetMessage()
        target_msg.sequence = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        msg2.body = target_msg
        self.assertEqual(msg2.pack(),
            '\x01\x00\x0b\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n')

    def test_dispatch_unpacking(self):
        msg = MyBasicDispatchMessage()
        msg.unpack("\x00\x00\rHello, world!")
        self.assertEqual(msg.type, 0x00)
        body = msg.body
        self.assertEqual(body.payload, "Hello, world!")


class TestBitFields(unittest.TestCase):

    def test_packing(self):
        field_proto = BitField(16,
            nib1=BitNum(4),
            nib2=BitNum(4),
            nib3=BitNum(4),
            nib4=BitNum(4),
        )
        field = field_proto.create_instance(None)

        field.nib1 = 1
        field.nib2 = 2
        field.nib3 = 3
        field.nib4 = 4

        field2 = field_proto.create_instance(None)
        sio = StringIO()
        field._pack(sio)
        sio.seek(0)
        field2._unpack(sio)
        self.assertEqual(field2.nib1, 1)
        self.assertEqual(field2.nib2, 2)
        self.assertEqual(field2.nib3, 3)
        self.assertEqual(field2.nib4, 4)


if __name__ == "__main__":
    unittest.main()
