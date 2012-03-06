import struct


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
    :param parent: Specify the parent of this field (typically a BaseMessage
        instace).

    """

    def __new__(cls, *args, **kwargs):
        if kwargs.get('instantiate', False):
            return object.__new__(cls, *args, **kwargs)
        else:
            return FieldPlaceholder(cls, args, kwargs)

    def __init__(self, **kwargs):
        self._value = None
        self._parent = kwargs.get('parent')

    def _ph2f(self, placeholder):
        """Lookup a field given a field placeholder"""
        return self._parent.lookup_field_by_placeholder(placeholder)

    def __repr__(self):
        return repr(self._value)

    def getval(self):
        return self._value

    def setval(self, value):
        self._value = value


class FieldProperty(BaseField):
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

    def __init__(self, field, onget=None, onset=None, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.onget = onget
        self.onset = onset
        self.field = self._ph2f(field)

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

    def _unpack(self, stream):
        pass

    def _pack(self, stream):
        pass


class DispatchField(BaseField):
    """Decorate a field as a dispatch byte (used as conditional)

    A DispatchField is always used with a DispatchTarget within the same
    message (at some level).

    Example::

        class MyMessage(BaseMessage):
            type = DispatchField(UBInt8())
            body = DispatchTarget(dispatch_field = type, dispatch_mapping={
                0x00: MessageType0,
                0x01: MessageType1,
            })

    :param field: The field containing the dispatch parameter.  This is
        typically an integer but could be any hashable object.

    """

    def __init__(self, field, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.field = field.create_instance(self._parent)

    def getval(self):
        return self.field.getval()

    def setval(self, value):
        return self.field.setval(value)

    def __repr__(self):
        return repr(self.field)

    def _pack(self, stream):
        return self.field._pack(stream)

    def _unpack(self, stream):
        return self.field._unpack(stream)


class DispatchTarget(BaseField):
    """Represent a conditional branch on some DispatchField

    Example::

        class MyMessage(BaseMessage):
            type = DispatchField(UBInt8())
            body = DispatchTarget(dispatch_field = type, dispatch_mapping={
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
        self.length_provider = self._ph2f(length_provider)
        self.dispatch_field = self._ph2f(dispatch_field)
        self.dispatch_mapping = dispatch_mapping
        self.inverse_dispatch_mapping = dict((v, k) for (k, v)
                                             in dispatch_mapping.iteritems())

        self.length_provider._associate_length_consumer(self)

    def _lookup_msg_type(self):
        target_key = self.dispatch_field.getval()
        target = self.dispatch_mapping.get(target_key, None)
        if target is None:
            target = self.dispatch_mapping.get(None, None)

        return target

    def getval(self):
        return self._value

    def setval(self, value):
        try:
            vtype = type(value)
            key = self.inverse_dispatch_mapping[vtype]
        except KeyError:
            raise ValueError("The type specified is not in the dispatch table")

        # OK, things check out.  Set both the value here and the
        # type byte value
        self._value = value
        value._parent = self._parent
        self.dispatch_field.setval(key)

    def _pack(self, stream):
        return self._value._packer.write(stream)

    def _unpack(self, stream):
        target_msg_type = self._lookup_msg_type()
        message_instance = target_msg_type()
        self.setval(message_instance)
        self._value._packer.unpack_stream(stream)


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

    def getval(self):
        length_value = self.length_field.getval()
        return length_value

    def setval(self, value):
        raise AttributeError("Cannot set the value of a LengthField")

    def _associate_length_consumer(self, target_field):
        def _length_value_provider():
            from StringIO import StringIO
            sio = StringIO()
            target_field._pack(sio)
            target_field_length = len(sio.getvalue())
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
        return self.getval() * self.multiplier


class VariableRawPayload(BaseField):
    """Variable length raw (byte string) field

    This field is expected to be used with a LengthField.  The variable
    length field provides a value to be used by the LengthField on
    message pack and vice-versa for unpack.

    :param length_provider: The LengthField with which this variable
        length payload is associated.

    """

    def __init__(self, length_provider, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.length_provider = self._ph2f(length_provider)
        self.length_provider._associate_length_consumer(self)

    def _pack(self, stream):
        stream.write(self._value)

    def _unpack(self, stream):
        length = self.length_provider.get_adjusted_length()
        self._value = stream.read(length)


class BaseVariableByteSequence(BaseField):

    def __init__(self, make_format, length_provider, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.make_format = make_format
        self.length_provider = self._ph2f(length_provider)
        self.length_provider._associate_length_consumer(self)

    def _pack(self, stream):
        sfmt = self.make_format(len(self._value))
        stream.write(struct.pack(sfmt, *self._value))

    def _unpack(self, stream):
        length = self.length_provider.get_adjusted_length()
        sfmt = self.make_format(length)
        self._value = struct.unpack(sfmt, stream.read(length))


class DependentField(BaseField):
    """Field populated by container packet at lower level

    It is sometimes the case that information from another layer of a
    messaging protocol be needed at another higher-level of the protocol.
    The DependentField is a way of declaring that a message at some layer
    is dependent on a field with some name from the parent layer.

    For instance, let's suppose that my protocol had an option byte that
    I wanted to include in some logic handling packets at some higher
    layer.  I could include that byte in my message as follows::

        class MyDependentMessage(BaseMessage):
            ll_options = DependentField('proto_options')
            data = UBInt8Sequence(16)

        class LowerLevelProtocol(BaseMessage):
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
        self.parent_field_name = name
        self.parent_field = None

    def _pack(self, stream):
        pass

    def _unpack(self, stream):
        pass

    def getval(self):
        message_parent = self._parent._parent
        target_field = message_parent.lookup_field_by_name(
                            self.parent_field_name)
        return target_field.getval()

    def setval(self, value):
        return self.parent_field.setval(value)


class BaseFixedByteSequence(BaseField):
    """Base fixed-length byte sequence field"""

    def __init__(self, make_format, size, **kwargs):
        BaseField.__init__(self, **kwargs)
        self.size = size
        self.format = make_format(size)

    def _pack(self, stream):
        stream.write(struct.pack(self.format, *self._value))

    def _unpack(self, stream):
        self._value = struct.unpack(self.format, stream.read(self.size))


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
    definining ``FORMAT`` at the class level.  ``FORMAT`` is expected to
    be a format string that could be used with struct.pack/unpack.  It
    should include endianess information.  If the ``FORMAT`` includes
    multiple elements, the default ``_unpack`` logic assumes that each
    element is a single byte and will OR these together.  To specialize
    this, _unpack should be overriden.

    """

    def __init__(self, **kwargs):
        BaseField.__init__(self, **kwargs)
        self._value = None
        self._size = struct.calcsize(self.FORMAT)

    def _pack(self, stream):
        stream.write(struct.pack(self.FORMAT, self._value))

    def _unpack(self, stream):
        value = 0
        data = stream.read(self._size)
        for i, byte in enumerate(reversed(struct.unpack(self.FORMAT, data))):
            value |= (byte << (i * 8))
        self._value = value


#==============================================================================
# Unsigned Big Endian
#==============================================================================
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


#==============================================================================
# Signed Big Endian
#==============================================================================
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


#==============================================================================
# Unsigned Little Endian
#==============================================================================
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


#==============================================================================
# Signed Little Endian
#==============================================================================
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
