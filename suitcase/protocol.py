# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.

"""Define protocol handlers for different classes of protocols

These protocols all wrap some base message schema and provide
all the necessary hooks for pushing in a stream of bytes and
getting out packets in the order they were found.  The protocol
handlers will also provide notifications of error conditions
(for instance, unexpected bytes or a bad checksum)

"""
from functools import partial

import six
from suitcase.fields import Magic


class StreamProtocolHandler(object):
    """Protocol handler that deals fluidly with a stream of bytes

    The protocol handler is agnostic to the data source or methodology
    being used to collect the data  (blocking reads on a socket to async
    IO on a serial port).

    Here's an example of what one usage might look like (very simple
    appraoch for parsing a simple tcp protocol::


        from suitcase.protocol import StreamProtocolHandler
        from suitcase.fields import LengthField, UBInt16, VariableRawPayload
        from suitcase.struct import Structure
        import socket

        class SimpleFramedMessage(Structure):
            length = LengthField(UBInt16())
            payload = VariableRawPayload(length)

        def packet_received(packet):
            print(packet)

        def run_forever(host, port):
            protocol_handler = StreamProtocolHandler(SimpleFramedMessage,
                                                     packet_received)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(host, port)
            sock.setblocking(1)
            while True:
                bytes = sock.recv(1024)
                if len(bytes) == 0:
                    print("Socket closed... exiting")
                    return
                else:
                    protocol_handler.feed(bytes)

    :param message_schema: The top-level message schema that defines the
        packets for the protocol to be used.
    :param packet_callback: A callback to be executed with the form
        ``callback(packet)`` when a fully-formed packet is detected.

    """

    def __init__(self, message_schema, packet_callback):
        # configuration parameters
        self.message_schema = message_schema
        self.packet_callback = packet_callback

        # internal state
        self._available_bytes = b""
        self._packet_generator = self._create_packet_generator()

    def _create_packet_generator(self):
        while True:
            curmsg = self.message_schema()
            for i, (_name, field) in enumerate(curmsg):
                bytes_required = field.bytes_required

                if i == 0 and isinstance(field, Magic):
                    magic_seq = field.getval()
                    while True:
                        if len(self._available_bytes) < bytes_required:
                            yield None
                            continue

                        idx = self._available_bytes.find(magic_seq)
                        if idx == -1:  # no match in buffer
                            # Since we know the entire magic_seq is not here, there can be at most
                            # bytes_required - 1 bytes of the magic_seq available.  Thus we keep
                            # that many bytes around in case it is the start of the magic field.
                            self._available_bytes = self._available_bytes[-(bytes_required - 1):]
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
                        new_bytes = self._available_bytes[bytes_required:]
                        self._available_bytes = new_bytes
                        field.unpack(field_bytes)
                        break
                    else:
                        yield None
            yield curmsg

    def feed(self, new_bytes):
        """Feed a new set of bytes into the protocol handler

        These bytes will be immediately fed into the parsing state machine and
        if new packets are found, the ``packet_callback`` will be executed
        with the fully-formed message.

        :param new_bytes: The new bytes to be fed into the stream protocol
            handler.

        """
        self._available_bytes += new_bytes
        callbacks = []
        try:
            while True:
                packet = six.next(self._packet_generator)
                if packet is None:
                    break
                else:
                    callbacks.append(partial(self.packet_callback, packet))
        except Exception:
            # When we receive an exception, we assume that the _available_bytes
            # has already been updated and we just choked on a field.  That
            # is, unless the number of _available_bytes has not changed.  In
            # that case, we reset the buffered entirely

            # TODO: black hole may not be the best.  What should the logging
            # behavior be?
            self.reset()

        # callbacks are partials that are boudn to packet already.  We do
        # this in order to separate out parsing activity (and error handling)
        # from the execution of callbacks.  Callbacks should not in any way
        # rely on the parsers position in the byte stream.
        for callback in callbacks:
            callback()

    def reset(self):
        """Reset the internal state machine to a fresh state

        If the protocol in use does not properly handle cases of possible
        desycnronization it might be necessary to issue a reset if bytes
        are being received but no packets are coming out of the state
        machine.  A reset is issue internally whenever an unexpected exception
        is encountered while processing bytes from the stream.

        """
        self._packet_generator = self._create_packet_generator()
        self._available_bytes = b""
