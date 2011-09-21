#! /usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    import distribute_setup
    distribute_setup.use_setuptools()
    from setuptools import setup, find_packages


setup(name = 'nestly',
      version = '0.2',
      description = 'Nestly is a collection of functions designed to make \
                     running software with combinatorial choices of parameters easier.',
      author = 'Erick Matsen',
      author_email = 'matsen@fhcrc.org',
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'nestrun = nestly.scripts.nestrun:main'
          ]
      },
      #install_requires=['argparse'],
      )
