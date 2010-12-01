#!/usr/bin/env python

import sys, os, collections, string
sys.path.append(".")
sys.path.append("../..")
from nestly import *

# DESIRED: i'd like for this to be an argument
templ = string.Template("raxmlHPC -m GTRGAMMA -n bla -s $infile")

# DESIRED: I'd like two flags which control the execution
# these two options should be mutually exclusive.
# "--local n" runs the commands with at most n processes at a time (xargs?)
# "--srun" runs the commands through srun on hyrax. 
# in the future, we may want to cap the number of jobs submitted to hyrax, and trickle them out over time.

for fname in sys.argv[1:]:
    d = d_of_jsonfile(fname)
    # DESIRED: chdir to the location of the json file
    print templ.substitute(d)
    # DESIRED: rather than printing this, run the command

