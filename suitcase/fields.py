# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.
import struct

import six
from suitcase.exceptions import SuitcaseChecksumException, SuitcaseProgrammingError, \
    SuitcaseParseError, SuitcaseException, SuitcasePackStructException
from six import BytesIO, StringIO


class FieldPlaceholder(object):
    """Internally used object that holds information about a field schema

    A FieldPlaceholder is what is actually instantiated and stored with
    the message schema class when a message schema is declared.  The
    placeholder stores all instantiation information needed to create
    the fields when the message object is instantiated

    """

    # record the number of instantiations of fields.  This is how
    # we can track the order of fields within a message
    _global_seqno = 0

    def __init__(self, cls, args, kwargs):
        self._field_seqno = FieldPlaceholder._global_seqno
        FieldPlaceholder._global_seqno += 1
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def create_instance(self, parent):
        """Create an instance based off this placeholder with some parent"""
        self.kwargs['instantiate'] = True
        self.kwargs['parent'] = parent
        instance = self.cls(*self.args, **self.kwargs)
        instance._field_seqno = self._field_seqno
        return instance


class BaseField(object):
    """Base class for all Field instances

    Some magic is used whenever a field is created normally in order to
    allow for a declarative syntax without having to create explicit
    factory methods/classes everywhere.  By default (for a normal call)
    when a field is instantiated, it actually ends up returning a
    FieldPlaceholder object containing information about the field
    that has been declared.

    To get an actual instance of the field, the call to the construction
    must include a keyword argument ``instantiate`` that is set to some
    truthy value.  Typically, this instantiation logic is done by
    calling ``FieldPlaceholder.create_instance(parent)``.  This is the
    recommended way to construct a field as it ensure all invariants
    are in place (having a parent).

    :param instantiate: Create an actual instance instead of a placeholder
    :param parent: Specify the parent of this field (typically a Structure
        instace).

    """

    def __new__(cls, *args, **kwargs):
        instantiate = kwargs.pop('instantiate', False)
        if instantiate:
            return super(BaseField, cls).__new__(cls)
        else:
            return FieldPlaceholder(cls, args, kwargs)

    def __init__(self, *args, **kwargs):
        self._value = None
        self._parent = kwargs.get('parent')

    def _ph2f(self, placeholder):
        """Lookup a field given a field placeholder"""
        return self._parent.lookup_field_by_placeholder(placeholder)

    def __repr__(self):
        return repr(self.getval())

    def getval(self):
        return self._value

    def setval(self, value):
        self._value = value


class CRCField(BaseField):
    r"""Field representing CRC (Cyclical Redundancy Check) in a message

    CRC checks and calculation frequently work quite differently
    from other fields in a protocol and as such are treated differently
    by the messag container.  In particular, a CRCField requires
    special steps at either the beginning or end of the message
    pack/unpack process.  For each CRCField, we specify the following:

    :param field: The underlying field defining how the checksum will
        be stored.  This should match the size of the checksum in
        whatever algorithm is being used (16 bits for CRC16).
    :param algo: The algorithm to be used for performing the checksum.
       This is basically a function that takes a chunk of data and
       gives the checksum.  Several of these are provided out of the
       box in ``suitcase.crc``.
    :param start: The offset in the overall message at which we should
        start the checksum.  This may be positive (from the start) or
        negative (from the end of the message).
    :param end: The offset in the overall message at which we should
        end the checksum algo.  This may be positive (from the start)
        or negative (from the end of the message).

    A quick example of a message with a checksum is in order::

        class MyChecksummedMessage(Structure):
            soh = Magic('\x1f\x1f')
            message_id = UBInt16()
            sequence_number = UBInt8()
            payload_length = LengthField(UBInt16())
            payload = VariableRawPayload(payload_length)

            # crc starts after soh and ends before crc
            crc = CRCField(UBInt16(), crc16_ccitt, 2, -3)
            eof = Magic('~')

    """

    def __init__(self, field, algo, start, end, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.field = field.create_instance(self._parent)
        self.field.setval(0)
        self.algo = algo
        self.start = start
        self.end = end
        self._value = None

    @property
    def bytes_required(self):
        return self.field.bytes_required

    def validate(self, data, offset):
        """Raises :class:`SuitcaseChecksumException` if not valid"""
        recorded_checksum = self.field.getval()

        # convert negative offset to positive
        if offset < 0:
            offset += len(data)

        # replace checksum region with zero
        data = b''.join((data[:offset],
                         b"\x00" * self.bytes_required,
                         data[offset + self.bytes_required:]))
        actual_checksum = self.algo(data[self.start:self.end])
        if recorded_checksum != actual_checksum:
            raise SuitcaseChecksumException(
                "recorded checksum %r did not match actual %r.  full data: %r",
                recorded_checksum, actual_checksum, data)

    def packed_checksum(self, data):
        """Given the data of the entire packet reutrn the checksum bytes"""
        self.field.setval(self.algo(data[self.start:self.end]))
        sio = BytesIO()
        self.field.pack(sio)
        return sio.getvalue()

    def getval(self):
        return self.field.getval()

    def setval(self, *args):
        raise SuitcaseProgrammingError("CRC will be set automatically")

    def pack(self, stream):
        # write placeholder during the first pass
        stream.write(b'\x00' * self.field.bytes_required)

    def unpack(self, data):
        self.field.unpack(data)


class Magic(BaseField):
    """Represent Byte Magic (fixed, expected sequence of bytes)"""

    def __init__(self, expected_sequence, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.expected_sequence = expected_sequence
        self.bytes_required = len(self.expected_sequence)

    def getval(self):
        return self.expected_sequence

    def setval(self, *args):
        raise SuitcaseProgrammingError("One does not simply modify Magic")

    def pack(self, stream):
        stream.write(self.expected_sequence)

    def unpack(self, data):
        if not data == self.expected_sequence:
            raise SuitcaseParseError(
                "Expected sequence %r for magic field but got %r on "
                "message %r" % (self.expected_sequence, data, self._parent))

    def __repr__(self):
        return "Magic(%r)" % (self.expected_sequence,)


class FieldProperty(BaseField):
    """Provide the ability to define "Property" getter/setters for other fields

    This is useful and preferable and preferable to inheritance if you want
    to provide a different interface for getting/setting one some field
    within a message.  Take the test case as an example::

        # define the message
        class MyMessage(Structure):
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

    :param field: The field that is wrapped by this FieldProperty.  The value
        of this field is passed into or set by the associated get/set fns.
    :param onget: This is a function pointer to a function called to mutate
        the value returned on field access.  The function receives a single
        argument containing the value of the wrapped field.
    :oaram onset: This is a functoin pointer to a function called to map
        between the property and the underlying field.  The function takes
        a single parameter which is the value the property was set to.  It
        should return the value that the underlying field expects (or raise
        an exception if appropriate).

    """

    def __init__(self, field, onget=None, onset=None, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.onget = onget
        self.onset = onset
        self.field = self._ph2f(field)
        self.bytes_required = 0

    def _default_onget(self, value):
        return value

    def _default_onset(self, value):
        return value

    def getval(self):
        onget = self.onget
        if onget is None:
            onget = self._default_onget
        value = self.field.getval()
        return onget(value)

    def setval(self, value):
        onset = self.onset
        if onset is None:
            onset = self._default_onset

        self.field.setval(onset(value))

    def unpack(self, data):
        pass

    def pack(self, stream):
        pass


class DispatchField(BaseField):
    """Decorate a field as a dispatch byte (used as conditional)

    A DispatchField is always used with a DispatchTarget within the same
    message (at some level).

    Example::

        class MyMessage(Structure):
            type = DispatchField(UBInt8())
            body = DispatchTarget(dispatch_field=type, dispatch_mapping={
                0x00: MessageType0,
                0x01: MessageType1,
            })

    :param field: The field containing the dispatch parameter.  This is
        typically an integer but could be any hashable object.

    """

    def __init__(self, field, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.field = field.create_instance(self._parent)

    @property
    def bytes_required(self):
        return self.field.bytes_required

    def getval(self):
        return self.field.getval()

    def setval(self, value):
        return self.field.setval(value)

    def __repr__(self):
        return repr(self.field)

    def pack(self, stream):
        return self.field.pack(stream)

    def unpack(self, data):
        assert len(data) == self.bytes_required
        return self.field.unpack(data)


class DispatchTarget(BaseField):
    """Represent a conditional branch on some DispatchField

    Example::

        class MyMessage(Structure):
            type = DispatchField(UBInt8())
            body = DispatchTarget(dispatch_field=type, dispatch_mapping={
                0x00: MessageType0,
                0x01: MessageType1,
            })

    :param length_provider: The field providing a length value binding this
        message (if any).  Set this field to None to leave unconstrained.
    :param dispatch_field: The field being target for dispatch.  In most
        protocols this is an integer type byte or something similar.  The
        possible values for this field act as the keys for the dispatch.
    :param dispatch_mapping: This is a dictionary mapping dispatch_field
        values to associated message types to handle the remaining processing.

    """

    def __init__(self, length_provider, dispatch_field,
                 dispatch_mapping, **kwargs):
        BaseField.__init__(self, **kwargs)
        if length_provider is None:
            self.length_provider = None
        else:
            self.length_provider = self._ph2f(length_provider)
            self.length_provider.associate_length_consumer(self)
        self.dispatch_field = self._ph2f(dispatch_field)
        self.dispatch_mapping = dispatch_mapping
        self.inverse_dispatch_mapping = dict((v, k) for (k, v)
                                             in dispatch_mapping.items())

    def _lookup_msg_type(self):
        target_key = self.dispatch_field.getval()
        target = self.dispatch_mapping.get(target_key, None)
        if target is None:
            target = self.dispatch_mapping.get(None, None)

        return target

    @property
    def bytes_required(self):
        if self.length_provider is None:
            return None
        else:
            return self.length_provider.get_adjusted_length()

    def getval(self):
        return self._value

    def setval(self, value):
        try:
            vtype = type(value)
            key = self.inverse_dispatch_mapping[vtype]
        except KeyError:
            raise SuitcaseProgrammingError("The type specified is not in the "
                                           "dispatch table")

        # OK, things check out.  Set both the value here and the
        # type byte value
        self._value = value
        value._parent = self._parent
        self.dispatch_field.setval(key)

    def pack(self, stream):
        return self._value._packer.write(stream)

    def unpack(self, data):
        target_msg_type = self._lookup_msg_type()
        if target_msg_type is None:
            target_msg_type = self.dispatch_mapping.get(None)
        if target_msg_type is None:  # still none
            raise SuitcaseParseError("Input data contains type byte not"
                                     " contained in mapping")
        message_instance = target_msg_type()
        self.setval(message_instance)
        self._value.unpack(data)


class LengthField(BaseField):
    """Wraps an existing field marking it as a LengthField

    This field wraps another field which is assumed to return an
    integer value.  A LengthField can be pointed to by a variable
    length field and the two will be coupled appropriately.

    :param length_field: The field providing the actual length value to
        be used.  This field should return an integer value representing
        the length (or a multiple of the length) as a return value
    :param multiplier: If specified, this multiplier is applied to the
        length.  If I specify a multiplier of 8, I am saying that each bit
        in the length field represents 8 bytes of actual payload length. By
        default the multiplier is 1 (1 bit/byte).

    """

    def __init__(self, length_field, multiplier=1, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.multiplier = multiplier
        self.length_field = length_field.create_instance(self._parent)
        self.length_value_provider = None

    def __repr__(self):
        return repr(self.length_field)

    @property
    def bytes_required(self):
        return self.length_field.bytes_required

    def getval(self):
        length_value = self.length_field.getval()
        return length_value

    def setval(self, value):
        raise SuitcaseProgrammingError("Cannot set the value of a LengthField")

    def associate_length_consumer(self, target_field):
        def _length_value_provider():
            sio = BytesIO()
            target_field.pack(sio)
            target_field_length = len(sio.getvalue())
            if not target_field_length % self.multiplier == 0:
                raise SuitcaseProgrammingError("Payload length not divisible "
                                               "by %s" % self.multiplier)
            return (target_field_length // self.multiplier)

        self.length_value_provider = _length_value_provider

    def pack(self, stream):
        if self.length_value_provider is None:
            raise SuitcaseException("No length_provider added to this LengthField")
        self.length_field._value = self.length_value_provider()
        self.length_field.pack(stream)

    def unpack(self, data):
        assert len(data) == self.bytes_required
        return self.length_field.unpack(data)

    def get_adjusted_length(self):
        return self.getval() * self.multiplier


class TypeField(BaseField):
    """Wraps an existing field marking it as a TypeField

    This field wraps another field which is assumed to return an
    integer value.  A TypeField can be pointed to by a variable
    length field and will fix that field's length.

    :param type_field: The field providing the type id that will
        be used to lookup a length value
    :param length_mapping: This is a dictionary mapping type_field
        values to associated length values.

    For example, a TypeField could be used as a replacement for a
    DispatchField so that the associated DispatchTarget is non-greedy,
    without the existence of a seperate LengthField. This enables
    a greedy field to follow the dispatch field, without the usage of
    complex ConditionalField setups::

        class Structure8Bit(Structure):
            value = UBInt8()

        class Structure16Bit(Structure):
            value = UBInt16()

        class DispatchStructure(Structure):
            type = TypeField(UBInt8(), {0x40: 1,
                                        0x80: 2})
            # Here the TypeField is providing both a size and type id
            dispatch = DispatchTarget(type, type, {0x40: Structure8Bit,
                                                   0x80: Structure16Bit})
            greedy = Payload()
    """

    def __init__(self, type_field, length_mapping, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.type_field = type_field.create_instance(self._parent)
        self.length_mapping = length_mapping
        self.length_value_provider = None

    def _lookup_msg_length(self):
        target_key = self.type_field.getval()
        target_length = self.length_mapping.get(target_key, None)
        if target_length is None:
            target_length = self.length_mapping.get(None, None)

        return target_length

    def __repr__(self):
        return repr(self.type_field)

    @property
    def bytes_required(self):
        return self.type_field.bytes_required

    def getval(self):
        return self.type_field.getval()

    def setval(self, value):
        self.type_field.setval(value)

    def associate_length_consumer(self, target_field):
        def _length_value_provider():
            sio = BytesIO()
            target_field.pack(sio)
            target_field_length = len(sio.getvalue())
            if target_field_length != self.get_adjusted_length():
                raise SuitcaseProgrammingError("Payload length %i does not" +
                                               " match length %i specified by type"
                                               % (target_field_length, self.get_adjusted_length()))
            return target_field_length

        self.length_value_provider = _length_value_provider

    def pack(self, stream):
        if self.length_value_provider is None:
            raise SuitcaseException("No length_provider added to this TypeField")
        # This will throw a SuitcasePackException if the length is not correct
        self.length_value_provider()

        self.type_field.pack(stream)

    def unpack(self, data):
        assert len(data) == self.bytes_required
        return self.type_field.unpack(data)

    def get_adjusted_length(self):
        return self._lookup_msg_length()


class ConditionalField(BaseField):
    """Field which may or may not be included depending on some condition

    In some protocols, there exist fields which may or may not be present
    depending on the values of other fields that would have already been
    parsed at this point in time.  Wrapping such fields in  a ConditionalField
    allows us to define a function to examine that state and only have the
    field capture the bytes if the conditions are right.

    :param field: The field which should handle the parsing if the condition
        evaluates to true.

    :param condition: This is a function which is given access to the parent
        message that is expected to return a boolean value.  If the value
        is true, then ``field`` will handle the bytes.  If not, then the
        field will be skipped and left with its default value (None).

    """

    def __init__(self, field, condition, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.field = field.create_instance(self._parent)
        self.condition = condition

    def __repr__(self):
        if self.condition(self._parent):
            return repr(self.field)
        else:
            return "<ConditionalField: not included>"

    @property
    def bytes_required(self):
        if self.condition(self._parent):
            return self.field.bytes_required
        else:
            return 0

    def pack(self, stream):
        if self.condition(self._parent):
            self.field.pack(stream)

    def unpack(self, data):
        # length of data will be determined by bytes_required output value
        # which is in turn determined by our condition evaluation
        if len(data) > 0:
            self.field.unpack(data)

    def getval(self):
        return self.field.getval()

    def setval(self, value):
        return self.field.setval(value)

    def associate_length_consumer(self, target_field):
        self.field.associate_length_consumer(target_field)

    def get_adjusted_length(self):
        return self.field.get_adjusted_length()


class Payload(BaseField):
    """Variable length raw (byte string) field

    This field is expected to be used with a LengthField.  The variable
    length field provides a value to be used by the LengthField on
    message pack and vice-versa for unpack.

    :param length_provider: The LengthField with which this variable
        length payload is associated.  If not included, it is assumed that
        the length_provider should consume the remainder of the bytes
        available in the string.  This is only valid in cases where the
        developer knows that they will be dealing with a fixed sequence
        of bytes (already boxed).

    """

    def __init__(self, length_provider=None, **kwargs):
        BaseField.__init__(self, **kwargs)
        if isinstance(length_provider, FieldPlaceholder):
            self.length_provider = self._ph2f(length_provider)
            self.length_provider.associate_length_consumer(self)
        else:
            self.length_provider = None

    @property
    def bytes_required(self):
        if self.length_provider is None:
            return None
        else:
            return self.length_provider.get_adjusted_length()

    def pack(self, stream):
        stream.write(self._value)

    def unpack(self, data):
        self._value = data


# keep for backwards compatability
VariableRawPayload = Payload


class BaseVariableByteSequence(BaseField):
    def __init__(self, make_format, length_provider, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.make_format = make_format
        if length_provider is not None:
            self.length_provider = self._ph2f(length_provider)
            self.length_provider.associate_length_consumer(self)

    @property
    def bytes_required(self):
        return self.length_provider.get_adjusted_length()

    def pack(self, stream):
        sfmt = self.make_format(len(self._value))
        try:
            stream.write(struct.pack(sfmt, *self._value))
        except struct.error as e:
            raise SuitcasePackStructException(e)

    def unpack(self, data):
        assert len(data) == self.bytes_required

        length = self.bytes_required
        sfmt = self.make_format(length)
        try:
            self._value = struct.unpack(sfmt, data)
        except struct.error as e:
            raise SuitcasePackStructException(e)


class DependentField(BaseField):
    """Field populated by container packet at lower level

    It is sometimes the case that information from another layer of a
    messaging protocol be needed at another higher-level of the protocol.
    The DependentField is a way of declaring that a message at some layer
    is dependent on a field with some name from the parent layer.

    For instance, let's suppose that my protocol had an option byte that
    I wanted to include in some logic handling packets at some higher
    layer.  I could include that byte in my message as follows::

        class MyDependentMessage(Structure):
            ll_options = DependentField('proto_options')
            data = UBInt8Sequence(16)

        class LowerLevelProtocol(Structure):
            type = DispatchField(UBInt16())
            proto_options = UBInt8()
            body = DispatchTarget(None, type, {
                0x00: MyDependentMessage,
            })

    :params name: The name of the field from the parent message that we
        would like brought into our message namespace.

    """

    def __init__(self, name, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.bytes_required = 0
        self.parent_field_name = name
        self.parent_field = None

    def _get_parent_field(self):
        if self.parent_field is None:
            message_parent = self._parent._parent
            target_field = message_parent.lookup_field_by_name(
                self.parent_field_name)
            self.parent_field = target_field
        return self.parent_field

    def __getattr__(self, attr):
        return getattr(self._get_parent_field(), attr)

    def pack(self, stream):
        pass

    def unpack(self, data):
        pass

    def getval(self):
        return self._get_parent_field().getval()

    def setval(self, value):
        return self._get_parent_field().setval(value)


class SubstructureField(BaseField):
    """Field which contains another non-greedy Structure.

    Often data-types are needed which cannot be easily
    described by a single field, but are representable as
    Structures. For example, Pascal style strings are prefixed
    with their length. It is often desirable to embed these
    data-types within another Structure, to avoid reimplementing
    them in every usage.


    A Pascal style string could be described as follows::

        from suitcase.structure import Structure
        from suitcase.fields import Payload, UBInt16, LengthField, SubstructureField

        class PascalString16(Structure):
            length = LengthField(UBInt16())
            value = Payload(length)

    A structure describing a name of a person might consist of two
    Pascal style strings. Instead of describing the ugly way::

        class NameUgly(Structure):
            first_length = LengthField(UBInt16())
            first_value = Payload(first_length)
            last_length = LengthField(UBInt16())
            last_value = Payload(last_length)

    it could be defined using a SubstructureField::

        class Name(Structure):
            first = SubstructureField(PascalString16)
            last = SubstructureField(PascalString16)
    """

    def __init__(self, substructure, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.substructure = substructure
        self._value = substructure()

    @property
    def bytes_required(self):
        # We return None but do not count as a greedy field to the packer
        return None

    def pack(self, stream):
        stream.write(self._value.pack())

    def unpack(self, data, trailing):
        self._value = self.substructure()
        return self._value.unpack(data, trailing)


class FieldArray(BaseField):
    """Field which contains a list of some other field.

    In some protocols, there exist repeated substructures which are present in a
    variable number. The variable nature of these fields make a DispatchField
    and DispatchTarget combination unsuitable; instead a FieldArray may be
    used to pack/unpack these fields to/from a list.

    :param substructure: The type of the array element. Must not be a greedy
        field, or else the array will only ever have one element containing
        the entire contents of the array.
    :param length_provider: The field providing a length value binding this
        message (if any).  Set this field to None to leave unconstrained.

    For example, one can imagine a message listing the zipcodes covered by
    a telephone area code. Depending on the population density, the number
    of zipcodes per area code could vary greatly. One implementation of this
    data structure could be::

        from suitcase.structure import Structure
        from suitcase.fields import UBInt16, FieldArray

        class ZipcodeStructure(Structure):
            zipcode = UBInt16()

        class TelephoneZipcodes(Structure):
            areacode = UBInt16()
            zipcodes = FieldArray(ZipcodeStructure)  # variable number of zipcodes

    """

    def __init__(self, substructure, length_provider=None, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.substructure = substructure
        self._value = list()
        if isinstance(length_provider, FieldPlaceholder):
            self.length_provider = self._ph2f(length_provider)
            self.length_provider.associate_length_consumer(self)
        else:
            self.length_provider = None

    @property
    def bytes_required(self):
        if self.length_provider is None:
            return None
        else:
            return self.length_provider.get_adjusted_length()

    def pack(self, stream):
        for structure in self._value:
            stream.write(structure.pack())

    def unpack(self, data):
        while True:
            structure = self.substructure()
            data = structure.unpack(data, trailing=True).read()
            self._value.append(structure)
            if data == b"":
                break


class BaseFixedByteSequence(BaseField):
    """Base fixed-length byte sequence field"""

    def __init__(self, make_format, size, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.bytes_required = size
        self.format = make_format(size)

    def pack(self, stream):
        try:
            stream.write(struct.pack(self.format, *self._value))
        except struct.error as e:
            raise SuitcasePackStructException(e)

    def unpack(self, data):
        try:
            self._value = struct.unpack(self.format, data)
        except struct.error as e:
            raise SuitcasePackStructException(e)


def byte_sequence_factory_factory(make_format):
    def byte_sequence_factory(length_or_provider):
        if isinstance(length_or_provider, int):
            return BaseFixedByteSequence(make_format, length_or_provider)
        else:
            return BaseVariableByteSequence(make_format, length_or_provider)

    return byte_sequence_factory


UBInt8Sequence = byte_sequence_factory_factory(lambda l: ">" + "B" * l)
ULInt8Sequence = byte_sequence_factory_factory(lambda l: "<" + "B" * l)
SBInt8Sequence = byte_sequence_factory_factory(lambda l: ">" + "b" * l)
SLInt8Sequence = byte_sequence_factory_factory(lambda l: "<" + "b" * l)


class BaseStructField(BaseField):
    """Base for fields based very directly on python struct module formats

    It is expected that this class will be subclassed and customized by
    defining ``FORMAT`` at the class level.  ``FORMAT`` is expected to
    be a format string that could be used with struct.pack/unpack.  It
    should include endianess information.  If the ``FORMAT`` includes
    multiple elements, the default ``_unpack`` logic assumes that each
    element is a single byte and will OR these together.  To specialize
    this, _unpack should be overriden.

    """

    def __init__(self, **kwargs):
        BaseField.__init__(self, **kwargs)
        self._value = None
        self._keep_bytes = getattr(self, "KEEP_BYTES", None)
        if self._keep_bytes is not None:
            self.bytes_required = self._keep_bytes
        else:
            self.bytes_required = struct.calcsize(self.PACK_FORMAT)

    def pack(self, stream):
        try:
            keep_bytes = getattr(self, 'KEEP_BYTES', None)
            if keep_bytes is not None:
                if self.PACK_FORMAT[0] == b">"[0]:  # The element access makes this compatible with Python 2 and 3
                    to_write = struct.pack(self.PACK_FORMAT, self._value)[-keep_bytes:]
                else:
                    to_write = struct.pack(self.PACK_FORMAT, self._value)[:keep_bytes]
            else:
                to_write = struct.pack(self.PACK_FORMAT, self._value)
        except struct.error as e:
            raise SuitcasePackStructException(e)
        stream.write(to_write)

    def unpack(self, data):
        value = 0
        if self.UNPACK_FORMAT[0] == b">"[0]:  # The element access makes this compatible with Python 2 and 3
            for i, byte in enumerate(reversed(struct.unpack(self.UNPACK_FORMAT, data))):
                value |= (byte << (i * 8))
        else:
            for i, byte in enumerate(struct.unpack(self.UNPACK_FORMAT, data)):
                value |= (byte << (i * 8))
        self._value = value


# ==============================================================================
# Unsigned Big Endian
# ==============================================================================
class UBInt8(BaseStructField):
    """Unsigned Big Endian 8-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">B"


class UBInt16(BaseStructField):
    """Unsigned Big Endian 16-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">H"


class UBInt24(BaseStructField):
    """Unsigned Big Endian 24-bit integer field"""
    KEEP_BYTES = 3
    PACK_FORMAT = b">I"
    UNPACK_FORMAT = b">BBB"


class UBInt32(BaseStructField):
    """Unsigned Big Endian 32-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">I"


class UBInt40(BaseStructField):
    """Unsigned Big Endian 40-bit integer field"""
    KEEP_BYTES = 5
    PACK_FORMAT = b">Q"
    UNPACK_FORMAT = b">BBBBB"


class UBInt48(BaseStructField):
    """Unsigned Big Endian 48-bit integer field"""
    KEEP_BYTES = 6
    PACK_FORMAT = b">Q"
    UNPACK_FORMAT = b">BBBBBB"


class UBInt56(BaseStructField):
    """Unsigned Big Endian 56-bit integer field"""
    KEEP_BYTES = 7
    PACK_FORMAT = b">Q"
    UNPACK_FORMAT = b">BBBBBBB"


class UBInt64(BaseStructField):
    """Unsigned Big Endian 64-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">Q"


# ==============================================================================
# Signed Big Endian
# ==============================================================================
class SBInt8(BaseStructField):
    """Signed Big Endian 8-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">b"


class SBInt16(BaseStructField):
    """Signed Big Endian 16-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">h"


class SBInt24(BaseStructField):
    """Signed Big Endian 24-bit integer field"""
    KEEP_BYTES = 3
    PACK_FORMAT = b">i"
    UNPACK_FORMAT = b">bBB"


class SBInt32(BaseStructField):
    """Signed Big Endian 32-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">i"


class SBInt40(BaseStructField):
    """Signed Big Endian 40-bit integer field"""
    KEEP_BYTES = 5
    PACK_FORMAT = b">q"
    UNPACK_FORMAT = b">bBBBB"


class SBInt48(BaseStructField):
    """Signed Big Endian 48-bit integer field"""
    KEEP_BYTES = 6
    PACK_FORMAT = b">q"
    UNPACK_FORMAT = b">bBBBBB"


class SBInt56(BaseStructField):
    """Signed Big Endian 56-bit integer field"""
    KEEP_BYTES = 7
    PACK_FORMAT = b">q"
    UNPACK_FORMAT = b">bBBBBBB"


class SBInt64(BaseStructField):
    """Signed Big Endian 64-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b">q"


# ==============================================================================
# Unsigned Little Endian
# ==============================================================================
class ULInt8(BaseStructField):
    """Unsigned Little Endian 8-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<B"


class ULInt16(BaseStructField):
    """Unsigned Little Endian 16-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<H"


class ULInt24(BaseStructField):
    """Unsigned Little Endian 24-bit integer field"""
    KEEP_BYTES = 3
    PACK_FORMAT = b"<I"
    UNPACK_FORMAT = b"<BBB"


class ULInt32(BaseStructField):
    """Unsigned Little Endian 32-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<I"


class ULInt40(BaseStructField):
    """Unsigned Little Endian 40-bit integer field"""
    KEEP_BYTES = 5
    PACK_FORMAT = b"<Q"
    UNPACK_FORMAT = b"<BBBBB"


class ULInt48(BaseStructField):
    """Unsigned Little Endian 48-bit integer field"""
    KEEP_BYTES = 6
    PACK_FORMAT = b"<Q"
    UNPACK_FORMAT = b"<BBBBBB"


class ULInt56(BaseStructField):
    """Unsigned Little Endian 56-bit integer field"""
    KEEP_BYTES = 7
    PACK_FORMAT = b"<Q"
    UNPACK_FORMAT = b"<BBBBBBB"


class ULInt64(BaseStructField):
    """Unsigned Little Endian 64-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<Q"


# ==============================================================================
# Signed Little Endian
# ==============================================================================
class SLInt8(BaseStructField):
    """Signed Little Endian 8-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<b"


class SLInt16(BaseStructField):
    """Signed Little Endian 16-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<h"


class SLInt24(BaseStructField):
    """Signed Little Endian 24-bit integer field"""
    KEEP_BYTES = 3
    PACK_FORMAT = b"<i"
    UNPACK_FORMAT = b"<BBb"


class SLInt32(BaseStructField):
    """Signed Little Endian 32-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<i"


class SLInt40(BaseStructField):
    """Signed Little Endian 40-bit integer field"""
    KEEP_BYTES = 5
    PACK_FORMAT = b"<q"
    UNPACK_FORMAT = b"<BBBBb"


class SLInt48(BaseStructField):
    """Signed Little Endian 48-bit integer field"""
    KEEP_BYTES = 6
    PACK_FORMAT = b"<q"
    UNPACK_FORMAT = b"<BBBBBb"


class SLInt56(BaseStructField):
    """Signed Little Endian 56-bit integer field"""
    KEEP_BYTES = 7
    PACK_FORMAT = b"<q"
    UNPACK_FORMAT = b"<BBBBBBb"


class SLInt64(BaseStructField):
    """Signed Little Endian 64-bit integer field"""
    PACK_FORMAT = UNPACK_FORMAT = b"<q"


# ==============================================================================
# BitField and Bits
# ==============================================================================
def bitfield_placeholder_factory_factory(cls):
    def _factory_fn(*args, **kwargs):
        return cls(*args, **kwargs)

    return _factory_fn


class _BitFieldFieldPlaceholder(object):
    _global_seqno = 0

    def __init__(self, cls, args, kwargs):
        self.cls = cls
        self.args = args
        self.kwargs = kwargs
        self.sequence_number = _BitFieldFieldPlaceholder._global_seqno
        _BitFieldFieldPlaceholder._global_seqno += 1

    def create_instance(self):
        kwargs = self.kwargs
        kwargs['instantiate'] = True
        return self.cls(*self.args, **self.kwargs)


class _BitFieldField(object):
    def __init__(self, *args, **kwargs):
        pass

    def __repr__(self):
        return repr(self.viewget())

    def __new__(cls, *args, **kwargs):
        if 'instantiate' in kwargs:
            return super(_BitFieldField, cls).__new__(cls)
        else:
            return _BitFieldFieldPlaceholder(cls, args, kwargs)


class _BitBool(_BitFieldField):
    def __init__(self, **kwargs):
        _BitFieldField.__init__(self, **kwargs)
        self.size = 1
        self._value = 0

    def getval(self):
        return self._value

    def setval(self, value):
        self._value = value

    def viewget(self):
        return (self._value == 1)

    def viewset(self, value):
        if value:
            self._value = 1
        else:
            self._value = 0


class _BitNum(_BitFieldField):
    def __init__(self, size, **kwargs):
        _BitFieldField.__init__(self, **kwargs)
        self.size = size
        self._value = 0

    def getval(self):
        return self._value

    viewget = getval

    def setval(self, value):
        self._value = value

    viewset = setval


BitNum = bitfield_placeholder_factory_factory(_BitNum)
BitBool = bitfield_placeholder_factory_factory(_BitBool)


class BitField(BaseField):
    """Represent a sequence of bytes broken down into bit segments

    Bit segments may be any BitFieldField instance, with the two most
    commonly used fields being:

    * BitBool(): A single bit flag that is either True or False
    * BitNum(bits): A multi-bit field treated like a big-endian integral
           value.

    Example Usage::

        class TCPFrameHeader(Structure):
            source_address = UBInt16()
            destination_address = UBInt16()
            sequence_number = UBInt32()
            acknowledgement_number = UBInt32()
            options = BitField(16,
                data_offset=BitNum(4),
                reserved=BitNum(3),
                NS=BitBool(),
                CWR=BitBool(),
                ECE=BitBool(),
                URG=BitBool(),
                ACK=BitBool(),
                PSH=BitBool(),
                RST=BitBool(),
                SYN=BitBool(),
                FIN=BitBool()
            )
            window_size = UBInt16()
            checksum = UBInt16()
            urgent_pointer = UBInt16()

        tcp_packet = TCPFrameHeader()
        o = tcp_packet.options
        o.data_offset = 3
        o.NS = True
        o.CWR = False
        o.
        # ... so on, so forth

    """

    def __init__(self, number_bits, field=None, **kwargs):
        BaseField.__init__(self, **kwargs)
        self._ordered_bitfields = []
        self._bitfield_map = {}
        if number_bits % 8 != 0:
            raise SuitcaseProgrammingError("Number of bits must be a factor of "
                                           "8, was %d" % number_bits)

        self.number_bits = number_bits
        self.number_bytes = number_bits // 8
        self.bytes_required = self.number_bytes
        if field is None:
            field = {
                1: UBInt8,
                2: UBInt16,
                3: UBInt24,
                4: UBInt32,
                5: UBInt40,
                6: UBInt48,
                7: UBInt56,
                8: UBInt64,
            }[self.number_bytes]()
        self._field = field.create_instance(self._parent)

        placeholders = []
        for key, value in six.iteritems(kwargs):
            if isinstance(value, _BitFieldFieldPlaceholder):
                placeholders.append((key, value))

        for key, placeholder in sorted(placeholders, key=lambda kv: kv[1].sequence_number):
            value = placeholder.create_instance()
            self._bitfield_map[key] = value
            self._ordered_bitfields.append((key, value))

    def __getattr__(self, key):
        if key in self.__dict__.get('_bitfield_map', {}):
            return self._bitfield_map[key].viewget()
        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        if key in self.__dict__.get('_bitfield_map', {}):
            self._bitfield_map[key].viewset(value)
        else:
            self.__dict__[key] = value

    def __repr__(self):
        sio = StringIO()
        sio.write("BitField(\n")
        for key, field in self._ordered_bitfields:
            sio.write("    %s=%r,\n" % (key, field))
        sio.write("  )")
        return sio.getvalue()

    def getval(self):
        return self

    def setval(self, value):
        raise SuitcaseProgrammingError("Setting the value of a bitfield "
                                       "directly is prohibited")

    def pack(self, stream):
        value = 0
        shift = self.number_bits
        for _key, field in self._ordered_bitfields:
            shift -= field.size
            mask = (2 ** field.size - 1)  # mask off size bits
            value |= ((field.getval() & mask) << shift)

        self._field.setval(value)
        sio = BytesIO()
        self._field.pack(sio)
        out = sio.getvalue()[-self.number_bytes:]
        stream.write(out)

    def unpack(self, data):
        self._field.unpack(data)
        value = self._field.getval()
        shift = self.number_bits
        for _key, field in self._ordered_bitfields:
            shift -= field.size
            mask = (2 ** field.size - 1)
            fval = (value >> shift) & mask
            field.setval(fval)
