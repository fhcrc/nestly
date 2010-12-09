#######!/usr/bin/env python

import sys, os, collections, json
#sys.path.append(".")
#sys.path.append("../..")
from nestly.nestly import *

wd = os.getcwd()
startersdir = os.path.join(wd,"starters/")
winedir = os.path.join(wd,"wine/")
mainsdir = os.path.join(wd,"mains/")

ctl = collections.OrderedDict({})

# start by mirroring the two directory levels in startersdir, and name those 
# directories "ethnicity" and "dietary"
mirror_dir(startersdir, ["ethnicity", "dietary"], ctl)

# now get all of the starters 
ctl["starter"] = (lambda(c): map(file_nv, collect_globs(c["dietary"].val, ["*"])))

# now get the corresponding mains
ctl["main"] = (lambda(c): [file_nv(mainsdir+c["ethnicity"].name+"_stirfry.txt")])

# get only the tasty wines
ctl["wine"] = all_globs(file_nv, winedir, ["*.tasty"])

# the wineglasses should be chosen by the wine choice, but we don't want to
# make a directory for those, so they get a none_nv
ctl["wineglass"] = (lambda(c): [none_nv(c["wine"].name+" wine glasses")])

build({"control": ctl, "destdir": "runs"})

