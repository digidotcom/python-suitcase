from pacman.fields import BaseField
from itertools import izip
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class Packer(object):

    def __init__(self, ordered_fields):
        self.ordered_fields = ordered_fields
        self.ordered_field_lengths = [len(f) for _n, f in ordered_fields]
        self.total_length = sum(self.ordered_field_lengths)

    def pack(self):
        # use a StringIO with the right length, starting from the beginning
        sio = StringIO()

        for _name, field in self.ordered_fields:
            sio.write(field.pack())
        return sio.getvalue()

    def unpack(self, data):
        if len(data) != self.total_length:
            raise ValueError("Expected data to have length %s, had %s"
                             % (self.total_length, len(data)))
        pos = 0
        fields_with_lengths = izip(self.ordered_fields,
                                   self.ordered_field_lengths)
        for (_name, field), length in fields_with_lengths:
            new_pos = pos + length
            data_seg = data[pos:new_pos]
            pos = new_pos
            field.unpack(data_seg)


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

    def __len__(self):
        return sum(len(f) for _n, f in self)

    def __iter__(self):
        return iter(self._sorted_fields)

    def __repr__(self):
        output = "%s (\n" % self.__class__.__name__
        for field_name, field in self:
            output += "  %s=%s,\n" % (field_name, field)
        output += ")"
        return output

    def unpack(self, data):
        return self._packer.unpack(data)

    def pack(self):
        return self._packer.pack()
