import struct


class FieldProperty(object):

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


class BaseStructField(BaseField):

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


class BaseByteSequence(BaseField):

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


class UBByteSequence(BaseByteSequence):
    FORMAT_MODIFIER = lambda self, l: ">" + "B" * l


class ULByteSequence(BaseByteSequence):
    FORMAT_MODIFIER = lambda self, l: "<" + "B" * l


#===============================================================================
# Unsigned Big Endian
#===============================================================================
class UBInt8(BaseStructField):
    FORMAT = ">B"


class UBInt16(BaseStructField):
    FORMAT = ">H"


class UBInt24(BaseStructField):
    FORMAT = ">BBB"


class UBInt32(BaseStructField):
    FORMAT = ">I"


class UBInt64(BaseStructField):
    FORMAT = ">Q"


#===============================================================================
# Signed Big Endian
#===============================================================================
class BInt8(BaseStructField):
    FORMAT = ">b"


class BInt16(BaseStructField):
    FORMAT = ">h"


class BInt32(BaseStructField):
    FORMAT = ">i"


class BInt64(BaseStructField):
    FORMAT = ">q"


#===============================================================================
# Unsigned Little Endian
#===============================================================================
class ULInt8(BaseStructField):
    FORMAT = "<B"


class ULInt16(BaseStructField):
    FORMAT = "<H"


class ULInt32(BaseStructField):
    FORMAT = "<I"


class ULInt64(BaseStructField):
    FORMAT = "<Q"


#===============================================================================
# Signed Little Endian
#===============================================================================
class LInt8(BaseStructField):
    FORMAT = "<b"


class LInt16(BaseStructField):
    FORMAT = "<h"


class LInt32(BaseStructField):
    FORMAT = "<i"


class LInt64(BaseStructField):
    FORMAT = "<q"
