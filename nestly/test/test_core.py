import contextlib
import json
import os
import os.path
import unittest
import tempfile
import shutil

from nestly import core


@contextlib.contextmanager
def tempdir():
    td = tempfile.mkdtemp()
    try:
        yield td
    finally:
        shutil.rmtree(td)

class SimpleNestTestCase(unittest.TestCase):

    def setUp(self):
        nest = core.Nest()
        nest.add_level("number", (1, 10))
        nest.add_level("name", ("a", "b"))
        self.nest = nest
        self.expected =  [('1/a', {'name': 'a', 'number': 1}),
                          ('1/b', {'name': 'b', 'number': 1}),
                          ('10/a', {'name': 'a', 'number': 10}),
                          ('10/b', {'name': 'b', 'number': 10})]

    def test_iter_once(self):
        actual = list(self.nest.iter())
        self.assertEqual(self.expected, actual)

    def test_iter_repeatable(self):
        # Run once
        list(self.nest.iter())
        actual = list(self.nest.iter())
        self.assertEqual(self.expected, actual)

    def test_iter_prefix(self):
        actual = list(self.nest.iter('test2/test'))
        expected = [('test2/test/' + a, b) for a, b in self.expected]
        self.assertEqual(expected, actual)

    def test_build(self):
        with tempdir() as td:
            self.nest.build(td)
            actual = [os.path.join(p, f) for p, d, files in os.walk(td)
                      for f in files]
            expected = {os.path.join(td, a, 'control.json'): b
                        for a, b in self.expected}

            # Test that all controls were created
            self.assertEqual(frozenset(expected.keys()), frozenset(actual))

            for a in actual:
                with open(a) as fp:
                    d = json.load(fp)
                self.assertEqual(expected[a], d)

class IsIterTestCase(unittest.TestCase):

    def test_list(self):
        self.assertTrue(core._is_iter([1, 2, 3]))

    def test_generator(self):
        g = (i for i in xrange(4))
        self.assertTrue(core._is_iter(g))

        # Can't consume
        self.assertEqual([0, 1, 2, 3], list(g))

    def test_non_iterable(self):
        non_iters = [False, True, 9, 4.5, object()]
        for i in non_iters:
            self.assertFalse(core._is_iter(i))
