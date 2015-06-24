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
shared between the client and the server.  For the server portion,
we can use ``SocketServer`` from the standard library in order to
accept connections.  ``Suitcase`` has no special support for any
networking libraries, so you are free to use it with other network
libraries like twisted, gevent, etc. as you please.

.. literalinclude:: ../suitcase/examples/client_server.py
   :language: python
   :lines: 6-
