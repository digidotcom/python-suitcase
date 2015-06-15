Suitcase
========

Suitcase is a library providing a set of primitives and helpers for
specifying and parsing protocols.  Suitcase provides an internal DSL
(Domain Specific Language) for describing protocol frames.  It seeks
to do for binary protocols what things like
`Django's ORM <https://docs.djangoproject.com/en/1.8/topics/db/models/>`_
and
`Sqlalchemy's Declarative Syntax
<http://docs.sqlalchemy.org/en/latest/orm/tutorial.html#declare-a-mapping>`_
do for Database ORMs and adopts a similar, class-based syntax.

.. toctree::
   :maxdepth: 2

   examples
   api

Example: Packetized TCP Server and Client
-----------------------------------------

The following example shows an example of a protocol on TCP which has
a length field and a payload of ``length`` bytes.  With suitcase, we
only need to declare the basic structure of the message and we get a
packer and a stream protocol handler out of the library with very
little effort.

Since the protocol definition is declarative, it is easy to see what
the structure of packets is.   The definition of the protocol is
shared between the client and the server::

    from suitcase.structure import Structure
    from suitcase.fields import UBInt16, LengthField, Payload, UBInt8

    FRAME_TYPE_ECHO_REQUEST = 0x00
    FRAME_TYPE_ECHO_RESPONSE = 0x10

    class EchoProtocolFrame(Structure):
        frame_type = UBInt8()
        payload_length = LengthField(UBInt16())
        payload = Payload(payload_length)

For the server portion, we can use ``SocketServer`` from the standard library
in order to accept connections.  ``Suitcase`` has no special support for any
networking libraries, so you are free to use it with other network libraries
like twisted, gevent, etc. as you please::

    class EchoTCPHandler(SocketServer.BaseRequestHandler):

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

    def run_server():
        server = SocketServer.TCPServer(('0.0.0.0', 7070), EchoTCPHandler)
        server.serve_forever()

And a simple client and runner::

    def client():
        def message_received(frame):
            print frame

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
            print "Usage Client: %s -c" % sys.argv[0]
            print "Usage Server: %s -s" % sys.argv[1]
        if sys.argv[1] == '-c':
            client()
        elif sys.argv[1] == '-s':
            run_server()
