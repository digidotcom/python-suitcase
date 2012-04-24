from pacman.fields import FieldPlaceholder, CRCField
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class ParseError(Exception):
    """Exception raied when there is an error parsing"""


class CRCError(ParseError):
    """ParseError raised when a CRC doesn't match expected value"""


class Packer(object):
    """Object responsible for packing/unpacking bytes into/from fields"""

    def __init__(self, ordered_fields, crc_field):
        self.crc_field = crc_field
        self.ordered_fields = ordered_fields

    def pack(self):
        sio = StringIO()
        self.write(sio)
        return sio.getvalue()

    def write(self, stream):
        # now, pack everything in
        crc_fields = []
        for name, field in self.ordered_fields:
            try:
                if isinstance(field, CRCField):
                    crc_offset = stream.tell()
                    field.pack(stream)
                    crc_fields.append((field, crc_offset))
                else:
                    field.pack(stream)
            except:
                # TODO: don't just print... give a better exception in some
                # way, shape, or form.
                print ("Error packing field '%s' with type %s" %
                       (name, type(field)))
                raise

        # if there is a crc value, seek back to the field and
        # pack it with the right value
        if len(crc_fields) > 0:
            data = stream.getvalue()
            for field, offset in crc_fields:
                stream.seek(offset)
                checksum_data = self.crc_field.packed_checksum(data)
                stream.write(checksum_data)

    def unpack(self, data):
        self.unpack_stream(StringIO(data))

    def unpack_stream(self, stream):
        """Unpack bytes from a stream of data field-by-field

        In the most basic case, the basic algorithm here is as follows::

            for _name, field in self.ordered_fields:
               length = field.bytes_required
               data = stream.read(length)
               field.unpack(data)

        This logic is complicated somewhat by the handling of variable length
        greedy fields (there may only be one).  The logic when we see a
        greedy field (bytes_required returns None) in the stream is to
        pivot and parse the remaining fields starting from the last and
        moving through the stream backwards.  There is also some special
        logic present for dealing with checksum fields.

        """
        crc_fields = []
        greedy_field = None
        # go through the fields from first to last.  If we hit a greedy
        # field, break out of the loop
        for i, (_name, field) in enumerate(self.ordered_fields):
            if isinstance(field, CRCField):
                crc_fields.append(field)
            length = field.bytes_required
            if length is None:
                greedy_field = field
                break
            else:
                data = stream.read(length)
            field.unpack(data)

        if greedy_field is not None:
            remaining_data = stream.read()
            inverted_stream = StringIO(remaining_data[::-1])

            # work through the remaining fields in reverse order in order
            # to narrow in on the right bytes for the greedy field
            reversed_remaining_fields = self.ordered_fields[(i + 1):][::-1]
            for _name, field in reversed_remaining_fields:
                print _name, field
                if isinstance(field, CRCField):
                    crc_fields.append(field)
                length = field.bytes_required
                data = inverted_stream.read(length)[::-1]
                field.unpack(data)

            greedy_data_chunk = inverted_stream.read()[::-1]
            greedy_field.unpack(greedy_data_chunk)

        if len(crc_fields) > 0:
            data = stream.getvalue()
            for crc_field in crc_fields:
                if not crc_field.is_valid(data):
                    raise CRCError()


class MessageMeta(type):
    """Metaclass for all message objects

    When a class with this metaclass is created, we look for any
    FieldPrpoerty instances associated with the class and record
    those for use later on.

    """

    def __new__(cls, name, bases, dct):
        #  find all the placeholders in this class declaration and store
        # them away.  Add name mangling to the original fields so they
        # do not get in the way.
        dct['_field_placeholders'] = {}
        dct['_crc_field'] = None
        for key, value in dct.items():  # use a copy, we mutate dct
            if isinstance(value, FieldPlaceholder):
                dct['_field_placeholders'][key] = value
                dct['__%s' % key] = value
                del dct[key]
                if value.cls == CRCField:
                    dct['_crc_field'] = value

        sorted_fields = list(sorted(dct['_field_placeholders'].items(),
                                    key=lambda (k, v): v._field_seqno))
        dct['_sorted_fields'] = sorted_fields
        return type.__new__(cls, name, bases, dct)


class BaseMessage(object):
    r"""Base class for message schema declaration

    ``BaseMessage`` forms the core of the Pacman library and allows for
    a declarative syntax for specifying packet schemas and associated
    methods for transforming these schemas into packed bytes (and vice-versa).

    Here's an example showing how one might specify the format for a UDP
    Datagram::


        class UDPDatagram(BaseMessage):
            source_port = UBInt16()
            destination_port = UBInt16()
            length = LengthField(UBInt16())
            checksum = UBInt16()
            data = VariableRawPayload(length)

    From this we have a near-ideal form for packing and parsing packet
    data following the schema::

        >>> dgram = UDPDatagram()
        >>> dgram.source_port = 9110
        >>> dgram.destination_port = 1001
        >>> dgram.checksum = 27193
        >>> dgram.data = "Hello, world!"
        >>> dgram.pack()
        '#\x96\x03\xe9\x00\rj9Hello, world!'
        >>> dgram2 = UDPDatagram()
        >>> dgram2.unpack(dgram.pack())
        >>> print dgram2
        UDPDatagram (
          source_port=9110,
          destination_port=1001,
          length=13,
          checksum=27193,
          data='Hello, world!',
        )

    """

    __metaclass__ = MessageMeta

    @classmethod
    def from_data(cls, data):
        """Create a new, populated message from some data

        This factory method is identical to doing the following, it just takes
        one line instead of two and looks nicer in general::

            m = MyMessage()
            m.unpack(data)

        Can be rewritten as just::

            m = MyMessage.from_data(data)

        """
        m = cls()
        m.unpack(data)
        return m

    def __init__(self):
        self._key_to_field = {}
        self._parent = None
        self._sorted_fields = []
        self._placeholder_to_field = {}
        if self.__class__._crc_field is None:
            self._crc_field = None
        else:
            self._crc_field = self.__class__._crc_field.create_instance(self)
        for key, field_placeholder in self.__class__._sorted_fields:
            field = field_placeholder.create_instance(self)
            self._key_to_field[key] = field
            self._placeholder_to_field[field_placeholder] = field
            self._sorted_fields.append((key, field))
        self._packer = Packer(self._sorted_fields, self._crc_field)

    def __getattr__(self, key):
        k2f = self.__dict__.get('_key_to_field', {})
        if key in k2f:
            field = self._key_to_field[key]
            return field.getval()
        raise AttributeError

    def __setattr__(self, key, value):
        k2f = self.__dict__.get('_key_to_field', {})
        if key in k2f:
            field = self._key_to_field[key]
            return field.setval(value)
        return object.__setattr__(self, key, value)

    def __iter__(self):
        return iter(self._sorted_fields)

    def __repr__(self):
        output = "%s (\n" % self.__class__.__name__
        for field_name, field in self:
            output += "  %s=%s,\n" % (field_name, field)
        output += ")"
        return output

    def lookup_field_by_name(self, name):
        for fname, field in self:
            if name == fname:
                return field
        raise KeyError

    def lookup_field_by_placeholder(self, placeholder):
        return self._placeholder_to_field[placeholder]

    def unpack(self, data):
        return self._packer.unpack(data)

    def pack(self):
        return self._packer.pack()
