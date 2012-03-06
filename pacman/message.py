from pacman.fields import BaseField, DependentField
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class Packer(object):
    """Object responsible for packing/unpacking bytes into/from fields"""

    def __init__(self, ordered_fields, relationships=()):
        self.ordered_fields = ordered_fields

    def pack(self):
        sio = StringIO()
        self.write(sio)
        return sio.getvalue()

    def write(self, stream):
        # now, pack everything in
        for _name, field in self.ordered_fields:
            field._pack(stream)

    def unpack(self, data):
        self.unpack_stream(StringIO(data))

    def unpack_stream(self, stream):
        # sanity checks
        # if len(stream) < self.minimum_length:
        #     raise ValueError("Expected data to have at least length %s, had %s"
        #                      % (self.total_length, len(data)))
        for _name, field in self.ordered_fields:
            field._unpack(stream)


class MessageMeta(type):

    def __new__(cls, name, bases, dct):
        cls._fields = {}
        for key, value in dct.iteritems():  # use a copy, we mutate dct
            if isinstance(value, BaseField):
                cls._fields[key] = value

        sorted_fields = list(sorted(cls._fields.items(),
                                    key=lambda (k, v): v._field_seqno))
        dct['_sorted_fields'] = sorted_fields

        # create a "packer" object for the message.  This is allows us
        # to take advantage of optimizations from stringing fields
        # together at class creation time.  It also prevents us from
        # having to do extra work at runtime on data that is only
        # modified once (at class creation time)
        dct['_packer'] = Packer(sorted_fields)

        return type.__new__(cls, name, bases, dct)


class BaseMessage(object):

    __metaclass__ = MessageMeta

    def __init__(self):
        self._parent = None
        for _key, field in self._sorted_fields:
            field._associate_parent(self)

    def _associate_parent(self, parent):
        self._parent = parent

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

    def unpack(self, data):
        return self._packer.unpack(data)

    def pack(self):
        return self._packer.pack()
