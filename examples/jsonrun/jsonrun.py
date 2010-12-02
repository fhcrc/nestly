#!/usr/bin/env python

import sys, os, collections, string, argparse, re

sys.path.append(".")
sys.path.append("../..")
from nestly import *

MAX_PROCS=100 # Set the default maximum number of child processes that can be spawned.

# DESIRED: i'd like for this to be an argument
templ = string.Template("raxmlHPC -m GTRGAMMA -n bla -s $infile")

# DESIRED: I'd like two flags which control the execution
# these two options should be mutually exclusive.
# "--local n" runs the commands with at most n processes at a time (xargs?)
# "--srun" runs the commands through srun on hyrax. 
# in the future, we may want to cap the number of jobs submitted to hyrax, and trickle them out over time.

def invoke(srun, max_procs, json_files):
    """

    """
    
    # Keep track of where we started, so users can specify either full or 
    # relative paths to json files.
    start_directory = os.getcwd()

    for fname in json_files:
        # Support either full or relative paths.
        os.chdir(start_directory)

        d = d_of_jsonfile(fname)
        json_directory = os.path.dirname(fname)

        # cd into the directory containing the json file.
        os.chdir(json_directory)

        # Need to figure out how to limit the number of children at this step
        # and execute the commands.
        print templ.substitute(d)

        
        # DESIRED: rather than printing this, run the command

def file_test(argument):
    """
    Test to make sure the path leads to a file that is readable.
    """
    if os.access(argument, os.R_OK) and os.path.isfile(argument):
        return argument

def parse_arguments():
    """
    Grab options and json files.
    """

    max_procs = MAX_PROCS
    srun = False # Default behavior is to execute commands locally.

    # We will use argv to build up a list of files.
    argv = sys.argv[1:]
    
    json_files = filter(file_test, argv)

    parser = argparse.ArgumentParser(description='jsonrun.py - substitute values into a template and run commands.')
    
    parser.add_argument('--local', dest='local_procs', type=int, help='Run a maximum of N processes locally.')
    parser.add_argument('--srun', dest='srun_procs', type=int, help='Run a maximum of N processes on a cluster with slurm.')
    parser.add_argument('catchall', nargs='*') # Used sys.argv already for this, but could have done a custom type here.

    arguments = parser.parse_args()
 
    if arguments.local_procs is not None and arguments.srun_procs is not None:
        parser.print_help()
        parser.exit(1, "\nError: --srun and --local are mutually exclusive.\n")

    if arguments.local_procs is not None: 
        max_procs = arguments.local_procs
    elif  arguments.srun_procs is not None:
        max_procs = arguments.srun_procs
        srun = True

    return srun, max_procs, json_files

def main():
    srun, max_procs, json_files = parse_arguments()
    invoke(srun, max_procs, json_files)


if __name__ == '__main__':
    sys.exit(main())

