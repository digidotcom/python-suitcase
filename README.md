Suitcase
========

[![Build Status](https://travis-ci.org/digidotcom/python-suitcase.svg?branch=master)](https://travis-ci.org/digidotcom/python-suitcase)
[![Coverage Status](https://img.shields.io/coveralls/digidotcom/python-suitcase.svg)](https://coveralls.io/r/digidotcom/python-suitcase)
[![Code Climate](https://img.shields.io/codeclimate/github/digidotcom/python-suitcase.svg)](https://codeclimate.com/github/digidotcom/python-suitcase)
[![Latest Version](https://img.shields.io/pypi/v/suitcase.svg)](https://pypi.python.org/pypi/suitcase/)
[![License](https://img.shields.io/badge/license-MPL%202.0-blue.svg)](https://github.com/digidotcom/python-suitcase/blob/master/LICENSE.txt)

Suitcase is a library providing a set of primitives and helpers for
specifying and parsing protocols.  Suitcase provides an internal DSL
(Domain Specific Language) for describing protocol frames.  It seeks
to do for binary protocols what things like
[Django's ORM](https://docs.djangoproject.com/en/1.8/topics/db/models/)
and
[Sqlalchemy's Declarative Syntax](http://docs.sqlalchemy.org/en/latest/orm/tutorial.html#declare-a-mapping)
do for Database ORMs and adopts a similar, class-based syntax.

[View the Full Documentation](https://digidotcom.github.io/python-suitcase)

The original version of suitcase was generously contributed by the
[Digi](http://www.digi.com/)
[Wireless Design Services](http://www.digi.com/wireless-design-services/).
The software is provided as Alpha software and has not undergone
formal testing but does ship with extensive unit testing.

[View the Changelog](https://github.com/digidotcom/python-suitcase/blob/master/CHANGELOG.md)

Example
=======

The following example shows how you would use Suitcase to describe some
of the core network protocols that form the backbone of the internet:

```python
from suitcase.fields import UBInt16, Payload, LengthField, Magic, \
    UBInt8Sequence, DispatchField, DispatchTarget, UBInt8, UBInt32, BitField, BitNum, \
    BitBool
from suitcase.structure import Structure


class TCPFrameHeader(Structure):
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
    # TODO: additional options if data_offset > 5


class UDPFrame(Structure):
    source_port = UBInt16()
    destination_port = UBInt16()
    length = LengthField(UBInt16())
    checksum = UBInt16()
    data = Payload(length)


class IPV4Frame(Structure):
    options = BitField(64,
        version=BitNum(4),
        internet_header_length=BitNum(4),
        differentiated_services_code_point=BitNum(6),
        explicit_congestion_notification=BitNum(2),
        total_length=BitNum(16),
        identification=BitNum(16),
        flags=BitNum(3),
        fragment_offset=BitNum(13),
    )
    time_to_live = UBInt8()
    protocol = DispatchField(UBInt8())
    header_checksum = UBInt16()
    source_ip_address = UBInt32()
    destination_ip_address = UBInt32()
```

From these declarative definitions, you can both create message
instances and pack them or parse bytes (including stream parsing) to
get objects that you can do with as you please.

For more information, including how to use the structures that you
have described, please refer to the
[Full Documentation](https://digidotcom.github.io/python-suitcase).

Design Goals
============

The library seeks to adhere to these core principles:

* Simple Interfaces

  Interfaces to the library should be simple and there should be a
  logical consistency in the library API.  Internally, advanced
  language techniques are used, but the API consumer shouldn't need to
  be aware of these details.

* Declarative Syntax

  Wherever appropriate, the library should seek to provide a syntax
  for specifying protocols that is as declarative as possible.  These
  declarations should be explicit and it should be clear what is being
  declared.

* Informative Error Messages

  When implementing a protocol, you usually don't get it right the
  first time.  The library should use all available information to
  provide information to the API consumer that can help them figure
  out what is going wrong easily.

* Common Use Cases Should Be Easy

  There are certain data types/patterns that are common amongst
  protocols.  The library should include code to help with these cases
  to make the programmer's life easier.

* Less Common Use Cases Should Be Possible

  When there is a protocol that is significantly different than the
  norm, the library should still provide some useful code that can be
  reused.  Some parts of the library might need to be abandoned, but
  the hope would be that one would not need to start from scratch.

License
=======

This software is open-source software. Copyright Digi International, 2015.

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this file,
you can obtain one at http://mozilla.org/MPL/2.0/.
