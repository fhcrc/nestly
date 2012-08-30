#!/bin/sh

export TIME='elapsed,maxmem,exitstatus\n%e,%M,%x'

/usr/bin/time -o time.csv \
  rppr min_adcl_tree --algorithm {algorithm} --leaves {k} {tree}
