#!/bin/sh

echo "count_file lines words chars"
for f in "$@"; do
    echo "$f " | tr -d '\n'
    cat $f
done
