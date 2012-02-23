======
nestly
======

Nestly is a collection of functions designed to ease running software with combinatorial choices of parameters.
It can easily do so for "cartesian products" of parameter choices, but can do much more-- arbitrary "backwards-looking" dependencies can be used.

The vision here is that we take a fixed set of parameters and generate a single type of output for each defined combination, which can then be combined in some way for comparison and retrieval.
We would like to set things up tidily with nested directories for output reflecting nested parameter choices.

Imagine you'd like to try all possible variations of the following:

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

  nestrun --dry-run ---save-cmd-file command.sh \
          --template='my_command -s {strategy} --count={run_count} {input_file}' \
          $(find runs -name "control.json")


This was a "cartesian product" example, but the meal example exhibits a more complex setup.

Templates
=========

``nestrun`` takes a template and a list of control.json files with variables to
substitute. By default, substitution is performed using the Python built-in
``str.format`` method. See the `Python documentation`_ for details on syntax,
and ``examples/jsonrun/do_nestrun.sh`` for an example.

.. _`Python Documentation`: http://docs.python.org/library/string.html#formatstrings
