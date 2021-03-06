#!/bin/sh

set -e
set -u
set -x

# Build a nested directory structure
./make_nest.py

# Let's look at a sample control file:
cat runs/approximate/1/file1/control.json

# Run `echo.sh` using every control.json under the `runs` directory, 2
# processes at a time
nestrun --processes 2 --template-file echo.sh -d runs

# Merge the CSV files named '{strategy}.csv' (where strategy value is taken
# from the control file)
nestagg delim '{strategy}.csv' -d runs -o aggregated.csv
