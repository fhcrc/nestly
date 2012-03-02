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

DEFAULT_SEP = ','
DEFAULT_NAME = 'control.json'

# JSON loaders retaining key order
_ordered_load = functools.partial(json.load,
                                  object_pairs_hook=collections.OrderedDict)
_ordered_loads = functools.partial(json.loads,
                                   object_pairs_hook=collections.OrderedDict)

def _delim_accum(delimited_files, keys=None, separator=DEFAULT_SEP,
                 control_name=DEFAULT_NAME):
    """
    Accumulator for delimited files

    Combines each file with values from JSON dictionary in same directory

    :param iterable delimited_files: Iterable of delimited files
    :param keys: List of keys to select from JSON dictionary. If ``None``, keep
                 all keys.
    :param separator: Delimiter
    """
    for f in delimited_files:
        dn = os.path.dirname(f)
        with open(os.path.join(dn, control_name)) as fp:
            control = _ordered_load(fp)

        keys = keys if keys is not None else control.keys()

        with open(f) as fp:
            reader = csv.DictReader(fp, delimiter=separator)
            for row in reader:
                row_dict = collections.OrderedDict(itertools.chain(
                        ((k, row[k]) for k in reader.fieldnames),
                        ((k, v) for k, v in control.items() if k in keys))
                )

                yield row_dict

def delim(arguments):
    """
    Execute delim action.

    :param arguments: Parsed command line arguments from :func:`main`
    """
    with arguments.output as fp:
        results = _delim_accum(arguments.delimited_files, arguments.keys,
                               arguments.separator)
        r = next(results)
        writer = csv.DictWriter(fp, r.keys(), delimiter=arguments.separator)
        writer.writeheader()
        writer.writerow(r)
        writer.writerows(results)

def main(args=sys.argv[1:]):
    """
    Command-line interface for nestagg
    """
    parser = argparse.ArgumentParser(description="""Accumulate results of
            nestly runs""")
    subparsers = parser.add_subparsers()
    delim_parser = subparsers.add_parser('delim', help="""Combine control files
            with delimited files.""")
    delim_parser.set_defaults(func=delim)
    delim_parser.add_argument('-k', '--keys', help="""Comma separated list of
            keys from the JSON file to include [default: all keys]""")
    #delim_parser.add_argument('-d', '--directory',
        #help="""Directory to search for control.json files""")
    delim_parser.add_argument('delimited_files', metavar="delim_file",
            help="""Delimited file(s) to combine. A control.json file must be
            present in each directory""", nargs="+")
    delim_parser.add_argument('-s', '--separator', default=DEFAULT_SEP,
            help="""Separator [default: %(default)s]""")
    delim_parser.add_argument('-t', '--tab', action='store_const',
            dest='separator', const='\t', help="""Files are tab-separated""")
    delim_parser.add_argument('-o', '--output', default=sys.stdout,
        type=argparse.FileType('w'), help="""Output file [default: stdout]""")

    arguments = parser.parse_args()

    arguments.func(arguments)
