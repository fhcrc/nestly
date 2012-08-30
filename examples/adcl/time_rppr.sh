#!/bin/sh

export TIME='elapsed,avgmem,maxmem,exitstatus\n%E,%D,%M,%x'

/usr/bin/time -o time.csv \
  rppr min_adcl_tree --algorithm {algorithm} --leaves {k} {tree}
