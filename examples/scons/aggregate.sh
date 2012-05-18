#!/bin/sh

echo 'countsfile,lines,words,bytes'
for f in "$@"; do
    echo "$f" | tr -d '\n'
    sed -E 's: +:,:g' <"$f"
done
