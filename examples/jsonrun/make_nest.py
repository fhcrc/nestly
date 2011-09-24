#!/usr/bin/env python

import collections
import glob
import os.path

from nestly import Nest

wd = os.getcwd()
indir = os.path.join(wd,"prep/some_phy/")

nest = Nest()

nest.add('infile', glob.glob(os.path.join(indir, '*')),
        label_func=os.path.basename)

nest.build()
