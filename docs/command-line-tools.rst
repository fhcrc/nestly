Command line tools
==================

``nestrun``
-----------

``nestrun`` takes a command template and a list of control.json files with variables to
substitute. Substitution is performed using the Python built-in
``str.format`` method. See the `Python Formatter documentation`_ for details on syntax,
and ``examples/jsonrun/do_nestrun.sh`` for an example.

.. _`Python Formatter documentation`: http://docs.python.org/library/string.html#formatstrings

Signals
^^^^^^^

``nestrun`` also handles some signals by default.

.. describe:: SIGTERM

    This tells ``nestrun`` to stop spawning jobs. All jobs that were already
    spawned will continue running.

.. describe:: SIGINT

    This tells ``nestrun`` to terminate if received twice. On the first
    SIGTERM, ``nestrun`` will emit a warning message; on the second, it will
    terminate all jobs and then itself.

.. describe:: SIGUSR1

    This tells ``nestrun`` to immediately write a list of all currently-running
    processes and their working directories to stderr, then flush stderr.


Help
^^^^

::

    usage: nestrun.py [-h] [-j N] [--template 'template text'] [--stop-on-error]
                      [--template-file FILE] [--save-cmd-file SAVECMD_FILE]
                      [--log-file LOG_FILE | --no-log] [--dry-run]
                      [--summary-file SUMMARY_FILE] [-d DIR]
                      [control_files [control_files ...]]

    nestrun - substitute values into a template and run commands in parallel.

    optional arguments:
      -h, --help            show this help message and exit
      -j N, --processes N, --local N
                            Run a maximum of N processes in parallel locally
                            (default: 2)
      --template 'template text'
                            Command-execution template, e.g. bash {infile}. By
                            default, nestrun executes the templatefile.
      --stop-on-error       Terminate remaining processes if any process returns
                            non-zero exit status (default: False)
      --template-file FILE  Command-execution template file path.
      --save-cmd-file SAVECMD_FILE
                            Name of the file that will contain the command that
                            was executed.
      --log-file LOG_FILE   Name of the file that will contain output of the
                            executed command.
      --no-log              Don't create a log file
      --dry-run             Dry run mode, does not execute commands.
      --summary-file SUMMARY_FILE
                            Write a summary of the run to the specified file

    Control files:
      control_files         Nestly control dictionaries
      -d DIR, --directory DIR
                            Run on all control files under DIR. May be used in
                            place of specifying control files.

``nestagg``
-----------

The ``nestagg`` command provides a mechanism for combining results of multiple
runs, via a subcommand interface.  Currently, the only supported action is
merging delimited files from a set of leaves, adding values from the control
dictionary on each.  This is performed via ``nestagg delim``.

Help
^^^^

::

    usage: nestagg.py delim [-h] [-k KEYS | -x EXCLUDE_KEYS] [-m {fail,warn}]
                            [-d DIR] [-s SEPARATOR] [-t] [-o OUTPUT]
                            file_template [control.json [control.json ...]]

    positional arguments:
      file_template         Template for the delimited file to read in each
                            directory [e.g. '{run_id}.csv']
      control.json          Control files

    optional arguments:
      -h, --help            show this help message and exit
      -k KEYS, --keys KEYS  Comma separated list of keys from the JSON file to
                            include [default: all keys]
      -x EXCLUDE_KEYS, --exclude-keys EXCLUDE_KEYS
                            Comma separated list of keys from the JSON file not to
                            include [default: None]
      -m {fail,warn}, --missing-action {fail,warn}
                            Action to take when a file is missing [default: fail]
      -d DIR, --directory DIR
                            Run on all control files under DIR. May be used in
                            place of specifying control files.
      -s SEPARATOR, --separator SEPARATOR
                            Separator [default: ,]
      -t, --tab             Files are tab-separated
      -o OUTPUT, --output OUTPUT
                            Output file [default: stdout]
