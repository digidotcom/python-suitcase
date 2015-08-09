# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.
import sys
import socket

from six.moves import socketserver
from suitcase.protocol import StreamProtocolHandler
from suitcase.structure import Structure
from suitcase.fields import UBInt16, LengthField, Payload, UBInt8

FRAME_TYPE_ECHO_REQUEST = 0x00
FRAME_TYPE_ECHO_RESPONSE = 0x10


class EchoProtocolFrame(Structure):
    frame_type = UBInt8()
    payload_length = LengthField(UBInt16())
    payload = Payload(payload_length)


class EchoTCPHandler(socketserver.BaseRequestHandler):
    def _frame_received(self, request_frame):
        # frame is an instance of EchoProtocolFrame
        print("Received %r" % request_frame)
        if request_frame.frame_type == FRAME_TYPE_ECHO_REQUEST:
            response = EchoProtocolFrame()
            response.frame_type = FRAME_TYPE_ECHO_RESPONSE
            response.payload = "You sent %r" % request_frame.payload
            self.request.sendall(response.pack())
        else:
            print("Unexpected frame: %r" % request_frame)

    def setup(self):
        self.handler = StreamProtocolHandler(EchoProtocolFrame, self._frame_received)

    def handle(self):
        while True:
            self.handler.feed(self.request.recv(1024))


def client():
    def message_received(frame):
        print(frame)

    s = socket.socket()
    s.connect(('127.0.0.1', 7070))
    proto_handler = StreamProtocolHandler(EchoProtocolFrame, message_received)
    while True:
        input = raw_input("Data to send: ")
        request = EchoProtocolFrame()
        request.frame_type = FRAME_TYPE_ECHO_REQUEST
        request.payload = input
        s.sendall(request.pack())

        # to handle asynchronous messages, this would be done asynchrnonously
        proto_handler.feed(s.recv(1024))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage Client: %s -c" % sys.argv[0])
        print("Usage Server: %s -s" % sys.argv[1])
    if sys.argv[1] == '-c':
        client()
    elif sys.argv[1] == '-s':
        server = socketserver.TCPServer(('0.0.0.0', 7070), EchoTCPHandler)
        server.serve_forever()
