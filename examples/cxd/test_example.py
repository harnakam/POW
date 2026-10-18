import unittest

from example import greet


class ExampleTests(unittest.TestCase):
    def test_greeting(self):
        self.assertEqual(greet('POW'), 'Hello, POW!')

    def test_unicode_name(self):
        self.assertEqual(greet('世界'), 'Hello, 世界!')


if __name__ == '__main__':
    unittest.main()
