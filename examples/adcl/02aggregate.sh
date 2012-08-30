#!/bin/sh

# Using all the leaf directories containing JSON files in the `runs` directory,
# merge all of the `time.csv` files into `results.csv`
nestagg delim -d runs -o results.csv time.csv
