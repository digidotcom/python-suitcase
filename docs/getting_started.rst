Getting Started
===============

Installation
------------

Suitcase may be installed directly from `PyPi
<https://pypi.python.org/pypi/suitcase>`_ using `pip
<https://pip.pypa.io/en/stable/>`_::

    pip install suitcase

This will install the library as well as any libraries depended on
by Suitcase.

The library is tested to work on the following python versions:

* Python 2.7
* Python 3.2
* Python 3.3
* Python 3.4

Data Modeling
-------------

Suitcase provides a declarative syntax for recording the structure of
the messages in your problem domain.  The first step is to understand
those messages and convert each message layer into its corresponding
:class:`suitcase.structure.Structure` s and
:class:`suitcase.fields.BaseField` s.

Typically, you will end up with one structure for each layer of a
protocol stack, if that is your domain.  For instance, let's say that
we wanted to parser and/or pack `DNS messsages
<https://en.wikipedia.org/wiki/Domain_Name_System#DNS_message_format>`_.

With just a little reading, we see that each DNS request and response
has a common form which can be declared in Suitcase with the following
structure:

.. literalinclude:: ../suitcase/examples/dns.py
   :language: python
   :lines: 6-35

Although there is a fair bit here, you can see that it is generally
easy to follow and about as simple as the table you can find on the
Wikipedia page describing the same message.

.. note::

   This example is based on a quick review of the DNS message format
   and may not be correct.  Please create a github issue if you
   believe there is a problem with this example.

Using the Model
---------------

The structure above provides Suitcase with a wealth of information
about the names, sizes, order, and relationship between different
elements in a `DNSMessage`.  That knowledge is enough so that Suitcase
can now both pack (generate bytes from and object) and parse (generate
an object from bytes) for our message.

Parsing
^^^^^^^

For some input data, I opened up wireshark and then navigated to
`docs.digi.com <https://docs.digi.com>`_ in my web browser.  Looking
through wireshark, I can see the request and copy the hex for the DNS
portion of the message:

.. literalinclude:: ../suitcase/examples/dns.py
   :language: python
   :lines: 40-45

This generates the following based on the repr of the returned instance
of our structure::

   DNSMessage (
     identification=10419,
     fields=BitField(
       is_reply=False,
       opcode=0,
       truncated=False,
       recursion_desired=False,
       ra=True,
       z=False,
       non_authenticated_data_acceptable=False,
       cd=False,
       rcode=0,
     ),
     total_questions=1,
     total_answers_rrs=0,
     total_authority_rrs=0,
     total_additional_rrs=0,
     data='\x04docs\x04digi\x03com\x00\x00\x01\x00\x01',
   )

Packing
^^^^^^^

In the same way that a stream of bytes can be used to populate an instance of our
structure, we can also build up a `DNSMessage` and turn it into bytes.  This
is a little tedious since `DNSMessage` has quite a few fields, but it is
very easy to see what is going on.

.. literalinclude:: ../suitcase/examples/dns.py
   :language: python
   :lines: 50-

This generates a string like this::

    '\x124\x02\x00\x00\x01\x00\x00\x00\x00\x00\x00docs.digi.com\x00\x00\x00\x00'

Working With Streams
--------------------

In addition to being able to parse and pack messages, Suitcase also includes
helpers that make working with stream-based protocols (e.g. TCP, Serial Port, etc.)
much easier.  See the API documentation for more details.
