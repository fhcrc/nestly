"""
Aggregate results of ``nestly`` runs.
"""

import argparse
import collections
import csv
import functools
import itertools
import os.path
import json
import sys

from ..core import control_iter, nest_map

DEFAULT_SEP = ','
DEFAULT_NAME = 'control.json'

# JSON loaders retaining key order
_ordered_load = functools.partial(json.load,
                                  object_pairs_hook=collections.OrderedDict)
_ordered_loads = functools.partial(json.loads,
                                   object_pairs_hook=collections.OrderedDict)

def warn(message):
    print >>sys.stderr, message

def _warn_on_io(fn):
    @functools.wraps(fn)
    def f(*args, **kwargs):
        r = fn(*args, **kwargs)
        try:
            for i in r:
                yield i
        except IOError as e:
            warn(str(e))
    return f

def _delim_accum(control_files, filename_template, keys=None,
        exclude_keys=None, separator=DEFAULT_SEP, missing_action='fail'):
    """
    Accumulator for delimited files

    Combines each file with values from JSON dictionary in same directory

    :param iterable control_files: Iterable of control files
    :param filename_template: A template for the file to nest_map
    :param keys: List of keys to select from JSON dictionary. If ``None``, keep
                 all keys.
    :param separator: Delimiter
    """
    def map_fn(d, control, keys=keys):
        f = os.path.join(d, filename_template.format(**control))

        keys = keys if keys is not None else control.keys()
        if exclude_keys:
            keys = list(frozenset(keys) - frozenset(exclude_keys))
        if frozenset(keys) - frozenset(control):
            # Unknown keys
            raise ValueError(
                    "The following required key(s) are not present in {1}: {0}".format(
                        ', '.join(frozenset(keys) - frozenset(control)),
                        f))
        with open(f) as fp:
            reader = csv.DictReader(fp, delimiter=separator)
            for row in reader:
                row_dict = collections.OrderedDict(
                        itertools.chain(((k, row[k]) for k in reader.fieldnames),
                        ((k, v) for k, v in control.items() if k in keys)))

                yield row_dict
    if missing_action == 'warn':
        map_fn = _warn_on_io(map_fn)

    return itertools.chain.from_iterable(nest_map(control_files, map_fn))

def delim(arguments):
    """
    Execute delim action.

    :param arguments: Parsed command line arguments from :func:`main`
    """

    if bool(arguments.control_files) == bool(arguments.directory):
        raise ValueError(
                'Exactly one of control_files and `-d` must be specified.')

    if arguments.directory:
        arguments.control_files.extend(control_iter(arguments.directory))

    with arguments.output as fp:
        results = _delim_accum(arguments.control_files,
                arguments.file_template, arguments.keys,
                arguments.exclude_keys, arguments.separator,
                missing_action=arguments.missing_action)
        r = next(results)
        writer = csv.DictWriter(fp, r.keys(), delimiter=arguments.separator)
        writer.writeheader()
        writer.writerow(r)
        writer.writerows(results)

def comma_separated_values(s):
    s = s.split(',')
    return s

def main(args=sys.argv[1:]):
    """
    Command-line interface for nestagg
    """
    parser = argparse.ArgumentParser(description="""Aggregate results of
            nestly runs""")
    subparsers = parser.add_subparsers()
    delim_parser = subparsers.add_parser('delim', help="""Combine control files
            with delimited files.""")
    delim_parser.set_defaults(func=delim)
    key_group = delim_parser.add_mutually_exclusive_group()
    key_group.add_argument('-k', '--keys', help="""Comma separated list of
            keys from the JSON file to include [default: all keys]""",
            type=comma_separated_values)
    key_group.add_argument('-x', '--exclude-keys', help="""Comma separated
            list of keys from the JSON file not to include [default:
            %(default)s]""", type=comma_separated_values)
    delim_parser.add_argument('-m', '--missing-action', choices=('fail',
        'warn'), help="""Action to take when a file is missing [default:
        %(default)s]""", default='fail')
    delim_parser.add_argument('file_template', help="""Template for the
            delimited file to read in each directory [e.g. '{run_id}.csv']""")
    delim_parser.add_argument('control_files', metavar="control.json",
            help="""Control files""", nargs="*")
    delim_parser.add_argument('-d', '--directory', help="""Run on all control
            files under %(metavar)s. May be used in place of specifying control
            files.""", metavar='DIR')
    delim_parser.add_argument('-s', '--separator', default=DEFAULT_SEP,
            help="""Separator [default: %(default)s]""")
    delim_parser.add_argument('-t', '--tab', action='store_const',
            dest='separator', const='\t', help="""Files are tab-separated""")
    delim_parser.add_argument('-o', '--output', default=sys.stdout,
        type=argparse.FileType('w'), help="""Output file [default: stdout]""")

    arguments = parser.parse_args()

    arguments.func(arguments)
