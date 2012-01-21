"""
nestrun.py - run commands based on control dictionaries.
"""
import argparse
import collections
import csv
import datetime
import json
import logging
import os
import os.path
import shlex
import shutil
import subprocess
import sys
import yaml


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
        proc.terminate()
    sys.exit(1)


def invoke(max_procs, data, controls):
    running_procs = {}
    all_procs = []
    n_done = 0
    while True:
        while len(running_procs) < max_procs:
            try:
                control = controls.next()
            except MoreLater:
                break
            except StopIteration:
                if not running_procs:
                    write_summary(all_procs, data['summary_file'])
                    return
                break
            g = worker(data, control)
            try:
                proc = g.next()
            except StopIteration:
                continue
            except OSError:
                # OSError thrown when command couldn't be started
                logging.exception("Exception starting %s", control)
                if data['stop_on_error']:
                    _terminate_procs(running_procs)
                    write_summary(all_procs, data['summary_file'])
                    return
            else:
                all_procs.append(proc)
                running_procs[proc.pid] = proc, g

        pid, status = os.wait()

        exit_status = os.WEXITSTATUS(status)
        proc, g = running_procs.pop(pid)
        proc.complete(exit_status, data['status_files'])
        controls.done(proc.control)

        try:
            g.next()
        except StopIteration:
            pass
        else:
            raise ValueError('worker generators should only yield once')

        n_done += 1
        # Check exit status, cancel jobs if stop_on_error specified and
        # non-zero
        if exit_status:
            logging.warn(
                '[%s] %s Finished (%d/%d) with non-zero exit status %s\n%s',
                pid, proc.working_dir, n_done, len(controls), exit_status,
                proc.log_tail())
            if data['stop_on_error']:
                _terminate_procs(running_procs)
                break
        else:
            logging.info(
                "[%s] %s Finished (%d/%d) with %s",
                pid, proc.working_dir, n_done, len(controls), exit_status)


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

    def __init__(self, control, command, working_dir, popen, log_name='log.txt'):
        self.control = control
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

    def complete(self, return_code, write_status_file):
        """
        Mark the process as complete with provided return_code
        """
        self.return_code = return_code
        self.status = 'COMPLETE' if not return_code else 'FAILED'
        self.end_time = datetime.datetime.now()
        if write_status_file:
            with open(os.path.join(self.working_dir, 'status'), 'w') as fobj:
                fobj.write('%s\n' % (return_code,))

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


def worker(data, control):
    """
    Handle parameter substitution and execute command as child process.
    """
    d = control.load()
    json_directory = os.path.dirname(os.path.abspath(control.path))
    def p(*parts):
        return os.path.join(json_directory, *parts)

    # STDOUT and STDERR will be written to a log file in each job directory.
    log_file = data['log_file']

    # A template file will be written in each job directory, including the
    # substitution that was performed..
    savecmd_file = data['savecmd_file']

    # if a template file is being used, then we write out to it
    template_file = control.template_file
    if template_file:
        output_template = p(os.path.basename(template_file))
        with open(output_template, 'w') as out_fobj:
            template_subs_file(template_file, out_fobj, d)

        # Copy permissions to destination
        try:
            shutil.copymode(template_file, output_template)
        except OSError, e:
            if e.errno == 1:
                logging.warn("Couldn't set permissions on %s. "
                        "Continuing with existing permissions",
                        output_template)
            else:
                raise

    work = control.template.format(**d)

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
                pr = subprocess.Popen(cmd, stdout=log, stderr=log, cwd=p())
                logging.info('[%d] Started %s in %s', pr.pid, work, p())
                nestproc = NestlyProcess(control, cmd, p(), pr)
                yield nestproc
        except Exception, e:
            # Seems useful to print the command that failed to make the
            # traceback more meaningful.  Note that error output could get
            # mixed up if two processes encounter errors at the same instant
            logging.error("%s - Error executing %s - %s", p(), work, e)
            raise


class ControlFile(object):
    def __init__(self, path, template_loader=None):
        self.path = path
        self.dir = os.path.dirname(path).split(os.sep)
        self.children = []
        self.parent = None
        self.template = None
        self.template_file = None
        self.template_loader = template_loader

    def check_parent(self, parent):
        if len(self.dir) > len(parent.dir) and self.dir[:len(parent.dir)] == parent.dir:
            if self.parent is None:
                parent.children.append(self)
                self.parent = parent
            return True
        return False

    def __repr__(self):
        return '<ControlFile at %#x: %r>' % (id(self), self.path)

    def load(self):
        with open(self.path) as infile:
            d = json.load(infile)
        if self.template_loader:
            self.template_loader(d, self)
        return d

def control_key(path):
    splut = path.split('/')
    splut[-1] = splut[-1] == 'control.json'
    return splut

def organize_files(json_files, template_loader=None):
    json_files.sort(key=control_key)
    controls = []
    parent_stack = []
    for json_file in json_files:
        control = ControlFile(json_file, template_loader)
        controls.append(control)
        if not parent_stack:
            parent_stack.append(control)
        else:
            while parent_stack and not control.check_parent(parent_stack[-1]):
                parent_stack.pop()
            parent_stack.append(control)
    return controls

class MoreLater(Exception):
    pass

class MultiNestIterator(object):
    def __init__(self, json_files, template_loader=None):
        self.controls = set(organize_files(json_files, template_loader))
        self.available = (
            collections.deque(c for c in self.controls if c.parent is None))
        self.n_controls = len(self.controls)

    def __iter__(self):
        return self

    def __len__(self):
        return self.n_controls

    def next(self):
        if not self.controls:
            raise StopIteration
        elif not self.available:
            raise MoreLater
        return self.available.popleft()

    def done(self, control):
        if control not in self.controls:
            raise ValueError('not waiting on this control', control)
        self.controls.remove(control)
        self.available.extend(control.children)


def extant_file(x):
    """
    'Type' for argparse - checks that file exists but does not open.
    """
    if not os.path.exists(x):
        raise argparse.ArgumentError("{0} does not exist".format(x))
    return x


def yaml_template_loader(yaml):
    key_pairs = []
    for k, v in yaml.iteritems():
        all_keys = {k}.union(v.get('deps', []))
        key_pairs.append((all_keys, v))
    def loader(d, control):
        d_keys = set(d)
        d = next((v for k, v in key_pairs if k == d_keys), None)
        if d is None:
            raise ValueError('no specification found', d_keys)
        control.template = d['template']
        control.template_file = d.get('template-file')
    return loader

def plain_template_loader(template, template_file):
    def loader(d, control):
        control.template = template
        control.template_file = template_file
    return loader


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
    parser.add_argument('--multinest-file', metavar='FILE',
            type=argparse.FileType('r'),
            help="""A YAML file containing information for running multiple
            levels of control.json files.""")
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
    parser.add_argument('--status-files', action='store_true', default=False,
        help="""Write exit status files into the same directory as the status.json
        files.""")
    parser.add_argument('json_files', type=extant_file, nargs='+',
            help='Nestly control dictionaries')
    arguments = parser.parse_args()

    if arguments.multinest_file:
        multinest = yaml.safe_load(arguments.multinest_file)
        template_loader = yaml_template_loader(multinest)
    else:
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
                    parser.exit(
                        "the template file {0} is not executable.".format(
                            arguments.template_file))

        if not (arguments.template or arguments.template_file):
            parser.exit("Error: Please specify either a template "
                    "or a template file")

        logging.info('Template: %s', template)
        template_loader = plain_template_loader(
            template, arguments.template_file)

    if arguments.local_procs is not None:
        max_procs = arguments.local_procs

    if arguments.dry_run is not None:
        dry_run = arguments.dry_run

    # Create a dictionary that will be shared amongst all forked processes.
    data = {}
    data['dry_run'] = dry_run
    data['start_directory'] = os.getcwd()
    data['savecmd_file'] = arguments.savecmd_file
    data['log_file'] = arguments.log_file
    data['stop_on_error'] = arguments.stop_on_error
    data['summary_file'] = arguments.summary_file
    data['status_files'] = arguments.status_files

    controls = MultiNestIterator(arguments.json_files, template_loader)
    return data, max_procs, controls

def main():
    data, max_procs, controls = parse_arguments()
    invoke(max_procs, data, controls)

