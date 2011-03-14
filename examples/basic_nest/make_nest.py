#!/usr/bin/env python

import collections
import os
import os.path
import sys
from nestly import nestly

wd = os.getcwd()
input_dir = os.path.join(wd, 'inputs')

ctl = collections.OrderedDict()

def value_range(iterable):
    def inner(ctl):
        for i in iterable:
            val = str(i)
            yield (val, val)
    return inner

ctl['strategy'] = value_range(('exhaustive', 'approximate'))
ctl['run_count'] = value_range([10**(i + 1) for i in xrange(3)])
ctl['input_file'] = lambda x: map(nestly.file_nv, nestly.collect_globs(input_dir, ['file*']))

nestly.build(ctl, 'runs')
