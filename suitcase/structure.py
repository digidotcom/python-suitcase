# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.
import sys

import six
from suitcase.exceptions import SuitcaseException, \
    SuitcasePackException, SuitcaseParseError
from suitcase.fields import FieldPlaceholder, CRCField, SubstructureField
from six import BytesIO


class ParseError(Exception):
    """Exception raied when there is an error parsing"""


class Packer(object):
    """Object responsible for packing/unpacking bytes into/from fields"""

    def __init__(self, ordered_fields, crc_field):
        self.crc_field = crc_field
        self.ordered_fields = ordered_fields

    def pack(self):
        sio = BytesIO()
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
            except SuitcaseException:
                raise  # just reraise the same exception object
            except Exception:
                # keep the original traceback information, see
                # http://stackoverflow.com/questions/3847503/wrapping-exceptions-in-python
                exc_value = SuitcasePackException("Unexpected exception during pack of %r" % name)
                six.reraise(type(exc_value), exc_value, sys.exc_info()[2])

        # if there is a crc value, seek back to the field and
        # pack it with the right value
        if len(crc_fields) > 0:
            data = stream.getvalue()
            for field, offset in crc_fields:
                stream.seek(offset)
                checksum_data = self.crc_field.packed_checksum(data)
                stream.write(checksum_data)

    def unpack(self, data, trailing=False):
        stream = BytesIO(data)
        self.unpack_stream(stream)
        stream.tell()
        if trailing:
            return stream
        elif stream.tell() != len(data):
            raise SuitcaseParseError("Structure fully parsed but additional bytes remained.  Parsing "
                                     "consumed %d of %d bytes" %
                                     (stream.tell(), len(data)))

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
        for i, (name, field) in enumerate(self.ordered_fields):
            if isinstance(field, CRCField):
                crc_fields.append((field, stream.tell()))
            length = field.bytes_required
            if isinstance(field, SubstructureField):
                remaining_data = stream.getvalue()[stream.tell():]
                returned_stream = field.unpack(remaining_data, trailing=True)
                # We need to fast forward by as much as was consumed by the structure
                stream.seek(stream.tell() + returned_stream.tell())
                continue
            elif length is None:
                greedy_field = field
                break
            else:
                data = stream.read(length)
                if len(data) != length:
                    raise SuitcaseParseError("While attempting to parse field "
                                             "%r we tried to read %s bytes but "
                                             "we were only able to read %s." %
                                             (name, length, len(data)))

            try:
                field.unpack(data)
            except SuitcaseException:
                raise  # just re-raise these
            except Exception:
                exc_value = SuitcaseParseError("Unexpected exception while unpacking field %r" % name)
                six.reraise(type(exc_value), exc_value, sys.exc_info()[2])

        if greedy_field is not None:
            remaining_data = stream.read()
            inverted_stream = BytesIO(remaining_data[::-1])

            # work through the remaining fields in reverse order in order
            # to narrow in on the right bytes for the greedy field
            reversed_remaining_fields = self.ordered_fields[(i + 1):][::-1]
            for _name, field in reversed_remaining_fields:
                if isinstance(field, CRCField):
                    crc_fields.append(
                        (field, -inverted_stream.tell() - field.bytes_required))
                length = field.bytes_required
                data = inverted_stream.read(length)[::-1]
                if len(data) != length:
                    raise SuitcaseParseError("While attempting to parse field "
                                             "%r we tried to read %s bytes but "
                                             "we were only able to read %s." %
                                             (name, length, len(data)))
                try:
                    field.unpack(data)
                except SuitcaseException:
                    raise  # just re-raise these
                except Exception:
                    exc_value = SuitcaseParseError("Unexpected exception while unpacking field %r" % name)
                    six.reraise(type(exc_value), exc_value, sys.exc_info()[2])

            greedy_data_chunk = inverted_stream.read()[::-1]
            greedy_field.unpack(greedy_data_chunk)

        if crc_fields:
            data = stream.getvalue()
            for (crc_field, offset) in crc_fields:
                crc_field.validate(data, offset)


class StructureMeta(type):
    """Metaclass for all structure objects

    When a class with this metaclass is created, we look for any
    FieldProperty instances associated with the class and record
    those for use later on.

    """

    def __new__(cls, name, bases, dct):
        #  find all the placeholders in this class declaration and store
        # them away.  Add name mangling to the original fields so they
        # do not get in the way.
        dct['_field_placeholders'] = {}
        dct['_crc_field'] = None
        for key, value in list(dct.items()):  # use a copy, we mutate dct
            if isinstance(value, FieldPlaceholder):
                dct['_field_placeholders'][key] = value
                dct['__%s' % key] = value
                del dct[key]
                if value.cls == CRCField:
                    dct['_crc_field'] = value

        sorted_fields = list(sorted(dct['_field_placeholders'].items(),
                                    key=lambda kv: kv[1]._field_seqno))
        dct['_sorted_fields'] = sorted_fields
        return type.__new__(cls, name, bases, dct)


@six.add_metaclass(StructureMeta)
class Structure(object):
    r"""Base class for message schema declaration

    ``Structure`` forms the core of the Suitcase library and allows for
    a declarative syntax for specifying packet schemas and associated
    methods for transforming these schemas into packed bytes (and vice-versa).

    Here's an example showing how one might specify the format for a UDP
    Datagram::


        >>> from suitcase.fields import UBInt16, LengthField, VariableRawPayload
        >>> class UDPDatagram(Structure):
        ...     source_port = UBInt16()
        ...     destination_port = UBInt16()
        ...     length = LengthField(UBInt16())
        ...     checksum = UBInt16()
        ...     data = VariableRawPayload(length)

    From this we have a near-ideal form for packing and parsing packet
    data following the schema::

        >>> def printb(s):
        ...     print(repr(s).replace("b'", "'").replace("u'", "'"))
        ...
        >>> dgram = UDPDatagram()
        >>> dgram.source_port = 9110
        >>> dgram.destination_port = 1001
        >>> dgram.checksum = 27193
        >>> dgram.data = b"Hello, world!"
        >>> printb(dgram.pack())
        '#\x96\x03\xe9\x00\rj9Hello, world!'
        >>> dgram2 = UDPDatagram()
        >>> dgram2.unpack(dgram.pack())
        >>> dgram2
        UDPDatagram (
          source_port=9110,
          destination_port=1001,
          length=13,
          checksum=27193,
          data=...'Hello, world!',
        )

    """

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

    def unpack(self, data, trailing=False):
        return self._packer.unpack(data, trailing)

    def pack(self):
        return self._packer.pack()
