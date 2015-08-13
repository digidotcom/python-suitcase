# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.
import binascii
from suitcase.fields import Payload
from suitcase.fields import UBInt16
from suitcase.fields import BitNum
from suitcase.fields import BitBool
from suitcase.fields import BitField
from suitcase.structure import Structure

class DNSMessage(Structure):
    identification = UBInt16()
    fields = BitField(16,
                      is_reply=BitBool(),  # QR
                      opcode=BitNum(4),
                      truncated=BitBool(),
                      recursion_desired=BitBool(),
                      ra=BitBool(),
                      z=BitBool(),
                      non_authenticated_data_acceptable=BitBool(),
                      cd=BitBool(),
                      rcode=BitNum(4),
                  )
    total_questions = UBInt16()
    total_answers_rrs = UBInt16()
    total_authority_rrs = UBInt16()
    total_additional_rrs = UBInt16()
    data = Payload()  # greedy





#
# Parsing Example (Line 40)
#
dns_request_hex = (
    b"28b30100000100000000000004646f63730464696769"
    b"03636f6d0000010001")
dns_request_data = binascii.unhexlify(dns_request_hex)
print(DNSMessage.from_data(dns_request_data))


#
# Packing Example (Line 50)
#
m = DNSMessage()
m.identification = 0x1234
m.fields.is_reply = False
m.fields.opcode = 0
m.fields.truncated = False
m.fields.recursion_desired = True
m.fields.ra = False
m.fields.z = False
m.fields.non_authenticated_data_acceptable = False
m.fields.cd = False
m.fields.rcode = 0
m.total_questions = 1
m.total_answers_rrs = 0
m.total_authority_rrs = 0
m.total_additional_rrs = 0
m.data = b"docs.digi.com\x00\x00\x00\x00"

print(repr(m.pack()))
