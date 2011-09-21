#!/usr/bin/env python

import glob
import os
import os.path
from nestly import Nest

wd = os.getcwd()
input_dir = os.path.join(wd, 'inputs')

nest = Nest()
nest.add_level('strategy', ('exhaustive', 'approximate'))
nest.add_level('run_count', [10**i for i in xrange(3)])
nest.add_level('input_file', glob.glob(os.path.join(input_dir, 'file*')),
        label_func=os.path.basename)

nest.build('runs')
