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

def suite():
    suite = unittest.TestSuite()
    for cls in [AddTargetWithEnvTestCase]:
        suite.addTest(unittest.makeSuite(cls))
    return suite
