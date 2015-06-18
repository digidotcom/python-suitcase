# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.

"""Example of UDP protocol datagram parsing with suitcase"""
import unittest

import six
from suitcase.fields import UBInt16, VariableRawPayload, LengthField, Magic, \
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
    data = VariableRawPayload(length)


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


# This may not be fully accurate for ethernet as this is usually at
# a level well below anything Suitcase was designed to handle and there
# are some cases that we just don't handle (like a field being either
# a length of a type byte).
# 
# For instance, we don't allow for the option 802.1q vlan tagging
# which could come after mac_source
class EthernetFrame(Structure):
    preamble_sof = Magic('\xAA' * 8)  # 8 bytes of 10101010
    mac_dest = UBInt8Sequence(6)
    mac_source = UBInt8Sequence(6)
    ethertype = DispatchField(UBInt16())
    payload = DispatchTarget(None, ethertype, {
        0x0800: IPV4Frame,
        #         0x85DD: IPV6Message,
        #         0x0806: ARPMessage,
    })

    checksum = UBInt32()


class TestIPV4Frame(unittest.TestCase):
    def test(self):
        ipv4 = IPV4Frame()
        ipv4.options.version = 0x01
        ipv4.options.internet_header_length = 0
        ipv4.options.differentiated_services_code_point = 0x05
        ipv4.options.explicit_congestion_notification = 0x01
        ipv4.options.total_length = 0x03
        ipv4.options.identification = 0xFEFE
        ipv4.options.flags = 0x01
        ipv4.options.fragment_offset = 0x9F

        ipv4.source_ip_address = 0x91919191
        ipv4.destination_ip_address = 0x88776655

        ipv4.protocol = 0x06
        ipv4.time_to_live = 0x10
        ipv4.header_checksum = 0x90

        packed_value = six.b('\x10\x15\x00\x03\xfe\xfe \x9f\x10\x06\x00\x90\x91\x91\x91\x91\x88wfU')
        ipv4_2 = IPV4Frame()
        ipv4_2.unpack(packed_value)
        self.assertEqual(ipv4_2.options.version, 0x01)
        self.assertEqual(ipv4_2.options.internet_header_length, 0x00)


class TestUDPDatagram(unittest.TestCase):
    def test(self):
        dgram = UDPFrame()
        dgram.source_port = 9101
        dgram.destination_port = 9100
        dgram.checksum = 0x00
        dgram.data = six.b("Hello, UDP World!")
        packed = dgram.pack()
        self.assertEqual(packed,
                         six.b('#\x8d#\x8c\x00\x11\x00\x00Hello, UDP World!'))
        dgram2 = UDPFrame()
        dgram2.unpack(packed)
        self.assertEqual(dgram2.data, six.b("Hello, UDP World!"))


if __name__ == '__main__':
    unittest.main()
