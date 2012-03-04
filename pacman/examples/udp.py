"""Example of UDP protocol datagram parsing with pacman"""
from pacman.fields import UBInt16, VariableRawPayload, LengthField
from pacman.message import BaseMessage
import unittest


class UDPDatagram(BaseMessage):
    source_port = UBInt16()
    destination_port = UBInt16()
    length = LengthField(UBInt16())
    checksum = UBInt16()
    data = VariableRawPayload(length)


class TestUDPDatagram(unittest.TestCase):

    def test(self):
        dgram = UDPDatagram()
        dgram.source_port = 9101
        dgram.destination_port = 9100
        dgram.checksum = 0x00
        dgram.data = "Hello, UDP World!"
        packed = dgram.pack()
        self.assertEqual(packed,
                         '#\x8d#\x8c\x00\x11\x00\x00Hello, UDP World!')
        dgram2 = UDPDatagram()
        dgram2.unpack(packed)
        self.assertEqual(dgram2.data, "Hello, UDP World!")

if __name__ == '__main__':
    unittest.main()
