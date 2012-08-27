import unittest

from . import test_core

def suite():
    suite = unittest.TestSuite()
    for mod in [test_core]:
        suite.addTest(unittest.findTestCases(mod))
    return suite

suite = suite()
