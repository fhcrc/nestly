import contextlib
import json
import os
import os.path
import unittest
import tempfile
import shutil
import warnings

from nestly import core

@contextlib.contextmanager
def tempdir():
    td = tempfile.mkdtemp()
    try:
        yield td
    finally:
        shutil.rmtree(td)

class NestCompareMixIn(object):
    def assertNestsEqual(self, expected, actual):
        self.assertEqual(len(expected), len(actual))
        for (ie, de), (ia, da) in zip(expected, actual):
            self.assertEqual(ie, ia)
            self.assertEqual(de, da)

class SimpleNestTestCase(NestCompareMixIn, unittest.TestCase):

    def setUp(self):
        nest = core.Nest()
        nest.add("number", (1, 10))
        nest.add("name", ("a", "b"))
        self.nest = nest
        self.expected =  [('1/a', {'name': 'a', 'number': 1}),
                          ('1/b', {'name': 'b', 'number': 1}),
                          ('10/a', {'name': 'a', 'number': 10}),
                          ('10/b', {'name': 'b', 'number': 10})]

    def test_iter_once(self):
        actual = list(self.nest.iter())
        self.assertNestsEqual(self.expected, actual)

    def test_iter_repeatable(self):
        # Run once
        list(self.nest.iter())
        actual = list(self.nest.iter())
        self.assertNestsEqual(self.expected, actual)

    def test_iter_prefix(self):
        actual = list(self.nest.iter('test2/test'))
        expected = [('test2/test/' + a, b) for a, b in self.expected]
        self.assertNestsEqual(expected, actual)

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

    def test_stringiter_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.nest.add('string', 'value')
            self.assertEqual(1, len(w))


class TemplateTestCase(NestCompareMixIn, unittest.TestCase):
    """
    Test template substitution
    """
    def test_template(self):
        nest = core.Nest()
        nest.add('number', [1, 2])
        nest.add('dirname', ['number-{number}'], template_subs=True,
                create_dir=False)
        actual = list(nest.iter())
        expected = [('1', {'dirname': 'number-1', 'number': 1}),
                    ('2', {'dirname': 'number-2', 'number': 2})]
        self.assertNestsEqual(expected, actual)


class UpdateTestCase(NestCompareMixIn, unittest.TestCase):

    def test_update(self):
        nest = core.Nest()
        values = [{'number': 1, 'description': 'one'},
                  {'number': 2, 'description': 'two'}]
        nest.add("number", values, update=True)
        actual = list(nest.iter())
        expected = list(zip(('1', '2'), values))
        self.assertNestsEqual(expected, actual)

    def test_update_nokey(self):
        nest = core.Nest()
        self.assertRaises(KeyError, nest.add,
                          "number", [{'description': 'one'}], update=True)

    def test_update_overwrite(self):
        nest = core.Nest(fail_on_clash=True)
        nest.add("description", ['Test'])
        values = [{'number': 1, 'description': 'one'},
                  {'number': 2, 'description': 'two'}]
        self.assertRaises(KeyError, nest.add, "number", values, update=True)


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

class SimpleNestMixin(object):
    """
    Builds a temporary nest
    """
    def setUp(self):
        self.td = tempfile.mkdtemp(prefix='nest')
        n = core.Nest()
        n.add('run_id', (1, 2))
        n.build(self.td)

        self.controls = [os.path.join(p, f)
                         for p, _, files in os.walk(self.td)
                         for f in files if f == 'control.json']

    def tearDown(self):
        shutil.rmtree(self.td)

    def test_preconditions(self):
        self.assertEqual(2, len(self.controls))

class NestMapTestCase(SimpleNestMixin, unittest.TestCase):
    def test_provides_dirs(self):
        actual = sorted(core.nest_map(self.controls, lambda d, c: d))
        expected = sorted(os.path.dirname(f) for f in self.controls)
        self.assertEqual(expected, actual)

    def test_control(self):
        actual = sorted(core.nest_map(self.controls, lambda d, c: c['run_id']))
        expected = [1, 2]
        self.assertEqual(expected, actual)

def suite():
    suite = unittest.TestSuite()
    for cls in [IsIterTestCase,
            NestMapTestCase,
            SimpleNestTestCase,
            TemplateTestCase,
            UpdateTestCase]:
        suite.addTest(unittest.makeSuite(cls))
    return suite
