# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.

import unittest

import six
from suitcase.crc import crc16_ccitt, crc32
from suitcase.exceptions import SuitcaseProgrammingError, SuitcasePackStructException, SuitcasePackException, \
    SuitcaseParseError, SuitcaseException
from suitcase.fields import DependentField, LengthField, VariableRawPayload, \
    Magic, BitField, BitBool, BitNum, DispatchTarget, CRCField, Payload, \
    UBInt8, UBInt16, UBInt24, UBInt32, UBInt40, UBInt48, UBInt56, UBInt64, \
    SBInt8, SBInt16, SBInt24, SBInt32, SBInt40, SBInt48, SBInt56, SBInt64, \
    ULInt8, ULInt16, ULInt24, ULInt32, ULInt40, ULInt48, ULInt56, ULInt64, \
    SLInt8, SLInt16, SLInt24, SLInt32, SLInt40, SLInt48, SLInt56, SLInt64, \
    ConditionalField, UBInt8Sequence, SBInt8Sequence, FieldProperty, \
    DispatchField, FieldArray, TypeField, SubstructureField
from suitcase.structure import Structure
import struct


def raise_value_error(*args, **kwargs):
    raise ValueError("Artifically Raised ValueError")


class SuperChild(Structure):
    options = DependentField('options')
    ubseq = DependentField('ubseq')
    length = LengthField(DependentField('submessage_length'))

    remaining = VariableRawPayload(length)


# Message containing every field
class SuperMessage(Structure):
    magic = Magic(b'\xAA\xAA')

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
    ubint40 = UBInt40()
    ubint48 = UBInt48()
    ubint56 = UBInt56()
    ubint64 = UBInt64()

    # signed big endian
    sbint8 = SBInt8()
    sbint16 = SBInt16()
    sbint24 = SBInt24()
    sbint32 = SBInt32()
    sbint40 = SBInt40()
    sbint48 = SBInt48()
    sbint56 = SBInt56()
    sbint64 = SBInt64()

    # unsigned little endian
    ulint8 = ULInt8()
    ulint16 = ULInt16()
    ulint24 = ULInt24()
    ulint32 = ULInt32()
    ulint40 = ULInt40()
    ulint48 = ULInt48()
    ulint56 = ULInt56()
    ulint64 = ULInt64()

    # signed little endian
    slint8 = SLInt8()
    slint16 = SLInt16()
    slint24 = SLInt24()
    slint32 = SLInt32()
    slint40 = SLInt40()
    slint48 = SLInt48()
    slint56 = SLInt56()
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
    eof = Magic(b'~')


class TestMagic(unittest.TestCase):
    def test_magic(self):
        magic_field = Magic('\xAA').create_instance(None)
        self.assertRaises(SuitcaseProgrammingError, magic_field.setval)


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
        s.ubint40 = 0xAABBCCDDEE
        s.ubint48 = 0xAABBCCDDEEFF
        s.ubint56 = 0xAABBCCDDEEFF00
        s.ubint64 = 0xAABBCCDDEEFF0011

        s.sbint8 = -100
        s.sbint16 = -1000
        s.sbint24 = -100000
        s.sbint32 = -100000000
        s.sbint40 = -10000000000
        s.sbint48 = -10000000000000
        s.sbint56 = -1000000000000000
        s.sbint64 = -100000000000000000

        s.ulint8 = 0xAA
        s.ulint16 = 0xAABB
        s.ulint16_byte_string = b'\xAA\xBB'
        s.ulint16_value = 0xBBAA

        s.ulint24 = 0xAABBCC
        s.ulint32 = 0xAABBCCDD
        s.ulint40 = 0xAABBCCDDEE
        s.ulint48 = 0xAABBCCDDEEFF
        s.ulint56 = 0xAABBCCDDEEFF00
        s.ulint64 = 0xAABBCCDDEEFF0011

        s.slint8 = -100
        s.slint16 = -1000
        s.slint24 = -100000
        s.slint32 = -100000000
        s.slint40 = -10000000000
        s.slint48 = -10000000000000
        s.slint56 = -1000000000000000
        s.slint64 = -100000000000000000

        s.optional_one = 1
        s.optional_two = 2

        s.ubseq = tuple(range(10))
        s.sbseq = tuple([x - 5 for x in range(10)])
        s.ubseqf = tuple(range(5))
        s.sbseqf = tuple([x - 2 for x in range(5)])

        sub = SuperChild()
        sub.remaining = b"Hello, this is SuperChild!"
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
                self.assertEqual(sm2_value, sm1_value,
                                 "%s: %s != %s, types(%s, %s)" % (
                                     key, sm2_value, sm1_value, type(sm2_value), type(sm1_value)))

    def test_struct_packing_exceptions(self):
        # Verify that exceptions available all work
        sm = self._create_supermessage()
        sm.ubint8 = 0xFFFF  # too big
        self.assertRaises(SuitcasePackStructException, sm.pack)

    def test_other_pack_exception(self):
        sm = self._create_supermessage()
        sm._key_to_field['ubint8'].pack = raise_value_error
        self.assertRaises(SuitcasePackException, sm.pack)

    def test_repr_works(self):
        # just make sure nothing crashes
        sm = self._create_supermessage()
        repr(sm)


class TestFieldProperty(unittest.TestCase):
    def test_basic_setget(self):
        # define the message
        class MyMessage(Structure):
            _version = UBInt8Sequence(2)
            version = FieldProperty(_version,
                                    onget=lambda v: "%d.%02d" % (v[0], v[1]),
                                    onset=lambda v: tuple(int(six.b(x)) for x in v.split(".", 1)))

        msg = MyMessage.from_data(b'\x10\x03')
        self.assertEqual(msg._version, (16, 3))
        self.assertEqual(msg.version, "16.03")

        msg.version = "22.7"
        self.assertEqual(msg._version, (22, 7))
        self.assertEqual(msg.version, "22.07")


class BasicMessage(Structure):
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
    class MyMuiltipliedLengthMessage(Structure):
        length = LengthField(UBInt8(), multiplier=8)
        payload = VariableRawPayload(length)

    class MyLengthyMessage(Structure):
        length = LengthField(UBInt16())
        payload = VariableRawPayload(length)

    def test_basic_length_pack(self):
        msg = self.MyLengthyMessage()
        payload = b"Hello, world!"
        msg.payload = payload
        self.assertEqual(msg.pack(), b"\x00\x0DHello, world!")

    def test_basic_length_unpack(self):
        msg = self.MyLengthyMessage()
        msg.unpack(b'\x00\x0DHello, world!')
        self.assertEqual(msg.length, 13)
        self.assertEqual(msg.payload, b"Hello, world!")

    def test_multiplied_length_pack(self):
        msg = self.MyMuiltipliedLengthMessage()
        payload = b''.join(six.b(chr(x)) for x in range(8 * 4))
        msg.payload = payload
        self.assertEqual(msg.pack(), b'\x04' + payload)

    def test_bad_modulus_multiplier(self):
        cls = self.MyMuiltipliedLengthMessage
        msg = self.MyMuiltipliedLengthMessage()
        payload = b'\x01'  # 1-byte is not modulo 8
        msg.payload = payload
        self.assertRaises(SuitcaseProgrammingError, msg.pack)

    def test_multiplied_length_unpack(self):
        msg = self.MyMuiltipliedLengthMessage()
        msg.unpack(b'\x04' + b''.join([six.b(chr(x)) for x in range(8 * 4)]))
        self.assertEqual(msg.length, 4)
        self.assertEqual(msg.payload,
                         b''.join([six.b(chr(x)) for x in range(8 * 4)]))

    def test_unpack_insufficient_bytes(self):
        msg = self.MyLengthyMessage()
        self.assertRaises(SuitcaseParseError, msg.unpack, b'\x00\x0DHello')


class TestByteSequence(unittest.TestCase):
    def test_fixed_sequence(self):
        class MySeqMessage(Structure):
            type = UBInt8()
            byte_values = UBInt8Sequence(16)

        msg = MySeqMessage()
        msg.type = 0
        msg.byte_values = (0, 1, 2, 3, 4, 5, 6, 7, 8,
                           9, 10, 11, 12, 13, 14, 15)
        self.assertEqual(msg.pack(),
                         b'\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08'
                         b'\t\n\x0b\x0c\r\x0e\x0f')

    def test_variable_sequence(self):
        class MyVarSeqMessage(Structure):
            type = UBInt8()
            length = LengthField(UBInt8())
            seq = UBInt8Sequence(length)

        msg = MyVarSeqMessage()
        msg.type = 0
        msg.seq = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

        self.assertEqual(msg.pack(),
                         b'\x00\n\x01\x02\x03\x04\x05\x06\x07\x08\t\n')
        msg2 = MyVarSeqMessage()
        msg2.unpack(msg.pack())
        self.assertEqual(msg2.length, 10)
        self.assertEqual(msg2.seq, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))

    def test_variable_sequence_nolength(self):
        class MyVarSeqMessage(Structure):
            s = VariableRawPayload(None)
            b = UBInt8Sequence(None)

        m = MyVarSeqMessage()
        m.s = b"Hello, world - "
        m.b = [0, 1, 2, 3, 4, 5]
        self.assertEqual(m.pack(),
                         b'Hello, world - \x00\x01\x02\x03\x04\x05')


class MyTargetMessage(Structure):
    # inherited from the parent message
    _length = LengthField(DependentField('length'))
    payload = VariableRawPayload(_length)


class MyOtherTargetMessage(Structure):
    #: Inherited from the parent message
    _length = LengthField(DependentField('length'))
    sequence = UBInt8Sequence(_length)


class MySimpleFixedPayload(Structure):
    number = UBInt32()


class MyPayloadMessage(Structure):
    payload = Payload()


class MyDefaultTargetMessage(Structure):
    _length = LengthField(DependentField('length'))
    sequence = UBInt8Sequence(_length)


class MyBasicDispatchMessage(Structure):
    type = DispatchField(UBInt8())
    length = LengthField(UBInt16())
    body = DispatchTarget(length, type, {
        0x00: MyTargetMessage,
        0x01: MyOtherTargetMessage,
        None: MyDefaultTargetMessage
    })


class MyDynamicLengthDispatchMessage(Structure):
    type = DispatchField(UBInt8())
    body = DispatchTarget(None, type, {
        0x1F: MySimpleFixedPayload,
        0xCC: MyPayloadMessage,
    })
    eof = Magic(b'EOF')


class BasicGreedy(Structure):
    a = UBInt8()
    b = UBInt8()
    payload = Payload()


class BoxedGreedy(Structure):
    sof = Magic(b'\xAA')
    a = LengthField(UBInt8())
    b = UBInt8()
    payload = Payload()
    c = UBInt16()
    d = VariableRawPayload(a)
    eof = Magic(b'\xbb')


class CRCGreedyTail(Structure):
    payload = Payload()
    magic = Magic(b'~~')
    crc = CRCField(UBInt32(), crc32, 0, -1)  # all (checksum zeroed)


class TestGreedyFields(unittest.TestCase):
    def test_unpack_basic_greedy(self):
        # Test case with trailing greedy payload
        m = BasicGreedy()
        m.unpack(b"\x00\x01Hello, you greedy, greedy World!")
        self.assertEqual(m.a, 0x00)
        self.assertEqual(m.b, 0x01)
        self.assertEqual(m.payload, b"Hello, you greedy, greedy World!")

    def test_unpack_boxed_greedy(self):
        # Test case where fields exist on either side of payload
        m = BoxedGreedy()
        m.unpack(b"\xaa\x05\x00This is the payload\x00\x15ABCDE\xbb")
        self.assertEqual(m.a, 5)
        self.assertEqual(m.b, 0)
        self.assertEqual(m.payload, b"This is the payload")
        self.assertEqual(m.c, 0x15)
        self.assertEqual(m.d, b"ABCDE")

    def test_unpack_boxed_greedy_error_before_greedy(self):
        # should start with \xAA but does not
        m = BoxedGreedy()
        self.assertRaises(SuitcaseParseError, m.unpack,
                          b"\x11\x05\x00This is the payload\x00\x15ABCDE\xbb")
        m._key_to_field['sof'].unpack = raise_value_error  # simulate fault
        self.assertRaises(SuitcaseParseError, m.unpack,
                          b"\xaa\x05\x00This is the payload\x00\x15ABCDE\xbb")

    def test_unpack_boxed_greedy_error_after_greedy(self):
        # should end in \xBB but does not
        m = BoxedGreedy()
        self.assertRaises(SuitcaseParseError, m.unpack,
                          b"\xaa\x05\x00This is the payload\x00\x15ABCDE\xAF")

        m._key_to_field['eof'].unpack = raise_value_error  # simlulate fault
        self.assertRaises(SuitcaseParseError, m.unpack,
                          b"\xaa\x05\x00This is the payload\x00\x15ABCDE\xbb")

    def test_pack_basic_greedy(self):
        m = BasicGreedy()
        m.a = 10
        m.b = 20
        m.payload = b"This is a packed greedy payload"
        self.assertEqual(m.pack(), b'\n\x14This is a packed greedy payload')

    def test_pack_boxed_greedy(self):
        m = BoxedGreedy()
        m.b = 20
        m.c = 300
        m.d = b"ABCD"
        m.payload = b"My length isn't declared and I am in the middle"
        self.assertEqual(m.pack(),
                         b"\xaa\x04\x14My length isn't declared and I am in the "
                         b"middle\x01,ABCD\xbb")

    def test_greedy_tail_pack_basic(self):
        m = CRCGreedyTail()
        m.payload = b"A GREEDY PAYLOAD FROM THE START"
        self.assertEqual(m.pack(), b'A GREEDY PAYLOAD FROM THE START~~\xfc\xce`=')

    def test_greedy_tail_unpack_basic(self):
        m = CRCGreedyTail.from_data(b'A GREEDY PAYLOAD FROM THE START~~\xfc\xce`=')
        self.assertEqual(m.payload, b"A GREEDY PAYLOAD FROM THE START")

    def test_greedy_tail_not_enough_bytes(self):
        self.assertRaises(SuitcaseParseError, CRCGreedyTail.from_data, b'~\xfc\xce`=')


class TestMessageDispatching(unittest.TestCase):
    def test_dispatch_packing(self):
        msg = MyBasicDispatchMessage()
        target_msg = MyTargetMessage()
        target_msg.payload = b"Hello, world!"
        msg.body = target_msg
        self.assertEqual(msg.pack(), b"\x00\x00\rHello, world!")

        msg2 = MyBasicDispatchMessage()
        target_msg = MyOtherTargetMessage()
        target_msg.sequence = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
        msg2.body = target_msg
        self.assertEqual(msg2.pack(),
                         b'\x01\x00\x0b\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n')

    def test_dispatch_unpacking(self):
        msg = MyBasicDispatchMessage()
        msg.unpack(b"\x00\x00\rHello, world!")
        self.assertEqual(msg.type, 0x00)
        body = msg.body
        self.assertEqual(body.payload, b"Hello, world!")

    def test_foreign_type(self):
        msg = MyBasicDispatchMessage()
        self.assertRaises(SuitcaseProgrammingError,
                          setattr, msg, 'body', SuperMessage())

    def test_default_dispatch(self):
        msg = MyBasicDispatchMessage()
        msg.unpack(b"\x10\x00\rHello, world!")
        self.assert_(isinstance(msg.body, MyDefaultTargetMessage))


class TestMessageDispatchingVariableLength(unittest.TestCase):
    def test_fixed_field_dispatch_packing(self):
        msg = MyDynamicLengthDispatchMessage()
        target_msg = MySimpleFixedPayload()
        target_msg.number = 0xFFEEFFEE
        msg.body = target_msg
        self.assertEqual(msg.pack(), b"\x1f\xff\xee\xff\xeeEOF")

    def test_variable_field_dispatch_packing(self):
        msg = MyDynamicLengthDispatchMessage()
        target_msg = MyPayloadMessage()
        target_msg.payload = b"~~~I'M SO DYNAMIC~~~"
        msg.body = target_msg
        self.assertEqual(msg.pack(), b"\xcc~~~I'M SO DYNAMIC~~~EOF")

    def test_dispatch_unpacking_fixed(self):
        msg = MyDynamicLengthDispatchMessage.from_data(b"\x1f\xff\xee\xff\xeeEOF")
        self.assertEqual(msg.body.number, 0xFFEEFFEE)

    def test_dispatch_unpacking_variable(self):
        msg = MyDynamicLengthDispatchMessage.from_data(b"\xcc~~~I'M SO DYNAMIC~~~EOF")
        self.assertEqual(msg.body.payload, b"~~~I'M SO DYNAMIC~~~")

    def test_dispatch_unpacking_fixed_bad_length(self):
        # too many bytes before EOF
        self.assertRaises(SuitcaseParseError, MyDynamicLengthDispatchMessage.from_data,
                          b"\x1f\xff\xee\xff\xeeEXTRA_EOF")


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
        sio = six.BytesIO()
        field.pack(sio)
        field2.unpack(sio.getvalue())
        self.assertEqual(field2.nib1, 1)
        self.assertEqual(field2.nib2, 2)
        self.assertEqual(field2.nib3, 3)
        self.assertEqual(field2.nib4, 4)

    def test_bad_operations(self):
        field_proto = BitField(7,
                               num=BitNum(7))
        self.assertRaises(SuitcaseProgrammingError,
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
        sio = six.BytesIO()
        inst.pack(sio)

        # should be packed in little endian form
        self.assertEqual(sio.getvalue(), b"\xef\x81")

        inst2 = field_proto.create_instance(None)
        inst2.unpack(b"\xef\x81")
        self.assertEqual(inst.b1, inst2.b1)
        self.assertEqual(inst.b2, inst2.b2)
        self.assertEqual(inst.remaining, inst2.remaining)


# message where f2 is only defined if f2 is 255
class Conditional(Structure):
    f1 = UBInt8()
    f2 = ConditionalField(UBInt8(), lambda m: m.f1 == 255)


# message where f2 and f3 are only defined if f2 is 255,
# and f2 specifies a length for f3
class ConditionalLength(Structure):
    f1 = UBInt8()
    f2 = ConditionalField(LengthField(UBInt8()), lambda m: m.f1 == 255)
    f3 = ConditionalField(Payload(length_provider=f2), lambda m: m.f1 == 255)


class TestConditionalField(unittest.TestCase):
    def test_conditional_pack(self):
        m1 = Conditional()
        m1.f1 = 0x91
        self.assertEqual(m1.pack(), b'\x91')

        m2 = Conditional()
        m2.f1 = 0xFF
        m2.f2 = 0x09
        self.assertEqual(m2.pack(), b'\xff\x09')

    def test_conditional_rx(self):
        m1 = Conditional()
        m1.unpack(b'\x1f')
        self.assertEqual(m1.f1, 0x1f)
        self.assertEqual(m1.f2, None)

        m2 = Conditional()
        m2.unpack(b'\xff\x1f')
        self.assertEqual(m2.f1, 0xff)
        self.assertEqual(m2.f2, 0x1f)

    def test_conditional_length_pack(self):
        m1 = ConditionalLength()
        m1.f1 = 0x91
        self.assertEqual(m1.pack(), b'\x91')

        m2 = ConditionalLength()
        m2.f1 = 0xFF
        m2.f3 = b'\x01\x02\x03\x04\x05'
        self.assertEqual(m2.pack(), b'\xff\x05\x01\x02\x03\x04\x05')

    def test_conditional_length_unpack(self):
        m1 = ConditionalLength()
        m1.unpack(b'\x91')
        self.assertEqual(m1.f1, 0x91)
        self.assertEqual(m1.f2, None)
        self.assertEqual(m1.f3, None)

        m2 = ConditionalLength()
        m2.unpack(b'\xff\x05\x01\x02\x03\x04\x05')
        self.assertEqual(m2.f1, 0xff)
        self.assertEqual(m2.f2, 0x05)
        self.assertEqual(m2.f3, b'\x01\x02\x03\x04\x05')


class TestStructure(unittest.TestCase):
    def test_unpack_fewer_bytes_than_required(self):
        self.assertRaises(SuitcaseParseError, MySimpleFixedPayload.from_data, b'123')

    def test_unpack_more_bytes_than_required(self):
        self.assertRaises(SuitcaseParseError, MySimpleFixedPayload.from_data, b'12345')


# Test FieldArray and ConditionalField interaction
class ConditionalArrayElement(Structure):
    options = BitField(8,
                       cond8_present=BitBool(),
                       cond16_present=BitBool(),
                       unused=BitNum(6))
    cond8 = ConditionalField(UBInt8(), lambda m: m.options.cond8_present)
    cond16 = ConditionalField(UBInt16(), lambda m: m.options.cond16_present)


class ConditionalArrayGreedy(Structure):
    array = FieldArray(ConditionalArrayElement)


class ConditionalArrayGreedyAfter(Structure):
    length = LengthField(UBInt8())
    array = FieldArray(ConditionalArrayElement, length)
    greedy = Payload()


class TestConditionalArray(unittest.TestCase):
    def test_unpack_greedy(self):
        m = ConditionalArrayGreedy()
        m.unpack(b"\x00" +
                 b"\x80\x12" +
                 b"\x40\x34\x56" +
                 b"\xc0\x12\x34\x56")

        self.assertEqual(len(m.array), 4)

        self.assertEqual(m.array[0].options.cond8_present, 0)
        self.assertEqual(m.array[0].options.cond16_present, 0)
        self.assertEqual(m.array[0].cond8, None)
        self.assertEqual(m.array[0].cond16, None)

        self.assertEqual(m.array[1].options.cond8_present, 1)
        self.assertEqual(m.array[1].options.cond16_present, 0)
        self.assertEqual(m.array[1].cond8, 0x12)
        self.assertEqual(m.array[1].cond16, None)

        self.assertEqual(m.array[2].options.cond8_present, 0)
        self.assertEqual(m.array[2].options.cond16_present, 1)
        self.assertEqual(m.array[2].cond8, None)
        self.assertEqual(m.array[2].cond16, 0x3456)

        self.assertEqual(m.array[3].options.cond8_present, 1)
        self.assertEqual(m.array[3].options.cond16_present, 1)
        self.assertEqual(m.array[3].cond8, 0x12)
        self.assertEqual(m.array[3].cond16, 0x3456)

    def test_pack_greedy(self):
        m = ConditionalArrayGreedy()

        c1 = ConditionalArrayElement()
        c1.options.cond8_present = False
        c1.options.cond16_present = False
        c1.cond8 = None
        c1.cond16 = None
        m.array.append(c1)

        c2 = ConditionalArrayElement()
        c2.options.cond8_present = True
        c2.options.cond16_present = False
        c2.cond8 = 0x12
        c2.cond16 = None
        m.array.append(c2)

        c3 = ConditionalArrayElement()
        c3.options.cond8_present = False
        c3.options.cond16_present = True
        c3.cond8 = None
        c3.cond16 = 0x3456
        m.array.append(c3)

        c4 = ConditionalArrayElement()
        c4.options.cond8_present = True
        c4.options.cond16_present = True
        c4.cond8 = 0x12
        c4.cond16 = 0x3456
        m.array.append(c4)

        self.assertEqual(m.pack(),
                         b"\x00" +
                         b"\x80\x12" +
                         b"\x40\x34\x56" +
                         b"\xc0\x12\x34\x56")

    def test_unpack_greedy_after(self):
        m = ConditionalArrayGreedyAfter()
        m.unpack(b"\x05" +
                 b"\x00" +
                 b"\xc0\x12\x34\x56" +
                 b"Hello")

        self.assertEqual(len(m.array), 2)

        self.assertEqual(m.array[0].options.cond8_present, 0)
        self.assertEqual(m.array[0].options.cond16_present, 0)
        self.assertEqual(m.array[0].cond8, None)
        self.assertEqual(m.array[0].cond16, None)

        self.assertEqual(m.array[1].options.cond8_present, 1)
        self.assertEqual(m.array[1].options.cond16_present, 1)
        self.assertEqual(m.array[1].cond8, 0x12)
        self.assertEqual(m.array[1].cond16, 0x3456)

        self.assertEqual(m.greedy, b"Hello")

    def test_pack_greedy_after(self):
        m = ConditionalArrayGreedyAfter()

        c1 = ConditionalArrayElement()
        c1.options.cond8_present = False
        c1.options.cond16_present = False
        c1.cond8 = None
        c1.cond16 = None
        m.array.append(c1)

        c2 = ConditionalArrayElement()
        c2.options.cond8_present = True
        c2.options.cond16_present = True
        c2.cond8 = 0x12
        c2.cond16 = 0x3456
        m.array.append(c2)

        m.greedy = b"Hello"

        self.assertEqual(m.pack(),
                         b"\x05" +
                         b"\x00" +
                         b"\xc0\x12\x34\x56" +
                         b"Hello")


# Test TypeField and FieldArray interaction
class Structure8(Structure):
    value = UBInt8()


class Structure16(Structure):
    value = UBInt16()


class Structure32(Structure):
    value = UBInt32()


dispatch_mapping = {0x00: Structure8,
                    0x01: Structure16,
                    0x03: Structure32}

size_mapping = {0x00: 1,
                0x01: 2,
                None: 4}  # This handles the Structure32 case


class TypedArrayElement(Structure):
    type = TypeField(UBInt8(), size_mapping)
    value = DispatchTarget(type, type, dispatch_mapping)


class TypedArray(Structure):
    array = FieldArray(TypedArrayElement)


class TypeFieldNoLengthProvider(Structure):
    type = TypeField(UBInt8(), size_mapping)


class TypeFieldWrongSize(Structure):
    type = TypeField(UBInt8(), size_mapping)
    greedy = Payload(type)


class TestTypeField(unittest.TestCase):
    def test_unpack_typed_array(self):
        m = TypedArray.from_data(b"\x00\x12" +
                                 b"\x01\x12\x34" +
                                 b"\x03\x12\x34\x56\x78")

        self.assertEqual(m.array[0].type, 0x00)
        self.assertEqual(m.array[0].value.value, 0x12)

        self.assertEqual(m.array[1].type, 0x01)
        self.assertEqual(m.array[1].value.value, 0x1234)

        self.assertEqual(m.array[2].type, 0x03)
        self.assertEqual(m.array[2].value.value, 0x12345678)

    def test_pack_typed_array(self):
        m = TypedArray()

        e1 = TypedArrayElement()
        e1.value = Structure8.from_data(b"\x12")
        m.array.append(e1)

        e2 = TypedArrayElement()
        e2.value = Structure16.from_data(b"\x12\x34")
        m.array.append(e2)

        e3 = TypedArrayElement()
        e3.value = Structure32.from_data(b"\x12\x34\x56\x78")
        m.array.append(e3)

        self.assertEquals(m.pack(), b"\x00\x12" +
                          b"\x01\x12\x34" +
                          b"\x03\x12\x34\x56\x78")

    def test_repr(self):
        # Make sure nothing crashes
        m = TypedArray.from_data(b"\x03\x12\x34\x56\x78")
        repr(m)

    def test_no_length_provider(self):
        m = TypeFieldNoLengthProvider()
        m.type = 0x01
        self.assertRaises(SuitcaseException, m.pack)

    def test_wrong_size(self):
        m = TypeFieldWrongSize()
        m.type = 0x01  # Indicates a length of 2
        m.greedy = b"Hello"
        self.assertRaises(SuitcasePackException, m.pack)


# Test SubstructureField
class PascalString16(Structure):
    length = LengthField(UBInt16())
    value = Payload(length)


class NameStructure(Structure):
    first = SubstructureField(PascalString16)
    last = SubstructureField(PascalString16)


class NameStructureGreedyAfter(Structure):
    first = SubstructureField(PascalString16)
    last = SubstructureField(PascalString16)
    greedy = Payload()


class TestSubstructureField(unittest.TestCase):
    def test_pack_valid(self):
        m = NameStructure()
        m.first.value = b"John"
        m.last.value = b"Doe"
        self.assertEqual(m.pack(), b"\x00\x04John\x00\x03Doe")

    def test_unpack_valid(self):
        m = NameStructure().from_data(b"\x00\x04John\x00\x03Doe")
        self.assertIsInstance(m.first, PascalString16)
        self.assertEqual(m.first.value, b"John")
        self.assertIsInstance(m.last, PascalString16)
        self.assertEqual(m.last.value, b"Doe")

    def test_pack_greedy_after(self):
        m = NameStructureGreedyAfter()
        m.first.value = b"John"
        m.last.value = b"Doe"
        m.greedy = b"Hello World!"
        self.assertEqual(m.pack(), b"\x00\x04John\x00\x03DoeHello World!")

    def test_unpack_greedy_after(self):
        m = NameStructureGreedyAfter().from_data(b"\x00\x04John\x00\x03DoeHello World!")
        self.assertIsInstance(m.first, PascalString16)
        self.assertEqual(m.first.value, b"John")
        self.assertIsInstance(m.last, PascalString16)
        self.assertEqual(m.last.value, b"Doe")
        self.assertEqual(m.greedy, b"Hello World!")

if __name__ == "__main__":
    unittest.main()
