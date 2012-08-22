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

# Items can update the control dictionary
nest.add('run_count', [{'run_count': 10**i, 'function': 'pow'}
                       for i in xrange(3)], update=True)

# label_func is applied to each item create a directory name
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
