#!/usr/bin/env python

import sys, os, collections
sys.path.append(".")
sys.path.append("../..")
from nestly import *

wd = os.getcwd()
indir = os.path.join(wd,"prep/some_phy/")

ctl = collections.OrderedDict({})

# now get all of the starters 
ctl["infile"] = (lambda(c): map(file_nv, collect_globs(indir, ["*"])))

build({"control": ctl, "destdir": "runs"})

