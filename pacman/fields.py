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


class BaseByteSequence(BaseField):
    """Base byte sequence field"""

    def __init__(self, num_bytes):
        BaseField.__init__(self)
        self.num_bytes = num_bytes
        self.format = self.FORMAT_MODIFIER(num_bytes)

    def __len__(self):
        return self.num_bytes

    def pack(self):
        return struct.pack(self.format, *self._value)

    def unpack(self, data):
        self._value = struct.unpack(self.format, data)


# NOTE: on bytes (uint8) these are actually really the same thing.  We
# leave as is for a consistent interface
class UBByteSequence(BaseByteSequence):
    """Provide access to a sequence of unsigned bytes

    Example::

        class MySeqMessage(BaseMessage):
            type = UBInt8()
            byte_values = UBByteSequence(16)

        msg = MySeqMessage()
        msg.type = 0
        msg.byte_values = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
        self.assertEqual(msg.pack(),
                         '\\x00\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08'
                         '\\t\\n\\x0b\\x0c\\r\\x0e\\x0f')

    """
    FORMAT_MODIFIER = lambda self, l: ">" + "B" * l


class ULByteSequence(BaseByteSequence):
    """Provide access to a sequnce of usnigned bytes"""
    FORMAT_MODIFIER = lambda self, l: "<" + "B" * l


class BaseStructField(BaseField):
    """Base for fields based very directly on python struct module formats"""

    def __init__(self):
        BaseField.__init__(self)
        self._value = None

    def __len__(self):
        return struct.calcsize(self.FORMAT)

    def pack(self):
        return struct.pack(self.FORMAT, self._value)

    def unpack(self, data):
        value = 0
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

