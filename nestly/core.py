"""
Core functions for building nests.
"""

import collections
import errno
import functools
import itertools
import json
import os
import os.path
import sys
import warnings

# Load a JSON file into an ordered dict
ordered_load = functools.partial(json.load,
        object_pairs_hook=collections.OrderedDict)

def stripext(path):
    """
    Return the basename, minus extension, of a path.

    :param string path: Path to file
    """
    return os.path.basename(os.path.splitext(path)[0])

def _mkdirs(d):
    """
    Make all directories up to d.

    No exception is raised if d exists.
    """
    try:
        os.makedirs(d)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

_Nestable = collections.namedtuple('Nestable', ('name', 'nestable',
                                               'create_dir', 'update',
                                               'label_func'))

def _is_iter(iterable):
    """
    Returns whether an item is iterable or not
    """
    try:
        iter(iterable)
        return True
    except TypeError:
        return False

def _repeat_iter(iterable):
    def repeat_iter(ctl):
        return iterable
    return repeat_iter

def _templated(fn):
    """
    Returns a function which applies ``str.format(**ctl)`` to all results of
    ``fn(ctl)``.
    """
    @functools.wraps(fn)
    def inner(ctl):
        return [i.format(**ctl) for i in fn(ctl)]
    return inner

class Nest(object):
    """
    Nests are used to build nested parameter selections, culminating in a
    directory structure representing choices made, and a JSON dictionary with
    all selections.

    Build parameter combinations with :meth:`Nest.add`, then create a nested
    directory structure with :meth:`Nest.build`.

    :param control_name: Name JSON file to be created in each leaf
    :param indent: Indentation level in json file
    :param fail_on_clash: Error if a nest level attempts to overwrite a
        previous value
    :param warn_on_clash: Print a warning if a nest level attempts ot overwrite
        a previous value
    :param base_dict: Base dictionary to start all control dictionaries from
        (default: ``{}``)
    """
    def __init__(self, control_name="control.json", indent=2,
            fail_on_clash=False, warn_on_clash=True, base_dict=None):
        self.control_name = control_name
        self.indent = indent
        self.fail_on_clash = fail_on_clash
        self.warn_on_clash = warn_on_clash
        self._levels = []
        self.base_dict = base_dict or collections.OrderedDict()

    def iter(self, root=None):
        """
        Create an iterator of (directory, control_dict) tuples for all valid
        parameter choices in this :class:`Nest`.

        :param root: Root directory
        :rtype: Generator of ``(directory, control_dictionary)`` tuples.
        """
        def inner(control, nestables, dirs=None):
            #FIXME: This is messy
            if not dirs:
                dirs = []
            if nestables:
                # Still more nestables to consume.
                n = nestables[0]

                result = n.nestable(control)

                for r in result:
                    ctl = control.copy()
                    if n.update:
                        # Make sure expected key exists
                        if not n.name in r:
                            raise KeyError("Missing key for {0}".format(n.name))

                        # Check for collisions
                        u = frozenset(control.keys()) & frozenset(r.keys())
                        if u:
                            if self.fail_on_clash:
                                raise KeyError("Key overlap: {0}".format(u))
                            elif self.warn_on_clash:
                                #FIXME: Something better here
                                print >>sys.stderr, "Key overlap:", u
                        ctl.update(r)

                        # For directory making below
                        r = r[n.name]
                    else:
                        ctl[n.name] = r

                    new_dirs = (dirs + [n.label_func(r)] if n.create_dir
                                else dirs[:])
                    for d, c in inner(ctl, nestables[1:], new_dirs):
                        yield d, c
            else:
                # At leaf node
                yield os.path.join(root or '', *dirs), control

        return inner(self.base_dict, self._levels[:])

    def __iter__(self):
        """
        Iterate over directory, control pairs. Same as :meth:`Nest.iter`.
        """
        return self.iter()

    def build(self, root="runs"):
        """
        Build a nested directory structure, starting in ``root``

        :param root: Root directory for structure
        """

        for d, control in self.iter(root):
            _mkdirs(d)
            with open(os.path.join(d, self.control_name), 'w') as fp:
                json.dump(control, fp, indent=self.indent)
                # RJSON and some other tools like a trailing newline
                fp.write('\n')

    def add(self, name, nestable, create_dir=True, update=False,
            label_func=str, template_subs=False):
        """
        Add a level to the nest

        :param string name: Name of the level. Forms the key in the output
            dictionary.
        :param nestable: Either an iterable object containing values, _or_ a
            function which takes a single argument (the control dictionary)
            and returns an iterable object containing values
        :param boolean create_dir: Should a directory level be created for this
            nestable?
        :param boolean update: Should the control dictionary be updated with
            the results of each value returned by the nestable? Only valid for
            dictionary results; useful for updating multiple values. At a
            minimum, a key-value pair corresponding to ``name`` must be
            returned.
        :param label_func: Function to be called to convert each value to a
            directory label.
        :param boolean template_subs: Should the strings in / returned by
            nestable be treated as templates? If true, str.format is called
            with the current values of the control dictionary.
        """
        # Convert everything to functions
        if not callable(nestable):
            if not _is_iter(nestable):
                raise ValueError("Invalid nestable: " + str(nestable))
            if isinstance(nestable, basestring):
                warnings.warn(
                        "Passed a string as an iterable for name {0}".format(name))
            old_nestable = nestable
            nestable = _repeat_iter(old_nestable)
        if template_subs:
            nestable = _templated(nestable)
        self._levels.append(_Nestable(name, nestable, create_dir, update,
                                      label_func))

def nest_map(control_iter, map_fn):
    """
    Aggregate over a nest.

    For each control file in control_iter, map_fn is called with the directory
    and control file contents as arguments.

    Example::

        >>> list(nest_map(['run1/control.json', 'run2/control.json'],
        ...     lambda d, c: c['run_id']))
        [1, 2]

    :param control_iter: Iterable of paths to JSON control files
    :param function map_fn: Function to run for each control file. Passed as
            arguments the directory of the control file and its json-decoded
            contents.
    """
    def fn(control_path):
        """
        Read the control file, return the result of calling map_fn
        """
        with open(control_path) as fp:
            control = ordered_load(fp)
        dn = os.path.dirname(control_path)
        return map_fn(dn, control)

    mapped = itertools.imap(fn, control_iter)
    return mapped
