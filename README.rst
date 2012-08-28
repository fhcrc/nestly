======
nestly
======

``nestly`` is a collection of functions designed to ease running software with combinatorial choices of parameters.
It can easily do so for "cartesian products" of parameter choices, but can do much more-- arbitrary "backwards-looking" dependencies can be used.

The vision here is that we take a fixed set of parameters and generate a single type of output for each defined combination, which can then be combined in some way for comparison and retrieval.
We would like to set things up tidily with nested directories for output reflecting nested parameter choices.

The `full documentation`_ is available on Github pages.

Installing
==========


The easiest way is with `pip`_::

    $ pip install nestly

Or, for the latest commit from master::

    $ pip install git+git://github.com/fhcrc/nestly.git@master

Python 2.7 is required.

Introductory example
====================

Imagine you'd like to try all possible combinations of the following:

========== ==============================
Option     Choices
---------- ------------------------------
strategy   approximate, exhaustive
---------- ------------------------------
run_count  10, 100, 1000
---------- ------------------------------
input file any file matching inputs/file*
========== ==============================

For this we can write a little ``make_nest.py``. The guts are::

    nest = Nest()

    nest.add('strategy', ('exhaustive', 'approximate'))
    nest.add('run_count', [10**i for i in xrange(3)])
    nest.add('input_file', glob.glob(os.path.join(input_dir, 'file*')),
            label_func=os.path.basename)

    nest.build('runs')

Running ``make_nest.py``, you get a directory tree like::

  runs
  ├── approximate
  │   ├── 10
  │   │   ├── file1
  │   │   │   └── control.json
  │   │   ├── file2
  │   │       └── control.json
  │   ├── 100
  │   │   ├── file1
  │   │   │   └── control.json
  │   │   ├── file2
  │   │       └── control.json
  │   └── 1000
  │       ├── file1
  │       │   └── control.json
  │       ├── file2
  │           └── control.json
  └── exhaustive
      ├── 10
      │   ├── file1
      │   │   └── control.json
      │   ├── file2
      │       └── control.json
      ├── 100
      │   ├── file1
      │   │   └── control.json
      │   ├── file2
      │       └── control.json
      └── 1000
          ├── file1
          │   └── control.json
          ├── file2
              └── control.json

With the final ``control.json`` reading, for example::

  {
      "input_file": "/Users/cmccoy/Development/nestly/examples/basic_nest/inputs/file3",
      "run_count": "1000",
      "strategy": "exhaustive"
  }

The control files created then serve as inputs to ``nestrun`` for template substition, for example::

  nestrun --save-cmd-file command.sh \
          --template='my_command -s {strategy} --count={run_count} {input_file}' \
          $(find runs -name "control.json")

This command runs ``my_command`` in all of the tip directories with the appropriate values for the parameters.

This was a "cartesian product" example.
The "meal" example in the repository exhibits a setup with more complex dependencies between the nests.

Templates
=========

``nestrun`` takes a template and a list of control.json files with variables to
substitute. By default, substitution is performed using the Python built-in
``str.format`` method. See the `Python Formatter documentation`_ for details on syntax,
and ``examples/jsonrun/do_nestrun.sh`` for an example.

SCons integration
=================

There is also a ``nestly.scons`` module to integrate nestly with the ``make`` replacement SCons_.

License
=======

``nestly`` source code is freely available under the `MIT License`_.

.. _`Python Formatter documentation`: http://docs.python.org/library/string.html#formatstrings
.. _`full documentation`: http://fhcrc.github.com/nestly/
.. _`pip`: http://www.pip-installer.org
.. _Scons: http://scons.org/
.. _`MIT License`: http://www.opensource.org/licenses/mit-license.html
