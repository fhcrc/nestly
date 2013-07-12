import unittest

from . import test_core, test_scons

def suite():
    suite = unittest.TestSuite()
    for mod in [test_core, test_scons]:
        suite.addTest(mod.suite())
    return suite

suite = suite()
