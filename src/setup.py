#! /usr/bin/env python

import glob
from distutils.core import setup

setup(name = 'nestly',
      version = '0.1',
      description = 'Nestly is a collection of functions designed to make \
                     running software with combinatorial choices of parameters easier.',
      author = 'Erick Matsen',
      author_email = 'matsen@fhcrc.org',
      package_dir = {'nestly': '.'},
      packages = ['nestly'],
      scripts = glob.glob('scripts/*.py'),
      requires = ['Python (>= 2.7)'],
      )
