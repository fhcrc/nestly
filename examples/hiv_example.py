#!/usr/bin/env python

import sys, os, collections
sys.path.append(".")
sys.path.append("..")
from nestly import *

homedir = "/cs/researcher/matsen/Overbaugh_J/HIV_Data/"
refdir = os.path.join(homedir,"sim/old/clean_fullGenomeLANL/")
fragdir = os.path.join(homedir,"sim/beastly/frags")
corraldir = os.path.join(homedir,"scripts/beast_corral/")

ctl = collections.OrderedDict({})

ctl["beast_template"] = all_choices(file_nv, corraldir, ["hky.coalescent.xml"])

mirror_dir(fragdir, ["is_superinf", "length", "locus"], ctl)

build({"control" : ctl})

