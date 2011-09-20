import unittest

from nestly import core

class NestTestCase(unittest.TestCase):

    def test_basic(self):
        nest = core.Nest()
        nest.add_level("number", (1, 10))
        nest.add_level("name", ("a", "b"))
        expected =  [('1/a', {'name': 'a', 'number': 1}),
                     ('1/b', {'name': 'b', 'number': 1}),
                     ('10/a', {'name': 'a', 'number': 10}),
                     ('10/b', {'name': 'b', 'number': 10})]
        actual = list(nest.iter())
        self.assertEqual(expected, actual)
