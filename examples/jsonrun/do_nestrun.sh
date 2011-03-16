nestrun --savecmdfile cmd.sh --srun 2 --template='raxmlHPC -T 2 -m GTRGAMMA -n bl4 -s {infile}' $(find runs -name control.json)
# Non-srun environment, non-thread raxml example
#nestrun.py --savecmdfile cmd.sh --template='raxmlHPC -m GTRGAMMA -n bl4 -s {infile}' $(find runs -name control.json)
