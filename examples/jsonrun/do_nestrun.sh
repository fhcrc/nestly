nestrun --save-cmd-file cmd.sh -j 2 --template='raxmlHPC -T 2 -m GTRGAMMA -n bl4 -s {infile}' $(find runs -name control.json)
