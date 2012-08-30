#!/usr/bin/env python

# This example compares runtimes of two implementations of
# an algorithm to minimize the average distance to the closest leaf
# (Matsen et. al., accepted to Systematic Biology).
#
# To run it, you'll need the `rppr` binary on your path, distributed as part of
# the pplacer suite. Source code, or binaries for OS X and 64-bit Linux are
# available from http://matsen.fhcrc.org/pplacer/.
#
# The `rppr min_adcl_tree` subcommand takes a tree, an algorithm name, and
# the number of leaves to keep.
#
# We wish to explore the runtime, over each tree, for various leaf counts.

import glob
from os.path import abspath

from nestly import Nest, stripext

# The `trees` directory contains 5 trees, each with 1000 leaves.
# We want to run each algorithm on all of them.
trees = [abspath(f) for f in glob.glob('trees/*.tre')]

n = Nest()

# We'll try both algorithms
n.add('algorithm', ['full', 'pam'])
# For every tree
n.add('tree', trees, label_func=stripext)

# Store the number of leaves - always 1000 here
n.add('n_leaves', [1000], create_dir=False)

# Now we vary the number of leaves to keep (k)
# Sample between 1 and the total number of leaves.
def k(c):
    n_leaves = c['n_leaves']
    return range(1, n_leaves, n_leaves // 10)

n.add('k', k)

n.build('runs')
