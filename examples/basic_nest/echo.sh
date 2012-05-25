#!/bin/sh
#
# Echo the value of two fake output variables: var1, which is always 13, and
# var2, which is 10 times the run_count.

echo "var1,var2
13,{run_count}0" > "{strategy}.csv"
