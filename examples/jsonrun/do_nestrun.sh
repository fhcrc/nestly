nestrun.py --dryrun --savecmdfile cmd.sh --srun 2 --template='raxmlHPC -T 2 -m GTRGAMMA -n bl4 -s $infile' $(find runs -name control.json)
