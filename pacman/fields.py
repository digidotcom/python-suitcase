import struct


class FieldProperty(object):
    """Provide the ability to define "Property" getter/setters for other fields

    This is useful and preferable and preferable to inheritance if you want
    to provide a different interface for getting/setting one some field
    within a message.  Take the test case as an example::

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

    def __init__(self, field, onget=None, onset=None):
        self.onget = onget
        self.onset = onset
        self.field = field

    def _default_onget(self, value):
        return value

    def _default_onset(self, value):
        return value

    def __get__(self, obj, objtype=None):
        onget = self.onget
        if onget is None:
            onget = self.onget

        value = self.field.__get__(self.field)
        return onget(value)

    def __set__(self, obj, value):
        onset = self.onset
        if onset is None:
            onset = self._default_onset

        self.field.__set__(self.field, onset(value))


class BaseField(object):
    """Base class for all Field intances"""

    # record the number of instantiations of fields.  This is how
    # we can track the order of fields within a message
    _global_seqno = 0

    def __init__(self):
        self._field_seqno = BaseField._global_seqno
        self._value = None
        BaseField._global_seqno += 1

    def __repr__(self):
        return repr(self._value)

    def __get__(self, obj, objtype=None):
        return self._value

    def __set__(self, obj, value):
        self._value = value


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

    def __init__(self, length_field, multiplier=1):
        BaseField.__init__(self)
        self.multiplier = multiplier
        self.length_field = length_field
        self.length_value_provider = None

    def __repr__(self):
        return repr(self.length_field)

    def __get__(self, obj, objtype=None):
        length_value = self.length_field.__get__(obj, objtype)
        return length_value

    def __set__(self, obj, value):
        raise AttributeError("Cannot set the value of a LengthField")

    def _associate_length_consumer(self, target_field):
        def _length_value_provider():
            target_field_length = len(target_field.__get__(target_field))
            if not target_field_length % self.multiplier == 0:
                raise ValueError("Payload length not divisible by %s"
                                 % self.multiplier)
            return (target_field_length / self.multiplier)
        self.length_value_provider = _length_value_provider

    def _pack(self, stream):
        if self.length_value_provider is None:
            raise Exception("No length_provider added to this LengthField")
        self.length_field._value = self.length_value_provider()
        self.length_field._pack(stream)

    def _unpack(self, stream):
        return self.length_field._unpack(stream)

    def get_adjusted_length(self):
        return self.__get__(self) * self.multiplier


class VariableRawPayload(BaseField):
    """Variable length raw (byte string) field"""

    def __init__(self, length_provider):
        BaseField.__init__(self)
        self.length_provider = length_provider
        self.length_provider._associate_length_consumer(self)

    def _pack(self, stream):
        stream.write(self._value)

    def _unpack(self, stream):
        length = self.length_provider.get_adjusted_length()
        self._value = stream.read(length)


class BaseVariableByteSequence(BaseField):
    """Base variable-length byte sequence field"""

    def __init__(self, length_field=None, length_function=None):
        BaseField.__init__(self)


class BaseFixedByteSequence(BaseField):
    """Base fixed-length byte sequence field"""

    def __init__(self, size):
        BaseField.__init__(self)
        self.size = size
        self.format = self.FORMAT_MODIFIER(size)

    def __len__(self):
        return self.size

    def _pack(self, stream):
        stream.write(struct.pack(self.format, *self._value))

    def _unpack(self, stream):
        self._value = struct.unpack(self.format, stream.read(self.size))


# NOTE: on bytes (uint8) these are actually really the same thing.  We
# leave as is for a consistent interface
class UBInt8Sequence(BaseFixedByteSequence):
    """Provide access to a sequence of unsigned bytes (fixed length)

    Example::

        class MySeqMessage(BaseMessage):
            type = UBInt8()
            byte_values = UBByteSequence(16)

        msg = MySeqMessage()
        msg.type = 0
        msg.byte_values = (0, 1, 2, 3, 4, 5, 6, 7, 8,
                           9, 10, 11, 12, 13, 14, 15)
        self.assertEqual(msg.pack(),
                         '\\x00\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08'
                         '\\t\\n\\x0b\\x0c\\r\\x0e\\x0f')

    """
    FORMAT_MODIFIER = lambda self, l: ">" + "B" * l


class ULInt8Sequence(BaseFixedByteSequence):
    """Provide access to a sequnce of usnigned bytes"""
    FORMAT_MODIFIER = lambda self, l: "<" + "B" * l


class BaseStructField(BaseField):
    """Base for fields based very directly on python struct module formats
    
    It is expected that this class will be subclassed and customized by
    definining ``FORMAT`` at the class level.  ``FORMAT`` is expected to
    be a format string that could be used with struct.pack/unpack.  It
    should include endianess information.  If the ``FORMAT`` includes
    multiple elements, the default ``_unpack`` logic assumes that each
    element is a single byte and will OR these together.  To specialize
    this, _unpack should be overriden.

    """

    def __init__(self):
        BaseField.__init__(self)
        self._value = None
        self._size = struct.calcsize(self.FORMAT)

    def __len__(self):
        return self._size

    def _pack(self, stream):
        stream.write(struct.pack(self.FORMAT, self._value))

    def _unpack(self, stream):
        value = 0
        data = stream.read(self._size)
        for i, byte in enumerate(reversed(struct.unpack(self.FORMAT, data))):
            value |= (byte << (i * 8))
        self._value = value


#===============================================================================
# Unsigned Big Endian
#===============================================================================
class UBInt8(BaseStructField):
    """Unsigned Big Endian 8-bit integer field"""
    FORMAT = ">B"


class UBInt16(BaseStructField):
    """Unsigned Big Endian 16-bit integer field"""
    FORMAT = ">H"


class UBInt24(BaseStructField):
    """Unsigned Big Endian 24-bit integer field"""
    FORMAT = ">BBB"


class UBInt32(BaseStructField):
    """Unsigned Big Endian 32-bit integer field"""
    FORMAT = ">I"


class UBInt64(BaseStructField):
    """Unsigned Big Endian 64-bit integer field"""
    FORMAT = ">Q"


#===============================================================================
# Signed Big Endian
#===============================================================================
class SBInt8(BaseStructField):
    """Signed Big Endian 8-bit integer field"""
    FORMAT = ">b"


class SBInt16(BaseStructField):
    """Signed Big Endian 16-bit integer field"""
    FORMAT = ">h"


class SBInt32(BaseStructField):
    """Signed Big Endian 32-bit integer field"""
    FORMAT = ">i"


class SBInt64(BaseStructField):
    """Signed Big Endian 64-bit integer field"""
    FORMAT = ">q"


#===============================================================================
# Unsigned Little Endian
#===============================================================================
class ULInt8(BaseStructField):
    """Unsigned Little Endian 8-bit integer field"""
    FORMAT = "<B"


class ULInt16(BaseStructField):
    """Unsigned Little Endian 16-bit integer field"""
    FORMAT = "<H"


class ULInt32(BaseStructField):
    """Unsigned Little Endian 32-bit integer field"""
    FORMAT = "<I"


class ULInt64(BaseStructField):
    """Unsigned Little Endian 64-bit integer field"""
    FORMAT = "<Q"


#===============================================================================
# Signed Little Endian
#===============================================================================
class SLInt8(BaseStructField):
    """Signed Little Endian 8-bit integer field"""
    FORMAT = "<b"


class SLInt16(BaseStructField):
    """Signed Little Endian 16-bit integer field"""
    FORMAT = "<h"


class SLInt32(BaseStructField):
    """Signed Little Endian 32-bit integer field"""
    FORMAT = "<i"


class SLInt64(BaseStructField):
    """Signed Little Endian 64-bit integer field"""
    FORMAT = "<q"
