"""Define protocol handlers for different classes of protocols

These protocols all wrap some base message schema and provide
all the necessary hooks for pushing in a stream of bytes and
getting out packets in the order they were found.  The protocol
handlers will also provide notifications of error conditions
(for instance, unexpected bytes or a bad checksum)

"""
from pacman.fields import Magic
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class StreamProtocolHandler(object):

    def __init__(self, message_schema, packet_callback,
                 checksum_handler=None):
        # configuration parameters
        self.message_schema = message_schema
        self.packet_callback = packet_callback
        self.checksum_handler = checksum_handler

        # internal state
        self._available_bytes = ""
        self._packet_generator = self._create_packet_generator()
        self._stream = StringIO()

    def _create_packet_generator(self):
        while True:
            curmsg = self.message_schema()
            for i, field in enumerate(curmsg):
                bytes_required = field.bytes_required

                # if the first byte is magic, go with a scanning behavior
                # where we just chop off one byte at a time
                if i == 0 and isinstance(i, Magic):
                    magic_seq = field.getval()
                    while True:
                        idx = self._available_bytes.find(magic_seq)
                        if idx == -1:  # no match in buffer
                            self._available_bytes = ""
                            yield None
                        else:
                            self._available_bytes = self._available_bytes[idx:]
                            break  # continue processing

                # For a specific field, read until we have enough bytes
                # and then give the field a try.
                while True:
                    bytes_available = len(self._available_bytes)
                    if bytes_required <= bytes_available:
                        field_bytes = self._available_bytes[:bytes_required]
                        new_avail_bytes = self._available_bytes[bytes_required:]
                        self._available_bytes = new_avail_bytes
                        field.unpack(field_bytes)
                    else:
                        yield None
            yield curmsg

    def feed(self, new_bytes):
        assert isinstance(bytes, str)
        self._available_bytes += new_bytes
        bytes_available = len(self._available_bytes)
        try:
            while True:
                packet = self._packet_generator.next()
                if packet is None:
                    break
                else:
                    self.packet_callback(packet)
        except Exception, e:
            # When we receive an exception, we assume that the _available_bytes
            # has already been updated and we just choked on a field.  That
            # is, unless the number of _available_bytes has not changed.  In
            # that case, we reset the buffered entirely
            self._packet_generator = self._create_packet_generator()
            if len(self._available_bytes) == bytes_available:
                self.reset()

    def reset(self):
        self._packet_generator = self._create_packet_generator()
        self._available_bytes = ""
