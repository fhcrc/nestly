# possible TODOs:
# - should we make it possible to specify a relative path for template_file?

from string import Template
import subprocess
import traceback
import argparse
import shlex
import sys
import os

from nestly.nestly import *
import nestly.template

# Constants to be used as defaults.
MAX_PROCS = 2                    # Set the default maximum number of child processes that can be spawned.
SRUN = False                     # Whether or not to use srun, default is False and to run locally.
SRUN_COMMAND = 'srun -p emhigh ' # Specify srun command with any options such as which partition.
DRYRUN = False                   # Run in dryrun mode, default is False.

# what is used by default to run template files
TEMPLATEFILE_RUN_CMD = 'source '

DEFAULT_TEMPLATE_ENGINE = 'stringformat'

def invoke(max_procs, data, json_files):
    procs = {}
    files = iter(json_files)
    while True:
        while len(procs) < max_procs:
            try:
                json_file = files.next()
            except StopIteration:
                if not procs:
                    return
                break
            g = worker(data, json_file)
            try:
                proc = g.next()
            except StopIteration:
                continue
            else:
                procs[proc.pid] = proc, g

        pid, _ = os.wait()
        proc, g = procs.pop(pid)
        try:
            g.next()
        except StopIteration:
            pass
        else:
            raise ValueError('worker generators should only yield once')


# use d to do template substitution on each line of in_file and write the output to out_fobj
def template_subs_file(in_file, out_fobj, d, engine):
    with open(in_file, 'r') as in_fobj:
        for line in in_fobj:
            # Possible TODO: switch to in_fobj.read(), then substitute.
            # If we want a complicated templater (e.g. Jinja), single line
            # substitution won't work.
            out_fobj.write(engine(line, d))

def worker(data, json_file):
    """
    Handle parameter substitution and execute command as child process.
    """
    # PERHAPS TODO: Support either full or relative paths.
    with json_file:
        d = json.load(json_file)
    json_directory = os.path.dirname(json_file.name)
    def p(*parts):
        return os.path.join(json_directory, *parts)

    # STDOUT and STDERR will be writtne to a log file in each job directory.
    log_file = data['log_file']

    # A template file will be written in each job directory, including the
    # substitution that was performed..
    savecmd_file = data['savecmd_file']

    # if a template file is being used, then we write out to it
    template_file = data['template_file']
    if template_file:
        with open(p(template_file), 'w') as out_fobj:
            template_subs_file(template_file, out_fobj, d,
                               data['renderer'])

    # Perform subsitution, prepend 'srun' if necessary.
    work = data['renderer'](data['template'], d)
    if data['srun']:
        work = SRUN_COMMAND + work

    if savecmd_file:
        with open(p(savecmd_file), 'w') as command_file:
            command_file.write(work + "\n")

    print "Execution directory: %s" % (p(),)

    # View what actions will take place in dryrun mode.
    if data['dryrun']:
        print "dry run of: " + work + "\n"
    else:
        print "running: " + work + "\n"
        try:
            #subprocess.call(command_regex.split(work))
            with open(p(log_file), 'w') as log:
                yield subprocess.Popen(shlex.split(work), stdout=log, stderr=log, cwd=p())
        except:
            traceback.print_exc(file=sys.stdout)
            # Seems useful to print the command that failed to make the traceback
            # more meaningful.
            # Note that error output could get mixed up if two processes encounter errors
            # at the same instance.
            print "Error executing: " + work + "\n"


def parse_arguments():
    """
    Grab options and json files.
    """
    max_procs = MAX_PROCS
    dryrun = DRYRUN
    srun = SRUN

    parser = argparse.ArgumentParser(description='jsonrun.py - substitute values into a template and run commands.')
    parser.add_argument('--local', dest='local_procs', type=int, help='Run a maximum of N processes in parallel locally.')
    parser.add_argument('--srun', dest='srun_procs', type=int, help='Run a maximum of N processes in parallel on a cluster with slurm.')
    parser.add_argument('--template', dest='template', metavar="'template text'",
                         help='Command-execution template. Must be in single quotes or \
                               $ character pre-pended to $infile must be escaped.')
    parser.add_argument('--templatefile', dest='template_file', metavar="FILE",
                         help='Command-execution template file path.')
    parser.add_argument('--template-engine', metavar='ENGINE',
                        choices=nestly.template.BACKENDS.keys(),
                        default=DEFAULT_TEMPLATE_ENGINE,
                        help="Template backend. Choices: [%(choices)s] default: %(default)s")
    parser.add_argument('--savecmdfile', dest='savecmd_file',
                        help='Name of the file that will contain the command that was executed.')
    parser.add_argument('--logfile', dest='log_file', default='log.txt',
                        help='Name of the file that will contain the command that was executed.')
    parser.add_argument('--dryrun', action='store_true', help='Run in dryrun mode, does not execute commands.')
    parser.add_argument('json_files', type=argparse.FileType('r'), nargs='+')
    arguments = parser.parse_args()

    def insufficient_args(complaint):
        parser.print_help()
        parser.exit(1, "\n"+complaint+"\n")

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

    template_engine = nestly.template.get_template_engine(arguments.template_engine)


    # Create a dictionary that will be shared amongst all forked processes.
    data = {}
    data['dryrun'] = dryrun
    data['srun'] = srun
    data['start_directory'] = os.getcwd()
    data['template'] = template
    data['template_file'] = arguments.template_file
    data['savecmd_file'] = arguments.savecmd_file
    data['log_file'] = arguments.log_file
    data['renderer'] = template_engine

    return data, max_procs, arguments.json_files

def main():
    data, max_procs, json_files = parse_arguments()
    invoke(max_procs, data, json_files)
