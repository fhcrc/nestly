#!/usr/bin/env python

# possible TODOs:
# - should we make it possible to specify a relative path for template_file?

import sys, os, collections, string, argparse, re, subprocess, traceback

sys.path.append(".")
sys.path.append("/home/rkodner/erick/src/nestly/")
from nestly import *
from multiprocessing import Pool

# This will get populated in main() and later be shared by all children. 
shmem.data = {}

# Constants to be used as defaults.
MAX_PROCS = 2                    # Set the default maximum number of child processes that can be spawned.
SRUN = False                     # Whether or not to use srun, default is False and to run locally.
SRUN_COMMAND = 'srun -p emhigh ' # Specify srun command with any options such as which partition.
DRYRUN = False                   # Run in dryrun mode, default is False.

# what is used by default to run template files
TEMPLATEFILE_RUN_CMD = 'source '


def invoke(max_procs, json_files):
    """
    Create a pool or processes that execute commands in parallel.
    """
    pool = Pool(processes=max_procs)
    pool.map(worker, json_files)
    #map(lambda f: worker(f, 1), json_files)

# NOTE: can we avoid doing this by passing a flag to open to make it barf?
def assert_file_exists(path):
    if not os.path.isfile(path):
	raise IOError("path "+path+" is not a file")

# use d to do template substitution on each line of in_file and write the output to out_fobj
def template_subs_file(in_file, out_fobj, d):
    assert_file_exists(in_file)
    with open(in_file, 'r') as in_fobj:
	for line in in_fobj:
	    out_fobj.write(string.Template(line).substitute(d))

def worker(json_file):
    """
    Handle parameter substitution and execute command as child process.
    """
    # PERHAPS TODO: Support either full or relative paths.
    os.chdir(shmem.data['start_directory'])
    d = d_of_jsonfile(json_file)
    json_directory = os.path.dirname(json_file)

    # STDOUT and STDERR will be writtne to a log file in each job directory.
    log_file = shmem.data['log_file']

    # A template file will be written in each job directory, including the 
    # substitution that was performed..
    savecmd_file = shmem.data['savecmd_file']

    # cd into the directory containing the json file.
    os.chdir(json_directory)

    # if a template file is being used, then we write out to it
    template_file = shmem.data['template_file']
    if template_file:
	assert_file_exists(template_file)
	with open(os.path.basename(template_file), 'w') as out_fobj:
	    template_subs_file(template_file, out_fobj, d)

    # Perform subsitution, prepend 'srun' if necessary.
    work = string.Template(shmem.data['template']).substitute(d)
    if shmem.data['srun']:
        work = SRUN_COMMAND + work

    if savecmd_file:
	with open(savecmd_file, 'w') as command_file:
	    command_file.write(work + "\n")

    print "Execution directory currently: " + os.getcwd()

    # View what actions will take place in dryrun mode.
    if shmem.data['dryrun']:
	print "dry run of: " + work + "\n"
    else:
	print "running: " + work + "\n"
        command_regex = re.compile(r'\s+')
        try:
            #subprocess.call(command_regex.split(work))
            with open(log_file, 'w') as log:
                child = subprocess.Popen(command_regex.split(work), stdout=log, stderr=log)
                child.wait()
        except: 
            traceback.print_exc(file=sys.stdout)
            # Seems useful to print the command that failed to make the traceback 
            # more meaningful.
            # Note that error output could get mixed up if two processes encounter errors 
            # at the same instance.
            print "Error executing: " + work + "\n"
    return


def json_file_test(argument):
    """
    Test to make sure the path leads to a .json file that is readable.
    """
    # Whitespace in filenames is *not* supported.
    filename = argument.replace(' ', '')
    if os.access(filename, os.R_OK) and os.path.isfile(filename) and '.json' in argument.lower():
        return argument


def parse_arguments():
    """
    Grab options and json files.
    """
    max_procs = MAX_PROCS
    dryrun = DRYRUN
    srun = SRUN 

    # We will use argv to build up a list of files.
    argv = sys.argv[1:]
    json_files = filter(json_file_test, argv)
    parser = argparse.ArgumentParser(description='jsonrun.py - substitute values into a template and run commands.')
    parser.add_argument('--local', dest='local_procs', type=int, help='Run a maximum of N processes in parallel locally.')
    parser.add_argument('--srun', dest='srun_procs', type=int, help='Run a maximum of N processes in parallel on a cluster with slurm.')
    parser.add_argument('--template', dest='template', metavar="'template text'",
                         help='Command-execution template. Must be in single quotes or \
                               $ character pre-pended to $infile must be escaped.')
    parser.add_argument('--templatefile', dest='template_file', metavar="'template file'",
                         help='Command-execution template file path.')
    parser.add_argument('--savecmdfile', dest='savecmd_file', help='Name of the file that will contain the command that was executed.')
    parser.add_argument('--logfile', dest='log_file', default='log.txt', help='Name of the file that will contain the command that was executed.')
    parser.add_argument('--dryrun', action='store_true', help='Run in dryrun mode, does not execute commands.')
    parser.add_argument('<json_files>', nargs='*') # Used sys.argv already for this, but could have done a custom type here.
    arguments = parser.parse_args()

    def insufficient_args(complaint):
        parser.print_help()
        parser.exit(1, "\n"+complaint+"\n")

    # Make sure at least one JSON file was specified.
    if len(json_files) == 0:
        insufficient_args("Error: No JSON files were specified.")
 
    if arguments.local_procs is not None and arguments.srun_procs is not None:
        insufficient_args("Error: --srun and --local are mutually exclusive.")
    
    # Make sure that either a template or a template file was given
    if arguments.template_file:
    # if given a template file, the default is to make a template using TEMPLATEFILE_RUN_CMD
	template = TEMPLATEFILE_RUN_CMD + arguments.template_file
    if arguments.template:
	template = arguments.template
    if not (arguments.template or arguments.template_file):
	insufficient_args("Error: Please specify either a template or a template file")
    
    print "template: "+template

    # Grab max procs if specified and whether or not srun will be used.
    if arguments.local_procs is not None: 
        max_procs = arguments.local_procs
    elif arguments.srun_procs is not None:
        max_procs = arguments.srun_procs
        srun = True
    
    if arguments.dryrun is not None:
        dryrun = arguments.dryrun


    # Create a dictionary that will be shared amongst all forked processes.
    data = {}
    data['dryrun'] = dryrun
    data['srun'] = srun
    data['start_directory'] = os.getcwd()
    data['template'] = template
    data['template_file'] = arguments.template_file
    data['savecmd_file'] = arguments.savecmd_file
    data['log_file'] = arguments.log_file

    return data, max_procs, json_files

def main():
    shmem.data, max_procs, json_files = parse_arguments()
    invoke(max_procs, json_files)


if __name__ == '__main__':
    sys.exit(main())

