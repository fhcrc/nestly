#!/bin/sh

set -e
set -u

CONTROLS=$(find runs -name control.json)
echo $CONTROLS

nestrun --processes 2 --template-file echo.sh $CONTROLS

# Merge the CSV files named '{strategy}.csv' (where strategy value is taken
# from the control file)
nestagg delim '{strategy}.csv' $CONTROLS -o aggregate.csv
