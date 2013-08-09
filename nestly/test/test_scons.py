import copy
import unittest
import mock

from nestly import scons, Nest

class OutputCopyingMock(mock.MagicMock):
    def __call__(self, *args, **kwargs):
        return copy.deepcopy(super(OutputCopyingMock, self).__call__(*args, **kwargs))

class AddTargetWithEnvTestCase(unittest.TestCase):
    def setUp(self):
        # Default output will a return a reference, which means consecutive
        # calls to .Clone will return references to the same dictionary. Use
        # OutputCopyingMock to avoid clobbering mutation.
        self.env = OutputCopyingMock(['Clone'], name='MockSConsEnvironment')
        self.env.Clone.return_value = {}
        self.func_mock = mock.Mock('__call__', name='func_mock')
        self.func_mock.__name__ = 'func_mock'
        self.n = Nest()
        self.n.add('item', [1, 2])

    def test_basic(self):
        w = scons.SConsWrap(self.n)

        w.add_target_with_env(self.env)(self.func_mock)

        # Clone is be called with no arguments
        self.env.Clone.assert_called_with()

        calls = [mock.call({'item': 1, 'OUTDIR': './1'}, './1', {'item': 1, 'OUTDIR': '1'}),
                 mock.call({'item': 2, 'OUTDIR': './2'}, './2', {'item': 2, 'OUTDIR': '2'})]
        self.func_mock.assert_has_calls(calls)

class CheckpointTestCase(unittest.TestCase):
    def setUp(self):
        self.nest = Nest()
        self.nest.add('list', [[]], create_dir=False)
        self.w = scons.SConsWrap(self.nest)
        self.w.add('level1', xrange(2))
        self.w.add('level2', (1, 2, 3))

    def test_pop_with_name(self):
        w = self.w

        @w.add_target()
        def key_file(outdir, c):
            c['list'].append(c['level2'])
            return True

        @w.add_target()
        def assertion_during(outdir, c):
            self.assertTrue(c['key_file'])
            self.assertTrue('level2' in c)
            return True

        n2 = w.nest
        w.pop('level1')
        n1 = w.nest

        # Want to make sure nested level checkpoints are popped off as well
        self.assertEqual(len(w.checkpoints), 0)
        # Make sure we have the right nest now
        self.assertTrue(self.nest is n1)
        self.assertFalse(self.nest is n2)

        @w.add_target()
        def assertion_after(outdir, c):
            self.assertFalse('key_file' in c)
            self.assertEqual(6, len(c['list']))
            self.assertFalse('level2' in c)

    def test_pop_last(self):
        w = self.w
        w.pop()

        # This time, there should be one checkpoint left
        self.assertEqual(len(w.checkpoints), 1)
        self.assertTrue('level1' in w.checkpoints)

        @w.add_target()
        def assertion_after(outdir, c):
            self.assertFalse('level2' in c)
            self.assertTrue('level1' in c)


def suite():
    suite = unittest.TestSuite()
    for cls in [AddTargetWithEnvTestCase, CheckpointTestCase]:
        suite.addTest(unittest.makeSuite(cls))
    return suite
