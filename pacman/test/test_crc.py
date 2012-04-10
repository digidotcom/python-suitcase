from pacman.crc import crc16_ccitt, crc32
import unittest


class TestCRC16CCITT(unittest.TestCase):

    def test_hello_world(self):
        crc = crc16_ccitt("Hello, world")
        self.assertEqual(crc, 0x3E99)


class TestCRC32(unittest.TestCase):

    def test_hello_world(self):
        crc = crc32("Hello, world")
        self.assertEqual(crc, 0xE79AA9C2)


if __name__ == '__main__':
    unittest.main()
