#!/usr/bin/env python

import collections
import json
import glob
import os
import os.path
import sys

from nestly import Nest

wd = os.getcwd()
startersdir = os.path.join(wd, "starters")
winedir = os.path.join(wd, "wine")
mainsdir = os.path.join(wd, "mains")

nest = Nest()

bn = os.path.basename
def strip_bn(path):
    """Return the basename of path, any extension stripped"""
    return bn(os.path.splitext(path)[0])

# start by mirroring the two directory levels in startersdir, and name those
# directories "ethnicity" and "dietary"
nest.add('ethnicity', glob.glob(os.path.join(startersdir, '*')),
    label_func=bn)
nest.add('dietary', lambda c: glob.glob(os.path.join(c['ethnicity'], '*')),
    label_func=bn)

## now get all of the starters
nest.add('starter', lambda c: glob.glob(os.path.join(c['dietary'], '*')),
    label_func=strip_bn)
## now get the corresponding mains
nest.add('main', lambda c: [os.path.join(mainsdir, bn(c['ethnicity']) + "_stirfry.txt")],
    label_func=strip_bn)

## get only the tasty wines
nest.add('wine', glob.glob(os.path.join(winedir, '*.tasty')),
    label_func=strip_bn)
## the wineglasses should be chosen by the wine choice, but we don't want to
## make a directory for those.
nest.add('wineglass', lambda c: c['wine'] + ' wine glasses', create_dir=False)

nest.build('runs')
