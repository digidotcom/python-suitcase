Getting Started
===============

Introduction
------------
This brief document seeks to provide the guidance needed to start
using the pacman package.  In brief, this
document should provide information on the following items:

* How to get the source code
* How to get the dependencies
* A simple example of how to use the package

Getting the Code
----------------
This should do it::

    $ hg clone https://spectrum.kilnhg.com/Code/Spectrum-Python/Libraries/Pacman

Getting the Dependencies
------------------------
This project uses zc.buildout for dependency management and basic task
automation.  The Spectrum pypi server is used to get accessed to shared
libraries, of which the project makes use wherever possible.  With
the project source code checked out, you should just need to do the
following to setup a basic environment with all dependencies::

    $ python bootstrap.py
    $ bin/buildout

Using the Package
-----------------

Pacman is meant to be used with other projects.  To include it with
your other digi projects simply add pacman under the eggs in your
buildout.cfg 

To start using it you can declare your Messages.

Example Usage::

        class TCPFrameHeader(BaseMessage):
            source_address = UBInt16()
            destination_address = UBInt16()
            sequence_number = UBInt32()
            acknowledgement_number = UBInt32()
            options = BitField(16,
                data_offset=BitNum(4),
                reserved=BitNum(3),
                NS=BitBool(),
                CWR=BitBool(),
                ECE=BitBool(),
                URG=BitBool(),
                ACK=BitBool(),
                PSH=BitBool(),
                RST=BitBool(),
                SYN=BitBool(),
                FIN=BitBool()
            )
            window_size = UBInt16()
            checksum = UBInt16()
            urgent_pointer = UBInt16()


You can then use the ``pack()`` function to convert the message down to the bit 
stream.::

    tcp_packet = TCPFrameHeader()
    tcp_packet.source_address = 0x1111
    o = tcp_packet.options
    o.data_offset = 3
    o.NS = True
    o.CWR = False
    # ... Continue filling in all appropriate fields
    
    out_data = tcp_packet.pack() 

Or conversely from a string of bits use the ``from_data(data)`` method to 
go from bits to method object.::

    tcp_packet = TCPFrameHeader.from_data(input_data)
    
    if tcp_packet.checksum != calc_checksum(input_data):
        raise ChecksumError()
    # ... Continue handling message     
    
