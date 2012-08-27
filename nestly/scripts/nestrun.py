"""
nestrun.py - run commands based on control dictionaries.
"""
import argparse
import collections
import csv
import datetime
import errno
import functools
import json
import logging
import os
import os.path
import shlex
import shutil
import signal
import subprocess
import sys

from nestly.core import control_iter

# Constants to be used as defaults.
MAX_PROCS = 2                    # Set the default maximum number of child processes that can be spawned.
DRY_RUN = False                   # Run in dry_run mode, default is False.


def _terminate_procs(procs):
    """
    Terminate all processes in the process dictionary
    """
    logging.warn("Stopping all remaining processes")
    for proc, g in procs.values():
        logging.debug("[%s] SIGTERM", proc.pid)
        try:
            proc.terminate()
        except OSError as e:
            # we don't care if the process we tried to kill didn't exist.
            if e.errno != errno.ESRCH:
                raise
    sys.exit(1)

def sigterm_handler(nonlocal, signum, frame):
    logging.warning('SIGTERM received; no longer spawning jobs')
    nonlocal['spawn_jobs'] = False

def sigusr1_handler(running_procs, signum, frame):
    for pid, (proc, _) in running_procs.iteritems():
        sys.stderr.write('%5d - in %s\n' % (pid, proc.working_dir))
    sys.stderr.flush()  # just in case it's being buffered by something

def sigint_handler(nonlocal, write_this_summary, running_procs, signum, frame):
    if nonlocal['received_SIGINT']:
        logging.warning('SIGINT received; terminating')
        _terminate_procs(running_procs)
        write_this_summary()
        sys.exit(0)
    else:
        logging.warning('SIGINT received; send again to terminate')
        nonlocal['received_SIGINT'] = True

def invoke(max_procs, data, json_files):
    nonlocal = {'spawn_jobs': True, 'received_SIGINT': False}
    running_procs = {}
    all_procs = []
    def write_this_summary():
        write_summary(all_procs, data['summary_file'])

    signal.signal(signal.SIGTERM, functools.partial(sigterm_handler, nonlocal))
    signal.signal(signal.SIGUSR1,
        functools.partial(sigusr1_handler, running_procs))
    signal.signal(signal.SIGINT,
        functools.partial(sigint_handler, nonlocal, write_this_summary,
                          running_procs))

    files = iter(json_files)
    try:
        while True:
            while nonlocal['spawn_jobs'] and len(running_procs) < max_procs:
                try:
                    json_file = files.next()
                except StopIteration:
                    # no more files; allow other processes to finish.
                    break
                g = worker(data, json_file)
                try:
                    proc = g.next()
                except StopIteration:
                    continue
                except OSError:
                    # OSError thrown when command couldn't be started
                    logging.exception("Exception starting %s", json_file)
                    if data['stop_on_error']:
                        _terminate_procs(running_procs)
                        return
                else:
                    all_procs.append(proc)
                    running_procs[proc.pid] = proc, g

            try:
                pid, status = os.wait()
            except OSError as e:
                # wait(2) raising ECHILD means there's no child processes to wait
                # for anymore, so we're done.
                if e.errno == errno.ECHILD:
                    return
                elif e.errno == errno.EINTR:
                    continue
                else:
                    raise

            # Pull the actual exit status - high byte of 16-bit number
            exit_status = os.WEXITSTATUS(status)
            proc, g = running_procs.pop(pid)
            proc.complete(exit_status)

            try:
                g.next()
            except StopIteration:
                pass
            else:
                raise ValueError('worker generators should only yield once')

            # Check exit status, cancel jobs if stop_on_error specified and
            # non-zero
            if exit_status:
                logging.warn('[%s] %s Finished with non-zero exit status %s\n%s',
                        pid, proc.working_dir, exit_status, proc.log_tail())
                if data['stop_on_error']:
                    _terminate_procs(running_procs)
                    return
            else:
                logging.info("[%s] %s Finished with %s", pid, proc.working_dir,
                        exit_status)
    finally:
        write_this_summary()


def write_summary(all_procs, summary_file):
    """
    Write a summary of all run processes to summary_file in tab-delimited
    format.
    """
    if not summary_file:
        return

    with summary_file:
        writer = csv.writer(summary_file, delimiter='\t', lineterminator='\n')
        writer.writerow(('directory', 'command', 'start_time', 'end_time',
            'run_time', 'exit_status', 'result'))
        rows = ((p.working_dir, ' '.join(p.command), p.start_time, p.end_time,
                p.running_time, p.return_code, p.status) for p in all_procs)
        writer.writerows(rows)


def template_subs_file(in_file, out_fobj, d):
    """
    Substitute template arguments in in_file from variables in d, write the
    result to out_fobj.
    """
    with open(in_file, 'r') as in_fobj:
        for line in in_fobj:
            out_fobj.write(line.format(**d))


class NestlyProcess(object):
    """
    Metadata about a process run
    """

    def __init__(self, command, working_dir, popen, log_name='log.txt'):
        self.command = command
        self.working_dir = working_dir
        self.log_name = log_name
        self.popen = popen
        self.pid = popen.pid
        self.return_code = None
        self.start_time = datetime.datetime.now()
        self.end_time = None
        self.status = 'RUNNING'

    def terminate(self):
        self.popen.terminate()
        self.end_time = datetime.datetime.now()
        self.status = 'TERMINATED'

    def complete(self, return_code):
        """
        Mark the process as complete with provided return_code
        """
        self.return_code = return_code
        self.status = 'COMPLETE' if not return_code else 'FAILED'
        self.end_time = datetime.datetime.now()

    @property
    def running_time(self):
        if self.end_time is None:
            return None

        return self.end_time - self.start_time

    def log_tail(self, nlines=10):
        """
        Return the last ``nlines`` lines of the log file
        """
        log_path = os.path.join(self.working_dir, self.log_name)
        with open(log_path) as fp:
            d = collections.deque(maxlen=nlines)
            d.extend(fp)
            return ''.join(d)


def worker(data, json_file):
    """
    Handle parameter substitution and execute command as child process.
    """
    # PERHAPS TODO: Support either full or relative paths.
    with open(json_file) as fp:
        d = json.load(fp)
    json_directory = os.path.dirname(json_file)
    def p(*parts):
        return os.path.join(json_directory, *parts)

    # STDOUT and STDERR will be written to a log file in each job directory.
    log_file = data['log_file']

    # A template file will be written in each job directory, including the
    # substitution that was performed..
    savecmd_file = data['savecmd_file']

    # if a template file is being used, then we write out to it
    template_file = data['template_file']
    if template_file:
        output_template = p(os.path.basename(template_file))
        with open(output_template, 'w') as out_fobj:
            template_subs_file(template_file, out_fobj, d)

        # Copy permissions to destination
        try:
            shutil.copymode(template_file, output_template)
        except OSError as e:
            if e.errno == errno.EPERM:
                logging.warn("Couldn't set permissions on %s. "
                        "Continuing with existing permissions",
                        output_template)
            else:
                raise

    work = data['template'].format(**d)

    if savecmd_file:
        with open(p(savecmd_file), 'w') as command_file:
            command_file.write(work + "\n")

    # View what actions will take place in dry_run mode.
    if data['dry_run']:
        logging.info("%s - Dry run of %s\n", p(), work)
    else:
        try:
            with open(p(log_file), 'w') as log:
                cmd = shlex.split(work)
                while True:
                    try:
                        pr = subprocess.Popen(
                            cmd, stdout=log, stderr=log, cwd=p())
                    except OSError as e:
                        if e.errno != errno.EINTR:
                            raise
                        continue
                    else:
                        break
                logging.info('[%d] Started %s in %s', pr.pid, work, p())
                nestproc = NestlyProcess(cmd, p(), pr)
                yield nestproc
        except Exception as e:
            # Seems useful to print the command that failed to make the
            # traceback more meaningful.  Note that error output could get
            # mixed up if two processes encounter errors at the same instant
            logging.error("%s - Error executing %s - %s", p(), work, e)
            raise e


def extant_file(x):
    """
    'Type' for argparse - checks that file exists but does not open.
    """
    if not os.path.exists(x):
        raise argparse.ArgumentError("{0} does not exist".format(x))
    return x


def parse_arguments():
    """
    Grab options and json files.
    """
    max_procs = MAX_PROCS
    dry_run = DRY_RUN
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format='%(asctime)s * %(levelname)s * %(message)s')

    parser = argparse.ArgumentParser(description="""nestrun - substitute values
            into a template and run commands in parallel.""")
    parser.add_argument('-j', '--processes', '--local', dest='local_procs',
            type=int, help="""Run a maximum of N processes in parallel locally
            (default: %(default)s)""", metavar='N', default=MAX_PROCS)
    parser.add_argument('--template', dest='template',
            metavar="'template text'", help="""Command-execution template, e.g.
            bash {infile}. By default, nestrun executes the templatefile.""")
    parser.add_argument('--stop-on-error', action='store_true',
            default=False, help="""Terminate remaining processes if any process
            returns non-zero exit status (default: %(default)s)""")
    parser.add_argument('--template-file', dest='template_file', metavar="FILE",
            help='Command-execution template file path.')
    parser.add_argument('--save-cmd-file', dest='savecmd_file',
            help="""Name of the file that will contain the command that was
            executed.""")
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('--log-file', dest='log_file', default='log.txt',
            help="""Name of the file that will contain output of the executed
            command.""")
    log_group.add_argument('--no-log', dest="log_file", action="store_const",
            default='log.txt', const=os.devnull, help="""Don't create a log
            file""")
    parser.add_argument('--dry-run', action='store_true', help="""Dry run mode,
            does not execute commands.""", default=False)
    parser.add_argument('--summary-file', type=argparse.FileType('w'),
            help="""Write a summary of the run to the specified file""")

    ctrl_group = parser.add_argument_group('Control files')
    ctrl_group.add_argument('json_files', metavar='control_files', type=extant_file,
            nargs='*', help="""Nestly control dictionaries""")
    ctrl_group.add_argument('-d', '--directory', help="""Run on all control
            files under %(metavar)s. May be used in place of specifying control
            files.""", metavar='DIR')
    arguments = parser.parse_args()


    # Load controls
    if bool(arguments.directory) == bool(arguments.json_files):
        parser.error('Exactly one of `-d` and control_files must be specified.')
    elif arguments.directory:
        arguments.json_files.extend(control_iter(arguments.directory))

    template = arguments.template

    # Make sure that either a template or a template file was given
    if arguments.template_file:
        # if given a template file, the default is to run the input
        if not arguments.template:
            template = os.path.join('.',
                    os.path.basename(arguments.template_file))

            # If using the default argument, the template must be executable:
            if (not os.access(arguments.template_file, os.X_OK) and not
                    arguments.dry_run):
                parser.error(
                        "{0} is not executable. Specify a template.".format(
                    arguments.template_file))

    if not (arguments.template or arguments.template_file):
        parser.exit("Error: Please specify either a template "
                "or a template file")

    logging.info('Template: %s', template)

    if arguments.local_procs is not None:
        max_procs = arguments.local_procs

    # Create a dictionary that will be shared amongst all forked processes.
    data = {}
    data['dry_run'] = arguments.dry_run
    data['start_directory'] = os.getcwd()
    data['template'] = template
    data['template_file'] = arguments.template_file
    data['savecmd_file'] = arguments.savecmd_file
    data['log_file'] = arguments.log_file
    data['stop_on_error'] = arguments.stop_on_error
    data['summary_file'] = arguments.summary_file

    return data, max_procs, arguments.json_files

def main():
    data, max_procs, json_files = parse_arguments()
    invoke(max_procs, data, json_files)

