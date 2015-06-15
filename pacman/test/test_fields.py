# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.

from StringIO import StringIO
from pacman.crc import crc16_ccitt
from pacman.exceptions import PacmanProgrammingError
from pacman.fields import DependentField, LengthField, VariableRawPayload, \
    Magic, BitField, BitBool, BitNum, UBInt8, UBInt16, UBInt24, UBInt32, UBInt64, \
    SBInt8, SBInt16, SBInt32, SBInt64, ULInt8, ULInt16, ULInt32, ULInt64, SLInt8, \
    SLInt16, SLInt32, SLInt64, ConditionalField, UBInt8Sequence, SBInt8Sequence, \
    FieldProperty, DispatchField, DispatchTarget, CRCField, Payload
from pacman.message import BaseMessage
import struct
import unittest


class SuperChild(BaseMessage):
    options = DependentField('options')
    ubseq = DependentField('ubseq')
    length = LengthField(DependentField('submessage_length'))

    remaining = VariableRawPayload(length)


# Message containing every field
class SuperMessage(BaseMessage):
    magic = Magic('\xAA\xAA')

    # bitfield
    options = BitField(8,
        b1=BitBool(),
        b2=BitBool(),
        rest=BitNum(6))

    # unsigned big endian
    ubint8 = UBInt8()
    ubint16 = UBInt16()
    ubint24 = UBInt24()
    ubint32 = UBInt32()
    ubint64 = UBInt64()

    # signed big endian
    sbint8 = SBInt8()
    sbint16 = SBInt16()
    sbint32 = SBInt32()
    sbint64 = SBInt64()

    # unsigned little endian
    ulint8 = ULInt8()
    ulint16 = ULInt16()
    ulint32 = ULInt32()
    ulint64 = ULInt64()

    # signed little endian
    slint8 = SLInt8()
    slint16 = SLInt16()
    slint32 = SLInt32()
    slint64 = SLInt64()

    # optional
    optional_one = ConditionalField(UBInt8(), lambda m: m.options.b1)
    optional_two = ConditionalField(UBInt8(), lambda m: m.options.b2)

    # sequences with variable lengths
    ubseql = LengthField(UBInt8())
    ubseq = UBInt8Sequence(ubseql)

    sbseql = LengthField(UBInt8())
    sbseq = SBInt8Sequence(sbseql)

    # sequences with fixed lengths
    ubseqf = UBInt8Sequence(5)
    sbseqf = SBInt8Sequence(5)

    # don't change anything... for test coverage
    ulint16_value = FieldProperty(ulint16)
    ulint16_byte_string = FieldProperty(ulint16,
        onget=lambda v: str(v),
        onset=lambda v: struct.unpack(">H", v)[0])

    message_type = DispatchField(UBInt8())
    submessage_length = LengthField(UBInt16())
    submessage = DispatchTarget(submessage_length, message_type, {
        0xEF: SuperChild
    })

    # checksum starts after beginning magic, ends before
    # the checksum
    crc = CRCField(UBInt16(), crc16_ccitt, 2, -3)
    eof = Magic('~')


class TestMagic(unittest.TestCase):

    def test_magic(self):
        magic_field = Magic('\xAA').create_instance(None)
        self.assertRaises(PacmanProgrammingError, magic_field.setval)


class TestSuperField(unittest.TestCase):

    def _create_supermessage(self):
        s = SuperMessage()

        s.options.b1 = False
        s.options.b2 = True
        s.options.remaining = 0x1A

        # packed fields
        s.ubint8 = 0xAA
        s.ubint16 = 0xAABB
        s.ubint24 = 0xAABBCC
        s.ubint32 = 0xAABBCCDD
        s.ubint64 = 0xAABBCCDDEEFF0011

        s.sbint8 = -25
        s.sbint16 = -312
        s.sbint32 = -9570
        s.sbint64 = -29349579

        s.ulint8 = 0xAA
        s.ulint16 = 0xAABB
        s.ulint16_byte_string = '\xAA\xBB'
        s.ulint16_value = 0xBBAA

        s.ulint32 = 0xAABBCCDD
        s.ulint64 = 0xAABBCCDDEEFF0011

        s.slint8 = -25
        s.slint16 = -312
        s.slint32 = -9570
        s.slint64 = -29349579

        s.optional_one = 1
        s.optional_two = 2

        s.ubseq = tuple(range(10))
        s.sbseq = tuple([x - 5 for x in range(10)])
        s.ubseqf = tuple(range(5))
        s.sbseqf = tuple([x - 2 for x in range(5)])

        sub = SuperChild()
        sub.remaining = "Hello, this is SuperChild!"
        s.submessage = sub

        return s

    def test_super_message(self):
        sm = self._create_supermessage()
        packed = sm.pack()
        sm2 = SuperMessage.from_data(packed)

        for key, field in sm2:
            sm2_value = field.getval()
            if key == 'options':
                self.assertEqual(sm2_value.b1, sm.options.b1)
                self.assertEqual(sm2_value.b2, sm.options.b2)
                self.assertEqual(sm2_value.rest, sm.options.rest)

            elif key == 'submessage':
                self.assertEqual(sm2_value.ubseq, sm.ubseq)
                self.assertEqual(sm2_value.remaining, sm.submessage.remaining)
            elif key == 'optional_one':
                self.assertEqual(sm2_value, None)
            elif key == 'crc':
                pass  # validity check baked into protocol
            else:
                sm1_value = getattr(sm, key)
                self.assertEqual(sm2_value, sm1_value, "%s: %s != %s, types(%s, %s)" %
                                 (key, sm2_value, sm1_value, type(sm2_value), type(sm1_value)))

    def test_repr_works(self):
        # just make sure nothing creashes
        sm = self._create_supermessage()
        repr(sm)


class TestFieldProperty(unittest.TestCase):

    def test_basic_setget(self):
        # define the message
        class MyMessage(BaseMessage):
            _version = UBInt8Sequence(2)
            version = FieldProperty(_version,
                                    onget=lambda v: "%d.%02d" % (v[0], v[1]),
                                    onset=lambda v: tuple(int(x) for x
                                                          in v.split(".", 1)))

        msg = MyMessage.from_data('\x10\x03')
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
        self.assertRaises(PacmanProgrammingError, msg.pack)

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

    def test_variable_sequence_nolength(self):
        class MyVarSeqMessage(BaseMessage):
            s = VariableRawPayload(None)
            b = UBInt8Sequence(None)

        m = MyVarSeqMessage()
        m.s = "Hello, world - "
        m.b = [0, 1, 2, 3, 4, 5]
        self.assertEqual(m.pack(),
                         'Hello, world - \x00\x01\x02\x03\x04\x05')


class MyTargetMessage(BaseMessage):
    # inherited from the parent message
    _length = LengthField(DependentField('length'))
    payload = VariableRawPayload(_length)


class MyOtherTargetMessage(BaseMessage):
    #: Inherited from the parent message
    _length = LengthField(DependentField('length'))
    sequence = UBInt8Sequence(_length)


class MyDefaultTargetMessage(BaseMessage):
    _length = LengthField(DependentField('length'))
    sequence = UBInt8Sequence(_length)


class MyBasicDispatchMessage(BaseMessage):
    type = DispatchField(UBInt8())
    length = LengthField(UBInt16())
    body = DispatchTarget(length, type, {
        0x00: MyTargetMessage,
        0x01: MyOtherTargetMessage,
        None: MyDefaultTargetMessage
    })


class BasicGreedy(BaseMessage):
    a = UBInt8()
    b = UBInt8()
    payload = Payload()


class BoxedGreedy(BaseMessage):
    a = LengthField(UBInt8())
    b = UBInt8()
    payload = Payload()
    c = UBInt16()
    d = VariableRawPayload(a)


class TestGreedyFields(unittest.TestCase):

    def test_unpack_basic_greedy(self):
        # Test case with trailing greedy payload
        m = BasicGreedy()
        m.unpack("\x00\x01Hello, you greedy, greedy World!")
        self.assertEqual(m.a, 0x00)
        self.assertEqual(m.b, 0x01)
        self.assertEqual(m.payload, "Hello, you greedy, greedy World!")

    def test_unpack_boxed_greedy(self):
        # Test case where fields exist on either side of payload

        m = BoxedGreedy()
        m.unpack("\x05\x00This is the payload\x00\x15ABCDE")
        self.assertEqual(m.a, 5)
        self.assertEqual(m.b, 0)
        self.assertEqual(m.payload, "This is the payload")
        self.assertEqual(m.c, 0x15)
        self.assertEqual(m.d, "ABCDE")

    def test_pack_basic_greedy(self):
        m = BasicGreedy()
        m.a = 10
        m.b = 20
        m.payload = "This is a packed greedy payload"
        self.assertEqual(m.pack(), '\n\x14This is a packed greedy payload')

    def test_pack_boxed_greedy(self):
        m = BoxedGreedy()
        m.b = 20
        m.c = 300
        m.d = "ABCD"
        m.payload = "My length isn't declared and I am in the middle"
        self.assertEqual(m.pack(),
                         "\x04\x14My length isn't declared and I am in the "
                         "middle\x01,ABCD")


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

    def test_foreign_type(self):
        msg = MyBasicDispatchMessage()
        self.assertRaises(PacmanProgrammingError,
                          setattr, msg, 'body', SuperMessage())

    def test_default_dispatch(self):
        msg = MyBasicDispatchMessage()
        msg.unpack("\x10\x00\rHello, world!")
        self.assert_(isinstance(msg.body, MyDefaultTargetMessage))


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
        field.pack(sio)
        field2.unpack(sio.getvalue())
        self.assertEqual(field2.nib1, 1)
        self.assertEqual(field2.nib2, 2)
        self.assertEqual(field2.nib3, 3)
        self.assertEqual(field2.nib4, 4)

    def test_bad_operations(self):
        field_proto = BitField(7,
            num=BitNum(7))
        self.assertRaises(PacmanProgrammingError,
                          field_proto.create_instance, None)

    def test_explicit_field_override(self):
        field_proto = BitField(16, ULInt16(),
            b1=BitBool(),
            b2=BitBool(),
            remaining=BitNum(14))
        inst = field_proto.create_instance(None)
        inst.b1 = True
        inst.b2 = False
        inst.remaining = 0x1EF
        sio = StringIO()
        inst.pack(sio)

        # should be packed in little endian form
        self.assertEqual(sio.getvalue(), "\xef\x81")

        inst2 = field_proto.create_instance(None)
        inst2.unpack("\xef\x81")
        self.assertEqual(inst.b1, inst2.b1)
        self.assertEqual(inst.b2, inst2.b2)
        self.assertEqual(inst.remaining, inst2.remaining)


# message where f2 is only defined if f2 is 255
class Conditional(BaseMessage):
    f1 = UBInt8()
    f2 = ConditionalField(UBInt8(), lambda m: m.f1 == 255)


class TestConditionalField(unittest.TestCase):

    def test_conditional_pack(self):
        m1 = Conditional()
        m1.f1 = 0x91
        self.assertEqual(m1.pack(), '\x91')

        m2 = Conditional()
        m2.f1 = 0xFF
        m2.f2 = 0x09
        self.assertEqual(m2.pack(), '\xff\x09')

    def test_conditional_rx(self):
        m1 = Conditional()
        m1.unpack('\x1f')
        self.assertEqual(m1.f1, 0x1f)
        self.assertEqual(m1.f2, None)

        m2 = Conditional()
        m2.unpack('\xff\x1f')
        self.assertEqual(m2.f1, 0xff)
        self.assertEqual(m2.f2, 0x1f)

if __name__ == "__main__":
    unittest.main()
