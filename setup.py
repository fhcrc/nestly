#!/usr/bin/env python
import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    import distribute_setup
    distribute_setup.use_setuptools()
    from setuptools import setup, find_packages

import nestly

if sys.version_info < (2, 7, 0):
    raise Exception('Python 2.7 is required.')

setup(name='nestly',
      version=nestly.__version__,
      description="""Nestly is a collection of functions designed to make
      running software with combinatorial choices of parameters easier.""",
      author='Erick Matsen',
      author_email='matsen@fhcrc.org',
      url='https://github.com/fhcrc/nestly',
      packages=find_packages(),
      test_suite='nestly.test.suite',
      entry_points={
          'console_scripts': [
              'nestrun = nestly.scripts.nestrun:main',
              'nestagg = nestly.scripts.nestagg:main',
          ]
      },
      tests_require=['mock>=1.0.1'])
