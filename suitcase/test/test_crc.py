# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015 Digi International Inc. All Rights Reserved.

import unittest

from suitcase.crc import crc16_ccitt, crc32, crc16_kermit


class TestCRC16CCITT(unittest.TestCase):
    def test_hello_world(self):
        crc = crc16_ccitt(b"Hello, world")
        self.assertEqual(crc, 0x3E99)


class TestCRC16Kermit(unittest.TestCase):
    def test_hello_world(self):
        crc = crc16_kermit(b"Hello, world")
        self.assertEqual(crc, 0xEB86)


class TestCRC32(unittest.TestCase):
    def test_hello_world(self):
        crc = crc32(b"Hello, world")
        self.assertEqual(crc, 0xE79AA9C2)


if __name__ == '__main__':
    unittest.main()
