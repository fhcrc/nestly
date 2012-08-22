#!/usr/bin/env python

import glob
import math
import os
import os.path
from nestly import Nest

wd = os.getcwd()
input_dir = os.path.join(wd, 'inputs')

nest = Nest()

# Simplest case: Levels are added with a name and an iterable
nest.add('strategy', ('exhaustive', 'approximate'))

# Sometimes it's useful to add multiple keys to the nest in one operation, e.g.
# for grouping related data.
# This can be done by passing an iterable of dictionaries to the `Nest.add` call,
# each containing at least the named key, along with the `update=True` flag.
#
# Here, 'run_count' is the named key, and will be used to create a directory in the nest,
# and the value of 'power' will be added to each control dictionary as well.
nest.add('run_count', [{'run_count': 10**i, 'power': i}
                       for i in xrange(3)], update=True)

# label_func can be used to generate a meaningful name. Here, it strips the all
# but the file name from the file path
nest.add('input_file', glob.glob(os.path.join(input_dir, 'file*')),
        label_func=os.path.basename)

# Items can be added that don't generate directories
nest.add('base_dir', [os.getcwd()], create_dir=False)

# Any function taking one argument (control dictionary) and returning an
# iterable may also be used.
# This one just takes the logarithm of 'run_count'.
# Since the function only returns a single result, we don't create a new directory.
def log_run_count(c):
    run_count = c['run_count']
    return [math.log(run_count, 10)]
nest.add('run_count_log', log_run_count, create_dir=False)

nest.build('runs')
